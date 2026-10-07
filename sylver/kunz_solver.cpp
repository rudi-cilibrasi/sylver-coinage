// Kunz-coordinate discovery engine: the exact recurrence of native_solver.cpp
// and parallel_solver.cpp, searched by several threads that share one memo,
// with every state held as its Kunz coordinates instead of a bitset.
//
// Every reachable state contains the root's smallest generator m (at most
// 16), so a state S is determined by its Apery set with respect to m: the
// least element w_i of S in each residue class i mod m. The engine keeps the
// Kunz coordinates k_i = (w_i - i) / m, the number of gaps of S congruent to
// i, one byte per residue in a 16-byte vector (k_0 = 0; lanes from m on are
// 0). Then
//
//   * n is a gap of S exactly when n / m < k_{n mod m};
//   * S + Nn = S + {0, ..., m-1}n, since m*n is already in S, so adjoining a
//     move n is the min-plus update "w <- min(w, w + d)" for d = n, 2n, 4n,
//     8n (as many doublings as m needs): a byte shuffle, an add and a min;
//   * the vector itself is the memo key.
//
// A memo slot is that vector, with its value folded into bits no coordinate
// uses, plus a one-byte fingerprint: 17 bytes, where parallel_solver.cpp's
// slots take 8 bytes per 64 of the root's gaps plus 2 (66 bytes in the
// X={16,26,82,88} sweeps near reply 683).
//
// Threads, --odd-range/--odd-list sweeps, --stop-at-p and --verify-memo work
// as in parallel_solver.cpp, and with --threads 1 the output is
// native_solver.cpp's, state count included. A sweep can also end early at a
// row boundary (--max-states, --stop-file) and still verify its memo. --verify-memo also checks that
// every key is the Kunz vector of a numerical semigroup containing the root.
// The root's smallest generator must be at most 16 and every coordinate at
// most 127, so the Frobenius bound is below 127m (2031 for m = 16) and at most
// 2047. Discovery only: published replays and the arena verifier keep using
// native_solver.cpp.

#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <memory>
#include <mutex>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <string>
#include <system_error>
#include <thread>
#include <utility>
#include <vector>

#if defined(__GLIBC__)
#include <malloc.h>
#endif

namespace {

constexpr int kLanes = 16;               // residues mod m, one byte each
constexpr int kMaximumCoordinate = 127;  // a coordinate byte's top bit may hold memo value bits
constexpr int kMaximumBound = 2047;      // moves fit 15 value bits; paired-loser sets hold 2048 bits
constexpr int kAborted = -2;             // the root was decided elsewhere; nothing below is recorded

using Lanes = std::uint8_t __attribute__((vector_size(kLanes)));

// A state's Kunz coordinates with respect to the root's smallest generator.
struct State {
    Lanes k{};
};

// A memo key: the 16 coordinate bytes as two words.
struct Key {
    std::uint64_t low = 0;
    std::uint64_t high = 0;

    bool operator==(const Key&) const = default;
};

[[nodiscard]] Key key_of(const State& state) noexcept { return std::bit_cast<Key>(state.k); }

[[nodiscard]] State state_of(const Key& key) noexcept { return State{std::bit_cast<Lanes>(key)}; }

[[nodiscard]] std::uint64_t mix(std::uint64_t value) noexcept {
    value += 0x9e3779b97f4a7c15ULL;
    value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31);
}

[[nodiscard]] std::size_t hash_key(const Key& key) noexcept {
    return static_cast<std::size_t>(mix(key.low ^ mix(key.high)));
}

// A memo value (0 for P, else the winning move, below 2^15) is stored in lane
// 0's byte (value bits 0-7) and the top bits of lanes 1-7 (bits 8-14), which
// no key uses: k_0 = 0 and every coordinate is at most 127.
constexpr std::uint64_t kKeyBitsLow = 0x7F7F7F7F7F7F7F00ULL;

[[nodiscard]] std::uint64_t with_value(std::uint64_t low, int value) noexcept {
    const auto bits = static_cast<std::uint64_t>(value);
    low |= bits & 0xFFU;
    for (int bit = 0; bit < 7; ++bit) low |= ((bits >> (8 + bit)) & 1U) << (15 + 8 * bit);
    return low;
}

