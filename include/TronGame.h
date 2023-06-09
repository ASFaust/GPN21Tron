#ifndef UTILS_H
#define UTILS_H

#include <sstream>
#include <vector>
#include <iostream>
//for throwing invalid argument:
#include <stdexcept>

using namespace std;

class TronGame;

struct vec{
    int x,y;
};

struct Player{
    vec head;
    vector<vec> trail;
    int id;
    TronGame* game;
};

class TronGame{
    public:
        TronGame(int width, int height, int n_players);
        vector<vector<int>> board;
        int width, height;
        vector<Player> players;
        void remove_player(int player_id);
        void step();
};


#endif // UTILS_H
