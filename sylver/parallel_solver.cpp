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
// copies of the whole memo; shards fill to 7/8 and grow by half, with hash
// fingerprints keeping the long probes of a full table cheap. Every reachable state contains the root's
// semigroup, so a memo key keeps only the state's bits at the root's gaps:
// about half the Frobenius number in bits instead of 64 * SYLVER_NATIVE_WORDS.
// --odd-range and --odd-list evaluate base+m for each listed odd m with one
// shared memo, as native_solver.cpp's scans do (the base is then the root
// whose gaps key the memo); later candidates reuse the earlier ones' states.
// With --verify-memo the finished memo is checked as a certificate (see
// Solver::verify_memo), so N results are checked too, not only the P results
// that published replays re-run. Results are printed as they are decided;
// the output ends with `verified entries=N` only if the check passed, and
// output without that line is unverified.
// Discovery only: published replays and the arena verifier keep using
// native_solver.cpp.
#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
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
#include <system_error>
#include <thread>
#include <utility>
#include <vector>

#if defined(__GLIBC__)
#include <malloc.h>
#endif
#if defined(__BMI2__)
#include <immintrin.h>
#endif

namespace {

#ifndef SYLVER_NATIVE_WORDS
#define SYLVER_NATIVE_WORDS 8
#endif

constexpr int kWords = SYLVER_NATIVE_WORDS;
static_assert(kWords > 0, "SYLVER_NATIVE_WORDS must be positive");
constexpr int kMaximumFrobenius = 64 * kWords - 1;
static_assert(kMaximumFrobenius < 0xFFFF, "memo values are 16-bit moves");
constexpr int kAborted = -2;  // the root was decided elsewhere; nothing below is recorded

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

// A memo key: a state's bits at the root's gaps, packed into the first
// ``KeyPacker::words()`` words (the rest stay zero).
using Key = std::array<std::uint64_t, kWords>;

[[nodiscard]] std::size_t hash_key(const Key& key) noexcept {
    std::uint64_t hash = 0x9e3779b97f4a7c15ULL;
    for (const std::uint64_t word : key) {
        std::uint64_t mixed = word + 0x9e3779b97f4a7c15ULL;
        mixed = (mixed ^ (mixed >> 30)) * 0xbf58476d1ce4e5b9ULL;
        mixed = (mixed ^ (mixed >> 27)) * 0x94d049bb133111ebULL;
        mixed ^= mixed >> 31;
        hash ^= mixed + 0x9e3779b97f4a7c15ULL + (hash << 6) + (hash >> 2);
    }
    return static_cast<std::size_t>(hash);
}

// The bits of ``value`` selected by ``mask``, packed into the low bits.
[[nodiscard, maybe_unused]] std::uint64_t extract_bits(std::uint64_t value, std::uint64_t mask) noexcept {
#if defined(__BMI2__)
    return _pext_u64(value, mask);
#else
    std::uint64_t result = 0;
    for (std::uint64_t bit = 1; mask != 0; mask &= mask - 1, bit <<= 1) {
        if (value & mask & (~mask + 1)) result |= bit;
    }
    return result;
#endif
}

// Deposits the low bits of ``value`` at the positions of ``mask``.
[[nodiscard, maybe_unused]] std::uint64_t deposit_bits(std::uint64_t value, std::uint64_t mask) noexcept {
#if defined(__BMI2__)
    return _pdep_u64(value, mask);
#else
    std::uint64_t result = 0;
    for (std::uint64_t bit = 1; mask != 0; mask &= mask - 1, bit <<= 1) {
        if (value & bit) result |= mask & (~mask + 1);
    }
    return result;
#endif
}

#ifdef SYLVER_PARALLEL_KUNZ_KEYS
// Kunz-coordinate keys, for roots whose smallest element m is 2, 4, 8 or 16
// (so a bit's residue mod m does not depend on its word): byte i - 1 of a key
// is the number of the state's gaps congruent to i mod m. Every state
// contains the root, hence m, so its gaps in each residue class form a
// prefix and these counts determine it; a key takes ceil((m - 1) / 8) words.
// Only the memo's encoding changes: moves, search and --verify-memo are this
// engine's bitset code, which makes this build an independent cross-check of
// kunz_solver.cpp's byte-vector moves with keys of the same size (18-byte
// slots for m = 16). Build with -DSYLVER_PARALLEL_KUNZ_KEYS.
class KeyPacker {
  public:
    KeyPacker() = default;
    KeyPacker(const State& root, int frobenius) {
        for (int n = 1; n <= frobenius && modulus_ == 0; ++n) {
            if (root.test(n)) modulus_ = n;
        }
        if (modulus_ == 0) modulus_ = frobenius + 1;   // states hold no bits above F, all of them elements
        if (modulus_ != 2 && modulus_ != 4 && modulus_ != 8 && modulus_ != 16) {
            throw std::invalid_argument("Kunz keys need a smallest root element of 2, 4, 8 or 16");
        }
        if (frobenius / modulus_ + 1 > 255) throw std::invalid_argument("a Kunz key count would exceed a byte");
        for (int bit = 0; bit <= frobenius; ++bit) limit_.set(bit);
        for (int residue = 0; residue < modulus_; ++residue) {
            for (int bit = residue; bit < 64; bit += modulus_) classes_[static_cast<std::size_t>(residue)] |= std::uint64_t{1} << bit;
        }
        words_ = (modulus_ - 1 + 7) / 8;
    }
    [[nodiscard]] int words() const { return words_; }
    [[nodiscard]] Key pack(const State& state) const {
        Key key{};
        for (int residue = 1; residue < modulus_; ++residue) {
            std::uint64_t count = 0;
            for (int word = 0; word < kWords; ++word) {
                const auto index = static_cast<std::size_t>(word);
                count += static_cast<std::uint64_t>(std::popcount(~state.words[index] & limit_.words[index] &
                                                                  classes_[static_cast<std::size_t>(residue)]));
            }
            key[static_cast<std::size_t>((residue - 1) / 8)] |= count << (8 * ((residue - 1) % 8));
        }
        return key;
    }

