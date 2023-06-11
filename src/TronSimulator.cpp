#include "TronSimulator.h"
#include "vec.h"
#include "Player.h"

using namespace std;

/*

class Player {
    public:
        Player(int id, int** board, int bw, int bh);
        Player(Player* p, int** b);
        vec head;
        bool alive;
        int id;
        vector<vec> trail;
        int **board;
        int bw, bh;
        vector<vec> get_possible_moves();
        void move(vec v);
};

*/

TronSimulator::TronSimulator(
    int** _board, int _width, int _height, int _num_steps,
    map<int, Player*>* _players, int _player_id, vec _direction
){
    board = _board;
    width = _width;
    height = _height;
    num_steps = _num_steps;
    players = _players;
    player_id = _player_id;
    direction = _direction;
}

int TronSimulator::simulate() {
    //first move the player into direction, using vec.wrap
    auto& ps = *players;
    (ps[player_id])->move(direction);
    //ply.move(direction); //moving only moves the head. we need to check for head collisions after moving.
    //if head collides with head, both players die
    //if head collides with trail, player whose head it is dies
    //but first, now move all other players for the first move.
    for (auto& kv : ps) { //does that iterate over map values? it iterates over pairs, so i guess it does.
        if (kv.first == player_id) {
            continue;
        }
        Player& p = *kv.second;
        if(!p.alive) {
            continue;
        }
        auto moves = get_moves(kv.second);
        //if there are no moves, the player dies
        if (moves.size() == 0) {
            p.alive = false;
            continue;
        }
        int choice = rand() % moves.size();
        //int choice = rand() % moves.size();
        p.move(moves[choice]);
    }
    //now check for collisions of heads
    check_head_collisions();
    check_trail_collisions();
    if(!ps[player_id]->alive) {
        return 0;
    }
    remove_dead_players();
    update(); //updates trails with head positions and also updates the board.
    if(ps.size() == 1) {
        //area of board? may be a little too much.
        return num_steps;
    }
    for(int i = 0; i < num_steps; i++) {
        //now move all players
        for (auto& kv : ps) { //does that iterate over map values? it iterates over pairs, so i guess it does.
            Player& p = *kv.second;
            if(!p.alive) {
                continue;
            }
            auto moves = get_moves(kv.second);
            //if there are no moves, the player dies
            if (moves.size() == 0) {
                p.alive = false;
                continue;
            }
            int choice = rand() % moves.size();
            if(p.id == player_id) {
                choice = 0;
            } //always move in preferred direction for player
            p.move(moves[choice]);
        }
        //now check for collisions of heads
        check_head_collisions();
        check_trail_collisions();
        if(!ps[player_id]->alive) {
            return i;
        }
        remove_dead_players();
        update(); //updates trails with head positions and also updates the board.
        if(ps.size() == 1) {
            //area of board? may be a little too much.
            return num_steps;
        }
    }
    return num_steps;
}

void TronSimulator::check_head_collisions() {
    auto& ps = *players;
    for (auto& kv : ps) {
        Player& p = *kv.second;
        if(!p.alive) {
            continue;
        }
        for (auto& kv2 : ps) {
            Player& p2 = *kv2.second;
            if(!p2.alive) {
                continue;
            }
            if (p.id == p2.id) {
                continue;
            }
            if (p.head == p2.head) {
                p.alive = false;
                p2.alive = false;
            }
        }
    }
}

void TronSimulator::check_trail_collisions() {
    auto& ps = *players;
    for (auto& kv : ps) {
        Player& p = *kv.second;
        if(!p.alive) {
            continue;
        }
        for (auto& kv2 : ps) {
            Player& p2 = *kv2.second;
            if(!p2.alive) {
                continue;
            }
            for (auto& v : p2.trail) {
                if (p.head == v) { //maybe all players die here? well they should be moved, so head shouldnt be in trail.
                    p.alive = false;
                }
            }
        }
    }
}

void TronSimulator::remove_dead_players() {
    //checks the alive flag of all players and removes them from the board if they are dead.
    auto& ps = *players;
    vector<int> to_remove;
    for (auto& kv : ps) {
        Player& p = *kv.second;
        if (!p.alive) {
            to_remove.push_back(p.id);
        }
    }
    //removes their trails from the board
    for (int i : to_remove) {
        Player& p = *ps[i];
        for (auto& v : p.trail) {
            board[v.x][v.y] = -1;
        }
    }
}

void TronSimulator::update() {
    //updates the board with the new positions of the players
    auto& ps = *players;
    for (auto& kv : ps) {
        Player& p = *kv.second;
        if(!p.alive) {
            continue;
        }
        board[p.head.x][p.head.y] = p.id;
        p.trail.push_back(p.head);
    }
}

int TronSimulator::count_area() {
    //counts the floodfill free area when starting at player head.
    //free area is marked with -1 on the board.
    //board wraps around at the edges.
    int area = 0;
    auto& ps = *players;
    Player& p = *ps[player_id];
    vector<vec> to_check;
    board[p.head.x][p.head.y] = -2;
    to_check.push_back(p.head);
    while (to_check.size() > 0) {
        vec v = to_check.back();
        to_check.pop_back();
        area++;
        for (int i = 0; i < 4; i++) {
            vec v2 = v + vec::directions[i];
            v2.wrap(width, height);
            if (board[v2.x][v2.y] == -1) {
                board[v2.x][v2.y] = -2; // Mark as visited
                to_check.push_back(v2);
            }
        }
    }
    return area;
}


vector<vec> TronSimulator::get_moves(Player* p) {
    //returns a vector of possible moves for a player
    vector<vec> moves;
    vector<vec> possible_moves = p->get_possible_moves(); //possible moves are relative to the player's position

    if(possible_moves.size() == 0) {
        return moves;
    }
    else if(possible_moves.size() == 1) {
        moves.push_back(possible_moves[0]);
        return moves;
    }
    //now we want to check if the move is safe
    for (auto& v : possible_moves) {
        vec v2 = p->head + v;
        v2.wrap(width, height);
        //a move isnt safe if it leads to a dead end
        //a dead end is indicated by the 4 directions around it being occupied
        int num_occupied = 0;
        for (int i = 0; i < 4; i++) {
            vec v3 = v2 + vec::directions[i];
            v3.wrap(width, height);
            if (board[v3.x][v3.y] != -1) {
                num_occupied++;
            }
        }
        if (num_occupied < 4) {
            moves.push_back(v);
        }
    }
    if(moves.size() == 0) {
        //if no moves are safe, just return all possible moves
        moves = possible_moves;
    }
    return moves;
}

/*
class TronSimulator {
public:
    int width;
    int height;
    int** board;
    int num_steps;
    map<int, Player*>* players;
    int player_id;
    int direction;
    TronSimulator(int width, int height, int** board, int num_steps, map<int, Player*>* players, int player_id, int direction);
    int simulate();
    void check_head_collisions();
    void check_trail_collisions();
    void remove_dead_players();
    void update();
    int count_area();
};
*/
