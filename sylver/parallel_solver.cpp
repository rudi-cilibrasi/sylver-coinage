// Parallel discovery engine: the exact recurrence of native_solver.cpp,
// searched by several threads that share one memo.
//
// Every thread runs the same depth-first recurrence from the root. Near the
// root (depth below --split-depth) a thread defers a child that another
// thread is already searching and returns to it after its other children
// (ABDADA-style), so threads spread over different subtrees; a thread that
// finds a node already decided by another thread returns that result. Deeper
// nodes are searched exactly as in native_solver.cpp. Memo entries are only
// ever exact results, so outcomes are exact; a reported winning move is a
// winning move, but with more than one thread it need not be the one the
// sequential engines report, and the state count (distinct memoized states)
// varies from run to run. With --threads 1 the search, its winning move,
// and its state count are those of native_solver.cpp.
//
// The memo is split into shards, each an open-addressing table with its own
// lock, so a table grows one shard at a time instead of briefly holding two
// copies of the whole memo. Discovery only: published replays and the arena
// verifier keep using native_solver.cpp.
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <limits>
#include <memory>
#include <mutex>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#if defined(__GLIBC__)
#include <malloc.h>
#endif

namespace {

#ifndef SYLVER_NATIVE_WORDS
#define SYLVER_NATIVE_WORDS 8
#endif

constexpr int kWords = SYLVER_NATIVE_WORDS;
static_assert(kWords > 0, "SYLVER_NATIVE_WORDS must be positive");
constexpr int kMaximumFrobenius = 64 * kWords - 1;
constexpr int kAborted = -1;  // the root was decided elsewhere; nothing below is recorded

struct State {
    std::array<std::uint64_t, kWords> words{};

    bool operator==(const State&) const = default;

    [[nodiscard]] bool test(int bit) const {
        return (words.at(static_cast<std::size_t>(bit / 64)) >> (bit % 64)) & 1U;
    }

    void set(int bit) {
        words.at(static_cast<std::size_t>(bit / 64)) |=
            std::uint64_t{1} << (bit % 64);
    }
};

struct StateHash {
    [[nodiscard]] std::size_t operator()(const State& state) const noexcept {
        std::uint64_t hash = 0x9e3779b97f4a7c15ULL;
        for (const std::uint64_t word : state.words) {
            std::uint64_t mixed = word + 0x9e3779b97f4a7c15ULL;
            mixed = (mixed ^ (mixed >> 30)) * 0xbf58476d1ce4e5b9ULL;
            mixed = (mixed ^ (mixed >> 27)) * 0x94d049bb133111ebULL;
            mixed ^= mixed >> 31;
            hash ^= mixed + 0x9e3779b97f4a7c15ULL + (hash << 6) + (hash >> 2);
        }
        return static_cast<std::size_t>(hash);
    }
};

class SpinLock {
  public:
    void lock() noexcept {
        while (flag_.test_and_set(std::memory_order_acquire)) {
            while (flag_.test(std::memory_order_relaxed)) {
#if defined(__x86_64__) || defined(__i386__)
                __builtin_ia32_pause();
#endif
            }
        }
    }
    void unlock() noexcept { flag_.clear(std::memory_order_release); }

  private:
    std::atomic_flag flag_;
};

// The flat memo of fast_solver.cpp, split into independently locked shards
// chosen by the top bits of the hash. Every semigroup state contains 0, so
// the all-zero state marks an empty slot; a key is never stored twice and a
// stored value is never overwritten.
class ShardedMemo {
  public:
    static constexpr int kShardBits = 12;

    [[nodiscard]] int lookup(const State& state, std::size_t hash) {
        Shard& shard = shard_for(hash);
        std::lock_guard guard(shard.lock);
        for (std::size_t slot = hash & shard.mask;; slot = (slot + 1) & shard.mask) {
            const State& key = shard.keys[slot];
            if (key.words[0] == 0) return -1;
            if (key == state) return shard.values[slot];
        }
    }

