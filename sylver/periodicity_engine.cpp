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
//   periodicity_engine CACHE_FILE LIMIT [--base-record FILE]... GEN...
//
// Prints P-hits for the base even part as they are found, plus a period
// certificate when detected.

#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <queue>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

using U64 = std::uint64_t;

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
};

struct ExactResult {
    bool is_p;
    std::size_t states;
};

template <std::size_t Words>
ExactResult solve_exact_with_words(
    const std::vector<int>& generators, int frobenius
) {
    ExactSolver<Words> solver(generators, frobenius);
    const bool is_p = solver.solve() == 0;
    return {is_p, solver.states_evaluated()};
}

ExactResult solve_exact_position(
    const std::vector<int>& generators, int frobenius
) {
    if (frobenius <= 63) return solve_exact_with_words<1>(generators, frobenius);
    if (frobenius <= 127) return solve_exact_with_words<2>(generators, frobenius);
    if (frobenius <= 255) return solve_exact_with_words<4>(generators, frobenius);
    if (frobenius <= 511) return solve_exact_with_words<8>(generators, frobenius);
    return solve_exact_with_words<16>(generators, frobenius);
}

struct Engine {
    std::vector<int> base;       // full coordinates, gcd 2
    std::vector<int> half;
    int f = 0, tbar = 0, auto_min = 0;
    std::string cache_path;
    int scanned_to = 1;

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
        const ExactResult exact = solve_exact_position(gens, frob);
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
        // Finite fallbacks dominate runtime on hard fronts.  Persist each
        // completed result immediately so an interrupted tail run never has
        // to repeat a multi-minute exact subgame.
        save_cache();
        return exact.is_p;
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

    void ensure_single_history(int eid) {
        int sid = single_sid[eid];
        if (sid < 0) sid = register_shape(eid, {0});
        for (int m = history_to[eid] + 2; m <= scanned_to; m += 2) {
            evaluate(sid, m);
            history_to[eid] = m;
        }
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
        signed char result;
        std::vector<int> anchors;
        for (int o : shapes[sid].offsets) anchors.push_back(m + o);
        const std::optional<bool> cached = cached_outcome(
            shapes[sid].eid, anchors);
        if (cached.has_value()) {
            result = *cached ? 1 : 0;
        } else if (m < auto_min) {
            result = exact_outcome(shapes[sid].eid, anchors) ? 1 : 0;
        } else {
            const int eid = shapes[sid].eid;
            bool winning = first_p[eid] <= m - tbar - 2;
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
                        // current recurrence window.
                        ensure_single_history(neid);
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
                }
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
               "[--base-record FILE]... GEN...\n";
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
        } else {
            eng.base.push_back(std::atoi(argv[i]));
        }
    }
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
    std::cout << "engine base=";
    for (int v : eng.base) std::cout << v << ",";
    std::cout << " f=" << eng.f << " tbar=" << eng.tbar << std::endl;
    // main loop with stamp syncing
    {
        long n = 1;
        std::vector<U64> checkpoint;
        int checkpoint_n = 0;
        long brent_power = 1;
        long brent_length = 0;
        while (n < limit) {
            n += 2;
            eng.begin_row();
            if (n == limit)
                std::cout << "ROW begin n=" << n
                          << " shapes=" << eng.shapes.size()
                          << " eparts=" << eng.emask.size() << std::endl;
            size_t count = eng.shapes.size();
            for (size_t sid = 0; sid < count; ++sid)
                eng.evaluate(static_cast<int>(sid), static_cast<int>(n));
            while (count < eng.shapes.size()) {
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
                }
                std::cout << "BACKFILL end n=" << n
                          << " from=" << from
                          << " to=" << count
                          << " shapes=" << eng.shapes.size() << std::endl;
            }
            eng.scanned_to = static_cast<int>(n);
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
        eng.save_cache();
    }
    return 0;
}
