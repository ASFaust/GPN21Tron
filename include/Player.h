#ifndef PLAYER_H
#define PLAYER_H

#include "vec.h"
#include <vector>

using namespace std;

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

#endif  // PLAYER_H