    void insert(const State& state, std::size_t hash, std::uint16_t value) {
        Shard& shard = shard_for(hash);
        std::lock_guard guard(shard.lock);
        if ((shard.count + 1) * 4 > shard.keys.size() * 3) shard.grow();
        std::size_t slot = hash & shard.mask;
        for (; shard.keys[slot].words[0] != 0; slot = (slot + 1) & shard.mask) {
            if (shard.keys[slot] == state) return;
        }
        shard.keys[slot] = state;
        shard.values[slot] = value;
        ++shard.count;
    }

    [[nodiscard]] std::size_t size() {
        std::size_t total = 0;
        for (Shard& shard : shards_) {
            std::lock_guard guard(shard.lock);
            total += shard.count;
        }
        return total;
    }

  private:
    struct alignas(64) Shard {
        SpinLock lock;
        std::vector<State> keys = std::vector<State>(16);
        std::vector<std::uint16_t> values = std::vector<std::uint16_t>(16);
        std::size_t mask = 15;
        std::size_t count = 0;

        void grow() {
            const std::size_t capacity = keys.size() * 2;
            std::vector<State> new_keys(capacity);
            std::vector<std::uint16_t> new_values(capacity);
            const std::size_t new_mask = capacity - 1;
            for (std::size_t i = 0; i < keys.size(); ++i) {
                if (keys[i].words[0] == 0) continue;
                std::size_t slot = StateHash{}(keys[i]) & new_mask;
                while (new_keys[slot].words[0] != 0) slot = (slot + 1) & new_mask;
                new_keys[slot] = keys[i];
                new_values[slot] = values[i];
            }
            keys.swap(new_keys);
            values.swap(new_values);
            mask = new_mask;
        }
    };

    Shard& shard_for(std::size_t hash) {
        return shards_[hash >> (std::numeric_limits<std::size_t>::digits - kShardBits)];
    }

    std::vector<Shard> shards_ = std::vector<Shard>(std::size_t{1} << kShardBits);
};

// How many threads are searching each (hashed) state near the root. A
// collision only defers a child that nobody is searching, which costs order,
// never correctness.
class BusyTable {
  public:
    static constexpr std::size_t kSize = std::size_t{1} << 20;

    [[nodiscard]] bool busy(std::size_t hash) const {
        return counters_[index(hash)].load(std::memory_order_relaxed) != 0;
    }
    void enter(std::size_t hash) { counters_[index(hash)].fetch_add(1, std::memory_order_relaxed); }
    void leave(std::size_t hash) { counters_[index(hash)].fetch_sub(1, std::memory_order_relaxed); }

  private:
    static std::size_t index(std::size_t hash) { return (hash >> 20) & (kSize - 1); }
    std::unique_ptr<std::atomic<std::uint32_t>[]> counters_ =
        std::make_unique<std::atomic<std::uint32_t>[]>(kSize);
};

[[nodiscard]] State shifted_left(const State& state, int shift) {
    State result;
    const int word_shift = shift / 64;
    const int bit_shift = shift % 64;
    for (int destination = kWords - 1; destination >= word_shift; --destination) {
        const int source = destination - word_shift;
        result.words[static_cast<std::size_t>(destination)] |=
            state.words[static_cast<std::size_t>(source)] << bit_shift;
        if (bit_shift != 0 && source > 0) {
            result.words[static_cast<std::size_t>(destination)] |=
                state.words[static_cast<std::size_t>(source - 1)] >>
                (64 - bit_shift);
        }
    }
    return result;
}

[[nodiscard]] int frobenius_number(const std::vector<int>& generators) {
    const int modulus = generators.front();
    constexpr std::int64_t infinity = std::numeric_limits<std::int64_t>::max();
    std::vector<std::int64_t> distance(static_cast<std::size_t>(modulus), infinity);
    using QueueEntry = std::pair<std::int64_t, int>;
    std::priority_queue<QueueEntry, std::vector<QueueEntry>, std::greater<>> queue;
    distance[0] = 0;
    queue.emplace(0, 0);
    while (!queue.empty()) {
        const auto [value, residue] = queue.top();
        queue.pop();
        if (value != distance[static_cast<std::size_t>(residue)]) {
            continue;
        }
        for (const int generator : generators) {
            const std::int64_t candidate = value + generator;
            const int next_residue = static_cast<int>(candidate % modulus);
            if (candidate < distance[static_cast<std::size_t>(next_residue)]) {
                distance[static_cast<std::size_t>(next_residue)] = candidate;
                queue.emplace(candidate, next_residue);
            }
        }
    }
    return static_cast<int>(*std::max_element(distance.begin(), distance.end())) - modulus;
}

class Solver {
  public:
    Solver(const std::vector<int>& generators, int frobenius, int threads, int split_depth)
        : frobenius_(frobenius), threads_(threads), split_depth_(threads > 1 ? split_depth : 0),
          mask_(make_mask()) {
        root_.set(0);
        for (const int generator : generators) {
            root_ = adjoin(root_, generator);
        }
    }