    // The state with Kunz key ``key``: n in [0, F] is an element exactly when
    // n / m is at least the count of n's residue class.
    [[nodiscard]] State unpack(const Key& key, const State&) const {
        State state;
        for (int word = 0; word < kWords; ++word) {
            std::uint64_t bits = classes_[0];   // the multiples of m
            for (int residue = 1; residue < modulus_; ++residue) {
                const auto count = static_cast<int>(
                    (key[static_cast<std::size_t>((residue - 1) / 8)] >> (8 * ((residue - 1) % 8))) & 0xFFU);
                // This word's bits of the class are 64*word + residue + t*m, with
                // quotient 64*word/m + t: elements once t reaches ``skip``.
                const int skip = count - 64 * word / modulus_;
                const std::uint64_t members = classes_[static_cast<std::size_t>(residue)];
                if (skip <= 0) {
                    bits |= members;
                } else if (skip < 64 / modulus_) {
                    bits |= members & ~((std::uint64_t{1} << (residue + skip * modulus_)) - 1);
                }
            }
            state.words[static_cast<std::size_t>(word)] = bits & limit_.words[static_cast<std::size_t>(word)];
        }
        return state;
    }

  private:
    int modulus_ = 0;
    int words_ = 1;
    State limit_;
    std::array<std::uint64_t, 16> classes_{};
};
#else
class KeyPacker {
  public:
    KeyPacker() = default;
    KeyPacker(const State& root, int frobenius) {
        int total = 0;
        for (int bit = 0; bit <= frobenius; ++bit) {
            if (!root.test(bit)) {
                gaps_.set(bit);
                ++total;
            }
        }
        words_ = std::max(1, (total + 63) / 64);
    }
    [[nodiscard]] int words() const { return words_; }
    [[nodiscard]] Key pack(const State& state) const {
        Key key{};
        int offset = 0;
        for (int word = 0; word < kWords; ++word) {
            const std::uint64_t mask = gaps_.words[static_cast<std::size_t>(word)];
            if (mask == 0) continue;
            const std::uint64_t bits = extract_bits(state.words[static_cast<std::size_t>(word)], mask);
            const int count = std::popcount(mask);
            const auto index = static_cast<std::size_t>(offset / 64);
            const int shift = offset % 64;
            key[index] |= bits << shift;
            if (shift != 0 && shift + count > 64) key[index + 1] |= bits >> (64 - shift);
            offset += count;
        }
        return key;
    }

