#include "TronListener.h"
#include "Player.h"
#include "vec.h"

//the listener interfaces with the tcp API strings
//it provides the trails and game board to the Ai class
//the ai class then can use the simulator class with the listener's data to simulate the game from the current listener state

//the listener recieves width, height and player_id on construction
//then it recieves position updates. it needs to figure out the number of players from the position updates

//the player ids start at 0, so empty board spaces are represented by -1

//the players contain vec head, and vector<vec> trail, which should include head.

//vec supports bracket initialization, so vec v = {1, 2} is valid

//the listener doesnt need to keep track of anything about the self player except for its id.

/*

the player class looks like this:


class Player {
    public:
        Player(int id);
        vec head;
        int id;
        bool alive;
        vector<vec> trail;
};
*/

using namespace std;

TronListener::TronListener(int _width, int _height, int _player_id) {
    width = _width;
    height = _height;
    player_id = _player_id;
    num_players = 0;
    board = new int*[width];
    for(int i = 0; i < width; i++){
        board[i] = new int[height];
        for(int j = 0; j < height; j++){
            board[i][j] = -1;
        }
    }
    dead = false;
}

//Player::Player(int _id, int** _board, int _bw, int _bh) {

void TronListener::update_pos(int p_id, int x, int y){
    //we need to look in the map of players, wether the player exists or not
    //if it doesnt exist, we need to create it
    //if it does exist, we need to update it

    //if the player doesnt exist, we need to add it to the map
    if(players.find(p_id) == players.end()){
        players[p_id] = new Player(p_id, board, width, height);
        num_players = players.size();
    }

    //now we need to update the player's position
    players[p_id]->head = {x, y};

    //add the head to the trail
    players[p_id]->trail.push_back({x, y});

    //update the board
    board[x][y] = p_id;
}

void TronListener::remove_player(int p_id){
    if(p_id == player_id){
        death();
    }
    Player* p = players[p_id];
    //remove the trail from the board
    for(vec v : p->trail){
        board[v.x][v.y] = -1;
    }
    //remove the player from the map
    players.erase(p_id);
    //decrement the number of players
    num_players = players.size();
    //delete the player
    delete p;
}

void TronListener::death(){
    //self_id player died. set a boolean to true
    dead = true;
}

TronListener::~TronListener() {
    for(int i = 0; i < width; i++){
        delete[] board[i];
    }
    delete[] board;
    //delete all the players
    for(auto it = players.begin(); it != players.end(); it++){
        delete it->second;
    }
}