[[nodiscard]] int value_in(std::uint64_t low) noexcept {
    std::uint64_t bits = low & 0xFFU;
    for (int bit = 0; bit < 7; ++bit) bits |= ((low >> (15 + 8 * bit)) & 1U) << (8 + bit);
    return static_cast<int>(bits);
}

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

// Open-addressing memo split into independently locked shards chosen by the
// top bits of the hash. A slot holds a key with its value folded in, and a
// one-byte tag: kEmpty for a free slot, else a fingerprint of the hash, so a
// probe reads a key only when the fingerprint matches. A shard is filled to
// at most 7/8 and then grows by half. Initial capacities are staggered
// log-uniformly over one growth step, so the shards grow at different times
// and the memo holds about 1.41 slots per entry (24 bytes) at every size
// instead of jumping by half at once. A key is never stored twice and a
// stored value is never overwritten.
class ShardedMemo {
  public:
    static constexpr int kShardBits = 12;
    static constexpr std::size_t kShards = std::size_t{1} << kShardBits;
    static constexpr std::uint8_t kEmpty = 0;   // fingerprints run from 1 to 255

    ShardedMemo() {
        for (std::size_t index = 0; index < kShards; ++index) {
            const double stagger = std::pow(1.5, static_cast<double>(index) / static_cast<double>(kShards));
            shards_[index].resize(static_cast<std::size_t>(64.0 * stagger));
        }
    }

    [[nodiscard]] int lookup(const Key& key, std::size_t hash) {
        Shard& shard = shard_for(hash);
        const std::uint8_t print = fingerprint(hash);
        std::lock_guard guard(shard.lock);
        const std::size_t capacity = shard.tags.size();
        for (std::size_t slot = home(hash, capacity);; slot = next(slot, capacity)) {
            const std::uint8_t tag = shard.tags[slot];
            if (tag == kEmpty) return -1;
            if (tag == print && shard.holds(slot, key)) return value_in(shard.slots[slot].low);
        }
    }

    void insert(const Key& key, std::size_t hash, int value) {
        Shard& shard = shard_for(hash);
        const std::uint8_t print = fingerprint(hash);
        std::lock_guard guard(shard.lock);
        if ((shard.count + 1) * 8 > shard.tags.size() * 7) shard.grow();
        const std::size_t capacity = shard.tags.size();
        std::size_t slot = home(hash, capacity);
        for (; shard.tags[slot] != kEmpty; slot = next(slot, capacity)) {
            if (shard.tags[slot] == print && shard.holds(slot, key)) return;
        }
        shard.slots[slot] = Slot{with_value(key.low, value), key.high};
        shard.tags[slot] = print;
        ++shard.count;
    }

#ifdef SYLVER_KUNZ_TEST_FORGE_MOVE_ONE
    void overwrite(const Key& key, std::size_t hash, int value) {
        insert(key, hash, value);
        Shard& shard = shard_for(hash);
        const std::size_t capacity = shard.tags.size();
        for (std::size_t slot = home(hash, capacity);; slot = next(slot, capacity)) {
            if (shard.tags[slot] != kEmpty && shard.holds(slot, key)) {
                shard.slots[slot].low = with_value(key.low, value);
                return;
            }
        }
    }
#endif

    // Calls f(key, value) for every entry of shard ``index``. Only for use
    // after every search thread has finished.
    template <class F>
    void for_each_in_shard(std::size_t index, F&& f) const {
        const Shard& shard = shards_[index];
        for (std::size_t slot = 0; slot < shard.tags.size(); ++slot) {
            if (shard.tags[slot] == kEmpty) continue;
            f(Key{shard.slots[slot].low & kKeyBitsLow, shard.slots[slot].high}, value_in(shard.slots[slot].low));
        }
    }

    [[nodiscard]] std::size_t size() {
        std::size_t total = 0;
        for (Shard& shard : shards_) {
            std::lock_guard guard(shard.lock);
            total += shard.count;
        }
        return total;
    }

    // Slots and bytes held by the tables (after every search thread has finished).
    [[nodiscard]] std::pair<std::size_t, std::size_t> footprint() const {
        std::size_t slots = 0;
        for (const Shard& shard : shards_) slots += shard.tags.size();
        return {slots, slots * (sizeof(Slot) + 1)};
    }

  private:
    struct Slot {
        std::uint64_t low;
        std::uint64_t high;
    };

