#ifndef TRONLISTENER_H
#define TRONLISTENER_H

#include <map>
#include <vector>
#include "vec.h"
#include "Player.h"

using namespace std;

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

#endif  // TRONLISTENER_H