// Ultimate-periodicity engine for gcd-two Sylver Coinage positions.
//
// C++ port of sylver/periodicity.py (the executable specification, validated
// differentially against the exact native solver).  The Periodicity Theorem
// (Winning Ways ch. 18; Sicherman, Integers 2 (2002) #G02) makes the odd-tail
// outcome sequence of a g=2 position computable by a finite-state system:
//
//   - an odd move below min(anchors) - tbar resets the position to a single
//     smaller anchor (value: a monotone flag per even part);
//   - odd moves above max(anchors) + tbar are illegal;
//   - for min(anchors) >= tbar + 2 the window dynamics are translation
//     invariant, so states are (even part, anchor offsets) shapes.
//
// Base-region states (min < tbar + 2) are solved by an embedded copy of the
// repository's exact native recurrence; results are cached on disk.  Every
// (shape, relative move) transition is computed once and cached, so a scan
// step costs one table sweep.  Certified periodicity: when the full window
// snapshot repeats with stable reset flags, the tail repeats forever.  The
// snapshots are compared exactly (Brent's cycle algorithm), not by hash.
//
// Usage:
//   periodicity_engine CACHE_FILE LIMIT [OPTIONS] GEN...
//
// Prints P-hits for the base even part as they are found, plus a period
// certificate when detected.

#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <limits>
#include <queue>
#include <thread>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

using U64 = std::uint64_t;

volatile std::sig_atomic_t interrupt_requested = 0;

extern "C" void request_interrupt(int signal_number) {
    interrupt_requested = signal_number;
}

struct CampaignInterrupted {};

void throw_if_interrupted() {
    if (interrupt_requested != 0) throw CampaignInterrupted{};
}

constexpr U64 kRowCheckpointMagic = 0x53594c524f573031ULL;  // SYLROW01
constexpr U64 kRowCheckpointVersion = 1;
constexpr U64 kCheckpointCountLimit = 100000000ULL;

class CheckpointWriter {
  public:
    explicit CheckpointWriter(const std::string& path)
        : out_(path, std::ios::binary | std::ios::trunc) {
        if (!out_) throw std::runtime_error("cannot open checkpoint temporary file");
    }

    template <typename T>
    void pod(const T& value) {
        out_.write(reinterpret_cast<const char*>(&value), sizeof(value));
        if (!out_) throw std::runtime_error("cannot write checkpoint");
        hash_bytes(reinterpret_cast<const unsigned char*>(&value), sizeof(value));
    }

    void u64(U64 value) { pod(value); }
    void i32(int value) { pod(static_cast<std::int32_t>(value)); }
    void byte(std::uint8_t value) { pod(value); }

    void text(const std::string& value) {
        u64(value.size());
        out_.write(value.data(), static_cast<std::streamsize>(value.size()));
        if (!out_) throw std::runtime_error("cannot write checkpoint text");
        hash_bytes(
            reinterpret_cast<const unsigned char*>(value.data()), value.size());
    }

    void ints(const std::vector<int>& values) {
        u64(values.size());
        for (int value : values) i32(value);
    }

    void chars(const std::vector<char>& values) {
        u64(values.size());
        for (char value : values) byte(static_cast<std::uint8_t>(value));
    }

    void signed_chars(const std::vector<signed char>& values) {
        u64(values.size());
        for (signed char value : values)
            byte(static_cast<std::uint8_t>(value));
    }

    void finish() {
        out_.write(reinterpret_cast<const char*>(&hash_), sizeof(hash_));
        if (!out_) throw std::runtime_error("cannot write checkpoint checksum");
        out_.flush();
        if (!out_) throw std::runtime_error("cannot flush checkpoint");
        out_.close();
        if (!out_) throw std::runtime_error("cannot close checkpoint");
    }

  private:
    void hash_bytes(const unsigned char* data, std::size_t size) {
        for (std::size_t i = 0; i < size; ++i) {
            hash_ ^= data[i];
            hash_ *= 1099511628211ULL;
        }
    }

    std::ofstream out_;
    U64 hash_ = 14695981039346656037ULL;
};

class CheckpointReader {
  public:
    explicit CheckpointReader(const std::string& path)
        : in_(path, std::ios::binary) {
        if (!in_) throw std::runtime_error("cannot open checkpoint");
    }

    template <typename T>
    T pod() {
        T value{};
        in_.read(reinterpret_cast<char*>(&value), sizeof(value));
        if (!in_) throw std::runtime_error("truncated checkpoint");
        hash_bytes(reinterpret_cast<const unsigned char*>(&value), sizeof(value));
        return value;
    }

    U64 u64() { return pod<U64>(); }
    int i32() { return static_cast<int>(pod<std::int32_t>()); }
    std::uint8_t byte() { return pod<std::uint8_t>(); }

    U64 count() {
        const U64 value = u64();
        if (value > kCheckpointCountLimit)
            throw std::runtime_error("checkpoint count exceeds safety limit");
        return value;
    }

    std::string text() {
        const U64 size = count();
        if (size > 4096) throw std::runtime_error("checkpoint text is too long");
        std::string value(static_cast<std::size_t>(size), '\0');
        in_.read(value.data(), static_cast<std::streamsize>(size));
        if (!in_) throw std::runtime_error("truncated checkpoint text");
        hash_bytes(
            reinterpret_cast<const unsigned char*>(value.data()), value.size());
        return value;
    }

    std::vector<int> ints() {
        const U64 size = count();
        std::vector<int> values;
        values.reserve(static_cast<std::size_t>(size));
        for (U64 i = 0; i < size; ++i) values.push_back(i32());
        return values;
    }

    std::vector<char> chars() {
        const U64 size = count();
        std::vector<char> values;
        values.reserve(static_cast<std::size_t>(size));
        for (U64 i = 0; i < size; ++i)
            values.push_back(static_cast<char>(byte()));
        return values;
    }

    std::vector<signed char> signed_chars() {
        const U64 size = count();
        std::vector<signed char> values;
        values.reserve(static_cast<std::size_t>(size));
        for (U64 i = 0; i < size; ++i)
            values.push_back(static_cast<signed char>(byte()));
        return values;
    }

    void finish() {
        U64 expected_hash = 0;
        in_.read(reinterpret_cast<char*>(&expected_hash), sizeof(expected_hash));
        if (!in_) throw std::runtime_error("truncated checkpoint checksum");
        if (expected_hash != hash_)
            throw std::runtime_error("row checkpoint checksum mismatch");
        if (in_.peek() != std::char_traits<char>::eof())
            throw std::runtime_error("checkpoint has trailing data");
    }

  private:
    void hash_bytes(const unsigned char* data, std::size_t size) {
        for (std::size_t i = 0; i < size; ++i) {
            hash_ ^= data[i];
            hash_ *= 1099511628211ULL;
        }
    }

    std::ifstream in_;
    U64 hash_ = 14695981039346656037ULL;
};

int frobenius_of(const std::vector<int>& gens, int bound) {
    std::vector<char> reach(bound + 1, 0);
    reach[0] = 1;
    for (int v = 1; v <= bound; ++v)
        for (int g : gens)
            if (v >= g && reach[v - g]) { reach[v] = 1; break; }
    for (int v = bound; v >= 1; --v)
        if (!reach[v]) return v;
    return 0;
}

std::vector<int> minimal_generators(std::vector<int> values) {
    std::sort(values.begin(), values.end());
    values.erase(std::unique(values.begin(), values.end()), values.end());
    std::vector<int> out;
    int bound = values.empty() ? 0 : values.back();
    std::vector<char> reach(bound + 1, 0);
    reach[0] = 1;
    for (int v = 1; v <= bound; ++v) {
        for (int g : out)
            if (v >= g && reach[v - g]) { reach[v] = 1; break; }
        if (!reach[v] &&
            std::find(values.begin(), values.end(), v) != values.end()) {
            out.push_back(v);
            reach[v] = 1;
        }
    }
    return out;
}


// ---- embedded exact solver (ported unchanged from native_solver.cpp) ----
constexpr int kMaximumFrobenius = 1023;

template <std::size_t Words>
struct State {
    std::array<std::uint64_t, Words> words{};
    bool operator==(const State&) const = default;
    [[nodiscard]] bool test(int bit) const {
        return (words[static_cast<std::size_t>(bit / 64)] >> (bit % 64)) & 1U;
    }
    void set(int bit) {
        words[static_cast<std::size_t>(bit / 64)] |= std::uint64_t{1} << (bit % 64);
    }
};

