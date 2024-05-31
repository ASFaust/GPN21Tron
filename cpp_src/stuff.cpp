#include "stuff.h"
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <vector>
#include <tuple>
#include <queue>

float flood_fill(py::array_t<int> &input_array, int x, int y) {
    py::buffer_info buf = input_array.request();
    int *ptr = static_cast<int *>(buf.ptr);
    int rows = buf.shape[0];
    int cols = buf.shape[1];

    // Use a stack to keep track of cells to visit
    std::vector<std::tuple<int, int>> stack;
    stack.emplace_back(x, y);
    int count = 0;

    while (!stack.empty()) {
        auto [cx, cy] = stack.back();
        stack.pop_back();

        int index = cx * cols + cy;

        // If the cell is not free space, skip it
        if (ptr[index] != -1) { // -1 marks free space
            continue;
        }

        // Mark the cell as visited
        ptr[index] = -2; // -2 marks visited space
        count++;

        // Push neighboring cells onto the stack
        stack.emplace_back((cx + 1) % rows, cy);
        stack.emplace_back((cx - 1 + rows) % rows, cy);
        stack.emplace_back(cx, (cy + 1) % cols);
        stack.emplace_back(cx, (cy - 1 + cols) % cols);
    }

    return count;
}

py::array_t<int> distances(py::array_t<int> &input_array, int x, int y) {
    // this function calculates the distance of each cell from the given cell (x, y)
    // but only for cells which are free cells (i.e. have value -1)

    py::buffer_info buf = input_array.request();
    int *ptr = static_cast<int *>(buf.ptr);
    int rows = buf.shape[0];
    int cols = buf.shape[1];

    // Initialize the distance array
    py::array_t<int> output_array({rows, cols});
    py::buffer_info out_buf = output_array.request();
    int *out_ptr = static_cast<int *>(out_buf.ptr);
    std::fill(out_ptr, out_ptr + rows * cols, -1);

    // Use a queue to keep track of cells to visit
    std::queue<std::tuple<int, int>> queue;

    // Push the starting cell onto the queue
    queue.emplace(x, y);

    // Initialize the distance of the starting cell to 0

    int index = x * cols + y;

    out_ptr[index] = 0;

    while (!queue.empty()) {
        auto [cx, cy] = queue.front();
        queue.pop();
        ptr[cx * cols + cy] = -2; // mark as visited

        // Push neighboring cells onto the queue. deltas for neighbors are (1, 0), (-1, 0), (0, 1), (0, -1)
        for (auto [dx, dy] : std::vector<std::pair<int, int>>{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}) {
            int nx = (cx + dx + rows) % rows;
            int ny = (cy + dy + cols) % cols;
            int nindex = nx * cols + ny;

            // If the cell is not free space or has already been visited, skip it
            if (ptr[nindex] != -1){
                continue;
            }

            ptr[nindex] = -2; // mark as visited

            // calculate the distance of the neighboring cell
            out_ptr[nindex] = out_ptr[cx * cols + cy] + 1;

            // Push the cell onto the queue
            queue.emplace(nx, ny);
        }
    }

    return output_array;
}