    // The state with packed key ``key``: ``root`` plus the key's gap bits.
    [[nodiscard]] State unpack(const Key& key, State state) const {
        int offset = 0;
        for (int word = 0; word < kWords; ++word) {
            const std::uint64_t mask = gaps_.words[static_cast<std::size_t>(word)];
            if (mask == 0) continue;
            const int count = std::popcount(mask);
            const auto index = static_cast<std::size_t>(offset / 64);
            const int shift = offset % 64;
            std::uint64_t bits = key[index] >> shift;
            if (shift != 0 && shift + count > 64) bits |= key[index + 1] << (64 - shift);
            state.words[static_cast<std::size_t>(word)] |= deposit_bits(bits, mask);
            offset += count;
        }
        return state;
    }

  private:
    State gaps_;
    int words_ = kWords;
};
#endif

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
// top bits of the hash. Each slot holds a packed key of ``stride`` words and a
// 16-bit tag: the low 10 bits are the value (0 for P, else the winning move)
// and the high 6 bits a fingerprint of the hash, so a probe compares keys only
// when the fingerprint matches; kEmpty marks a free slot. A shard is filled to
// at most 7/8 of its capacity and then grows by half, so it holds between
// 7/12 and 7/8 as many entries as slots. A key is never stored twice and a
// stored value is never overwritten.
class ShardedMemo {
  public:
    static constexpr int kShardBits = 12;
    static constexpr std::uint16_t kEmpty = 0xFFFF;  // fingerprints stop at 62, so no tag equals it
    static constexpr int kValueBits = 10;
    static constexpr std::uint16_t kValueMask = (1U << kValueBits) - 1;
    static_assert(kMaximumFrobenius <= kValueMask, "memo tags hold moves in 10 bits: at most 16 words");

    explicit ShardedMemo(int stride)
        : stride_(std::min(static_cast<std::size_t>(stride), static_cast<std::size_t>(kWords))) {
        for (Shard& shard : shards_) shard.resize(16, stride_);
    }

    [[nodiscard]] int lookup(const Key& key, std::size_t hash) {
        Shard& shard = shard_for(hash);
        const std::uint16_t print = fingerprint(hash);
        std::lock_guard guard(shard.lock);
        const std::size_t capacity = shard.tags.size();
        for (std::size_t slot = home(hash, capacity);; slot = next(slot, capacity)) {
            const std::uint16_t tag = shard.tags[slot];
            if (tag == kEmpty) return -1;
            if ((tag >> kValueBits) == print && shard.holds(slot, key, stride_)) return tag & kValueMask;
        }
    }

    void insert(const Key& key, std::size_t hash, std::uint16_t value) {
        Shard& shard = shard_for(hash);
        const std::uint16_t print = fingerprint(hash);
        std::lock_guard guard(shard.lock);
        if ((shard.count + 1) * 8 > shard.tags.size() * 7) shard.grow(stride_);
        const std::size_t capacity = shard.tags.size();
        std::size_t slot = home(hash, capacity);
        for (; shard.tags[slot] != kEmpty; slot = next(slot, capacity)) {
            if ((shard.tags[slot] >> kValueBits) == print && shard.holds(slot, key, stride_)) return;
        }
        std::copy(key.begin(), key.begin() + static_cast<std::ptrdiff_t>(stride_),
                  shard.keys.begin() + static_cast<std::ptrdiff_t>(slot * stride_));
        shard.tags[slot] = static_cast<std::uint16_t>((print << kValueBits) | value);
        ++shard.count;
    }

