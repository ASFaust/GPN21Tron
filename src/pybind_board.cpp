#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <stdexcept>
#include <string>
#include <vector>

#include "Board.h"

namespace py = pybind11;

PYBIND11_MODULE(TronBoard, m) {
    m.doc() = "pybind11 bindings for the Tron Board engine";

     py::class_<Board>(m, "Board")
          .def(py::init([](
                    unsigned char width,
                    unsigned int num_players,
                    unsigned int player_id,
                    const std::vector<unsigned int>& xs,
                    const std::vector<unsigned int>& ys){
               if (xs.size() != num_players)
                    throw std::invalid_argument(
                         "xs length must equal num_players");

               if (ys.size() != num_players)
                    throw std::invalid_argument(
                         "ys length must equal num_players");

               return new Board(
                    width,
                    num_players,
                    player_id,
                    const_cast<unsigned int*>(xs.data()),
                    const_cast<unsigned int*>(ys.data()));
               }),
               py::arg("width"),
               py::arg("num_players"),
               py::arg("player_id"),
               py::arg("xs"),
               py::arg("ys"))
          .def("update_positions",
               [](Board& b,
                    const std::vector<unsigned int>& xs,
                    const std::vector<unsigned int>& ys)
               {
                    if (xs.size() != ys.size())
                         throw std::invalid_argument(
                              "xs and ys must be the same length");

                    b.update_positions(
                         xs.data(),
                         ys.data());
               },
               py::arg("xs"),
               py::arg("ys"))
          .def("remove_player", &Board::remove_player, py::arg("p_id"))
          .def("get_player_move", &Board::get_player_move,
               py::arg("num_sims")    = 200,
               py::arg("max_depth")   = 50,
               py::arg("W_WIN")       = 10.0,
               py::arg("W_LOSS")      = 10.0,
               py::arg("K")           = 0.0,
               py::arg("DIR_PERSIST") = 0.0)
          // --- local self-play / evaluation interface ---
          .def("get_move", &Board::get_move,
               py::arg("q"),
               py::arg("num_sims")    = 200,
               py::arg("max_depth")   = 50,
               py::arg("W_WIN")       = 10.0,
               py::arg("W_LOSS")      = 10.0,
               py::arg("K")           = 0.0,
               py::arg("DIR_PERSIST") = 0.0,
               py::arg("seed")        = 123)
          .def("step_dirs", &Board::step_dirs, py::arg("dirs"))
          .def("is_alive", &Board::is_alive, py::arg("q"))
          .def("count_alive", &Board::count_alive)
          .def("winner", &Board::winner)
          // --- state readout (for visualization) ---
          .def("get_width", &Board::get_width)
          .def("get_trail_grid", &Board::get_trail_grid)
          .def("get_head_grid", &Board::get_head_grid)
          .def("get_alive", &Board::get_alive);
}
