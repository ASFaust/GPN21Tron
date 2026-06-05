#include "mcmc.h"
#include "Board.h"
#include "rng.h"

using namespace std;

vector<MCMC_result> run_mcmc(const Board& board,
                             unsigned int player_id,
                             unsigned int player_move_pos,
                             unsigned int num_sims,
                             unsigned int max_depth,
                             unsigned int seed) {
    vector<MCMC_result> results(num_sims);

    RNG_STATE rng;
    seed_rng(rng, seed); // caller-supplied seed (vary per game for fair battles)

    Board sim_board = board; // deep copy via Board's copy constructor
    unsigned int idxs[32];

    for (unsigned int i = 0; i < num_sims; ++i) {
        sim_board = board; // reset to the original state for each sim

        // First step: the player commits to the candidate cell, everyone else
        // proposes a random move.
        for (unsigned int q = 0; q < sim_board.num_players; ++q) {
            if (!(sim_board.alive_mask & (1U << q))) {
                idxs[q] = 0; // dead players don't move; placeholder value
                continue;
            }
            idxs[q] = (q == player_id)
                          ? player_move_pos
                          : sim_board.get_random_move(q, rng);
        }
        sim_board.step(idxs);

        bool player_dead = !(sim_board.alive_mask & (1U << player_id));
        bool player_win  =  (sim_board.alive_mask == (1U << player_id));

        unsigned int depth = 1;
        results[i].time_alive = player_dead ? 0 : 1;

        // Random rollout until the player dies, wins, or we hit max_depth.
        while (!player_dead && !player_win && depth < max_depth) {
            for (unsigned int q = 0; q < sim_board.num_players; ++q) {
                if (!(sim_board.alive_mask & (1U << q))) {
                    idxs[q] = 0; // dead players don't move; placeholder value
                    continue;
                }
                idxs[q] = sim_board.get_random_move(q, rng);
            }
            sim_board.step(idxs);
            ++depth;

            player_dead = !(sim_board.alive_mask & (1U << player_id));
            player_win  =  (sim_board.alive_mask == (1U << player_id));
            if (!player_dead) results[i].time_alive = depth;
        }

        results[i].win        = player_win;
        results[i].dead       = player_dead;
        results[i].time_to_win = player_win ? depth : 0; // 0 == invalid (no win)
    }

    return results;
}
