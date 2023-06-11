#include "Player.h"
#include "vec.h"

/*
class Player {
    public:
        Player(int id);
        vec head;
        bool alive;
        int id;
        vector<vec> trail;
        int **board;
        int bw, bh;
        vector<vec> get_possible_moves();
};
*/

Player::Player(int _id, int** _board, int _bw, int _bh) {
    alive = true;
    id = _id;
    board = _board;
    bw = _bw;
    bh = _bh;
}

Player::Player(Player* p, int** b){
//create a copy of the player on the board b
    alive = true;
    id = p->id;
    head = p->head;
    board = b;
    bw = p->bw;
    bh = p->bh;
    trail = p->trail; //does this copy the vector?
}

vector<vec> Player::get_possible_moves() {
    vector<vec> moves;
    if (alive) {
        //check up
        if (board[head.x][(head.y-1+bh)%bh] == -1) {
            moves.push_back(vec(0, -1));
        }
        //check down
        if (board[head.x][(head.y+1)%bh] == -1) {
            moves.push_back(vec(0, 1));
        }
        //check left
        if (board[(head.x-1+bw)%bw][head.y] == -1) {
            moves.push_back(vec(-1, 0));
        }
        //check right
        if (board[(head.x+1)%bw][head.y] == -1) {
            moves.push_back(vec(1, 0));
        }
    }
    return moves;
}

void Player::move(vec dir) {
    head = head + dir;
    head.x = (head.x + bw) % bw;
    head.y = (head.y + bh) % bh;
    //trail.push_back(head); //can't push the trail yet because others might have moved there too.
}


