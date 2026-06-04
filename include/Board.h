#ifndef BOARD_H
#define BOARD_H

#include <unordered_map>

// whatever RNG type you're using
struct RNG_STATE;

class Board {
public:
    static const unsigned int NO_SAFE_MOVE = ~0u;

    Board(unsigned char _width, unsigned int _num_players, unsigned int _player_id);
    ~Board();

    void update_pos(unsigned int p_id, unsigned int idx);
    void update_pos(unsigned int p_id, unsigned int x, unsigned int y);
    unsigned int get_random_safe_move(unsigned int p_id, RNG_STATE& rng_state);
    void remove_player(int p_id);

private:
    unsigned int f(unsigned int x, unsigned int y) const;
    bool is_contested(unsigned int cell, unsigned int p_id) const;

    // shared neighbor table, one per distinct width
    static const unsigned int* get_nbr_table(unsigned int width);
    static std::unordered_map<unsigned int, unsigned int*> nbr_cache;

    unsigned char width;
    unsigned int  player_id;
    unsigned int  num_players;
    unsigned int  alive_mask;
    bool          dead;

    unsigned int* head;          // length 32, board-index per player
    unsigned int* board;         // width*width, cell = (1U << p_id) or 0
    unsigned int* occupant_head; // width*width, (q+1) if player q's head is here, else 0
    const unsigned int* nbr;     // borrowed from nbr_cache, not owned
};

#endif