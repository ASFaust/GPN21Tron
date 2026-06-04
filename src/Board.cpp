#include "Board.h"
#include "TronListener.h"
#include "Player.h"
#include "vec.h"

using namespace std;

/*
board is a width*width array of unsigned int; each cell holds a player's
bit channel (1U << p_id), or 0 if empty. heads are stored as board indices.

occupant_head[idx] = (q+1) if player q's head currently sits on cell idx,
else 0. Maintained in update_pos so contested-cell checks are O(1) per
neighbor rather than O(num_players).

nbr[i*4 + d] = neighbor of cell i in direction d.
dir order: 0=right 1=left 2=up 3=down, arranged so reverse(d) == d^1.
The neighbor table depends only on width, so it is built once per width
and shared across all Board instances via nbr_cache.

A candidate move into empty cell c is "contested" if some other alive
player's head is adjacent to c (i.e. that player could also step into c
next turn). Move selection prefers uncontested cells when a choice exists.
*/

std::unordered_map<unsigned int, unsigned int*> Board::nbr_cache;

const unsigned int* Board::get_nbr_table(unsigned int width) {
    auto it = nbr_cache.find(width);
    if (it != nbr_cache.end()) return it->second;

    unsigned int n = width * width;
    unsigned int* nbr = new unsigned int[n * 4];
    for (unsigned int y = 0; y < width; ++y) {
        for (unsigned int x = 0; x < width; ++x) {
            unsigned int i = y * width + x;
            nbr[i*4 + 0] = y * width + (x + 1)         % width; // right
            nbr[i*4 + 1] = y * width + (x + width - 1) % width; // left
            nbr[i*4 + 2] = ((y + 1)         % width) * width + x; // up
            nbr[i*4 + 3] = ((y + width - 1) % width) * width + x; // down
        }
    }
    nbr_cache[width] = nbr;
    return nbr;
}

Board::Board(unsigned char _width, unsigned int _num_players, unsigned int _player_id) {
    width       = _width;
    player_id   = _player_id;
    num_players = _num_players;
    if (_num_players > 32) {
        //throw something
    }
    alive_mask = ~0u;
    dead       = false;

    unsigned int n = (unsigned int)_width * _width;
    head          = new unsigned int[32];
    board         = new unsigned int[n];
    occupant_head = new unsigned int[n];
    for (unsigned int i = 0; i < n; ++i) { board[i] = 0; occupant_head[i] = 0; }

    nbr = get_nbr_table(_width); // shared, not owned
}

unsigned int Board::f(unsigned int x, unsigned int y) const {
    return y * width + x;
}

void Board::update_pos(unsigned int p_id, unsigned int idx) {
    // clear the player's previous head marker, if any
    unsigned int old = head[p_id];
    if (occupant_head[old] == p_id + 1) occupant_head[old] = 0;

    head[p_id]         = idx;
    board[idx]         = 1U << p_id;
    occupant_head[idx] = p_id + 1;
}

void Board::update_pos(unsigned int p_id, unsigned int x, unsigned int y) {
    update_pos(p_id, f(x, y));
}

bool Board::is_contested(unsigned int cell, unsigned int p_id) const {
    const unsigned int* cn = &nbr[cell * 4];
    for (int d = 0; d < 4; ++d) {
        unsigned int occ = occupant_head[cn[d]];
        if (occ) {
            unsigned int q = occ - 1;
            if (q != p_id && (alive_mask & (1U << q))) return true;
        }
    }
    return false;
}

unsigned int Board::get_random_safe_move(unsigned int p_id, RNG_STATE& rng_state) {
    const unsigned int* nb = &nbr[head[p_id] * 4];

    unsigned int possible[4];   // direction indices of empty cells
    bool contested[4];
    int np = 0;
    int n_uncontested = 0;
    int last_uncontested = -1;

    for (int d = 0; d < 4; ++d) {
        unsigned int c = nb[d];
        if (board[c] != 0) continue;          // not a possible move
        bool con = is_contested(c, p_id);
        possible[np]  = d;
        contested[np] = con;
        if (!con) { ++n_uncontested; last_uncontested = np; }
        ++np;
    }

    if (np == 0) return NO_SAFE_MOVE;
    if (np == 1) return possible[0];          // forced move, take it

    if (n_uncontested == 1) return possible[last_uncontested];

    if (n_uncontested > 1) {                  // random among uncontested
        unsigned int k = next_rng(rng_state) % (unsigned int)n_uncontested;
        for (int i = 0; i < np; ++i)
            if (!contested[i] && k-- == 0) return possible[i];
    }

    // np > 1 but all contested: random among all possible
    return possible[next_rng(rng_state) % (unsigned int)np];
}

void Board::remove_player(int p_id) {
    alive_mask = alive_mask & ~(1U << p_id);
}

Board::~Board() {
    delete[] head;
    delete[] board;
    delete[] occupant_head;
    // nbr is borrowed from nbr_cache; do NOT delete here
}