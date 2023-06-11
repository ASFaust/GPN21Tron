#include "vec.h"

// Default constructor
vec::vec() : x(0), y(0) {}

// Constructor with initial values
vec::vec(int x, int y) : x(x), y(y) {}

// Constructor with initializer list
vec::vec(const std::initializer_list<int>& list) {
    if (list.size() >= 2) {
        auto it = list.begin();
        x = *it++;
        y = *it;
    } else {
        x = 0;
        y = 0;
    }
}

// Addition
vec vec::operator+(const vec& other) const {
    return vec(x + other.x, y + other.y);
}

// Subtraction
vec vec::operator-(const vec& other) const {
    return vec(x - other.x, y - other.y);
}

bool vec::operator==(const vec& other) const {
    return (x == other.x) && (y == other.y);
}

// Wrap around torus boundaries
vec vec::wrap(int mx, int my) {
    x = (x + mx) % mx;
    y = (y + my) % my;
    return *this;
}

int vec::length() const {
    return std::abs(x) + std::abs(y);
}

const vec vec::directions[4] = {
    vec(0, -1),  // Up
    vec(1, 0),   // Right
    vec(0, 1),   // Down
    vec(-1, 0)   // Left
};

std::ostream& operator<<(std::ostream& os, const vec& v) {
    os << "(" << v.x << ", " << v.y << ")";
    return os;
}