template <std::size_t Words>
struct StateHash {
    [[nodiscard]] std::size_t operator()(
        const State<Words>& state
    ) const noexcept {
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

template <std::size_t Words>
[[nodiscard]] State<Words> shifted_left(const State<Words>& state, int shift) {
    State<Words> result;
    const int word_shift = shift / 64;
    const int bit_shift = shift % 64;
    for (int destination = static_cast<int>(Words) - 1;
         destination >= word_shift; --destination) {
        const int source = destination - word_shift;
        result.words[static_cast<std::size_t>(destination)] |=
            state.words[static_cast<std::size_t>(source)] << bit_shift;
        if (bit_shift != 0 && source > 0) {
            result.words[static_cast<std::size_t>(destination)] |=
                state.words[static_cast<std::size_t>(source - 1)] >> (64 - bit_shift);
        }
    }
    return result;
}

[[nodiscard]] int exact_frobenius(const std::vector<int>& generators) {
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
        if (value != distance[static_cast<std::size_t>(residue)]) continue;
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

template <std::size_t Words>
class ExactSolver {
  public:
    ExactSolver(std::vector<int> generators, int frobenius)
        : generators_(std::move(generators)), frobenius_(frobenius), mask_(make_mask()) {
        memo_.reserve(262144);
        initial_.set(0);
        for (const int generator : generators_) initial_ = adjoin(initial_, generator);
    }
    [[nodiscard]] int solve() { return winning_move(initial_); }
    // Hints reorder only the root-level search.  Any winning move is a valid
    // N-certificate, so a hint that wins is returned immediately; otherwise
    // the unmodified exhaustive loop decides.  Outcomes cannot change.
    [[nodiscard]] int solve(const std::vector<int>& hints) {
        if (const auto found = memo_.find(initial_); found != memo_.end())
            return found->second;
        for (const int hint : hints) {
            if (hint < 2 || hint > frobenius_ || initial_.test(hint)) continue;
            if (winning_move(adjoin(initial_, hint)) == 0) {
                memo_.emplace(initial_, static_cast<std::uint16_t>(hint));
                return hint;
            }
        }
        return winning_move(initial_);
    }
    [[nodiscard]] std::size_t states_evaluated() const { return memo_.size(); }

  private:
    [[nodiscard]] State<Words> make_mask() const {
        State<Words> mask;
        for (int bit = 0; bit <= frobenius_; ++bit) mask.set(bit);
        return mask;
    }
    [[nodiscard]] State<Words> adjoin(State<Words> state, int move) const {
        for (int shift = move; shift <= frobenius_;) {
            const State<Words> shifted = shifted_left(state, shift);
            for (std::size_t word = 0; word < Words; ++word)
                state.words[static_cast<std::size_t>(word)] |=
                    shifted.words[static_cast<std::size_t>(word)] &
                    mask_.words[static_cast<std::size_t>(word)];
            if (shift > frobenius_ / 2) break;
            shift *= 2;
        }
        return state;
    }
    [[nodiscard]] int winning_move(const State<Words>& state) {
        // A signal must never interrupt mutation of the recursive memo table.
        // Poll at recurrence boundaries and unwind normally instead.
        if (((++interrupt_polls_) & 0x3fffU) == 0) throw_if_interrupted();
        if (const auto found = memo_.find(state); found != memo_.end())
            return found->second;
        State<Words> paired_losers;
        for (int move = 2; move <= frobenius_; ++move) {
            if (state.test(move) || paired_losers.test(move)) continue;
            const State<Words> child = adjoin(state, move);
            const int response = winning_move(child);
            if (response == 0) {
                memo_.emplace(state, static_cast<std::uint16_t>(move));
                return move;
            }
            if (response > move) paired_losers.set(response);
        }
        memo_.emplace(state, std::uint16_t{0});
        return 0;
    }
    std::vector<int> generators_;
    int frobenius_;
    State<Words> mask_;
    State<Words> initial_;
    std::unordered_map<State<Words>, std::uint16_t, StateHash<Words>> memo_;
    U64 interrupt_polls_ = 0;
};

struct ExactResult {
    bool is_p;
    int winning_move;  // 0 when P
    std::size_t states;
};

template <std::size_t Words>
ExactResult solve_exact_with_words(
    const std::vector<int>& generators, int frobenius,
    const std::vector<int>& hints
) {
    ExactSolver<Words> solver(generators, frobenius);
    const int move = solver.solve(hints);
    return {move == 0, move, solver.states_evaluated()};
}

ExactResult solve_exact_position(
    const std::vector<int>& generators, int frobenius,
    const std::vector<int>& hints = {}
) {
    if (frobenius <= 63)
        return solve_exact_with_words<1>(generators, frobenius, hints);
    if (frobenius <= 127)
        return solve_exact_with_words<2>(generators, frobenius, hints);
    if (frobenius <= 255)
        return solve_exact_with_words<4>(generators, frobenius, hints);
    if (frobenius <= 511)
        return solve_exact_with_words<8>(generators, frobenius, hints);
    return solve_exact_with_words<16>(generators, frobenius, hints);
}

struct Engine {
    std::vector<int> base;       // full coordinates, gcd 2
    std::vector<int> half;
    int f = 0, tbar = 0, auto_min = 0;
    std::string cache_path;
    std::string row_checkpoint_path;
    int scanned_to = 1;
    U64 stop_after_evaluations = 0;

    // ---- even parts (oversemigroups of half, masks up to f) -------------
    // mask bit v set  <=>  half-value v is in the even part
    std::vector<std::vector<char>> emask;       // [eid][0..f]
    std::vector<std::vector<int>> egaps;        // half-gaps remaining
    std::vector<std::vector<int>> efill;        // lazy [eid][gap-index] -> eid'
    std::map<std::vector<char>, int> eindex;
    std::vector<int> first_p;       // first single-anchor P-hit per even part
    std::vector<int> history_to;    // single-anchor history evaluated through
    std::vector<int> single_sid;    // singleton shape id per even part

    int register_epart(std::vector<char> mask) {
        // close under addition within [1, f]
        bool changed = true;
        while (changed) {
            changed = false;
            for (int v = 1; v <= f; ++v) {
                if (mask[v]) continue;
                for (int w = 1; w < v; ++w)
                    if (mask[w] && mask[v - w]) { mask[v] = 1; changed = true; break; }
            }
        }
        auto it = eindex.find(mask);
        if (it != eindex.end()) return it->second;
        int id = static_cast<int>(emask.size());
        eindex.emplace(mask, id);
        emask.push_back(mask);
        std::vector<int> gaps;
        for (int v = 1; v <= f; ++v)
            if (!mask[v]) gaps.push_back(v);
        egaps.push_back(gaps);
        efill.emplace_back(gaps.size(), -1);
        first_p.push_back(std::numeric_limits<int>::max());
        history_to.push_back(1);
        single_sid.push_back(-1);
        if (id != 0 && id % 100 == 0)
            std::cout << "EPARTS count=" << id
                      << " shapes=" << shapes.size()
                      << " scanned_to=" << scanned_to << std::endl;
        return id;
    }

    int fill_epart(int eid, std::size_t gap_index) {
        if (efill[eid][gap_index] >= 0) return efill[eid][gap_index];
        const int gap = egaps[eid][gap_index];
        std::vector<char> mask = emask[eid];
        mask[gap] = 1;
        const int result = register_epart(std::move(mask));
        efill[eid][gap_index] = result;
        return result;
    }

    bool even_member(int eid, int diff) const {  // diff even, full coords
        int h = diff / 2;
        if (h > f) return true;
        if (h <= 0) return false;
        return emask[eid][h];
    }

    // ---- shapes ----------------------------------------------------------
    struct OddOption {
        std::vector<int> offsets;
        int dmin = 0;
        int child = -1;
    };

    struct Shape {
        int eid;
        std::vector<int> offsets;               // even, offsets[0] == 0
        // Transition specifications are cached without materializing their
        // child shapes.  Children are registered only when evaluation reaches
        // the corresponding option, matching the executable specification.
        bool built = false;
        std::vector<OddOption> odd_options;
        std::vector<int> even_children;          // -1 until that option is used
    };
    std::vector<Shape> shapes;
    std::map<std::pair<int, std::vector<int>>, int> shape_index;

    int register_shape(int eid, const std::vector<int>& offsets) {
        auto key = std::make_pair(eid, offsets);
        auto it = shape_index.find(key);
        if (it != shape_index.end()) return it->second;
        int id = static_cast<int>(shapes.size());
        shape_index.emplace(key, id);
        Shape s; s.eid = eid; s.offsets = offsets;
        shapes.push_back(std::move(s));
        ring.emplace_back(window_slots, -1);
        value_stamp.emplace_back(window_slots, -1);
        if (offsets.size() == 1) single_sid[eid] = id;
        if (id != 0 && id % 10000 == 0)
            std::cout << "SHAPES count=" << id
                      << " eparts=" << emask.size()
                      << " scanned_to=" << scanned_to << std::endl;
        return id;
    }

    std::vector<int> canonical(int eid, std::vector<int> anchors) const {
        std::sort(anchors.begin(), anchors.end());
        std::vector<int> live;
        for (int a : anchors) {
            bool absorbed = false;
            for (int b : live)
                if (even_member(eid, a - b)) { absorbed = true; break; }
            if (!absorbed) live.push_back(a);
        }
        return live;
    }

    // ---- ring buffer of outcomes ----------------------------------------
    // ring[shape][slot(m)] in {-1 unknown, 0 N, 1 P}; slot = (m/2) % window_slots
    int window_slots = 0;
    std::vector<std::vector<signed char>> ring;
    U64 evaluation_calls = 0;
    // A newly discovered even part reconstructs its singleton history back
    // to 3.  That can revisit dependencies older than the bounded recurrence
    // ring and otherwise thrash entries that were computed earlier in the
    // same outer row.  Retain those exact values only until the row closes;
    // long scans still use bounded memory between rows.
    std::unordered_map<U64, signed char> row_memo;
    int slot_of(int m) const { return (m / 2) % window_slots; }
    static U64 row_memo_key(int sid, int m) {
        return (static_cast<U64>(static_cast<std::uint32_t>(sid)) << 32)
             | static_cast<std::uint32_t>(m);
    }
    void begin_row() {
        row_memo.clear();
        if (row_memo.bucket_count() == 1) row_memo.reserve(262144);
    }
    void end_row() { row_memo.clear(); }
    std::set<int> base_p_hits;

    // ---- base-region exact outcomes -------------------------------------
    std::unordered_map<std::string, bool> base_cache;
    int external_cache_max_anchor = 1;
    bool dirty_cache = false;
    // Batch-parallel exact fallbacks.  In collect mode a base-region cache
    // miss is queued instead of solved inline; unknown (-1) values are never
    // written to the ring, row memo, or first_p, so the period certificate
    // remains a function of exact outcomes only.  Pending work is transient
    // and never checkpointed: an interrupt simply re-collects on resume.
    int exact_threads = 1;
    bool memory_report_enabled = false;
    bool collect_mode = false;
    // Solve a batch as soon as this many positions are pending instead of
    // waiting for a complete sweep.  Early batches surface P outcomes whose
    // first_p reset flags prune sibling expansion, shrinking the closure
    // and bounding memory; correctness is unaffected because the collect
    // loop still terminates only on a complete sweep with zero pending.
    std::size_t batch_pending = 20000;
    std::vector<std::pair<std::string, std::vector<int>>> pending;
    std::set<std::string> pending_keys;
    // Recent distinct root winners; outcome-invariant reordering only.
    std::vector<int> hint_pool;
    // Transient per-sweep memo of unknown (sid,m) nodes.  Without it every
    // sweep entry re-derives the whole unknown-poisoned region down to the
    // same pending misses and the first sweep never terminates.  Cleared
    // before each re-sweep, never checkpointed, never an outcome.
    std::set<U64> unknown_memo;
    U64 exact_completed = 0;
    U64 exact_states = 0;

    void load_cache() {
        std::ifstream in(cache_path);
        std::string key; int val;
        while (in >> key >> val) {
            base_cache[key] = (val != 0);
            std::istringstream generators(key);
            std::string token;
            while (std::getline(generators, token, ','))
                external_cache_max_anchor = std::max(
                    external_cache_max_anchor, std::stoi(token));
        }
    }
    void save_cache() {
        if (!dirty_cache) return;
        const std::string temporary_path = cache_path + ".tmp";
        std::ofstream out(temporary_path, std::ios::trunc);
        if (!out) {
            std::cerr << "cannot open temporary cache: " << temporary_path << "\n";
            std::exit(2);
        }
        for (auto& kv : base_cache)
            out << kv.first << ' ' << (kv.second ? 1 : 0) << '\n';
        out.close();
        if (!out) {
            std::cerr << "cannot write temporary cache: " << temporary_path << "\n";
            std::exit(2);
        }
        if (std::rename(temporary_path.c_str(), cache_path.c_str()) != 0) {
            std::cerr << "cannot replace cache: " << cache_path << "\n";
            std::exit(2);
        }
        dirty_cache = false;
    }

    void save_row_checkpoint(int active_n) const {
        const std::string temporary_path = row_checkpoint_path + ".tmp";
        CheckpointWriter out(temporary_path);
        out.u64(kRowCheckpointMagic);
        out.u64(kRowCheckpointVersion);
        out.ints(base);
        out.i32(f);
        out.i32(tbar);
        out.i32(auto_min);
        out.i32(window_slots);
        out.i32(active_n);
        out.i32(scanned_to);

        // These are dependencies of already-computed row values.  A resume
        // may have a larger cache, but it must contain this exact subset.
        out.u64(base_cache.size());
        for (const auto& [key, value] : base_cache) {
            out.text(key);
            out.byte(value ? 1 : 0);
        }

        out.u64(emask.size());
        for (const auto& mask : emask) out.chars(mask);
        out.u64(efill.size());
        for (const auto& row : efill) out.ints(row);
        out.ints(first_p);
        out.ints(history_to);

        out.u64(shapes.size());
        for (const Shape& shape : shapes) {
            out.i32(shape.eid);
            out.ints(shape.offsets);
            out.byte(shape.built ? 1 : 0);
            out.u64(shape.odd_options.size());
            for (const OddOption& option : shape.odd_options) {
                out.ints(option.offsets);
                out.i32(option.dmin);
                out.i32(option.child);
            }
            out.ints(shape.even_children);
        }

        out.u64(ring.size());
        for (const auto& row : ring) out.signed_chars(row);
        out.u64(value_stamp.size());
        for (const auto& row : value_stamp) out.ints(row);
        out.u64(evaluation_calls);
        out.u64(exact_completed);
        out.u64(exact_states);

        out.u64(row_memo.size());
        for (const auto& [key, value] : row_memo) {
            out.u64(key);
            out.byte(static_cast<std::uint8_t>(value));
        }
        out.u64(base_p_hits.size());
        for (int hit : base_p_hits) out.i32(hit);
        out.finish();
        if (std::rename(temporary_path.c_str(), row_checkpoint_path.c_str()) != 0)
            throw std::runtime_error(
                "cannot replace row checkpoint: " +
                std::string(std::strerror(errno)));
    }

    bool load_row_checkpoint(int& active_n) {
        std::ifstream probe(row_checkpoint_path, std::ios::binary);
        if (!probe) return false;
        probe.close();

        CheckpointReader in(row_checkpoint_path);
        if (in.u64() != kRowCheckpointMagic)
            throw std::runtime_error("row checkpoint has wrong magic");
        if (in.u64() != kRowCheckpointVersion)
            throw std::runtime_error("unsupported row checkpoint version");
        if (in.ints() != base || in.i32() != f || in.i32() != tbar
            || in.i32() != auto_min || in.i32() != window_slots)
            throw std::runtime_error("row checkpoint belongs to another engine");
        active_n = in.i32();
        const int loaded_scanned_to = in.i32();
        if (active_n < 3 || active_n % 2 == 0
            || loaded_scanned_to < 1 || loaded_scanned_to % 2 == 0
            || active_n != loaded_scanned_to + 2)
            throw std::runtime_error("row checkpoint has invalid scan frontier");

        const U64 required_cache_size = in.count();
        for (U64 i = 0; i < required_cache_size; ++i) {
            const std::string key = in.text();
            const std::uint8_t raw_value = in.byte();
            if (raw_value > 1)
                throw std::runtime_error("row checkpoint has invalid cache outcome");
            const auto found = base_cache.find(key);
            if (found == base_cache.end() || found->second != (raw_value != 0))
                throw std::runtime_error(
                    "current cache does not contain checkpoint dependency " + key);
        }

        const U64 epart_count = in.count();
        std::vector<std::vector<char>> loaded_emask;
        loaded_emask.reserve(static_cast<std::size_t>(epart_count));
        for (U64 i = 0; i < epart_count; ++i)
            loaded_emask.push_back(in.chars());
        const U64 fill_count = in.count();
        std::vector<std::vector<int>> loaded_efill;
        loaded_efill.reserve(static_cast<std::size_t>(fill_count));
        for (U64 i = 0; i < fill_count; ++i)
            loaded_efill.push_back(in.ints());
        std::vector<int> loaded_first_p = in.ints();
        std::vector<int> loaded_history_to = in.ints();
        if (epart_count == 0 || fill_count != epart_count
            || loaded_first_p.size() != epart_count
            || loaded_history_to.size() != epart_count)
            throw std::runtime_error("row checkpoint has inconsistent even parts");
        if (loaded_emask.front() != base_member_mask)
            throw std::runtime_error("row checkpoint has wrong base even part");

        std::vector<std::vector<int>> loaded_egaps;
        std::map<std::vector<char>, int> loaded_eindex;
        loaded_egaps.reserve(static_cast<std::size_t>(epart_count));
        for (std::size_t eid = 0; eid < loaded_emask.size(); ++eid) {
            const auto& mask = loaded_emask[eid];
            if (mask.size() != static_cast<std::size_t>(f + 1))
                throw std::runtime_error("row checkpoint has invalid even mask");
            for (char value : mask)
                if (value != 0 && value != 1)
                    throw std::runtime_error("row checkpoint has non-Boolean mask");
            if (mask.front() != 1)
                throw std::runtime_error("checkpoint even part omits zero");
            for (int value = 0; value <= f; ++value)
                if (base_member_mask[static_cast<std::size_t>(value)]
                    && !mask[static_cast<std::size_t>(value)])
                    throw std::runtime_error(
                        "checkpoint even part does not contain the base");
            for (int left = 1; left <= f; ++left)
                if (mask[static_cast<std::size_t>(left)])
                    for (int right = 1; right <= f - left; ++right)
                        if (mask[static_cast<std::size_t>(right)]
                            && !mask[static_cast<std::size_t>(left + right)])
                            throw std::runtime_error(
                                "checkpoint even part is not addition-closed");
            std::vector<int> gaps;
            for (int value = 1; value <= f; ++value)
                if (!mask[static_cast<std::size_t>(value)]) gaps.push_back(value);
            if (loaded_efill[eid].size() != gaps.size())
                throw std::runtime_error("row checkpoint has invalid fill table");
            for (int child : loaded_efill[eid])
                if (child < -1 || child >= static_cast<int>(epart_count))
                    throw std::runtime_error("row checkpoint has invalid even child");
            if (!loaded_eindex.emplace(mask, static_cast<int>(eid)).second)
                throw std::runtime_error("row checkpoint has duplicate even parts");
            loaded_egaps.push_back(std::move(gaps));
        }
        for (std::size_t eid = 0; eid < loaded_emask.size(); ++eid) {
            for (std::size_t index = 0; index < loaded_efill[eid].size(); ++index) {
                const int child = loaded_efill[eid][index];
                if (child < 0) continue;
                std::vector<char> expected = loaded_emask[eid];
                expected[static_cast<std::size_t>(loaded_egaps[eid][index])] = 1;
                bool changed = true;
                while (changed) {
                    changed = false;
                    for (int value = 1; value <= f; ++value) {
                        if (expected[static_cast<std::size_t>(value)]) continue;
                        for (int left = 1; left < value; ++left)
                            if (expected[static_cast<std::size_t>(left)]
                                && expected[static_cast<std::size_t>(value - left)]) {
                                expected[static_cast<std::size_t>(value)] = 1;
                                changed = true;
                                break;
                            }
                    }
                }
                if (expected != loaded_emask[static_cast<std::size_t>(child)])
                    throw std::runtime_error(
                        "row checkpoint has inconsistent even fill edge");
            }
        }

        const U64 shape_count = in.count();
        std::vector<Shape> loaded_shapes;
        loaded_shapes.reserve(static_cast<std::size_t>(shape_count));
        for (U64 i = 0; i < shape_count; ++i) {
            Shape shape;
            shape.eid = in.i32();
            shape.offsets = in.ints();
            const std::uint8_t built = in.byte();
            if (built > 1)
                throw std::runtime_error("row checkpoint has invalid shape flag");
            shape.built = built != 0;
            const U64 odd_count = in.count();
            shape.odd_options.reserve(static_cast<std::size_t>(odd_count));
            for (U64 j = 0; j < odd_count; ++j) {
                OddOption option;
                option.offsets = in.ints();
                option.dmin = in.i32();
                option.child = in.i32();
                shape.odd_options.push_back(std::move(option));
            }
            shape.even_children = in.ints();
            loaded_shapes.push_back(std::move(shape));
        }

        std::map<std::pair<int, std::vector<int>>, int> loaded_shape_index;
        std::vector<int> loaded_single_sid(
            static_cast<std::size_t>(epart_count), -1);
        const auto valid_offsets = [](const std::vector<int>& offsets) {
            if (offsets.empty() || offsets.front() != 0) return false;
            for (std::size_t i = 1; i < offsets.size(); ++i)
                if (offsets[i] <= offsets[i - 1] || offsets[i] % 2 != 0)
                    return false;
            return true;
        };
        for (std::size_t sid = 0; sid < loaded_shapes.size(); ++sid) {
            const Shape& shape = loaded_shapes[sid];
            if (shape.eid < 0 || shape.eid >= static_cast<int>(epart_count)
                || !valid_offsets(shape.offsets))
                throw std::runtime_error("row checkpoint has invalid shape");
            if (!shape.built
                && (!shape.odd_options.empty() || !shape.even_children.empty()))
                throw std::runtime_error("unbuilt checkpoint shape has transitions");
            if (shape.built
                && shape.even_children.size()
                       != loaded_egaps[static_cast<std::size_t>(shape.eid)].size())
                throw std::runtime_error("checkpoint shape has invalid transitions");
            for (const OddOption& option : shape.odd_options)
                if (!valid_offsets(option.offsets) || option.child < -1
                    || option.child >= static_cast<int>(shape_count))
                    throw std::runtime_error("row checkpoint has invalid odd option");
            for (int child : shape.even_children)
                if (child < -1 || child >= static_cast<int>(shape_count))
                    throw std::runtime_error("row checkpoint has invalid shape child");
            const auto key = std::make_pair(shape.eid, shape.offsets);
            if (!loaded_shape_index.emplace(key, static_cast<int>(sid)).second)
                throw std::runtime_error("row checkpoint has duplicate shapes");
            if (shape.offsets.size() == 1)
                loaded_single_sid[static_cast<std::size_t>(shape.eid)] =
                    static_cast<int>(sid);
        }
        if (loaded_shapes.empty() || loaded_shapes.front().eid != 0
            || loaded_shapes.front().offsets != std::vector<int>{0})
            throw std::runtime_error("row checkpoint has wrong base shape");
        for (const Shape& shape : loaded_shapes) {
            for (const OddOption& option : shape.odd_options)
                if (option.child >= 0) {
                    const Shape& child =
                        loaded_shapes[static_cast<std::size_t>(option.child)];
                    if (child.eid != shape.eid || child.offsets != option.offsets)
                        throw std::runtime_error(
                            "row checkpoint has inconsistent odd transition");
                }
            for (std::size_t index = 0;
                 index < shape.even_children.size(); ++index) {
                const int child = shape.even_children[index];
                if (child >= 0) {
                    const int child_eid = loaded_efill[
                        static_cast<std::size_t>(shape.eid)][index];
                    if (child_eid < 0
                        || loaded_shapes[static_cast<std::size_t>(child)].eid
                               != child_eid)
                        throw std::runtime_error(
                            "row checkpoint has inconsistent even transition");
                }
            }
        }

        const U64 ring_count = in.count();
        std::vector<std::vector<signed char>> loaded_ring;
        loaded_ring.reserve(static_cast<std::size_t>(ring_count));
        for (U64 i = 0; i < ring_count; ++i)
            loaded_ring.push_back(in.signed_chars());
        const U64 stamp_count = in.count();
        std::vector<std::vector<int>> loaded_value_stamp;
        loaded_value_stamp.reserve(static_cast<std::size_t>(stamp_count));
        for (U64 i = 0; i < stamp_count; ++i)
            loaded_value_stamp.push_back(in.ints());
        if (ring_count != shape_count || stamp_count != shape_count)
            throw std::runtime_error("row checkpoint has inconsistent ring tables");
        for (std::size_t sid = 0; sid < loaded_ring.size(); ++sid) {
            if (loaded_ring[sid].size() != static_cast<std::size_t>(window_slots)
                || loaded_value_stamp[sid].size()
                       != static_cast<std::size_t>(window_slots))
                throw std::runtime_error("row checkpoint has invalid ring width");
            for (signed char value : loaded_ring[sid])
                if (value < -1 || value > 1)
                    throw std::runtime_error("row checkpoint has invalid outcome");
        }
        const U64 loaded_evaluation_calls = in.u64();
        const U64 loaded_exact_completed = in.u64();
        const U64 loaded_exact_states = in.u64();

        const U64 memo_count = in.count();
        std::unordered_map<U64, signed char> loaded_row_memo;
        loaded_row_memo.reserve(static_cast<std::size_t>(memo_count));
        for (U64 i = 0; i < memo_count; ++i) {
            const U64 key = in.u64();
            const signed char value = static_cast<signed char>(in.byte());
            const U64 sid = key >> 32;
            const U64 memo_m = key & 0xffffffffULL;
            if (sid >= shape_count || memo_m < 3
                || memo_m > static_cast<U64>(active_n) || memo_m % 2 == 0
                || (value != 0 && value != 1)
                || !loaded_row_memo.emplace(key, value).second)
                throw std::runtime_error("row checkpoint has invalid row memo");
        }
        const U64 hit_count = in.count();
        std::set<int> loaded_base_p_hits;
        for (U64 i = 0; i < hit_count; ++i)
            if (!loaded_base_p_hits.insert(in.i32()).second)
                throw std::runtime_error("row checkpoint has duplicate P-hits");
        in.finish();

        emask = std::move(loaded_emask);
        egaps = std::move(loaded_egaps);
        efill = std::move(loaded_efill);
        eindex = std::move(loaded_eindex);
        first_p = std::move(loaded_first_p);
        history_to = std::move(loaded_history_to);
        single_sid = std::move(loaded_single_sid);
        shapes = std::move(loaded_shapes);
        shape_index = std::move(loaded_shape_index);
        ring = std::move(loaded_ring);
        value_stamp = std::move(loaded_value_stamp);
        evaluation_calls = loaded_evaluation_calls;
        exact_completed = loaded_exact_completed;
        exact_states = loaded_exact_states;
        row_memo = std::move(loaded_row_memo);
        base_p_hits = std::move(loaded_base_p_hits);
        scanned_to = loaded_scanned_to;
        return true;
    }

    void remove_row_checkpoint() const {
        if (std::remove(row_checkpoint_path.c_str()) != 0 && errno != ENOENT)
            throw std::runtime_error(
                "cannot remove completed row checkpoint: " +
                std::string(std::strerror(errno)));
    }

    static std::string generator_key(const std::vector<int>& gens) {
        std::ostringstream out;
        for (std::size_t i = 0; i < gens.size(); ++i)
            out << (i ? "," : "") << gens[i];
        return out.str();
    }

    void load_base_record(const std::string& path) {
        std::ifstream in(path);
        if (!in) {
            std::cerr << "cannot open base record: " << path << "\n";
            std::exit(2);
        }
        std::string line;
        int loaded = 0;
        while (std::getline(in, line)) {
            std::istringstream row(line);
            std::string move_token, outcome, winner_token;
            if (!(row >> move_token >> outcome >> winner_token)
                || move_token.rfind("move=", 0) != 0
                || (outcome != "P" && outcome != "N")) {
                std::cerr << "malformed base-record row: " << line << "\n";
                std::exit(2);
            }
            const int move = std::stoi(move_token.substr(5));
            if (move < 3 || move % 2 == 0) {
                std::cerr << "invalid odd move in base record: " << move << "\n";
                std::exit(2);
            }
            std::vector<int> gens = base;
            gens.push_back(move);
            gens = minimal_generators(std::move(gens));
            const std::string key = generator_key(gens);
            const bool value = outcome == "P";
            if (const auto found = base_cache.find(key);
                found != base_cache.end() && found->second != value) {
                std::cerr << "base record conflicts with cache for " << key << "\n";
                std::exit(2);
            }
            base_cache[key] = value;
            external_cache_max_anchor = std::max(external_cache_max_anchor, move);
            if (outcome == "N" && winner_token.rfind("winning_move=", 0) == 0) {
                const std::string winner_value = winner_token.substr(13);
                if (winner_value != "null") {
                    const int winner = std::stoi(winner_value);
                    std::vector<int> child = base;
                    child.push_back(move);
                    child.push_back(winner);
                    child = minimal_generators(std::move(child));
                    const std::string child_key = generator_key(child);
                    if (const auto found = base_cache.find(child_key);
                        found != base_cache.end() && !found->second) {
                        std::cerr << "winning destination conflicts with cache for "
                                  << child_key << "\n";
                        std::exit(2);
                    }
                    base_cache[child_key] = true;
                    external_cache_max_anchor = std::max(
                        external_cache_max_anchor, winner);
                }
            }
            ++loaded;
        }
        std::cout << "base-record path=" << path << " rows=" << loaded << "\n";
    }

    bool exact_outcome(int eid, const std::vector<int>& anchors) {
        std::vector<int> gens = position_generators(eid, anchors);
        const std::string key = generator_key(gens);
        auto it = base_cache.find(key);
        if (it != base_cache.end()) return it->second;
        const int frob = exact_frobenius(gens);
        if (frob > kMaximumFrobenius) {
            std::cerr << "base position exceeds solver capacity: "
                      << key << "\n";
            std::exit(2);
        }
        const bool verbose = frob >= 180;
        if (verbose)
            std::cout << "EXACT begin key=" << key
                      << " f=" << frob << std::endl;
        const ExactResult exact = solve_exact_position(gens, frob, hint_pool);
        ++exact_completed;
        exact_states += exact.states;
        if (verbose) {
            std::cout << "EXACT end key=" << key
                      << " outcome=" << (exact.is_p ? "P" : "N")
                      << " states=" << exact.states << std::endl;
        } else if (exact_completed % 1000 == 0) {
            std::cout << "EXACT progress completed=" << exact_completed
                      << " states=" << exact_states
                      << " cache=" << (base_cache.size() + 1) << std::endl;
        }
        base_cache[key] = exact.is_p;
        dirty_cache = true;
        record_hint(exact.winning_move);
        // Finite fallbacks dominate runtime on hard fronts.  Persist each
        // completed result immediately so an interrupted tail run never has
        // to repeat a multi-minute exact subgame.
        save_cache();
        return exact.is_p;
    }

    signed char exact_or_collect(int eid, const std::vector<int>& anchors) {
        std::vector<int> gens = position_generators(eid, anchors);
        const std::string key = generator_key(gens);
        if (const auto it = base_cache.find(key); it != base_cache.end())
            return it->second ? 1 : 0;
        if (!collect_mode) return exact_outcome(eid, anchors) ? 1 : 0;
        // Cap the batch: one deep recursion can otherwise gather millions
        // of pending positions before the sweep-level threshold is seen.
        // A capped-out miss simply stays unknown and re-collects after the
        // next batch resolves part of the frontier.
        if (pending.size() < batch_pending * 4
            && pending_keys.insert(key).second)
            pending.emplace_back(key, std::move(gens));
        return -1;
    }

    void record_hint(int winner) {
        if (winner <= 0) return;
        for (const int existing : hint_pool)
            if (existing == winner) return;
        hint_pool.push_back(winner);
        if (hint_pool.size() > 16)
            hint_pool.erase(hint_pool.begin());
    }

    void solve_pending_parallel() {
        struct Item {
            std::string key;
            std::vector<int> gens;
            int frobenius = 0;
            bool done = false;
            ExactResult result{};
        };
        std::vector<Item> items;
        items.reserve(pending.size());
        for (auto& [key, gens] : pending) {
            Item item;
            item.key = key;
            item.gens = std::move(gens);
            item.frobenius = exact_frobenius(item.gens);
            if (item.frobenius > kMaximumFrobenius) {
                std::cerr << "base position exceeds solver capacity: "
                          << item.key << "\n";
                std::exit(2);
            }
            items.push_back(std::move(item));
        }
        pending.clear();
        pending_keys.clear();
        const std::vector<int> hints = hint_pool;  // frozen for the batch
        std::atomic<std::size_t> next{0};
        std::vector<std::thread> pool;
        const std::size_t width = std::min<std::size_t>(
            static_cast<std::size_t>(exact_threads), items.size());
        for (std::size_t t = 0; t < width; ++t)
            pool.emplace_back([&items, &next, &hints]() {
                for (;;) {
                    const std::size_t i = next.fetch_add(1);
                    if (i >= items.size() || interrupt_requested != 0) return;
                    try {
                        items[i].result = solve_exact_position(
                            items[i].gens, items[i].frobenius, hints);
                        items[i].done = true;
                    } catch (const CampaignInterrupted&) {
                        return;
                    }
                }
            });
        for (std::thread& worker : pool) worker.join();
        for (const Item& item : items) {
            if (!item.done) continue;
            ++exact_completed;
            exact_states += item.result.states;
            base_cache[item.key] = item.result.is_p;
            record_hint(item.result.winning_move);
            if (item.frobenius >= 180)
                std::cout << "EXACT end key=" << item.key
                          << " outcome=" << (item.result.is_p ? "P" : "N")
                          << " states=" << item.result.states << std::endl;
            else if (exact_completed % 1000 == 0)
                std::cout << "EXACT progress completed=" << exact_completed
                          << " states=" << exact_states
                          << " cache=" << base_cache.size() << std::endl;
        }
        dirty_cache = true;
        save_cache();
        // Completed work is merged and saved; now honor any pending signal.
        throw_if_interrupted();
    }

    std::vector<int> position_generators(
        int eid, const std::vector<int>& anchors
    ) const {
        std::vector<int> gens = base;
        for (int v = 1; v <= f; ++v)
            if (emask[eid][v] && !base_member(v)) gens.push_back(2 * v);
        for (int a : anchors) gens.push_back(a);
        return minimal_generators(std::move(gens));
    }

    std::optional<bool> cached_outcome(
        int eid, const std::vector<int>& anchors
    ) const {
        const std::string key = generator_key(position_generators(eid, anchors));
        if (const auto found = base_cache.find(key); found != base_cache.end())
            return found->second;
        return std::nullopt;
    }

    std::vector<char> base_member_mask;
    bool base_member(int halfval) const { return base_member_mask[halfval]; }

    // Exact capacity-based byte accounting per subsystem.  The report is
    // diagnostic only; it never affects outcomes or checkpoints.
    void memory_report() const {
        auto vec_bytes = [](const auto& v) {
            return v.capacity() * sizeof(v[0]);
        };
        std::size_t shapes_core = shapes.capacity() * sizeof(Shape);
        std::size_t transitions = 0;
        for (const Shape& s : shapes) {
            shapes_core += vec_bytes(s.offsets);
            transitions += s.odd_options.capacity() * sizeof(OddOption);
            for (const OddOption& o : s.odd_options)
                transitions += vec_bytes(o.offsets);
            transitions += vec_bytes(s.even_children);
        }
        // std::map node: payload + two pointers-ish of bookkeeping; use a
        // conservative fixed node overhead of 48 bytes plus key storage.
        std::size_t index = 0;
        for (const auto& [key, sid] : shape_index) {
            (void)sid;
            index += 48 + sizeof(key) + vec_bytes(key.second);
        }
        std::size_t ring_bytes = ring.capacity() * sizeof(ring[0]);
        for (const auto& r : ring) ring_bytes += vec_bytes(r);
        std::size_t stamp_bytes = value_stamp.capacity() * sizeof(value_stamp[0]);
        for (const auto& s : value_stamp) stamp_bytes += vec_bytes(s);
        std::size_t memo = row_memo.bucket_count() * sizeof(void*)
            + row_memo.size() * (sizeof(std::pair<U64, signed char>) + 16);
        std::size_t cache_bytes = 0;
        for (const auto& [key, value] : base_cache) {
            (void)value;
            cache_bytes += 64 + key.capacity();
        }
        std::size_t eparts = 0;
        for (const auto& m : emask) eparts += vec_bytes(m);
        for (const auto& [key, eid] : eindex) {
            (void)eid;
            eparts += 48 + vec_bytes(key);
        }
        const std::size_t total = shapes_core + transitions + index
            + ring_bytes + stamp_bytes + memo + cache_bytes + eparts;
        std::cout << "MEMORY total=" << total
                  << " shapes=" << shapes_core
                  << " transitions=" << transitions
                  << " index=" << index
                  << " ring=" << ring_bytes
                  << " stamps=" << stamp_bytes
                  << " memo=" << memo
                  << " basecache=" << cache_bytes
                  << " eparts=" << eparts
                  << " nshapes=" << shapes.size()
                  << std::endl;
    }

    // Returns true when the singleton history is complete through
    // scanned_to.  In collect mode an evaluation may be unknown; the
    // history must then stop advancing, or a missed P would silently
    // corrupt the first_p reset flag that the recurrence's outcomes
    // depend on.  Callers treat an incomplete history as unknown.
    bool ensure_single_history(int eid) {
        int sid = single_sid[eid];
        if (sid < 0) sid = register_shape(eid, {0});
        for (int m = history_to[eid] + 2; m <= scanned_to; m += 2) {
            if (evaluate(sid, m) < 0) return false;
            history_to[eid] = m;
        }
        return true;
    }

    // ---- transitions -----------------------------------------------------
    void build_transition_specs(int sid) {
        if (shapes[sid].built) return;
        const int eid = shapes[sid].eid;
        const std::vector<int> offsets = shapes[sid].offsets;  // copy
        const int top = offsets.back();
        std::vector<OddOption> odd_options;
        const int BASEM = 1 << 20;   // large virtual anchor for arithmetic
        for (int r = -tbar; r <= top + tbar; r += 2) {
            if (r == 0) continue;
            if (std::find(offsets.begin(), offsets.end(), r) != offsets.end())
                continue;
            bool illegal = false;
            for (int o : offsets)
                if (o < r && even_member(eid, r - o)) { illegal = true; break; }
            if (illegal) continue;
            std::vector<int> anchors;
            for (int o : offsets) anchors.push_back(BASEM + o);
            anchors.push_back(BASEM + r);
            anchors = canonical(eid, anchors);
            int nmin = anchors.front();
            std::vector<int> noff;
            for (int a : anchors) noff.push_back(a - nmin);
            odd_options.push_back({std::move(noff), nmin - BASEM, -1});
        }
        shapes[sid].odd_options = std::move(odd_options);
        shapes[sid].even_children.assign(egaps[eid].size(), -1);
        shapes[sid].built = true;
    }

    // evaluate shape sid at minimum anchor m (requires deps at smaller m done,
    // or base region); returns 1 for P, 0 for N
    signed char evaluate(int sid, int m) {
        ++evaluation_calls;
        if (interrupt_requested != 0
            || (stop_after_evaluations != 0
                && evaluation_calls >= stop_after_evaluations))
            throw CampaignInterrupted{};
        if (evaluation_calls % 10000000 == 0)
            std::cout << "EVALUATIONS count=" << evaluation_calls
                      << " sid=" << sid
                      << " m=" << m
                      << " shapes=" << shapes.size()
                      << " eparts=" << emask.size() << std::endl;
        signed char ring_value = ring[sid][slot_of(m)];
        if (ring_value >= 0 && value_stamp[sid][slot_of(m)] == m)
            return ring_value;
        const U64 memo_key = row_memo_key(sid, m);
        if (const auto found = row_memo.find(memo_key);
            found != row_memo.end())
            return found->second;
        if (collect_mode
            && unknown_memo.find(memo_key) != unknown_memo.end())
            return -1;
        signed char result;
        std::vector<int> anchors;
        for (int o : shapes[sid].offsets) anchors.push_back(m + o);
        const std::optional<bool> cached = cached_outcome(
            shapes[sid].eid, anchors);
        if (cached.has_value()) {
            result = *cached ? 1 : 0;
        } else if (m < auto_min) {
            result = exact_or_collect(shapes[sid].eid, anchors);
            if (result < 0) {
                unknown_memo.insert(memo_key);
                return -1;  // pending exact dependency; write nothing else
            }
        } else {
            const int eid = shapes[sid].eid;
            bool winning = first_p[eid] <= m - tbar - 2;
            bool saw_unknown = false;
            if (!winning) {
                build_transition_specs(sid);
                const std::size_t odd_count = shapes[sid].odd_options.size();
                for (std::size_t index = 0; index < odd_count; ++index) {
                    // Recursive evaluation can reallocate shapes, so copy the
                    // descriptor and write cached ids back by index.
                    const int dmin = shapes[sid].odd_options[index].dmin;
                    int child = shapes[sid].odd_options[index].child;
                    if (child < 0) {
                        const auto offsets = shapes[sid].odd_options[index].offsets;
                        child = register_shape(eid, offsets);
                        shapes[sid].odd_options[index].child = child;
                    }
                    const int cm = m + dmin;
                    signed char cv;
                    if (cm == m && child == sid) continue;  // defensive
                    if (dmin == 0) cv = evaluate(child, m);
                    else {
                        cv = ring[child][slot_of(cm)];
                        if (cv < 0 || value_stamp[child][slot_of(cm)] != cm)
                            cv = evaluate(child, cm);
                    }
                    if (cv == 1) { winning = true; break; }
                    if (cv < 0) saw_unknown = true;
                }
            }
            if (!winning) {
                const std::size_t even_count = shapes[sid].even_children.size();
                const int BASEM = 1 << 20;
                for (std::size_t index = 0; index < even_count; ++index) {
                    int child = shapes[sid].even_children[index];
                    if (child < 0) {
                        const int neid = fill_epart(eid, index);
                        // Reset options from this even part depend on its
                        // entire earlier singleton history, not merely the
                        // current recurrence window.  An incomplete history
                        // (pending exact dependency) defers this child: it
                        // is neither materialized nor decided this sweep.
                        if (!ensure_single_history(neid)) {
                            saw_unknown = true;
                            continue;
                        }
                        // If that history already contains a P-position
                        // below the reset cutoff, the even child is N for
                        // this row regardless of its anchor offsets.  Do not
                        // materialize a distinct dead shape.  The test is
                        // deliberately repeated at each row rather than
                        // cached in even_children: a newly discovered shape
                        // may subsequently be backfilled at smaller m where
                        // the same reset is not active yet.
                        if (first_p[neid] <= m - tbar - 2) continue;
                        std::vector<int> anchors;
                        for (int o : shapes[sid].offsets)
                            anchors.push_back(BASEM + o);
                        anchors = canonical(neid, std::move(anchors));
                        if (anchors.front() != BASEM) {
                            std::cerr << "minimum anchor was absorbed\n";
                            std::exit(2);
                        }
                        std::vector<int> offsets;
                        for (int a : anchors) offsets.push_back(a - BASEM);
                        child = register_shape(neid, offsets);
                        shapes[sid].even_children[index] = child;
                    }
                    const signed char cv = evaluate(child, m);
                    if (cv == 1) { winning = true; break; }
                    if (cv < 0) saw_unknown = true;
                }
            }
            // A P child decides the parent N even beside an unknown sibling;
            // otherwise an unknown child leaves the parent unknown, with no
            // ring, memo, or first_p writes until the batch resolves it.
            if (!winning && saw_unknown) {
                unknown_memo.insert(memo_key);
                return -1;
            }
            result = winning ? 0 : 1;
        }
        ring[sid][slot_of(m)] = result;
        value_stamp[sid][slot_of(m)] = m;
        row_memo.emplace(memo_key, result);
        if (result == 1 && shapes[sid].offsets.size() == 1) {
            int eid = shapes[sid].eid;
            first_p[eid] = std::min(first_p[eid], m);
            if (eid == 0 && base_p_hits.insert(m).second)
                std::cout << "P-HIT n=" << m << std::endl;
        }
        return result;
    }

    std::vector<std::vector<int>> value_stamp;  // guards ring reuse

    bool flags_are_stable(int n) const {
        const int cutoff = n - tbar - 2;
        for (std::size_t eid = 0; eid < first_p.size(); ++eid)
            if ((first_p[eid] <= cutoff) != (first_p[eid] <= n)) return false;
        return true;
    }

    std::vector<U64> snapshot(int n) const {
        // Bit-pack the exact outcome window.  Shape identities and even-part
        // identities are immutable and append-only, so their counts plus the
        // rows determine which registered state each bit belongs to.
        std::vector<U64> out;
        out.reserve(2 + shapes.size() * ((f + 64) / 64)
                    + (first_p.size() + 63) / 64);
        out.push_back(static_cast<U64>(shapes.size()));
        out.push_back(static_cast<U64>(first_p.size()));
        for (std::size_t sid = 0; sid < shapes.size(); ++sid) {
            U64 word = 0;
            int bit = 0;
            for (int m = n - tbar; m <= n; m += 2) {
                const int slot = slot_of(m);
                if (value_stamp[sid][slot] != m || ring[sid][slot] < 0) {
                    std::cerr << "incomplete period snapshot at shape=" << sid
                              << " m=" << m << "\n";
                    std::exit(2);
                }
                if (ring[sid][slot] == 1) word |= U64{1} << bit;
                if (++bit == 64) { out.push_back(word); word = 0; bit = 0; }
            }
            if (bit != 0) out.push_back(word);
        }
        U64 word = 0;
        int bit = 0;
        for (int hit : first_p) {
            if (hit <= n) word |= U64{1} << bit;
            if (++bit == 64) { out.push_back(word); word = 0; bit = 0; }
        }
        if (bit != 0) out.push_back(word);
        return out;
    }

};

}  // namespace

int main(int argc, char** argv) {
    if (argc < 4) {
        std::cerr
            << "usage: periodicity_engine CACHE LIMIT "
               "[--base-record FILE]... [--checkpoint-file FILE] "
               "[--stop-after-evaluations N] GEN...\n";
        return 1;
    }
    Engine eng;
    eng.cache_path = argv[1];
    long limit = std::atol(argv[2]);
    std::vector<std::string> base_records;
    for (int i = 3; i < argc; ++i) {
        const std::string argument = argv[i];
        if (argument == "--base-record") {
            if (++i >= argc) {
                std::cerr << "--base-record requires a path\n";
                return 1;
            }
            base_records.emplace_back(argv[i]);
        } else if (argument == "--checkpoint-file") {
            if (++i >= argc) {
                std::cerr << "--checkpoint-file requires a path\n";
                return 1;
            }
            eng.row_checkpoint_path = argv[i];
        } else if (argument == "--stop-after-evaluations") {
            if (++i >= argc) {
                std::cerr << "--stop-after-evaluations requires a count\n";
                return 1;
            }
            try {
                std::size_t parsed = 0;
                const std::string count = argv[i];
                eng.stop_after_evaluations = std::stoull(count, &parsed);
                if (parsed != count.size() || eng.stop_after_evaluations == 0)
                    throw std::invalid_argument("count");
            } catch (const std::exception&) {
                std::cerr << "invalid --stop-after-evaluations count\n";
                return 1;
            }
        } else if (argument == "--batch-pending") {
            if (++i >= argc) {
                std::cerr << "--batch-pending requires a count\n";
                return 1;
            }
            try {
                std::size_t parsed = 0;
                const std::string count = argv[i];
                const long long threshold = std::stoll(count, &parsed);
                if (parsed != count.size() || threshold < 1)
                    throw std::invalid_argument("count");
                eng.batch_pending = static_cast<std::size_t>(threshold);
            } catch (const std::exception&) {
                std::cerr << "invalid --batch-pending count\n";
                return 1;
            }
        } else if (argument == "--memory-report") {
            eng.memory_report_enabled = true;
        } else if (argument == "--exact-threads") {
            if (++i >= argc) {
                std::cerr << "--exact-threads requires a count\n";
                return 1;
            }
            try {
                std::size_t parsed = 0;
                const std::string count = argv[i];
                const long threads = std::stol(count, &parsed);
                if (parsed != count.size() || threads < 1 || threads > 64)
                    throw std::invalid_argument("count");
                eng.exact_threads = static_cast<int>(threads);
            } catch (const std::exception&) {
                std::cerr << "invalid --exact-threads count\n";
                return 1;
            }
        } else if (argument.rfind("--", 0) == 0) {
            std::cerr << "unknown option: " << argument << "\n";
            return 1;
        } else {
            eng.base.push_back(std::atoi(argv[i]));
        }
    }
    if (eng.row_checkpoint_path.empty())
        eng.row_checkpoint_path = eng.cache_path + ".rowstate";
    if (eng.row_checkpoint_path == eng.cache_path
        || eng.row_checkpoint_path == eng.cache_path + ".tmp") {
        std::cerr << "row checkpoint must not overwrite the exact cache\n";
        return 1;
    }
    std::signal(SIGINT, request_interrupt);
    std::signal(SIGTERM, request_interrupt);
    eng.base = minimal_generators(eng.base);
    int g = 0;
    for (int v : eng.base) g = std::gcd(g, v);
    if (g != 2) { std::cerr << "gcd must be 2\n"; return 1; }
    for (int v : eng.base) eng.half.push_back(v / 2);
    {
        int bound = 1;
        for (int a : eng.half) for (int b : eng.half) bound = std::max(bound, a * b);
        eng.f = frobenius_of(eng.half, bound);
    }
    eng.tbar = 2 * eng.f;
    eng.auto_min = eng.tbar + 2;
    eng.window_slots = eng.f + 8;
    eng.base_member_mask.assign(eng.f + 1, 0);
    {
        std::vector<char> reach(eng.f + 1, 0);
        reach[0] = 1;
        for (int v = 1; v <= eng.f; ++v)
            for (int gg : eng.half)
                if (v >= gg && reach[v - gg]) { reach[v] = 1; break; }
        eng.base_member_mask = reach;
    }
    {
        std::vector<char> mask(eng.f + 1, 0);
        for (int v = 0; v <= eng.f; ++v) mask[v] = eng.base_member_mask[v];
        int base_eid = eng.register_epart(mask);
        if (base_eid != 0) { std::cerr << "base epart id\n"; return 2; }
    }
    eng.register_shape(0, {0});
    eng.load_cache();
    for (const std::string& path : base_records) eng.load_base_record(path);
    int active_n = 0;
    bool resume_active_row = false;
    try {
        resume_active_row = eng.load_row_checkpoint(active_n);
    } catch (const std::exception& error) {
        std::cerr << "cannot load row checkpoint: " << error.what() << "\n";
        return 2;
    }
    if (resume_active_row && active_n > limit) {
        std::cerr << "row checkpoint frontier exceeds requested limit\n";
        return 2;
    }
    if (resume_active_row)
        std::cout << "ROW-CHECKPOINT loaded path=" << eng.row_checkpoint_path
                  << " active_n=" << active_n
                  << " scanned_to=" << eng.scanned_to
                  << " shapes=" << eng.shapes.size()
                  << " eparts=" << eng.emask.size()
                  << " evaluations=" << eng.evaluation_calls << std::endl;
    std::cout << "engine base=";
    for (int v : eng.base) std::cout << v << ",";
    std::cout << " f=" << eng.f << " tbar=" << eng.tbar << std::endl;
    // main loop with stamp syncing
    try {
        long n = resume_active_row ? active_n : 1;
        std::vector<U64> checkpoint;
        int checkpoint_n = 0;
        long brent_power = 1;
        long brent_length = 0;
        while (resume_active_row || n < limit) {
            if (resume_active_row) {
                // The saved row memo makes this replay cheap.  Sweeping from
                // the beginning also completes any transition whose child
                // was registered immediately before the interruption.
                resume_active_row = false;
            } else {
                n += 2;
                eng.begin_row();
            }
            if (n == limit)
                std::cout << "ROW begin n=" << n
                          << " shapes=" << eng.shapes.size()
                          << " eparts=" << eng.emask.size() << std::endl;
            try {
                for (;;) {
                    eng.collect_mode = eng.exact_threads > 1;
                    eng.pending.clear();
                    eng.pending_keys.clear();
                    eng.unknown_memo.clear();
                    bool truncated = false;
                    size_t count = eng.shapes.size();
                    for (size_t sid = 0; sid < count; ++sid) {
                        eng.evaluate(static_cast<int>(sid), static_cast<int>(n));
                        if (eng.pending.size() >= eng.batch_pending) {
                            truncated = true;
                            break;
                        }
                    }
                    while (!truncated && count < eng.shapes.size()) {
                        size_t from = count;
                        count = eng.shapes.size();
                        std::cout << "BACKFILL begin n=" << n
                                  << " from=" << from
                                  << " to=" << count
                                  << " shapes=" << eng.shapes.size() << std::endl;
                        for (size_t sid = from; sid < count; ++sid) {
                            if (sid != from && (sid - from) % 10000 == 0)
                                std::cout << "BACKFILL progress n=" << n
                                          << " sid=" << sid
                                          << " to=" << count
                                          << " shapes=" << eng.shapes.size() << std::endl;
                            for (long m = std::max(3L, n - eng.tbar); m <= n; m += 2)
                                eng.evaluate(static_cast<int>(sid), static_cast<int>(m));
                            if (eng.pending.size() >= eng.batch_pending) {
                                truncated = true;
                                break;
                            }
                        }
                        std::cout << "BACKFILL end n=" << n
                                  << " from=" << from
                                  << " to=" << count
                                  << " shapes=" << eng.shapes.size() << std::endl;
                    }
                    if (eng.pending.empty()) {
                        if (!truncated) break;
                        continue;
                    }
                    std::cout << "EXACT-BATCH n=" << n
                              << " pending=" << eng.pending.size()
                              << " threads=" << eng.exact_threads
                              << (truncated ? " truncated=1" : "") << std::endl;
                    eng.solve_pending_parallel();
                }
                throw_if_interrupted();
            } catch (const CampaignInterrupted&) {
                if (eng.memory_report_enabled) eng.memory_report();
                eng.save_cache();
                eng.save_row_checkpoint(static_cast<int>(n));
                std::cout << "ROW-CHECKPOINT saved path="
                          << eng.row_checkpoint_path
                          << " active_n=" << n
                          << " scanned_to=" << eng.scanned_to
                          << " shapes=" << eng.shapes.size()
                          << " eparts=" << eng.emask.size()
                          << " evaluations=" << eng.evaluation_calls << std::endl;
                return interrupt_requested == 0
                    ? 75 : 128 + static_cast<int>(interrupt_requested);
            }
            eng.scanned_to = static_cast<int>(n);
            // An older checkpoint is harmless, but once its row is complete
            // it should not be mistaken for the next frontier after a crash.
            eng.remove_row_checkpoint();
            if (n >= eng.auto_min + eng.tbar
                && n > eng.external_cache_max_anchor + eng.tbar
                && (n & 3) == 1
                && eng.flags_are_stable(static_cast<int>(n))) {
                std::vector<U64> current = eng.snapshot(static_cast<int>(n));
                if (checkpoint.empty()) {
                    checkpoint = std::move(current);
                    checkpoint_n = static_cast<int>(n);
                    brent_power = 1;
                    brent_length = 0;
                } else {
                    ++brent_length;
                    if (current == checkpoint) {
                        std::cout << "PERIOD start=" << checkpoint_n
                              << " length=" << (n - checkpoint_n)
                              << " shapes=" << eng.shapes.size() << std::endl;
                        if (eng.memory_report_enabled) eng.memory_report();
                        eng.save_cache();
                        return 0;
                    }
                    if (brent_length == brent_power) {
                        checkpoint = std::move(current);
                        checkpoint_n = static_cast<int>(n);
                        brent_power *= 2;
                        brent_length = 0;
                    }
                }
            }
            if (n % 20001 == 0 || n == 3)
                std::cout << "progress n=" << n
                          << " shapes=" << eng.shapes.size()
                          << " eparts=" << eng.emask.size() << std::endl;
            if (n % 20 == 1) eng.save_cache();
            eng.end_row();
        }
        std::cout << "LIMIT-REACHED n=" << n
                  << " shapes=" << eng.shapes.size() << std::endl;
        if (eng.memory_report_enabled) eng.memory_report();
        eng.save_cache();
    } catch (const std::exception& error) {
        std::cerr << "periodicity engine checkpoint error: "
                  << error.what() << "\n";
        return 2;
    }
    return 0;
}
