#include "Board.h"
#include "rng.h"
#include "mcmc.h"
#include <stdexcept>
#include <vector>
#include <cmath>

using namespace std;

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
            nbr[i*4 + 2] = ((y + width - 1) % width) * width + x; // up = -y
            nbr[i*4 + 3] = ((y + 1)         % width) * width + x; // down = +y
        }
    }
    nbr_cache[width] = nbr;
    return nbr;
}

Board::Board(unsigned char _width, unsigned int _num_players, unsigned int _player_id,unsigned int* xs, unsigned int* ys) {
    width       = _width;
    player_id   = _player_id;
    num_players = _num_players;
    if (_num_players > 32) {
        throw std::runtime_error("num_players > 32 not supported");
    }
    alive_mask = ~0u;
    //set all bits >= num_players to 0, so we can ignore them in bit ops
    alive_mask >>= (32 - num_players);    //we basically "shift in" 0s from the left 

    dead       = false;

    unsigned int board_size = (unsigned int)_width * _width;
    head_pos          = new unsigned int[32];
    board         = new unsigned int[board_size];
    head_map = new unsigned int[board_size];
    for (unsigned int i = 0; i < 32; ++i) head_pos[i] = 0;
    for (unsigned int i = 0; i < board_size;  ++i) { board[i] = 0; head_map[i] = 0; }

    nbr = get_nbr_table(_width); // shared, not owned


    //then seed board, head and head_map according to the initial positions
    for (unsigned int q = 0; q < _num_players; ++q) {
        if (!(alive_mask & (1U << q))){
            throw std::runtime_error("This should not happen: all players should be alive at the start of the game");
        }
        head_pos[q] = f(xs[q] % width, ys[q] % width);
        board[head_pos[q]] = 1U << q;
        head_map[head_pos[q]] = q + 1;
    }
}


Board::Board(const Board& other) {
    width       = other.width;
    player_id   = other.player_id;
    num_players = other.num_players;
    alive_mask  = other.alive_mask;
    dead        = other.dead;

    unsigned int board_size = (unsigned int)width * width;
    head_pos = new unsigned int[32];
    board    = new unsigned int[board_size];
    head_map = new unsigned int[board_size];
    for (unsigned int i = 0; i < 32; ++i) head_pos[i] = other.head_pos[i];
    for (unsigned int i = 0; i < board_size; ++i) {
        board[i]    = other.board[i];
        head_map[i] = other.head_map[i];
    }
    nbr = other.nbr; // shared, borrowed from nbr_cache; not owned
}

Board& Board::operator=(const Board& other) {
    if (this == &other) return *this;

    // The MCMC sims only ever assign between boards of identical width, so the
    // owned arrays are already the right size; copy contents in place.
    width       = other.width;
    player_id   = other.player_id;
    num_players = other.num_players;
    alive_mask  = other.alive_mask;
    dead        = other.dead;

    unsigned int board_size = (unsigned int)width * width;
    for (unsigned int i = 0; i < 32; ++i) head_pos[i] = other.head_pos[i];
    for (unsigned int i = 0; i < board_size; ++i) {
        board[i]    = other.board[i];
        head_map[i] = other.head_map[i];
    }
    nbr = other.nbr;
    return *this;
}

unsigned int Board::f(unsigned int x, unsigned int y) const {
    return y * width + x;
}

unsigned int Board::get_random_move(unsigned int q, RNG_STATE& rng) const {
    const unsigned int* nb = &nbr[head_pos[q] * 4];
    unsigned int free_cells[4];
    int nf = 0;
    for (int d = 0; d < 4; ++d) {
        if (board[nb[d]] & alive_mask) continue; // occupied by an alive bit
        free_cells[nf++] = nb[d];
    }
    if (nf == 0) return nb[0]; // boxed in: any (occupied) neighbour; dies next step
    if (nf == 1) return free_cells[0]; // deterministic move
    return free_cells[next_rng(rng) % nf];
}

