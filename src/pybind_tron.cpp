#include "TronGame.h"
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

namespace py = pybind11;

PYBIND11_MODULE(polyop, m) {
    py::class_<TronGame>(m, "TronGame")
        //init takes 2 ints
        .def(py::init<int, int, int>());
        .def("update_pos", &TronGame::update_pos)
        .def("remove_player", &TronGame::remove_player)
        .def("get_move", &TronGame::get_move);
};
