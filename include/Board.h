#ifndef BOARD_H
#define BOARD_H

#include <unordered_map>
#include <string>

#include "rng.h"
#include "mcmc.h"

using namespace std;

class Board {
public:
    Board(unsigned char _width, unsigned int _num_players, unsigned int _player_id,unsigned int* xs, unsigned int* ys);
    ~Board();

    // Owns raw arrays, so it needs deep copy semantics (used by the MCMC sims).
    Board(const Board& other);
    Board& operator=(const Board& other);

    void update_positions(const unsigned int* xs, const unsigned int* ys);

    void remove_player(unsigned int p_id);

    void step(const unsigned int* idxs);

    // MCMC hyperparameters are passed in per call so they can be tuned from
    // Python without rebuilding. See get_player_move() for their meaning.
    string get_player_move(unsigned int num_sims     = 200,
                           unsigned int max_depth     = 50,
                           double       W_WIN         = 10.0,
                           double       W_LOSS        = 10.0,
                           double       K             = 0.0,
                           double       DIR_PERSIST   = 0.0);

    // --- Local self-play / evaluation interface ---------------------------
    // The live client only ever drives its own `player_id`; for local battles
    // we need to control every player independently. These let a Python harness
    // pick a move for an arbitrary player, advance all players at once, and read
    // the win state.

    // MCMC-pick a direction (0=right,1=left,2=up,3=down) for an arbitrary
    // player. Returns -1 if the player is boxed in (no free neighbour) or dead.
    // `seed` seeds the rollout PRNG so each game/move can be varied.
    int get_move(unsigned int q,
                 unsigned int num_sims    = 200,
                 unsigned int max_depth   = 50,
                 double       W_WIN       = 10.0,
                 double       W_LOSS      = 10.0,
                 double       K           = 0.0,
                 double       DIR_PERSIST = 0.0,
                 unsigned int seed        = 123);

    // Advance the whole board by one tick: dirs[q] is the direction player q
    // moves (0..3); entries for dead players are ignored. Applies the same
    // collision/death rules as the live engine.
    void step_dirs(const std::vector<int>& dirs);

    bool         is_alive(unsigned int q) const;
    unsigned int count_alive() const;

    // --- State readout (for visualization) --------------------------------
    unsigned int get_width() const;
    // Flat width*width grid; each cell is -1 if empty, else the owning
    // player id (q) whose trail occupies it.
    std::vector<int> get_trail_grid() const;
    // Flat width*width grid; each cell is -1 if no head, else the player id
    // (q) whose head sits there.
    std::vector<int> get_head_grid() const;
    // alive_mask exposed as a per-player bool vector of length num_players.
    std::vector<bool> get_alive() const;

    // Sole-survivor player id, or -1 if the game is still running (>1 alive) or
    // ended in a mutual-death draw (0 alive).
    int          winner() const;

    // run_mcmc needs read access to the player bookkeeping and to the private
    // random-move sampler used during rollouts.
    friend std::vector<MCMC_result> run_mcmc(const Board& board,
                                             unsigned int player_id,
                                             unsigned int player_move_pos,
                                             unsigned int num_sims,
                                             unsigned int max_depth,
                                             unsigned int seed);

private:
    unsigned int f(unsigned int x, unsigned int y) const;

    // Shared core of get_player_move/get_move: MCMC-pick a direction (0..3) for
    // player q, or -1 if it has no free neighbour. Pure function of state plus
    // the supplied hyperparameters and rollout seed.
    // Not const: records the chosen direction in last_dir[q] so the next call
    // can apply the DIR_PERSIST boost to it.
    int pick_move_dir(unsigned int q,
                      unsigned int num_sims,
                      unsigned int max_depth,
                      double W_WIN, double W_LOSS, double K, double DIR_PERSIST,
                      unsigned int seed);

    // Uniformly sample a free neighbouring cell for player q; if the player is
    // boxed in, return an arbitrary neighbour (it dies on the next step).
    unsigned int get_random_move(unsigned int q, RNG_STATE& rng) const;

    // neighbor table shared across all boards of a given width
    static const unsigned int* get_nbr_table(unsigned int width);
    static std::unordered_map<unsigned int, unsigned int*> nbr_cache;

    //bool Board::is_contested(unsigned int cell, unsigned int p_id) const
    bool is_contested(unsigned int cell, unsigned int p_id) const;

    unsigned char width;
    unsigned int  player_id;
    unsigned int  num_players;
    unsigned int  alive_mask;
    bool          dead;

    // Last direction (0..3) MCMC-picked for each player, or -1 if none yet.
    // Used to apply the DIR_PERSIST score boost so paths stay less jittery.
    int           last_dir[32];

    unsigned int* head_pos;          // length 32, board index of each player's head
    unsigned int* board;         // width*width, OR-accumulated bit channels
    unsigned int* head_map; // width*width, (q+1) if player q's head is here, else 0
    const unsigned int* nbr;     // borrowed from nbr_cache, not owned
};

#endif