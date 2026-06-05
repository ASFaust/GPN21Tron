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

    string get_player_move();

    // run_mcmc needs read access to the player bookkeeping and to the private
    // random-move sampler used during rollouts.
    friend std::vector<MCMC_result> run_mcmc(const Board& board,
                                             unsigned int player_move_pos,
                                             unsigned int num_sims,
                                             unsigned int max_depth);

private:
    unsigned int f(unsigned int x, unsigned int y) const;

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

    unsigned int* head_pos;          // length 32, board index of each player's head
    unsigned int* board;         // width*width, OR-accumulated bit channels
    unsigned int* head_map; // width*width, (q+1) if player q's head is here, else 0
    const unsigned int* nbr;     // borrowed from nbr_cache, not owned
};

#endif