    // Bits 32-51 of the hash (the shard uses the top 12, the slot the low 32), as 1-255.
    static std::uint8_t fingerprint(std::size_t hash) {
        return static_cast<std::uint8_t>(1 + ((hash >> 32) & 0xFFFFF) % 255);
    }
    // A slot in [0, capacity) from the low 32 bits of the hash (multiply-shift).
    static std::size_t home(std::size_t hash, std::size_t capacity) {
        return static_cast<std::size_t>((static_cast<std::uint64_t>(static_cast<std::uint32_t>(hash)) * capacity) >> 32);
    }
    static std::size_t next(std::size_t slot, std::size_t capacity) { return slot + 1 == capacity ? 0 : slot + 1; }

    struct alignas(64) Shard {
        SpinLock lock;
        std::vector<Slot> slots;
        std::vector<std::uint8_t> tags;
        std::size_t count = 0;

        void resize(std::size_t capacity) {
            slots.assign(capacity, Slot{0, 0});
            tags.assign(capacity, kEmpty);
        }

        [[nodiscard]] bool holds(std::size_t slot, const Key& key) const {
            return (slots[slot].low & kKeyBitsLow) == key.low && slots[slot].high == key.high;
        }

        void grow() {
            std::vector<Slot> old_slots;
            std::vector<std::uint8_t> old_tags;
            old_slots.swap(slots);
            old_tags.swap(tags);
            const std::size_t capacity = old_tags.size() + old_tags.size() / 2;
            resize(capacity);
            for (std::size_t i = 0; i < old_tags.size(); ++i) {
                if (old_tags[i] == kEmpty) continue;
                const Key key{old_slots[i].low & kKeyBitsLow, old_slots[i].high};
                std::size_t slot = home(hash_key(key), capacity);
                while (tags[slot] != kEmpty) slot = next(slot, capacity);
                slots[slot] = old_slots[i];
                tags[slot] = old_tags[i];   // the fingerprint depends only on the key's hash
            }
        }
    };

    Shard& shard_for(std::size_t hash) {
        return shards_[hash >> (std::numeric_limits<std::size_t>::digits - kShardBits)];
    }

    std::vector<Shard> shards_ = std::vector<Shard>(kShards);
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

// A set of moves up to kMaximumBound (the paired losers of one search frame).
class MoveSet {
  public:
    explicit MoveSet(int words) {
        std::fill_n(words_.begin(), words, std::uint64_t{0});
    }
    [[nodiscard]] bool test(int move) const {
        return (words_[static_cast<std::size_t>(move / 64)] >> (move % 64)) & 1U;
    }
    void set(int move) { words_[static_cast<std::size_t>(move / 64)] |= std::uint64_t{1} << (move % 64); }

  private:
    std::array<std::uint64_t, (kMaximumBound + 1) / 64> words_;   // only the first ``words`` are used
};

// Frobenius number of a gcd-one generator set (int64: huge generators must
// fail the limit check rather than overflow).
[[nodiscard]] std::int64_t frobenius_number(const std::vector<int>& generators) {
    const int modulus = generators.front();
    // Every positive integer below the smallest generator is a gap, so F is
    // at least modulus - 1: past the limit, return that bound rather than
    // allocate a table of that size.
    if (modulus - 1 > kMaximumBound) return modulus - 1;
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
    return *std::max_element(distance.begin(), distance.end()) - modulus;
}

class Solver {
  public:
    // ``generators`` sorted ascending; ``bound`` is at least the Frobenius
    // number of every state to be solved (each then has gcd one).
    Solver(const std::vector<int>& generators, int bound, int threads, int split_depth)
        : modulus_(generators.front()), bound_(bound), threads_(threads),
          split_depth_(threads > 1 ? split_depth : 0) {
        if (modulus_ > kLanes) {
            throw std::invalid_argument("the smallest generator must be at most " + std::to_string(kLanes));
        }
        if (bound_ > kMaximumBound) {
            throw std::invalid_argument("Frobenius bound exceeds the Kunz engine's limit " +
                                        std::to_string(kMaximumBound));
        }
        while ((1 << steps_) < modulus_) ++steps_;
        for (int lane = 0; lane < kLanes; ++lane) {
            lanes_[lane] = lane < modulus_ ? 0xFF : 0;
        }
        for (int residue = 0; residue < modulus_; ++residue) {
            for (int lane = 0; lane < kLanes; ++lane) {
                // Lane i receives residue (i - d) mod m; lanes from m on stay 0
                // whatever they receive, since their additions are 0 and min keeps 0.
                rotations_[static_cast<std::size_t>(residue)][lane] =
                    static_cast<std::uint8_t>(lane < modulus_ ? (lane - residue + modulus_) % modulus_ : lane);
                carries_[static_cast<std::size_t>(residue)][lane] = lane < residue ? 1 : 0;
            }
        }
        // The multiples of m and every number above the bound, then the
        // other generators.
        for (int lane = 1; lane < modulus_; ++lane) {
            const int gaps = lane <= bound_ ? (bound_ - lane) / modulus_ + 1 : 0;
            if (gaps > kMaximumCoordinate) {
                throw std::invalid_argument("Frobenius bound " + std::to_string(bound_) +
                                            " needs a Kunz coordinate above " +
                                            std::to_string(kMaximumCoordinate) + " for modulus " +
                                            std::to_string(modulus_));
            }
            root_.k[lane] = static_cast<std::uint8_t>(gaps);
        }
        for (const int generator : generators) {
            root_ = adjoin(root_, generator);
        }
    }

