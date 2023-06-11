#ifndef TRONAI_H
#define TRONAI_H

#include "TronListener.h"
#include "vec.h"

#include <vector>
#include <string>
#include <random>
#include <time.h>
#include <map>
#include <iostream>
#include <thread>
#include <mutex>

using namespace std;

class TronAI {
    public:
        TronAI(double,int);
        void set_listener(TronListener& listener);
        string get_move();
        ~TronAI();
    private:
        TronListener* listener;
        int n_samples;
        int n_steps;
        double max_time;
        int** get_board_copy();
        map<int, Player*>* get_player_copy(int** board_copy);
        map<int, Player*>* reset_player_copy(map<int, Player*>* player_copies);
        int** reset_board_copy(int** board_copy);
        string vec2String(vec v);
        int flood_fill(int** board_copy, vec start);
        vector<vec> get_flood_moves(vector<vec> possible_moves);
        vector<vec> get_safe_moves(vector<vec> possible_moves);
        vec sample_games(vector<vec> possible_moves);
        void delete_board_copy(int** &board_copy);
        void delete_player_copy(map<int, Player*> *&player_copy);
        void sample_games_threaded(
            int thread_id,
            vector<vec> &possible_moves,
            vector<int> &scores,
            mutex &score_mutex,
            int** &board_copy,
            map<int, Player*> *&player_copies,
            mt19937 &rng,
            bool &stop_threads,
            int &sample_counter,
            mutex &sample_counter_mutex
        );



};

#endif  // TRONAI_H
