"""Derive kunz_p.cpp from sylver/kunz_solver.cpp: a P-table plus a lossy N-cache.

The memo keeps only P-positions (exact, unbounded but for --max-states). N-positions go to a
fixed-size set-associative cache that overwrites old entries; its keys are exact, so a hit is
always right. Before recursing, a state's moves are scanned for a child already in the P-table
(an enhanced transposition cutoff), which re-proves an evicted N-position in one pass.
"""
from pathlib import Path

SRC = Path('/home/ruclaw/src/sylver-coinage/sylver/kunz_solver.cpp')
OUT = Path(__file__).resolve().parent / 'kunz_p.cpp'
s = SRC.read_text()


def sub(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)


# 1. the N-cache
sub("// How many threads are searching each (hashed) state near the root. A\n",
    """// A fixed-size, lossy cache of N-positions with their winning moves: 4-way
// buckets under striped locks, each bucket replacing its entries in turn when
// full. Keys are exact, so a hit is always right; an evicted entry only costs
// a re-proof.
class NCache {
  public:
    void resize(std::size_t bytes) {
        buckets_ = bytes / sizeof(Bucket);
        table_ = std::vector<Bucket>(buckets_);
    }

    [[nodiscard]] int lookup(const Key& key, std::size_t hash) {
        if (buckets_ == 0) return -1;
        const std::size_t index = bucket(hash);
        Bucket& b = table_[index];
        std::lock_guard guard(locks_[index % kLocks]);
        for (int way = 0; way < kWays; ++way) {
            if (b.used[way] && (b.low[way] & kKeyBitsLow) == key.low && b.high[way] == key.high) {
                hits_.fetch_add(1, std::memory_order_relaxed);
                return value_in(b.low[way]);
            }
        }
        return -1;
    }

    void insert(const Key& key, std::size_t hash, int value) {
        if (buckets_ == 0) return;
        const std::size_t index = bucket(hash);
        Bucket& b = table_[index];
        std::lock_guard guard(locks_[index % kLocks]);
        int way = -1;
        for (int w = 0; w < kWays; ++w) {
            if (b.used[w] && (b.low[w] & kKeyBitsLow) == key.low && b.high[w] == key.high) return;
            if (way < 0 && !b.used[w]) way = w;
        }
        if (way < 0) {
            way = b.next;
            b.next = static_cast<std::uint8_t>((b.next + 1) % kWays);
            evictions_.fetch_add(1, std::memory_order_relaxed);
        }
        b.low[way] = with_value(key.low, value);
        b.high[way] = key.high;
        b.used[way] = 1;
        inserts_.fetch_add(1, std::memory_order_relaxed);
    }

    [[nodiscard]] std::size_t capacity() const { return buckets_ * kWays; }
    std::atomic<std::uint64_t> hits_{0}, inserts_{0}, evictions_{0};

  private:
    static constexpr int kWays = 4;
    static constexpr std::size_t kLocks = 1 << 16;
    struct Bucket {
        std::uint64_t low[kWays]{};
        std::uint64_t high[kWays]{};
        std::uint8_t used[kWays]{};
        std::uint8_t next = 0;
    };
    // The bucket from bits 16-63 of the hash (the P-table's shards use the top bits and its slots the low 32).
    [[nodiscard]] std::size_t bucket(std::size_t hash) const { return (hash >> 16) % buckets_; }

    std::size_t buckets_ = 0;
    std::vector<Bucket> table_;
    std::vector<SpinLock> locks_ = std::vector<SpinLock>(kLocks);
};

// How many threads are searching each (hashed) state near the root. A
""")