    // Winning move of the root, or 0 when it is a P-position.
    [[nodiscard]] int solve() { return solve_from(root_); }

    // The same for the root with ``move`` adjoined. Successive calls share
    // the memo, like native_solver.cpp's odd-range scans.
    [[nodiscard]] int solve_after_adjoining(int move) { return solve_from(adjoin(root_, move)); }

    [[nodiscard]] std::size_t states_evaluated() { return memo_.size(); }

    [[nodiscard]] std::pair<std::size_t, std::size_t> memo_footprint() const { return memo_.footprint(); }

#ifdef SYLVER_KUNZ_TEST_FORGE_MOVE_ONE
    // Test-only forgery that --verify-memo must reject: the root "wins" by
    // naming 1, whose child (every integer, all coordinates 0) is recorded as P.
    void forge_move_one() {
        const Key root_key = key_of(root_);
        memo_.overwrite(root_key, hash_key(root_key), 1);
        const Key all_key{};
        memo_.overwrite(all_key, hash_key(all_key), 0);
    }
#endif

#ifdef SYLVER_KUNZ_TEST_FORGE_KEY
    // Test-only forgery that --verify-memo must reject: a P entry whose key is
    // not the Kunz vector of a semigroup (the root's, with 1 made an element
    // though 1 + 1 = 2 is not).
    void forge_key() {
        State forged = root_;
        forged.k[1] = 0;
        const Key key = key_of(forged);
        memo_.insert(key, hash_key(key), 0);
    }
#endif

    // Checks the finished memo as a certificate: every key must be the Kunz
    // vector of a numerical semigroup containing the root; an N entry must
    // name a legal move whose child is memoized P; and every legal move m of
    // a P entry S must lead to a child memoized N or be a paired loser (a
    // smaller legal move m' with S+m'+m memoized P: m' answers m). By
    // induction on the number of gaps, every entry, and so every reported
    // root, is then exact, whatever order the threads searched in. Returns
    // the number of entries checked; throws on the first inconsistency.
    [[nodiscard]] std::size_t verify_memo() {
        std::atomic<std::size_t> checked{0};
        std::atomic<bool> failed{false};
        std::mutex error_mutex;
        std::string first_error;
        auto work = [&](int index) {
            for (auto shard = static_cast<std::size_t>(index); shard < ShardedMemo::kShards;
                 shard += static_cast<std::size_t>(threads_)) {
                if (failed.load(std::memory_order_relaxed)) return;
                std::size_t local = 0;
                memo_.for_each_in_shard(shard, [&](const Key& key, int value) {
                    const State state = state_of(key);
                    const char* problem = check_state(state);
                    if (problem == nullptr) problem = check_entry(state, value);
                    if (problem != nullptr) {
                        std::lock_guard guard(error_mutex);
                        if (!failed.exchange(true)) {
                            first_error = std::string(problem) + " (entry value " + std::to_string(value) + ")";
                        }
                    }
                    ++local;
                });
                checked += local;
            }
        };
        std::vector<std::thread> helpers;
        helpers.reserve(static_cast<std::size_t>(threads_));
        try {
            for (int index = 1; index < threads_; ++index) helpers.emplace_back(work, index);
        } catch (const std::system_error& error) {
            failed.store(true);
            for (std::thread& helper : helpers) helper.join();
            throw std::runtime_error(std::string("cannot start a verification thread: ") + error.what());
        }
        work(0);
        for (std::thread& helper : helpers) helper.join();
        if (failed.load()) throw std::runtime_error("memo verification failed: " + first_error);
        return checked.load();
    }

