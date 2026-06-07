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

unsigned int Board::count_free_neighbors(unsigned int position) const {
    unsigned int ret = 4; 
    const unsigned int* nb = &nbr[position * 4];
    for(int i = 0; i < 4; i++){
        if(board[nb[i]] & alive_mask){
            ret -= 1;
        }
    }
    return ret;
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
    //return free_cells[next_rng(rng) % nf];
    //improve this:
    unsigned int undead_ends[4];
    int n_undead = 0;
    for (int d = 0; d < nf; d++){
        if(count_free_neighbors(free_cells[d]) > 0){
            undead_ends[n_undead++] = free_cells[d];
        }
    }
    if(n_undead == 0){
        return free_cells[next_rng(rng) % nf];
    }
    if(n_undead == 1){
        return undead_ends[0];
    }
    if(next_rng(rng) % 6 == 0){ // 16% chance to select a contested move. 
        return undead_ends[next_rng(rng) % n_undead];
    }
    unsigned int uncontested_ends[4];
    unsigned int n_uncontested = 0;
    for (int d = 0; d < n_undead; d++){
        if(!is_contested(undead_ends[d],q)){
            uncontested_ends[n_uncontested++] = undead_ends[d];
        }
    }
    if(n_uncontested == 0){
        return undead_ends[next_rng(rng) % n_undead];
    }
    if(n_uncontested == 1){
        return uncontested_ends[0];
    }
    return uncontested_ends[next_rng(rng) % n_uncontested];
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

unsigned int Board::count_reachable_cells(unsigned int p_id) const {
    // BFS flood fill from head_pos[p_id], counting how many cells we can reach
    // without crossing any bits in alive_mask. Used for a simple heuristic in
    // get_player_move when the player is boxed in.
    bool visited[1024] = {false}; // max board size is 32*32=1024
    unsigned int queue[1024];
    unsigned int front = 0, back = 0;

    unsigned int start = head_pos[p_id];
    visited[start] = true;
    queue[back++] = start;

    while (front < back) {
        unsigned int idx = queue[front++];
        const unsigned int* nb = &nbr[idx * 4];
        for (int d = 0; d < 4; ++d) {
            unsigned int nidx = nb[d];
            if (visited[nidx]) continue;
            if (board[nidx] & alive_mask) continue; // occupied by an alive bit
            visited[nidx] = true;
            queue[back++] = nidx;
        }
    }
    return back; // number of visited cells
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

int Board::min_enemy_distance(unsigned int q) const {
    bool visited[1024] = {false};
    unsigned int queue[1024];
    unsigned int dist[1024];
    unsigned int front = 0, back = 0;
    unsigned int start = head_pos[q];
    visited[start] = true;
    dist[start] = 0;
    queue[back++] = start;
    while (front < back) {
        unsigned int idx = queue[front++];
        const unsigned int* nb = &nbr[idx * 4];
        for (int d = 0; d < 4; ++d) {
            unsigned int nidx = nb[d];
            if (visited[nidx]) continue;
            if (board[nidx] & alive_mask) {
                unsigned int occ = head_map[nidx];
                if (occ) {
                    unsigned int player_id = occ - 1;
                    if (player_id != q && (alive_mask & (1U << player_id))) {
                        return dist[idx] + 1;
                    }
                }
                continue;
            }
            visited[nidx] = true;
            dist[nidx] = dist[idx] + 1;
            queue[back++] = nidx;
        }
    }
    return -1;
}

long Board::score_fill(unsigned int c) const {
    // Flood-fill the free cells reachable *after* we step onto c (so c itself is
    // now occupied and acts as a wall). Each reachable cell counts 2 if it has
    // >=2 free neighbours (we can pass through it) and 1 if it has exactly 1 (a
    // dead-end pocket we can enter but not leave). Summing this gives a single
    // number that rewards both a large connected region and few wasted pockets.
    //
    // Note: free-neighbour counts are read from the current board, so cells
    // adjacent to c are over-counted by 1. That bias is tiny and the routine is
    // re-run every tick, so we keep it simple rather than special-casing c.
    bool visited[1024] = {false}; // max board size is 32*32 = 1024
    unsigned int queue[1024];
    unsigned int front = 0, back = 0;

    visited[c] = true; // c is where the head just moved: treat as a wall
    const unsigned int* cn = &nbr[c * 4];
    for (int d = 0; d < 4; ++d) {
        unsigned int n = cn[d];
        if (visited[n]) continue;
        if (board[n] & alive_mask) continue;
        visited[n] = true;
        queue[back++] = n;
    }

    long score = 0;
    while (front < back) {
        unsigned int idx = queue[front++];
        score += (count_free_neighbors(idx) >= 2) ? 2 : 1;
        const unsigned int* nb = &nbr[idx * 4];
        for (int d = 0; d < 4; ++d) {
            unsigned int n = nb[d];
            if (visited[n]) continue;
            if (board[n] & alive_mask) continue;
            visited[n] = true;
            queue[back++] = n;
        }
    }
    return score;
}

int Board::fill_efficiently(unsigned int q) const {
    // Endgame special case (two players, enemy unreachable): the game is now a
    // pure longest-path race in our own region, so just pick the direction that
    // fills it most efficiently. Longest-path is NP-hard, so this is a greedy
    // heuristic: pick the move maximizing score_fill (connectivity + pocket
    // penalty), breaking ties via Warnsdorff's rule -- prefer stepping into the
    // more enclosed cell so the open interior is preserved for later.
    const unsigned int* nb = &nbr[head_pos[q] * 4];
    int best_dir = -1;
    long best_score = -1;
    for (int d = 0; d < 4; ++d) {
        unsigned int c = nb[d];
        if (board[c] & alive_mask) continue; // occupied by an alive bit
        // score_fill dominates (scaled past the <=4 tiebreak range); the
        // subtracted free-neighbour count realises the Warnsdorff preference.
        long s = score_fill(c) * 8 - (long)count_free_neighbors(c);
        if (s > best_score) {
            best_score = s;
            best_dir = d;
        }
    }
    return best_dir; // caller guarantees >=1 free neighbour, so never -1 here
}

int Board::pick_move_dir(unsigned int q,
                         unsigned int num_sims,
                         unsigned int max_depth,
                         double W_WIN, double W_LOSS, double K,
                         double W_PLAYERS, double W_FREE,
                         unsigned int seed) {
    const unsigned int* nb = &nbr[head_pos[q] * 4];
    unsigned int possible[4];   // direction indices of free cells
    int np = 0;
    for (int d = 0; d < 4; ++d) {
        unsigned int c = nb[d];
        if (board[c] & alive_mask) continue;   // occupied by an alive bit
        possible[np++]  = d;
    }
    if (np == 0) return -1;          // boxed in: caller decides what to do
    if (np == 1) return possible[0]; // forced move, skip the rollouts

    //one extra case: if only 2 players are left, and we are not in the flood fill of the other player,
    //then we can just very efficiently fill the rest of the board. 
    
    if(count_alive() == 2){
        int enemy_q = -1;
        for(unsigned int i = 0; i < num_players; i++){
            if(i != q && (alive_mask & (1U << i))){
                enemy_q = i;
                break;
            }
        }
        if(enemy_q != -1 && min_enemy_distance(q) == -1){ // if the enemy is far away, we can just fill the board. 
            return fill_efficiently(q);
        }
    }

    //now we can do MCMC here!
    //for each possible move, roll out random games that start by committing to
    //that move's destination cell. Results are kept raw for now.
    vector<vector<MCMC_result>> move_scores(np);
    for (int i = 0; i < np; ++i){
        move_scores[i] = run_mcmc(
            *this,
            q,               // perspective player
            nb[possible[i]], // destination cell of this candidate move
            num_sims,        // num sims
            max_depth,       // max depth
            seed             // rollout seed
        );
    }
    // Collapse each move's rollouts into a single pessimistic score:
    //   per rollout:  r = time_alive + W_WIN*win + W_LOSS*dead
    //   per move:     score = mean(r) - K * std(r)
    // K is hand-tuned; K=0 is plain expected reward (first experiment).
    // W_WIN/W_LOSS dominate max_depth so a decisive result outweighs survival.
    // W_WIN, W_LOSS and K are supplied by the caller (see signature).
    int best_i = 0;
    double best_score = -INFINITY;
    for (int i = 0; i < np; ++i){
        const vector<MCMC_result>& rs = move_scores[i];
        unsigned int n = rs.size();
        if (n == 0) continue;

        double sum = 0.0, sum_sq = 0.0;
        for (const MCMC_result& r : rs){
            // W_FREE weights the free (reachable) cell fraction; W_PLAYERS
            // rewards (or, if negative, discourages) a change in the number of
            // players alive over the rollout.
            double v = W_FREE * r.reachable_cell_frac;
            v += r.win ? W_WIN : 0;
            v += r.dead ? W_LOSS : 0;
            v += W_PLAYERS * r.player_death_count;
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
    return possible[best_i];
}

string Board::get_player_move(unsigned int num_sims,
                              unsigned int max_depth,
                              double W_WIN,
                              double W_LOSS,
                              double K,
                              double W_PLAYERS,
                              double W_FREE){
    int d = pick_move_dir(player_id, num_sims, max_depth,
                          W_WIN, W_LOSS, K, W_PLAYERS, W_FREE, /*seed=*/123);
    if (d < 0) return "rip";
    return interpret_direction((unsigned int)d);
}

int Board::get_move(unsigned int q,
                    unsigned int num_sims,
                    unsigned int max_depth,
                    double W_WIN, double W_LOSS, double K,
                    double W_PLAYERS, double W_FREE,
                    unsigned int seed){
    return pick_move_dir(q, num_sims, max_depth, W_WIN, W_LOSS, K, W_PLAYERS, W_FREE, seed);
}

void Board::step_dirs(const std::vector<int>& dirs) {
    unsigned int idxs[32];
    for (unsigned int q = 0; q < num_players; ++q) {
        if (!(alive_mask & (1U << q)) || q >= dirs.size()) {
            idxs[q] = 0; // dead / unspecified: placeholder, step() skips it
            continue;
        }
        int d = dirs[q];
        // A boxed-in player reports dir -1; send it into an (occupied)
        // neighbour so step() resolves its death normally.
        unsigned int dir = (d >= 0 && d < 4) ? (unsigned int)d : 0;
        idxs[q] = nbr[head_pos[q] * 4 + dir];
    }
    step(idxs);
}

bool Board::is_alive(unsigned int q) const {
    return (alive_mask & (1U << q)) != 0;
}

unsigned int Board::count_alive() const {
    return (unsigned int)__builtin_popcount(alive_mask);
}

unsigned int Board::get_width() const {
    return (unsigned int)width;
}

std::vector<int> Board::get_trail_grid() const {
    unsigned int board_size = (unsigned int)width * width;
    std::vector<int> grid(board_size);
    for (unsigned int i = 0; i < board_size; ++i) {
        // Only render trails of still-alive players: a dead player's bits linger
        // in `board` but its cells should revert to background.
        grid[i] = (board[i] & alive_mask) ? (int)__builtin_ctz(board[i]) : -1;
    }
    return grid;
}

std::vector<int> Board::get_head_grid() const {
    unsigned int board_size = (unsigned int)width * width;
    std::vector<int> grid(board_size);
    for (unsigned int i = 0; i < board_size; ++i) {
        // Skip dead players: their head stays in head_map but must not render.
        unsigned int h = head_map[i];
        grid[i] = (h && (alive_mask & (1U << (h - 1)))) ? (int)(h - 1) : -1;
    }
    return grid;
}

std::vector<bool> Board::get_alive() const {
    std::vector<bool> a(num_players);
    for (unsigned int q = 0; q < num_players; ++q) {
        a[q] = (alive_mask & (1U << q)) != 0;
    }
    return a;
}

int Board::winner() const {
    if (count_alive() != 1) return -1; // still running, or mutual-death draw
    return __builtin_ctz(alive_mask);
}

Board::~Board() {
    delete[] head_pos;
    delete[] board;
    delete[] head_map;
    // nbr is borrowed from nbr_cache; do NOT delete
}