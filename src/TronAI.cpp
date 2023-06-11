#include "TronSimulator.h"
#include "TronAI.h"
#include "TronListener.h"
#include "vec.h"
#include "Player.h"

#include <random>
#include <time.h>
#include <string>
#include <vector>
#include <map>
#include <iostream>
#include <assert.h>
#include <queue>
#include <thread>

using namespace std;

//the tronAI class is the main class of the TronAI package
//it uses the listener to get the state of the game,
//and uses the simulator to simulate the game. it does so by the following process:

//1. get the current state of the game from the listener
//2. get all current possible moving directions for the player
//3. for each direction, create a copy of the state and move the player in that direction
//4. simulate the game for a certain number of steps a number of times using the simulator.
//the simulator does a random walk for all players, so we can sample the possible moves of the other players
//each time it runs, it returns true if the player is still alive after the n simulation steps, false otherwise
//5. calculate the score for each direction by counting the number of times the player survived
//6. return the direction with the highest score

//the tronListener class looks like this:

/*
class TronListener {
    public:
        TronListener(int width, int height, int player_id);
        void update_pos(int p_id, int x, int y);
        void remove_player(int p_id);
        void death();
        ~TronListener();
        bool dead;
        int width;
        int height;
        int player_id;
        int num_players;
        int** board;
        std::map<int, Player*> players;
};

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

TronAI::TronAI(double _max_time, int _n_steps) {
    srand(time(NULL));
    max_time = _max_time;
    n_steps = _n_steps;
}

void TronAI::set_listener(TronListener& _listener){
    listener = &_listener;
}

string TronAI::get_move(){
    if (listener->dead){
        cout << "listener dead" << endl;
        return "left";
    }
    //get the possible directions
    vector<vec> possible_moves = listener->players[listener->player_id]->get_possible_moves();
    if (possible_moves.size() == 0){
        cout << "no possible moves" << endl;
        return "left";
    }
    if (possible_moves.size() == 1){
        cout << "only one possible move" << endl;
        return vec2String(possible_moves[0]);
    }
    vector<vec> best_flood_moves = get_flood_moves(possible_moves);
    vector<vec> safe_flood_moves = get_safe_moves(best_flood_moves);
    vector<vec> safe_moves = get_safe_moves(possible_moves);
    if(safe_flood_moves.size() > 0){
        cout << "safe flood moves" << endl;
        return vec2String(sample_games(safe_flood_moves));
    }else{
        //no flood moves are safe. try safe moves. might result in going to a dead end.
        if(safe_moves.size() > 0){
            cout << "safe moves" << endl;
            return vec2String(sample_games(safe_moves));
        }else{
            //no safe moves. try flood moves
            cout << "flood moves" << endl;
            return vec2String(sample_games(best_flood_moves));
        }
    }
}
/*
string TronAI::get_move(){
    if (this->listener->dead){
        cout << "listener dead" << endl;
        return "left";
    }
    //get the possible directions
    vector<vec> possible_directions = this->listener->players[this->listener->player_id]->get_possible_moves();
    if (possible_directions.size() == 0){
        cout << "no possible directions" << endl;
        return "left";
    }
    if (possible_directions.size() == 1){
        cout << "only one possible direction" << endl;
        return vec2String(possible_directions[0]);
    }
    int max_score = 0;

    int max_score_index = 0;
    int** board_copy = get_board_copy();
    map<int, Player*> *player_copies = get_player_copy(board_copy);
    for(int i = 0; i < possible_directions.size(); i++){
        int score = 0;
        for(int j = 0; j < n_samples; j++){
            board_copy = reset_board_copy(board_copy);
            player_copies = reset_player_copy(player_copies);
            TronSimulator simulator(
                board_copy,
                listener->width, listener->height,
                n_steps,
                player_copies,
                this->listener->player_id,
                possible_directions[i]);
            score += simulator.simulate();
        }
        cout << "score for direction " << vec2String(possible_directions[i]) << " is " << score << endl;
        if (score > max_score){
            max_score = score;
            max_score_index = i;
        }
    }
    for(map<int, Player*>::iterator it = player_copies->begin(); it != player_copies->end(); it++){
        delete it->second;
    }
    delete player_copies;
    for(int i = 0; i < this->listener->height; i++){
        delete [] board_copy[i];
    }
    delete [] board_copy;
    return vec2String(possible_directions[max_score_index]);
}
*/

vec TronAI::sample_games(vector<vec> possible_moves){
    int max_score = 0;
    int max_score_index = 0;
    int** board_copy = get_board_copy();
    map<int, Player*> *player_copies = get_player_copy(board_copy);
    for(int i = 0; i < possible_moves.size(); i++){
        int score = 0;
        for(int j = 0; j < n_samples; j++){
            board_copy = reset_board_copy(board_copy);
            player_copies = reset_player_copy(player_copies);
            TronSimulator simulator(
                board_copy,
                listener->width, listener->height,
                n_steps,
                player_copies,
                this->listener->player_id,
                possible_moves[i]);
            score += simulator.simulate();
        }
        cout << "score for direction " << vec2String(possible_moves[i]) << " is " << score << endl;
        if (score > max_score){
            max_score = score;
            max_score_index = i;
        }
    }
    for(map<int, Player*>::iterator it = player_copies->begin(); it != player_copies->end(); it++){
        delete it->second;
    }
    delete player_copies;
    for(int i = 0; i < this->listener->height; i++){
        delete [] board_copy[i];
    }
    delete [] board_copy;
    return possible_moves[max_score_index];
}