  private:
    [[nodiscard]] bool contains(const State& state, int number) const {
        return number / modulus_ >= state.k[number % modulus_];
    }

    // The state's largest gap (its Frobenius number): every larger number is
    // an element, so move loops stop there.
    [[nodiscard]] int largest_gap(const State& state) const {
        int largest = 1;   // 1 is a gap of every state the search stores
        for (int lane = 1; lane < modulus_; ++lane) {
            if (state.k[lane] > 0) largest = std::max(largest, lane + modulus_ * (state.k[lane] - 1));
        }
        return largest;
    }

    [[nodiscard]] int apery(const State& state, int residue) const {
        return residue + modulus_ * state.k[residue];
    }

    // ``state`` with every multiple of ``quotient * m + residue`` adjoined.
    [[nodiscard]] State adjoin(State state, int quotient, int residue) const {
        for (int step = 0; step < steps_ && quotient <= kMaximumCoordinate; ++step) {
            // Shift every Apery element by d = quotient * m + residue: lane i
            // receives lane (i - residue) mod m, plus quotient, plus a carry
            // where the residue wrapped past m. Coordinates stay at most 127
            // and quotient at most 127, so no byte overflows.
            const auto shift = static_cast<std::uint8_t>(quotient);
            const Lanes shifted =
                __builtin_shuffle(state.k, rotations_[static_cast<std::size_t>(residue)]) + (lanes_ & shift) +
                carries_[static_cast<std::size_t>(residue)];
            state.k = shifted < state.k ? shifted : state.k;
            // d <- 2d
            quotient = 2 * quotient + (2 * residue >= modulus_ ? 1 : 0);
            residue = 2 * residue >= modulus_ ? 2 * residue - modulus_ : 2 * residue;
        }
        return state;
    }

    [[nodiscard]] State adjoin(const State& state, int move) const {
        return adjoin(state, move / modulus_, move % modulus_);
    }

    // nullptr when ``state`` is the Kunz vector of a numerical semigroup that
    // contains the root: k_0 = 0, lanes from m on 0, every coordinate at most
    // the root's, and w_i + w_j >= w_{(i+j) mod m} for all residues i, j
    // (the Apery set of a set closed under addition).
    [[nodiscard]] const char* check_state(const State& state) const {
        if (state.k[0] != 0) return "a key has a coordinate for residue 0";
        for (int lane = modulus_; lane < kLanes; ++lane) {
            if (state.k[lane] != 0) return "a key uses a lane beyond the modulus";
        }
        for (int lane = 1; lane < modulus_; ++lane) {
            if (state.k[lane] > root_.k[lane]) return "a key's state does not contain the root";
        }
        for (int i = 1; i < modulus_; ++i) {
            for (int j = i; j < modulus_; ++j) {
                if (apery(state, i) + apery(state, j) < apery(state, (i + j) % modulus_)) {
                    return "a key is not the Kunz vector of a semigroup";
                }
            }
        }
        return nullptr;
    }

    // nullptr when the memo entry ``value`` for ``state`` is locally consistent.
    [[nodiscard]] const char* check_entry(const State& state, int value) {
        auto memoized = [this](const State& position) {
            const Key key = key_of(position);
            return memo_.lookup(key, hash_key(key));
        };
        // Naming 1 loses, and a semigroup containing 1 has no moves at all: an
        // honest search never stores either, and accepting them would let a
        // forged entry "win" by naming 1.
        if (contains(state, 1)) return "an entry for a state containing 1";
        if (value > 0) {
            if (value < 2 || value > bound_ || contains(state, value)) return "an N entry names an illegal move";
            if (memoized(adjoin(state, value)) != 0) return "an N entry's move does not reach a memoized P child";
            return nullptr;
        }
        const int last = largest_gap(state);
        for (int move = 2; move <= last; ++move) {
            if (contains(state, move)) continue;
            const State child = adjoin(state, move);
            if (memoized(child) > 0) continue;
            bool answered = false;
            for (int smaller = 2; smaller < move && !answered; ++smaller) {
                answered = !contains(state, smaller) && memoized(adjoin(child, smaller)) == 0;
            }
            if (!answered) return "a P entry has a move to a child that is neither memoized N nor paired";
        }
        return nullptr;
    }

