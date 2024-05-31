#include "stuff.h"
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

namespace py = pybind11;

PYBIND11_MODULE(TronAlgos, m) {
    m.doc() = "TronAlgos python bindings";
    m.def("flood_fill", &flood_fill, "Flood fill algorithm");
    m.def("distances", &distances, "Distances of all grid cells to a given point. unreachable cells have distance -1");
};