    // Winning move of the root, or 0 when it is a P-position.
    [[nodiscard]] int solve() {
        std::vector<std::thread> helpers;
        std::vector<std::exception_ptr> errors(static_cast<std::size_t>(threads_));
        auto run = [this, &errors](int index) {
            try {
                if (search(root_, StateHash{}(root_), 0) != kAborted) {
                    done_.store(true, std::memory_order_relaxed);
                }
            } catch (...) {
                errors[static_cast<std::size_t>(index)] = std::current_exception();
                done_.store(true, std::memory_order_relaxed);
            }
        };
        for (int index = 1; index < threads_; ++index) helpers.emplace_back(run, index);
        run(0);
        for (std::thread& helper : helpers) helper.join();
        for (const std::exception_ptr& error : errors) {
            if (error) std::rethrow_exception(error);
        }
        const int result = memo_.lookup(root_, StateHash{}(root_));
        if (result < 0) throw std::logic_error("the root was not decided");
        return result;
    }

    [[nodiscard]] std::size_t states_evaluated() { return memo_.size(); }

  private:
    [[nodiscard]] State make_mask() const {
        State mask;
        for (int bit = 0; bit <= frobenius_; ++bit) {
            mask.set(bit);
        }
        return mask;
    }

    [[nodiscard]] State adjoin(State state, int move) const {
        for (int shift = move; shift <= frobenius_;) {
            const State shifted = shifted_left(state, shift);
            for (int word = 0; word < kWords; ++word) {
                state.words[static_cast<std::size_t>(word)] |=
                    shifted.words[static_cast<std::size_t>(word)] &
                    mask_.words[static_cast<std::size_t>(word)];
            }
            if (shift > frobenius_ / 2) {
                break;
            }
            shift *= 2;
        }
        return state;
    }

    // Winning move of ``state`` (0 when it is a P-position), or kAborted.
    [[nodiscard]] int search(const State& state, std::size_t hash, int depth) {
        if (done_.load(std::memory_order_relaxed)) return kAborted;
        if (const int found = memo_.lookup(state, hash); found >= 0) {
            return found;
        }
        State paired_losers;
        if (depth >= split_depth_) {
            // The sequential recurrence of native_solver.cpp.
            for (int move = 2; move <= frobenius_; ++move) {
                if (state.test(move) || paired_losers.test(move)) {
                    continue;
                }
                const State child = adjoin(state, move);
                const int response = search(child, StateHash{}(child), depth + 1);
                if (response == kAborted) return kAborted;
                if (response == 0) {
                    memo_.insert(state, hash, static_cast<std::uint16_t>(move));
                    return move;
                }
                if (response > move) {
                    paired_losers.set(response);
                }
            }
            memo_.insert(state, hash, std::uint16_t{0});
            return 0;
        }
        // Near the root: the same recurrence in two passes. The first defers
        // children another thread is searching; the second searches them
        // (by then usually decided). A move is skipped only when it is
        // illegal or a paired loser (its child is N: the reply that beat the
        // smaller move beats it too), so every legal move is accounted for.
        std::vector<int> deferred;
        for (int pass = 0; pass < 2; ++pass) {
            std::vector<int> moves;
            if (pass == 0) {
                for (int move = 2; move <= frobenius_; ++move) moves.push_back(move);
            } else {
                moves.swap(deferred);
            }
            for (const int move : moves) {
                if (state.test(move) || paired_losers.test(move)) {
                    continue;
                }
                const State child = adjoin(state, move);
                const std::size_t child_hash = StateHash{}(child);
                int response = memo_.lookup(child, child_hash);
                if (response < 0) {
                    if (pass == 0 && busy_.busy(child_hash)) {
                        deferred.push_back(move);
                        continue;
                    }
                    busy_.enter(child_hash);
                    response = search(child, child_hash, depth + 1);
                    busy_.leave(child_hash);
                }
                if (response == kAborted) return kAborted;
                if (response == 0) {
                    memo_.insert(state, hash, static_cast<std::uint16_t>(move));
                    return move;
                }
                if (response > move) {
                    paired_losers.set(response);
                }
                if (const int found = memo_.lookup(state, hash); found >= 0) {
                    return found;  // decided by another thread meanwhile
                }
            }
        }
        memo_.insert(state, hash, std::uint16_t{0});
        return 0;
    }