void Board::step(const unsigned int* idxs) {
    unsigned int new_alive = alive_mask;

    for (unsigned int q = 0; q < num_players; ++q) {
        if (!(alive_mask & (1U << q))) continue;
        unsigned int idx = idxs[q];

        if (board[idx] & alive_mask){ // occupied by something that was alive last turn: death by collision. 
            new_alive &= ~(1U << q); // this includes self-collision, but it doesn't include head-head collisions 
            //or does it? wait... it does! but we need to check if the occupant is _on_ that square
            unsigned int wall_player_id = __builtin_ctz(board[idx]);
            if ((wall_player_id < q) && (head_pos[wall_player_id] == idx)){
                // if the occupant is on that cell, then it's a head-head collision...? no. only if the index has already been process
                //this is the condition that now also kills wall_player_id
                new_alive &= ~(1U << wall_player_id); 
            }
        }
        head_map[head_pos[q]] = 0;
        head_pos[q]                = idx;
        board[idx]             = 1U << q;
        head_map[idx]     = q + 1;
    }
    alive_mask = new_alive;
}

void Board::update_positions(const unsigned int* xs, const unsigned int* ys) {
    // trust the server: lay down survivor heads, no death computation.
    // dead players are masked off via prior remove_player calls.
    for (unsigned int q = 0; q < num_players; ++q) {
        if (!(alive_mask & (1U << q))) continue;
        unsigned int idx = f(xs[q] % width, ys[q] % width);

        head_map[head_pos[q]] = 0;
        head_pos[q]                = idx;
        board[idx]             = 1U << q;
        head_map[idx]     = q + 1;
    }
}

void Board::remove_player(unsigned int p_id) {
    alive_mask &= ~(1U << p_id);
}


bool Board::is_contested(unsigned int cell, unsigned int p_id) const {
    const unsigned int* cn = &nbr[cell * 4];
    for (int d = 0; d < 4; ++d) {
        unsigned int occ = head_map[cn[d]];
        if (occ) {
            unsigned int q = occ - 1;
            if (q != p_id && (alive_mask & (1U << q))) return true;
        } 
    }
    return false;
}

string interpret_direction(unsigned int d) {
    switch (d) {
        case 0: return "right";
        case 1: return "left";
        case 2: return "up";
        case 3: return "down";
        default: throw std::runtime_error("invalid direction");
    }
}

string Board::get_player_move(){
    const unsigned int* nb = &nbr[head_pos[player_id] * 4];
    unsigned int possible[4];   // direction indices of free cells
    int np = 0;
    for (int d = 0; d < 4; ++d) {
        unsigned int c = nb[d];
        if (board[c] & alive_mask) continue;   // occupied by an alive bit
        possible[np++]  = d;
    }   
    if (np == 0){
        return "rip"; 
    }
    if (np == 1) return interpret_direction(possible[0]);

    //now we can do MCMC here!
    //for each possible move, roll out random games that start by committing to
    //that move's destination cell. Results are kept raw for now.
    vector<vector<MCMC_result>> move_scores(np);
    for (int i = 0; i < np; ++i){
        move_scores[i] = run_mcmc(
            *this,
            nb[possible[i]], // destination cell of this candidate move
            200,             // num sims
            50               // max depth
        );
    }
    // Collapse each move's rollouts into a single pessimistic score:
    //   per rollout:  r = time_alive + W_WIN*win - W_LOSS*dead
    //   per move:     score = mean(r) - K * std(r)
    // K is hand-tuned; K=0 is plain expected reward (first experiment).
    // W_WIN/W_LOSS dominate max_depth so a decisive result outweighs survival.
    const double W_WIN  = 10.0;
    const double W_LOSS = 10.0;
    const double K      = 0.0;

    int best_i = 0;
    double best_score = -INFINITY;
    for (int i = 0; i < np; ++i){
        const vector<MCMC_result>& rs = move_scores[i];
        unsigned int n = rs.size();
        if (n == 0) continue;

        double sum = 0.0, sum_sq = 0.0;
        for (const MCMC_result& r : rs){
            double v = static_cast<double>(r.time_alive)
                     + (r.win  ? W_WIN  : 0.0)
                     - (r.dead ? W_LOSS : 0.0);
            sum    += v;
            sum_sq += v * v;
        }
        double mean = sum / n;
        double var  = sum_sq / n - mean * mean; // population variance
        if (var < 0.0) var = 0.0;               // guard against fp noise
        double score = mean - K * std::sqrt(var);

        if (score > best_score){
            best_score = score;
            best_i = i;
        }
    }
    return interpret_direction(possible[best_i]);
}

Board::~Board() {
    delete[] head_pos;
    delete[] board;
    delete[] head_map;
    // nbr is borrowed from nbr_cache; do NOT delete
}