    [[nodiscard]] int solve_from(const State& root) {
        done_.store(false, std::memory_order_relaxed);
        std::vector<std::thread> helpers;
        std::vector<std::exception_ptr> errors(static_cast<std::size_t>(threads_));
        auto run = [this, &errors, &root](int index) {
            try {
                const Key key = key_of(root);
                if (search(root, key, hash_key(key), 0) != kAborted) {
                    done_.store(true, std::memory_order_relaxed);
                }
            } catch (...) {
                errors[static_cast<std::size_t>(index)] = std::current_exception();
                done_.store(true, std::memory_order_relaxed);
            }
        };
        helpers.reserve(static_cast<std::size_t>(threads_));
        try {
            for (int index = 1; index < threads_; ++index) helpers.emplace_back(run, index);
        } catch (const std::system_error& error) {
            done_.store(true, std::memory_order_relaxed);
            for (std::thread& helper : helpers) helper.join();
            throw std::runtime_error(std::string("cannot start a search thread: ") + error.what());
        }
        run(0);
        for (std::thread& helper : helpers) helper.join();
        for (const std::exception_ptr& error : errors) {
            if (error) std::rethrow_exception(error);
        }
        const Key key = key_of(root);
        const int result = memo_.lookup(key, hash_key(key));
        if (result < 0) throw std::logic_error("the root was not decided");
        return result;
    }

    // Winning move of ``state`` (0 when it is a P-position), or kAborted.
    [[nodiscard]] int search(const State& state, const Key& key, std::size_t hash, int depth) {
        if (done_.load(std::memory_order_relaxed)) return kAborted;
        if (const int found = memo_.lookup(key, hash); found >= 0) {
            return found;
        }
        const int last = largest_gap(state);
        MoveSet paired_losers(last / 64 + 1);
        if (depth >= split_depth_) {
            // The sequential recurrence of native_solver.cpp, with the move's
            // quotient and residue mod m kept alongside it, up to the largest
            // gap (larger moves are elements).
            int quotient = 0;
            int residue = 1;   // move 1 (m >= 2)
            for (int move = 2; move <= last; ++move) {
                if (++residue == modulus_) {
                    residue = 0;
                    ++quotient;
                }
                if (quotient >= state.k[residue] || paired_losers.test(move)) {
                    continue;
                }
#ifdef SYLVER_KUNZ_TEST_SKIP_MOVE
                // Test-only fault: a search that misses one child, which
                // --verify-memo must detect.
                if (move == SYLVER_KUNZ_TEST_SKIP_MOVE) continue;
#endif
                const State child = adjoin(state, quotient, residue);
                const Key child_key = key_of(child);
                const int response = search(child, child_key, hash_key(child_key), depth + 1);
                if (response < 0) return kAborted;
                if (response == 0) {
                    memo_.insert(key, hash, move);
                    return move;
                }
                if (response > move) {
                    paired_losers.set(response);
                }
            }
            memo_.insert(key, hash, 0);
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
                for (int move = 2; move <= last; ++move) moves.push_back(move);
            } else {
                moves.swap(deferred);
            }
            for (const int move : moves) {
                if (contains(state, move) || paired_losers.test(move)) {
                    continue;
                }
#ifdef SYLVER_KUNZ_TEST_SKIP_MOVE
                if (move == SYLVER_KUNZ_TEST_SKIP_MOVE) continue;
#endif
                const State child = adjoin(state, move);
                const Key child_key = key_of(child);
                const std::size_t child_hash = hash_key(child_key);
                int response = memo_.lookup(child_key, child_hash);
                if (response < 0) {
                    if (pass == 0 && busy_.busy(child_hash)) {
                        deferred.push_back(move);
                        continue;
                    }
                    busy_.enter(child_hash);
                    response = search(child, child_key, child_hash, depth + 1);
                    busy_.leave(child_hash);
                }
                if (response < 0) return kAborted;
                if (response == 0) {
                    memo_.insert(key, hash, move);
                    return move;
                }
                if (response > move) {
                    paired_losers.set(response);
                }
                if (const int found = memo_.lookup(key, hash); found >= 0) {
                    return found;  // decided by another thread meanwhile
                }
            }
        }
        memo_.insert(key, hash, 0);
        return 0;
    }

