#ifndef VEC_H
#define VEC_H

#include <initializer_list>
#include <iostream>


class vec {
public:
    int x;
    int y;

    // Default constructor
    vec();

    // Constructor with initial values
    vec(int x, int y);

    // Constructor with initializer list
    vec(const std::initializer_list<int>& list);

    // Addition
    vec operator+(const vec& other) const;

    // Subtraction
    vec operator-(const vec& other) const;

    // Equality
    bool operator==(const vec& other) const;

    // Wrap around torus boundaries
    vec wrap(int mx, int my);

    // directions
    static const vec directions[4];

    // length
    int length() const;

    // for outputting to streams
    friend std::ostream& operator<<(std::ostream& os, const vec& v);

};

//for outputting to streams. need to include iostream and
std::ostream& operator<<(std::ostream& os, const vec& v);


#endif  // VEC_H