    int frobenius_;
    int threads_;
    int split_depth_;
    State mask_;
    State root_;
    ShardedMemo memo_;
    BusyTable busy_;
    std::atomic<bool> done_{false};
};

[[nodiscard]] int parse_int_option(const std::string& name, const std::string& text, int low, int high) {
    std::size_t used = 0;
    const long value = std::stol(text, &used);
    if (used != text.size() || value < low || value > high) {
        throw std::invalid_argument(name + " must be an integer in [" + std::to_string(low) + ", " +
                                    std::to_string(high) + "]");
    }
    return static_cast<int>(value);
}

}  // namespace

int main(int argc, char** argv) {
#if defined(__GLIBC__)
    // Shard tables are large, short-lived allocations made by every thread:
    // map them directly (returned to the system when a shard grows) and keep
    // per-thread malloc arenas from reserving address space, which the
    // discovery scans cap with RLIMIT_AS.
    mallopt(M_MMAP_THRESHOLD, 64 * 1024);
    mallopt(M_ARENA_MAX, 2);
#endif
    try {
        int threads = static_cast<int>(std::max(1U, std::thread::hardware_concurrency()));
        int split_depth = 6;
        int first = 1;
        while (first + 1 < argc && std::string(argv[first]).rfind("--", 0) == 0) {
            const std::string option = argv[first];
            if (option == "--threads") {
                threads = parse_int_option(option, argv[first + 1], 1, 1024);
            } else if (option == "--split-depth") {
                split_depth = parse_int_option(option, argv[first + 1], 0, 1000);
            } else {
                throw std::invalid_argument("unknown option " + option);
            }
            first += 2;
        }
        if (argc <= first) {
            throw std::invalid_argument(
                "usage: parallel_solver [--threads N] [--split-depth D] GENERATOR...");
        }
        std::vector<int> generators;
        for (int index = first; index < argc; ++index) {
            const long value = std::stol(argv[index]);
            if (value < 2 || value > std::numeric_limits<int>::max()) {
                throw std::invalid_argument("generators must be integers greater than one");
            }
            generators.push_back(static_cast<int>(value));
        }
        std::sort(generators.begin(), generators.end());
        generators.erase(std::unique(generators.begin(), generators.end()), generators.end());
        if (std::accumulate(generators.begin() + 1, generators.end(), generators.front(),
                            [](int left, int right) { return std::gcd(left, right); }) != 1) {
            throw std::invalid_argument("exact evaluation requires generators with gcd one");
        }
        const int frobenius = frobenius_number(generators);
        if (frobenius > kMaximumFrobenius) {
            throw std::invalid_argument(
                "Frobenius number exceeds native limit " +
                std::to_string(kMaximumFrobenius)
            );
        }
        Solver solver(generators, frobenius, threads, split_depth);
        const int move = solver.solve();
        std::cout << (move == 0 ? "P" : "N") << " winning_move=";
        if (move == 0) {
            std::cout << "none";
        } else {
            std::cout << move;
        }
        std::cout << " frobenius=" << frobenius
                  << " states=" << solver.states_evaluated() << '\n';
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "parallel_solver: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