    static constexpr std::size_t kShards = std::size_t{1} << kShardBits;

#ifdef SYLVER_PARALLEL_TEST_FORGE_MOVE_ONE
    void overwrite(const Key& key, std::size_t hash, std::uint16_t value) {
        insert(key, hash, value);
        Shard& shard = shard_for(hash);
        const std::size_t capacity = shard.tags.size();
        for (std::size_t slot = home(hash, capacity);; slot = next(slot, capacity)) {
            if (shard.tags[slot] != kEmpty && shard.holds(slot, key, stride_)) {
                shard.tags[slot] = static_cast<std::uint16_t>((fingerprint(hash) << kValueBits) | value);
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
            Key key{};
            std::copy_n(shard.keys.begin() + static_cast<std::ptrdiff_t>(slot * stride_),
                        std::min(stride_, key.size()), key.begin());
            f(key, static_cast<std::uint16_t>(shard.tags[slot] & kValueMask));
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

  private:
    // Bits 32 and up of the hash (the shard uses the top 12, the slot the low 32).
    static std::uint16_t fingerprint(std::size_t hash) {
        return static_cast<std::uint16_t>(((hash >> 32) & 0xFFFFF) % 63);
    }
    // A slot in [0, capacity) from the low 32 bits of the hash (multiply-shift).
    static std::size_t home(std::size_t hash, std::size_t capacity) {
        return static_cast<std::size_t>((static_cast<std::uint64_t>(static_cast<std::uint32_t>(hash)) * capacity) >> 32);
    }
    static std::size_t next(std::size_t slot, std::size_t capacity) { return slot + 1 == capacity ? 0 : slot + 1; }

    struct alignas(64) Shard {
        SpinLock lock;
        std::vector<std::uint64_t> keys;
        std::vector<std::uint16_t> tags;
        std::size_t count = 0;

        void resize(std::size_t capacity, std::size_t stride) {
            keys.assign(capacity * stride, 0);
            tags.assign(capacity, kEmpty);
        }

        [[nodiscard]] bool holds(std::size_t slot, const Key& key, std::size_t stride) const {
            return std::equal(key.begin(), key.begin() + static_cast<std::ptrdiff_t>(stride),
                              keys.begin() + static_cast<std::ptrdiff_t>(slot * stride));
        }

        void grow(std::size_t stride) {
            Shard old;
            old.keys.swap(keys);
            old.tags.swap(tags);
            const std::size_t capacity = old.tags.size() + old.tags.size() / 2;
            resize(capacity, stride);
            for (std::size_t i = 0; i < old.tags.size(); ++i) {
                if (old.tags[i] == kEmpty) continue;
                Key key{};
                std::copy_n(old.keys.begin() + static_cast<std::ptrdiff_t>(i * stride), std::min(stride, key.size()),
                            key.begin());
                std::size_t slot = home(hash_key(key), capacity);
                while (tags[slot] != kEmpty) slot = next(slot, capacity);
                std::copy_n(key.begin(), std::min(stride, key.size()),
                            keys.begin() + static_cast<std::ptrdiff_t>(slot * stride));
                tags[slot] = old.tags[i];   // the fingerprint depends only on the key's hash
            }
        }
    };

    Shard& shard_for(std::size_t hash) {
        return shards_[hash >> (std::numeric_limits<std::size_t>::digits - kShardBits)];
    }

    std::size_t stride_;
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

// Frobenius number of a gcd-one generator set (int64: huge generators must
// fail the native limit check rather than overflow).
[[nodiscard]] std::int64_t frobenius_number(const std::vector<int>& generators) {
    const int modulus = generators.front();
    // Every positive integer below the smallest generator is a gap, so F is
    // at least modulus - 1: past the native limit, return that bound rather
    // than allocate a table of that size.
    if (modulus - 1 > kMaximumFrobenius) return modulus - 1;
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
    Solver(const std::vector<int>& generators, int frobenius, int threads, int split_depth)
        : frobenius_(frobenius), threads_(threads), split_depth_(threads > 1 ? split_depth : 0),
          mask_(make_mask()) {
        root_.set(0);
        for (const int generator : generators) {
            root_ = adjoin(root_, generator);
        }
        packer_ = KeyPacker(root_, frobenius_);
        memo_ = std::make_unique<ShardedMemo>(packer_.words());
    }

    // Winning move of the root, or 0 when it is a P-position.
    [[nodiscard]] int solve() { return solve_from(root_); }

    // The same for the root with ``move`` adjoined. Successive calls share
    // the memo, like native_solver.cpp's odd-range scans.
    [[nodiscard]] int solve_after_adjoining(int move) { return solve_from(adjoin(root_, move)); }

    [[nodiscard]] std::size_t states_evaluated() { return memo_->size(); }

#ifdef SYLVER_PARALLEL_TEST_FORGE_MOVE_ONE
    // Test-only forgery that --verify-memo must reject: the root "wins" by
    // naming 1, whose child (every integer) is recorded as P.
    void forge_move_one() {
        const Key root_key = packer_.pack(root_);
        memo_->overwrite(root_key, hash_key(root_key), 1);
        const Key all_key = packer_.pack(mask_);
        memo_->overwrite(all_key, hash_key(all_key), 0);
    }
#endif

    // Checks the finished memo as a certificate: an N entry must name a legal
    // move whose child is memoized P, and every legal move m of a P entry S
    // must lead to a child memoized N or be a paired loser (a smaller legal
    // move m' with S+m'+m memoized P: m' answers m). By induction on the
    // number of gaps, every entry, and so every reported root, is then
    // exact, whatever order the threads searched in. Returns the number of
    // entries checked; throws on the first inconsistency.
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
                memo_->for_each_in_shard(shard, [&](const Key& key, std::uint16_t value) {
                    const State state = packer_.unpack(key, root_);
                    const char* problem = packer_.pack(state) != key ? "a key does not encode a state"
                                                                   : check_entry(state, value);
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
    // nullptr when the memo entry ``value`` for ``state`` is locally consistent.
    [[nodiscard]] const char* check_entry(const State& state, int value) {
        auto memoized = [this](const State& position) {
            const Key key = packer_.pack(position);
            return memo_->lookup(key, hash_key(key));
        };
        // Naming 1 loses, and a semigroup containing 1 has no moves at all: an
        // honest search never stores either, and accepting them would let a
        // forged entry "win" by naming 1.
        if (state.test(1)) return "an entry for a state containing 1";
        if (value > 0) {
            if (value < 2 || value > frobenius_ || state.test(value)) return "an N entry names an illegal move";
            if (memoized(adjoin(state, value)) != 0) return "an N entry's move does not reach a memoized P child";
            return nullptr;
        }
        for (int move = 2; move <= frobenius_; ++move) {
            if (state.test(move)) continue;
            const State child = adjoin(state, move);
            if (memoized(child) > 0) continue;
            bool answered = false;
            for (int smaller = 2; smaller < move && !answered; ++smaller) {
                answered = !state.test(smaller) && memoized(adjoin(child, smaller)) == 0;
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
                const Key key = packer_.pack(root);
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
        const Key key = packer_.pack(root);
        const int result = memo_->lookup(key, hash_key(key));
        if (result < 0) throw std::logic_error("the root was not decided");
        return result;
    }

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
    [[nodiscard]] int search(const State& state, const Key& key, std::size_t hash, int depth) {
        if (done_.load(std::memory_order_relaxed)) return kAborted;
        if (const int found = memo_->lookup(key, hash); found >= 0) {
            return found;
        }
        State paired_losers;
        if (depth >= split_depth_) {
            // The sequential recurrence of native_solver.cpp.
            for (int move = 2; move <= frobenius_; ++move) {
                if (state.test(move) || paired_losers.test(move)) {
                    continue;
                }
#ifdef SYLVER_PARALLEL_TEST_SKIP_MOVE
                // Test-only fault: a search that misses one child, which
                // --verify-memo must detect.
                if (move == SYLVER_PARALLEL_TEST_SKIP_MOVE) continue;
#endif
                const State child = adjoin(state, move);
                const Key child_key = packer_.pack(child);
                const int response = search(child, child_key, hash_key(child_key), depth + 1);
                if (response < 0) return kAborted;
                if (response == 0) {
                    memo_->insert(key, hash, static_cast<std::uint16_t>(move));
                    return move;
                }
                if (response > move) {
                    paired_losers.set(response);
                }
            }
            memo_->insert(key, hash, std::uint16_t{0});
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
#ifdef SYLVER_PARALLEL_TEST_SKIP_MOVE
                if (move == SYLVER_PARALLEL_TEST_SKIP_MOVE) continue;
#endif
                const State child = adjoin(state, move);
                const Key child_key = packer_.pack(child);
                const std::size_t child_hash = hash_key(child_key);
                int response = memo_->lookup(child_key, child_hash);
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
                    memo_->insert(key, hash, static_cast<std::uint16_t>(move));
                    return move;
                }
                if (response > move) {
                    paired_losers.set(response);
                }
                if (const int found = memo_->lookup(key, hash); found >= 0) {
                    return found;  // decided by another thread meanwhile
                }
            }
        }
        memo_->insert(key, hash, std::uint16_t{0});
        return 0;
    }

    int frobenius_;
    int threads_;
    int split_depth_;
    State mask_;
    State root_;
    KeyPacker packer_;
    std::unique_ptr<ShardedMemo> memo_;
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
            } else if (option == "--odd-range") {
                const int low = parse_int_option(option, value_of(1), 3, kMaximumFrobenius);
                const int high = parse_int_option(option, value_of(2), low, kMaximumFrobenius);
                if (low % 2 == 0 || high % 2 == 0) throw std::invalid_argument("odd range must have odd endpoints >= 3");
                for (int move = low; move <= high; move += 2) moves.push_back(move);
                first += 3;
            } else if (option == "--odd-list") {
                const std::string text = value_of(1);
                std::size_t begin = 0;
                while (begin <= text.size()) {
                    std::size_t comma = text.find(',', begin);
                    if (comma == std::string::npos) comma = text.size();
                    const int move = parse_int_option(option, text.substr(begin, comma - begin), 3, kMaximumFrobenius);
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
                "usage: parallel_solver [--threads N] [--split-depth D] [--verify-memo] "
                "[--odd-range START END | --odd-list MOVES [--stop-at-p]] GENERATOR...");
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
        if (stop_at_p && moves.empty()) {
            throw std::invalid_argument("--stop-at-p applies only to --odd-range and --odd-list sweeps");
        }
        if (!moves.empty()) {
            // One memo for every child base+move, bounded by their largest
            // Frobenius number: each child has gcd one and conductor at most
            // bound+1, so its bitset is its exact semigroup.
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
                if (f > kMaximumFrobenius) {
                    throw std::invalid_argument("scan Frobenius bound exceeds native limit " +
                                                std::to_string(kMaximumFrobenius));
                }
                frobenius.push_back(static_cast<int>(f));
                bound = std::max(bound, frobenius.back());
            }
            Solver solver(generators, bound, threads, split_depth);
            for (std::size_t i = 0; i < moves.size(); ++i) {
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
            if (verify) {
#ifdef SYLVER_PARALLEL_TEST_FORGE_MOVE_ONE
                solver.forge_move_one();
#endif
                const std::size_t entries = solver.verify_memo();
                std::cerr << "parallel_solver: memo verified (" << entries << " entries)\n";
                std::cout << "verified entries=" << entries << std::endl;
            }
            return EXIT_SUCCESS;
        }
        if (gcd_of(generators) != 1) {
            throw std::invalid_argument("exact evaluation requires generators with gcd one");
        }
        const std::int64_t frobenius = frobenius_number(generators);
        if (frobenius > kMaximumFrobenius) {
            throw std::invalid_argument(
                "Frobenius number exceeds native limit " +
                std::to_string(kMaximumFrobenius)
            );
        }
        Solver solver(generators, static_cast<int>(frobenius), threads, split_depth);
        const int move = solver.solve();
        std::cout << (move == 0 ? "P" : "N") << " winning_move=";
        if (move == 0) {
            std::cout << "none";
        } else {
            std::cout << move;
        }
        std::cout << " frobenius=" << frobenius
                  << " states=" << solver.states_evaluated() << std::endl;
        if (verify) {
#ifdef SYLVER_PARALLEL_TEST_FORGE_MOVE_ONE
            solver.forge_move_one();
#endif
            const std::size_t entries = solver.verify_memo();
            std::cerr << "parallel_solver: memo verified (" << entries << " entries)\n";
            std::cout << "verified entries=" << entries << std::endl;
        }
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "parallel_solver: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
