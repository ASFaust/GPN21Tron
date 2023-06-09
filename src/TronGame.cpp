#include "TronGame.h"

using namespace std;

/*
//c++ code
struct vec{
    int x,y;
};

struct Player{
    vec head;
    vector<vec> trail;
    int id;
    TronGame* game;
    vec next_pos;
    bool alive;
    void step(); //should implement an
};

class TronGame{
    public:
        TronGame(int width, int height, int n_players);
        vector<vector<int>> board;
        int width, height;
        vector<Player> players;
        void remove_player(int player_id);
        void step();
        void set_board(... to be defined. fuck i am too tired for this shit
};

i need two different tron games. i should first concern myself with the one where i simulate locally the bots
and then make the interface to the actual game.
so i should redesign this library
*/

TronGame::TronGame(int _w, int _h, int _n){
    width = _w;
    height = _h;
    n_players = _n;
    //board is a double int vector to be initailized to -1
    board = vector<vector<int> >(width, vector<int>(height, -1));
    //coordinate system starts at top left
    /*this will be part of set_board.
    for(int i = 0; i < n_players; i++){
        players.push_back(Player());
    }*/
}

void TronGame::step(){
    for(auto& player : players){
        if(player.alive){
            player.step();
        }
    }
    
}

void TronGame::remove_player(int player_id){
    //remove the player from the board
    for(int i = 0; i < players[player_id].trail.size(); i++){
        board[players[player_id].trail[i].x][players[player_id].trail[i].y] = -1;
    }
    players[player_id].alive = false;
}

