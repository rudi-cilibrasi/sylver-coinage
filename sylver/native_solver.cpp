// Exact finite (gcd-one) Sylver Coinage evaluator.
//
// This is a low-overhead counterpart of solver.py for difficult certificate
// searches.  It deliberately supports only Frobenius numbers below 512; that
// keeps every game state in eight machine words and makes the search semantics
// easy to compare with the Python reference implementation.

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

#ifndef SYLVER_NATIVE_WORDS
#define SYLVER_NATIVE_WORDS 8
#endif

constexpr int kWords = SYLVER_NATIVE_WORDS;
static_assert(kWords > 0, "SYLVER_NATIVE_WORDS must be positive");
constexpr int kMaximumFrobenius = 64 * kWords - 1;

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
    Solver(std::vector<int> generators, int frobenius)
        : generators_(std::move(generators)), frobenius_(frobenius), mask_(make_mask()) {
        memo_.reserve(262144);
        initial_.set(0);
        for (const int generator : generators_) {
            initial_ = adjoin(initial_, generator);
        }
    }

    [[nodiscard]] int solve() { return winning_move(initial_); }
    [[nodiscard]] int solve_after_adjoining(int move) {
        return winning_move(adjoin(initial_, move));
    }
    [[nodiscard]] std::size_t states_evaluated() const { return memo_.size(); }

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

    [[nodiscard]] int winning_move(const State& state) {
        if (const auto found = memo_.find(state); found != memo_.end()) {
            return found->second;
        }
        State paired_losers;
        for (int move = 2; move <= frobenius_; ++move) {
            if (state.test(move) || paired_losers.test(move)) {
                continue;
            }
            const State child = adjoin(state, move);
            const int response = winning_move(child);
            if (response == 0) {
                memo_.emplace(state, static_cast<std::uint16_t>(move));
                return move;
            }
            if (response > move) {
                paired_losers.set(response);
            }
        }
        memo_.emplace(state, std::uint16_t{0});
        return 0;
    }

    std::vector<int> generators_;
    int frobenius_;
    State mask_;
    State initial_;
    std::unordered_map<State, std::uint16_t, StateHash> memo_;
};

[[nodiscard]] std::vector<int> parse_generators(
    int argc, char** argv, int first_argument, bool require_coprime
) {
    if (argc <= first_argument) {
        throw std::invalid_argument(
            "usage: native_solver GENERATOR... or "
            "native_solver --odd-range START END GENERATOR..."
        );
    }
    std::vector<int> generators;
    generators.reserve(static_cast<std::size_t>(argc - first_argument));
    for (int index = first_argument; index < argc; ++index) {
        const long value = std::stol(argv[index]);
        if (value < 2 || value > std::numeric_limits<int>::max()) {
            throw std::invalid_argument("generators must be integers greater than one");
        }
        generators.push_back(static_cast<int>(value));
    }
    std::sort(generators.begin(), generators.end());
    generators.erase(std::unique(generators.begin(), generators.end()), generators.end());
    if (require_coprime && std::accumulate(
            generators.begin() + 1,
            generators.end(),
            generators.front(),
            [](int left, int right) { return std::gcd(left, right); }) != 1) {
        throw std::invalid_argument("exact evaluation requires generators with gcd one");
    }
    return generators;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc >= 2 && std::string(argv[1]) == "--odd-range") {
            if (argc < 6) {
                throw std::invalid_argument(
                    "odd-range mode requires START END and base generators"
                );
            }
            const int start = std::stoi(argv[2]);
            const int end = std::stoi(argv[3]);
            if (start < 3 || start > end || start % 2 == 0 || end % 2 == 0) {
                throw std::invalid_argument("odd range must have odd endpoints >= 3");
            }
            const std::vector<int> base = parse_generators(argc, argv, 4, false);
            int bound = 0;
            for (int move = start; move <= end; move += 2) {
                std::vector<int> child = base;
                child.push_back(move);
                std::sort(child.begin(), child.end());
                if (std::accumulate(
                        child.begin() + 1,
                        child.end(),
                        child.front(),
                        [](int left, int right) { return std::gcd(left, right); }
                    ) != 1) {
                    throw std::invalid_argument(
                        "every odd-range child must have gcd one"
                    );
                }
                bound = std::max(bound, frobenius_number(child));
            }
            if (bound > kMaximumFrobenius) {
                throw std::invalid_argument(
                    "odd-range Frobenius bound exceeds native limit " +
                    std::to_string(kMaximumFrobenius)
                );
            }
            Solver solver(base, bound);
            for (int move = start; move <= end; move += 2) {
                std::vector<int> child = base;
                child.push_back(move);
                std::sort(child.begin(), child.end());
                const int actual_frobenius = frobenius_number(child);
                const int response = solver.solve_after_adjoining(move);
                std::cout << "move=" << move << ' '
                          << (response == 0 ? "P" : "N") << " winning_move=";
                if (response == 0) {
                    std::cout << "none";
                } else {
                    std::cout << response;
                }
                std::cout << " frobenius=" << actual_frobenius
                          << " cumulative_states=" << solver.states_evaluated()
                          << '\n';
            }
            return EXIT_SUCCESS;
        }

        const std::vector<int> generators = parse_generators(argc, argv, 1, true);
        const int frobenius = frobenius_number(generators);
        if (frobenius > kMaximumFrobenius) {
            throw std::invalid_argument(
                "Frobenius number exceeds native limit " +
                std::to_string(kMaximumFrobenius)
            );
        }
        Solver solver(generators, frobenius);
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
        std::cerr << "native_solver: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
