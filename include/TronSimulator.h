#ifndef TRONSIMULATOR_H
#define TRONSIMULATOR_H
#include "Player.h"
#include "vec.h"

#include <map>
#include <vector>
#include <iostream>
#include <string>
#include <stdlib.h>
#include <time.h>

using namespace std;

class TronSimulator {
    public:
        TronSimulator(
            int** board, int width, int height,
            int num_steps, map<int, Player*>* players,
            int player_id, vec direction
            );
        vec direction; //the direction the player_id is to be moved in the first step
        int simulate();
        void check_head_collisions();
        void check_trail_collisions();
        void remove_dead_players();
        void update();
        int count_area();

        vector<vec> get_moves(Player* p);

        int width;
        int height;
        int** board;
        int num_steps;
        map<int, Player*>* players;
        int player_id;
};

#endif