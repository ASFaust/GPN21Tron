#ifndef RNG_H
#define RNG_H

#include <cstdint>

// Small, fast, self-contained PRNG used for MCMC move proposals.
// State is a single 64-bit value advanced by SplitMix64, which gives good
// statistical quality with no warm-up and a trivial seed step.
struct RNG_STATE {
    uint64_t s;
};

// Seed the generator. A zero seed is remapped so the stream is never all-zero.
inline void seed_rng(RNG_STATE& st, uint64_t seed) {
    st.s = seed ? seed : 0x9E3779B97F4A7C15ULL;
}

// Advance the state and return the next 32 bits. Callers take this modulo a
// small count, so we return the high half where the bits mix best.
inline unsigned int next_rng(RNG_STATE& st) {
    uint64_t z = (st.s += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    z = z ^ (z >> 31);
    return (unsigned int)(z >> 32);
}

#endif