void TronAI::delete_board_copy(int** &board_copy){
    for(int i = 0; i < listener->width; i++){
        delete[] board_copy[i];
    }
    delete[] board_copy;
}

void TronAI::delete_player_copy(map<int, Player*> *&player_copy){
    //iterate over kv pairs
    for(auto const& kv : *player_copy){
        //delete the player
        delete kv.second;
        //delete player_copy[i];
    }
    delete[] player_copy;
}

vector<vec> TronAI::get_flood_moves(vector<vec> possible_moves){
    vector<vec> best_flood_moves;
    int max_flood_area = -1;
    for(int i = 0; i < possible_moves.size(); i++){
        int** board_copy = get_board_copy();
        vec move = possible_moves[i];
        vec head = listener->players[listener->player_id]->head + move;
        head.wrap(listener->width, listener->height);
        int flood_area = flood_fill(board_copy, head);
        if(flood_area > max_flood_area){
            max_flood_area = flood_area;
            best_flood_moves.clear();
            best_flood_moves.push_back(move);
        }else if(flood_area == max_flood_area){
            best_flood_moves.push_back(move);
        }
        delete_board_copy(board_copy);
        cout << "flood area for move " << vec2String(move) << " is " << flood_area << endl;
    }
    return best_flood_moves;
}

int TronAI::flood_fill(int** board_copy, vec start){
    int flood_area = 0;
    //cout << "flood fill start: " << vec2String(start) << endl;
    flood_area++;
    board_copy[start.x][start.y] = 1;
    queue<vec> q;
    q.push(start);
    while(!q.empty()){
        vec current = q.front();
        q.pop();
        for(int i = 0; i < 4; i++){
            vec next = current + vec::directions[i];
            next.wrap(listener->width, listener->height);
            if(board_copy[next.x][next.y] == -1){
                flood_area++;
                board_copy[next.x][next.y] = 1;
                q.push(next);
            }
        }
    }
    return flood_area;
}

vector<vec> TronAI::get_safe_moves(vector<vec> possible_moves){
    vector<vec> safe_moves;
    int** tainted_board = get_board_copy();
    //taint board with possible enemy moves
    for(map<int, Player*>::iterator it = listener->players.begin(); it != listener->players.end(); it++){
        if(it->first != listener->player_id){
            vec head = it->second->head;
            for(int i = 0; i < 4; i++){
                vec next = head + vec::directions[i];
                next.wrap(listener->width, listener->height);
                tainted_board[next.x][next.y] = 1;
            }
        }
    }
    //check if possible moves are safe
    for(int i = 0; i < possible_moves.size(); i++){
        vec move = possible_moves[i];
        vec head = listener->players[listener->player_id]->head + move;
        head.wrap(listener->width, listener->height);
        if(tainted_board[head.x][head.y] == -1){
            safe_moves.push_back(move);
        }
    }
    //clean up
    delete_board_copy(tainted_board);
    return safe_moves;
}


int** TronAI::get_board_copy(){
    int** board_copy = new int*[listener->width];
    for(int i = 0; i < listener->width; i++){
        board_copy[i] = new int[listener->height];
        for(int j = 0; j < listener->height; j++){
            board_copy[i][j] = listener->board[i][j];
        }
    }
    return board_copy;
}

map<int, Player*>* TronAI::get_player_copy(int** board_copy){
    map<int, Player*> *player_copies = new map<int, Player*>();
    for(map<int, Player*>::iterator it = listener->players.begin(); it != listener->players.end(); it++){
        Player* p = it->second;
        Player* p_copy = new Player(p, board_copy);
        player_copies->insert(pair<int, Player*>(p->id, p_copy));
    }
    return player_copies;
}

int** TronAI::reset_board_copy(int** board_copy){
    for(int i = 0; i < listener->height; i++){
        for(int j = 0; j < listener->width; j++){
            board_copy[i][j] = listener->board[i][j];
        }
    }
    return board_copy;
}

map<int, Player*>* TronAI::reset_player_copy(map<int, Player*>* player_copies){
    for(map<int, Player*>::iterator it = player_copies->begin(); it != player_copies->end(); it++){
        Player* p = it->second;
        p->head = listener->players[p->id]->head;
        p->alive = listener->players[p->id]->alive;
        assert (p->alive);
        p->trail = listener->players[p->id]->trail;
    }
    return player_copies;
}

string TronAI::vec2String(vec v){
    //coordinate system is top left is (0, 0)
    //bottom right is (width, height)

    //the string return should be "up", "down", "left", or "right"
    //v is one of (-1, 0), (1, 0), (0, -1), (0, 1)
    if(v.x == -1){
        return "left";
    }
    if(v.x == 1){
        return "right";
    }
    if(v.y == -1){
        return "up";
    }
    if(v.y == 1){
        return "down";
    }
    cout << "error in vec2String" << endl;
    return "left";
}

TronAI::~TronAI() {

}
