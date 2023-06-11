#include "TronListener.h"
#include "TronAI.h"
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

namespace py = pybind11;

/*

class TronAI {
    public:
        TronAI();
        void set_listener(TronListener* listener);
        std::string get_move();
        ~TronAI();
    private:
        TronListener* listener;
        TronSimulator* simulator;
        std::vector<vec> get_directions();
        std::string vec2String(vec v);
};

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

*/


PYBIND11_MODULE(TronGamer, m) {
    py::class_<TronAI>(m, "TronAI")
        .def(py::init<double,int>())
        .def("set_listener", &TronAI::set_listener)
        .def("get_move", &TronAI::get_move);
    py::class_<TronListener>(m, "TronListener")
        .def(py::init<int, int, int>())
        .def("update_pos", &TronListener::update_pos)
        .def("remove_player", &TronListener::remove_player)
        .def("death", &TronListener::death)
        .def_readonly("dead", &TronListener::dead)
        .def_readonly("width", &TronListener::width)
        .def_readonly("height", &TronListener::height)
        .def_readonly("player_id", &TronListener::player_id)
        .def_readonly("num_players", &TronListener::num_players);
};