    int modulus_;
    int bound_;
    int threads_;
    int split_depth_;
    int steps_ = 0;
    Lanes lanes_{};
    std::array<Lanes, kLanes> rotations_{};
    std::array<Lanes, kLanes> carries_{};
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
        int threads = 1;
        int split_depth = 6;
        bool stop_at_p = false;
        bool verify = false;
        bool memo_stats = false;
        std::size_t max_states = std::numeric_limits<std::size_t>::max();
        std::string stop_file;
        std::vector<int> moves;  // non-empty: a sweep of base+move for each listed odd move
        int first = 1;
        auto value_of = [&](int offset) -> std::string {
            if (first + offset >= argc) throw std::invalid_argument(std::string(argv[first]) + " needs a value");
            return argv[first + offset];
        };
        while (first < argc && std::string(argv[first]).rfind("--", 0) == 0) {
            const std::string option = argv[first];
            if (option == "--threads") {
                threads = parse_int_option(option, value_of(1), 1, 1024);
                first += 2;
            } else if (option == "--split-depth") {
                split_depth = parse_int_option(option, value_of(1), 0, 1000);
                first += 2;
            } else if (option == "--stop-at-p") {
                stop_at_p = true;
                first += 1;
            } else if (option == "--verify-memo") {
                verify = true;
                first += 1;
            } else if (option == "--memo-stats") {
                memo_stats = true;
                first += 1;
            } else if (option == "--max-states") {
                const std::string text = value_of(1);
                std::size_t used = 0;
                const unsigned long long value = std::stoull(text, &used);
                if (used != text.size() || text.front() == '-' || value == 0) {
                    throw std::invalid_argument("--max-states must be a positive integer");
                }
                max_states = static_cast<std::size_t>(value);
                first += 2;
            } else if (option == "--stop-file") {
                stop_file = value_of(1);
                first += 2;
            } else if (option == "--odd-range") {
                const int low = parse_int_option(option, value_of(1), 3, kMaximumBound);
                const int high = parse_int_option(option, value_of(2), low, kMaximumBound);
                if (low % 2 == 0 || high % 2 == 0) throw std::invalid_argument("odd range must have odd endpoints >= 3");
                for (int move = low; move <= high; move += 2) moves.push_back(move);
                first += 3;
            } else if (option == "--odd-list") {
                const std::string text = value_of(1);
                std::size_t begin = 0;
                while (begin <= text.size()) {
                    std::size_t comma = text.find(',', begin);
                    if (comma == std::string::npos) comma = text.size();
                    const int move = parse_int_option(option, text.substr(begin, comma - begin), 3, kMaximumBound);
                    if (move % 2 == 0) throw std::invalid_argument("odd-list moves must be odd and at least 3");
                    moves.push_back(move);
                    begin = comma + 1;
                }
                first += 2;
            } else {
                throw std::invalid_argument("unknown option " + option);
            }
        }
        if (argc <= first) {
            throw std::invalid_argument(
                "usage: kunz_solver [--threads N] [--split-depth D] [--verify-memo] [--memo-stats] "
                "[--odd-range START END | --odd-list MOVES [--stop-at-p] [--max-states N] [--stop-file PATH]] "
                "GENERATOR...");
        }
        if (threads > 1 && split_depth == 0) {
            throw std::invalid_argument("--split-depth 0 would make every thread repeat the same search");
        }
        std::vector<int> generators;
        for (int index = first; index < argc; ++index) {
            generators.push_back(parse_int_option("a generator", argv[index], 2, std::numeric_limits<int>::max()));
        }
        std::sort(generators.begin(), generators.end());
        generators.erase(std::unique(generators.begin(), generators.end()), generators.end());
        auto gcd_of = [](const std::vector<int>& values) {
            return std::accumulate(values.begin() + 1, values.end(), values.front(),
                                   [](int left, int right) { return std::gcd(left, right); });
        };
        if ((stop_at_p || !stop_file.empty() || max_states != std::numeric_limits<std::size_t>::max()) &&
            moves.empty()) {
            throw std::invalid_argument(
                "--stop-at-p, --max-states and --stop-file apply only to --odd-range and --odd-list sweeps");
        }
        auto report_memo = [&](Solver& solver) {
            if (verify) {
#ifdef SYLVER_KUNZ_TEST_FORGE_MOVE_ONE
                solver.forge_move_one();
#endif
#ifdef SYLVER_KUNZ_TEST_FORGE_KEY
                solver.forge_key();
#endif
                const std::size_t entries = solver.verify_memo();
                std::cerr << "kunz_solver: memo verified (" << entries << " entries)\n";
                std::cout << "verified entries=" << entries << std::endl;
            }
            if (memo_stats) {
                const auto [slots, bytes] = solver.memo_footprint();
                std::cerr << "kunz_solver: memo entries=" << solver.states_evaluated() << " slots=" << slots
                          << " bytes=" << bytes << '\n';
            }
        };
        if (!moves.empty()) {
            // One memo for every child base+move, bounded by their largest
            // Frobenius number: each child has gcd one and conductor at most
            // bound+1, so its coordinates are its exact Apery set.
            std::vector<int> frobenius;
            int bound = 0;
            for (const int move : moves) {
                std::vector<int> child = generators;
                child.push_back(move);
                std::sort(child.begin(), child.end());
                if (gcd_of(child) != 1) throw std::invalid_argument("every scanned child must have gcd one");
                std::vector<bool> generated(static_cast<std::size_t>(move) + 1, false);
                generated[0] = true;
                for (int n = 1; n <= move; ++n) {
                    for (const int g : generators) {
                        if (g <= n && generated[static_cast<std::size_t>(n - g)]) {
                            generated[static_cast<std::size_t>(n)] = true;
                            break;
                        }
                    }
                }
                if (generated[static_cast<std::size_t>(move)]) {
                    throw std::invalid_argument("scanned move " + std::to_string(move) +
                                                " is not a legal move of the base");
                }
                const std::int64_t f = frobenius_number(child);
                if (f > kMaximumBound) {
                    throw std::invalid_argument("scan Frobenius bound exceeds the Kunz engine's limit " +
                                                std::to_string(kMaximumBound));
                }
                frobenius.push_back(static_cast<int>(f));
                bound = std::max(bound, frobenius.back());
            }
            Solver solver(generators, bound, threads, split_depth);
            for (std::size_t i = 0; i < moves.size(); ++i) {
                // A long sweep can end early at a row boundary, with its
                // finished rows still verified below: once the memo holds
                // --max-states states, or when --stop-file appears.
                if (i > 0) {
                    const std::size_t states = solver.states_evaluated();
                    const bool full = states >= max_states;
                    if (full || (!stop_file.empty() && std::ifstream(stop_file).good())) {
                        std::cerr << "kunz_solver: sweep stopped before move=" << moves[i] << " ("
                                  << (full ? "memo holds " + std::to_string(states) + " states" : "stop file")
                                  << ")\n";
                        break;
                    }
                }
                const int response = solver.solve_after_adjoining(moves[i]);
                std::cout << "move=" << moves[i] << ' ' << (response == 0 ? "P" : "N") << " winning_move=";
                if (response == 0) {
                    std::cout << "none";
                } else {
                    std::cout << response;
                }
                // Flushed per row: a stopped sweep keeps its finished rows.
                std::cout << " frobenius=" << frobenius[i]
                          << " cumulative_states=" << solver.states_evaluated() << std::endl;
                if (response == 0 && stop_at_p) break;
            }
            report_memo(solver);
            return EXIT_SUCCESS;
        }
        if (gcd_of(generators) != 1) {
            throw std::invalid_argument("exact evaluation requires generators with gcd one");
        }
        const std::int64_t frobenius = frobenius_number(generators);
        if (frobenius > kMaximumBound) {
            throw std::invalid_argument("Frobenius number exceeds the Kunz engine's limit " +
                                        std::to_string(kMaximumBound));
        }
        Solver solver(generators, static_cast<int>(frobenius), threads, split_depth);
        const int move = solver.solve();
        std::cout << (move == 0 ? "P" : "N") << " winning_move=";
        if (move == 0) {
            std::cout << "none";
        } else {
            std::cout << move;
        }
        std::cout << " frobenius=" << frobenius << " states=" << solver.states_evaluated() << std::endl;
        report_memo(solver);
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "kunz_solver: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