# 2. the search: P-table and N-cache lookups, the cutoff scan, and stores split by outcome
start = s.index("    // Winning move of ``state`` (0 when it is a P-position), or kAborted.\n")
end = s.index("    static constexpr std::size_t kCountBatch = 4096;\n")
new_search = '''    // A known outcome: 0 for a P-position in the table, the winning move of a
    // cached N-position, or -1.
    [[nodiscard]] int known(const Key& key, std::size_t hash) {
        if (memo_.lookup(key, hash) == 0) return 0;
        return ncache_.lookup(key, hash);
    }

    // The least move from ``state`` to a P-position already in the table, or 0.
    [[nodiscard]] int known_winner(const State& state, int last) {
        int quotient = 0;
        int residue = 1;   // move 1 (m >= 2)
        for (int move = 2; move <= last; ++move) {
            if (++residue == modulus_) {
                residue = 0;
                ++quotient;
            }
            if (quotient >= state.k[residue]) continue;
            const State child = adjoin(state, quotient, residue);
            const Key child_key = key_of(child);
            if (memo_.lookup(child_key, hash_key(child_key)) == 0) return move;
        }
        return 0;
    }

    void store_p(const Key& key, std::size_t hash) {
        memo_.insert(key, hash, 0);
        count_insert();
    }

    // Winning move of ``state`` (0 when it is a P-position), or kAborted.
    [[nodiscard]] int search(const State& state, const Key& key, std::size_t hash, int depth) {
        if (done_.load(std::memory_order_relaxed)) return kAborted;
        if (const int found = known(key, hash); found >= 0) return found;
        const int last = largest_gap(state);
        if (const int move = known_winner(state, last); move > 0) {
            ncache_.insert(key, hash, move);
            return move;
        }
        MoveSet paired_losers(last / 64 + 1);
        if (depth >= split_depth_) {
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
                const State child = adjoin(state, quotient, residue);
                const Key child_key = key_of(child);
                const int response = search(child, child_key, hash_key(child_key), depth + 1);
                if (response < 0) return kAborted;
                if (response == 0) {
                    ncache_.insert(key, hash, move);
                    return move;
                }
                if (response > move) {
                    paired_losers.set(response);
                }
            }
            store_p(key, hash);
            return 0;
        }
        // Near the root: the same recurrence in two passes, the first deferring
        // children another thread is searching.
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
                const State child = adjoin(state, move);
                const Key child_key = key_of(child);
                const std::size_t child_hash = hash_key(child_key);
                int response = known(child_key, child_hash);
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
                    ncache_.insert(key, hash, move);
                    return move;
                }
                if (response > move) {
                    paired_losers.set(response);
                }
                if (const int found = known(key, hash); found >= 0) {
                    return found;  // decided by another thread meanwhile
                }
            }
        }
        store_p(key, hash);
        return 0;
    }

'''
s = s[:start] + new_search + s[end:]

# 3. the root's result does not depend on the cache
sub("""                const Key key = key_of(root);
                if (search(root, key, hash_key(key), 0) != kAborted) {
                    done_.store(true, std::memory_order_relaxed);
                }""",
    """                const Key key = key_of(root);
                const int result = search(root, key, hash_key(key), 0);
                if (result != kAborted) {
                    if (result >= 0) root_result_.store(result, std::memory_order_relaxed);
                    done_.store(true, std::memory_order_relaxed);
                }""")
sub("""        const Key key = key_of(root);
        const int result = memo_.lookup(key, hash_key(key));
        if (result >= 0) return result;""",
    """        const int result = root_result_.exchange(-1);
        if (result >= 0) return result;""")
sub("    ShardedMemo memo_;\n",
    "    ShardedMemo memo_;   // P-positions only\n    NCache ncache_;\n    std::atomic<int> root_result_{-1};\n")
sub("    [[nodiscard]] std::size_t states_evaluated() { return memo_.size(); }\n",
    """    [[nodiscard]] std::size_t states_evaluated() { return memo_.size(); }
    void set_ncache_bytes(std::size_t bytes) { ncache_.resize(bytes); }
    [[nodiscard]] std::string ncache_report() {
        return "ncache capacity=" + std::to_string(ncache_.capacity()) + " inserts=" + std::to_string(ncache_.inserts_.load()) +
               " evictions=" + std::to_string(ncache_.evictions_.load()) + " hits=" + std::to_string(ncache_.hits_.load());
    }
""")

# 4. options: --ncache-mb; --verify-memo refused (it reads N entries)
sub("        bool memo_stats = false;\n", "        bool memo_stats = false;\n        std::size_t ncache_mb = 4096;\n")
sub("""            } else if (option == "--memo-stats") {""",
    """            } else if (option == "--ncache-mb") {
                ncache_mb = static_cast<std::size_t>(parse_int_option(option, value_of(1), 0, 1 << 20));
                first += 2;
            } else if (option == "--memo-stats") {""")
sub("""            } else if (option == "--verify-memo") {
                verify = true;
                first += 1;""",
    """            } else if (option == "--verify-memo") {
                throw std::invalid_argument("kunz_p keeps only P-positions; --verify-memo needs every N entry");""")
sub("            Solver solver(generators, bound, threads, split_depth);\n",
    "            Solver solver(generators, bound, threads, split_depth);\n            solver.set_ncache_bytes(ncache_mb << 20);\n")
sub("        Solver solver(generators, static_cast<int>(frobenius), threads, split_depth);\n",
    "        Solver solver(generators, static_cast<int>(frobenius), threads, split_depth);\n        solver.set_ncache_bytes(ncache_mb << 20);\n")
sub("""            if (memo_stats) {
                const auto [slots, bytes] = solver.memo_footprint();""",
    """            if (memo_stats) {
                std::cerr << "kunz_p: " << solver.ncache_report() << '\\n';
                const auto [slots, bytes] = solver.memo_footprint();""")
s = s.replace('"kunz_solver: ', '"kunz_p: ')
OUT.write_text(s)
print('wrote', OUT)
