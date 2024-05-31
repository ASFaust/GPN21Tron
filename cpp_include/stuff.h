#ifndef STUFF_H
#define STUFF_H

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

using namespace std;

namespace py = pybind11;

//define the function that takes a numpy array of type int and returns a float
float flood_fill(py::array_t<int> &input_array, int x, int y);
py::array_t<int> distances(py::array_t<int> &input_array, int x, int y);

#endif
