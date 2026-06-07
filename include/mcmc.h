#ifndef MCMC_H
#define MCMC_H

#include <vector>

// Forward declaration: run_mcmc only needs a reference to Board, and Board.h
// includes this header (for the friend declaration), so we must not include
// Board.h back here.
class Board;

// Outcome of a single random rollout starting from a fixed first move.
struct MCMC_result {
    bool         win        = false; // player ended as the sole survivor
    bool         dead       = false; // player died during the rollout
    unsigned int time_to_death = 0;     // # of steps the player stayed alive
    unsigned int time_to_win = 0;    // depth at which the win happened (win only)
    double reachable_cell_frac = 0;
    int player_death_count = 0;
};

// Run `num_sims` random rollouts from `board`, evaluated from `player_id`'s
// perspective: that player's first move is forced to land on cell
// `player_move_pos` and every other move (all players, all subsequent steps) is
// sampled uniformly from free neighbours. `seed` seeds the rollout PRNG, so the
// caller can vary it per game/move. Rollouts stop on death, win, or after
// `max_depth` steps. Results are returned raw, one entry per simulation; no
// aggregation/evaluation is done here.
std::vector<MCMC_result> run_mcmc(const Board& board,
                                  unsigned int player_id,
                                  unsigned int player_move_pos,
                                  unsigned int num_sims,
                                  unsigned int max_depth,
                                  unsigned int seed);

#endif
