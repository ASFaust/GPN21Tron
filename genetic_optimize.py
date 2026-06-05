"""Coevolutionary genetic algorithm over MCMC hyperparameters.

The hard part here is that fitness is *relative*, not absolute: a config's win
rate depends entirely on who it's fighting. That breaks a naive GA in three ways
-- the target moves every generation (win rates aren't comparable across gens),
strategies can cycle (A beats B beats C beats A), and the pool can collapse onto
one style so the signal goes flat.

The fix is a Hall of Fame. Every battle is salted with a few champions archived
from previous generations, so each config is measured partly against a slowly-
moving, stable reference and not just its volatile peers. Elitism + the archive
keep the search from regressing or chasing its tail.

Genome = the kwargs Board.get_move accepts (see PARAMS). As in the random search
we hold max_depth * num_sims == BUDGET so every config gets the same compute per
move; the evolvable knob is max_depth and num_sims is derived from it.

Run: /home/andreas/venv/bin/python genetic_optimize.py
"""

import math
import multiprocessing as mp
import os
import random
import time

from eval_battle import run_battle

# --- search space ------------------------------------------------------------
BUDGET = 30000  # max_depth * num_sims, held constant across all configs

# Each evolvable gene: (low, high, scale). "log" genes mutate/cross multiplica-
# tively (matches how they span orders of magnitude); "lin" genes additively.
# max_depth is the compute knob; num_sims is derived as BUDGET / max_depth.
PARAMS = {
    "max_depth":   (3,    400.0, "log"),
    "W_WIN":       (0.1,  200.0,  "log"),
    "W_LOSS":      (0.1,  200.0, "log"),
    "K":           (-3.0,  3.0,   "lin"),
    "DIR_PERSIST": (-20.0, 20.0,  "lin"),
}

# --- GA knobs ----------------------------------------------------------------
POP_SIZE = 100             # configs per generation
GENERATIONS = 25
ELITES = 10                # top configs copied unchanged into the next gen
TOURNAMENT_K = 5          # tournament size for parent selection
CROSS_RATE = 0.5          # chance a child is a crossover (else a clone of one parent)
MUT_RATE = 0.3            # per-gene mutation probability
MUT_SIGMA = 0.35          # mutation strength (log-space stdev / fraction of lin range)

# --- evaluation knobs --------------------------------------------------------
BATTLES_PER_GEN = 300
MIN_PLAYERS = 10
MAX_PLAYERS = 16
HOF_SIZE = 30             # max champions kept in the archive
HOF_ANCHORS = 2           # champions injected into each battle (when available)
SMOOTH = 1.0              # Laplace smoothing on win rate: (wins+s)/(games+2s)
NUM_WORKERS = os.cpu_count()


# --- genome helpers ----------------------------------------------------------
def loguniform(rng, lo, hi):
    return math.exp(rng.uniform(math.log(lo), math.log(hi)))


def _finish(genes):
    """Turn a gene dict into a full, budget-honest config dict."""
    max_depth = max(1, round(genes["max_depth"]))
    num_sims = max(1, round(BUDGET / max_depth))
    max_depth = max(1, round(BUDGET / num_sims))  # snap so the product is exact
    return dict(
        num_sims=num_sims,
        max_depth=max_depth,
        W_WIN=round(genes["W_WIN"], 2),
        W_LOSS=round(genes["W_LOSS"], 2),
        K=round(genes["K"], 3),
        DIR_PERSIST=round(genes["DIR_PERSIST"], 3),
    )


def random_genes(rng):
    g = {}
    for name, (lo, hi, scale) in PARAMS.items():
        g[name] = loguniform(rng, lo, hi) if scale == "log" else rng.uniform(lo, hi)
    return g


def _clamp(name, val):
    lo, hi, _ = PARAMS[name]
    return min(hi, max(lo, val))


def crossover(rng, a, b):
    """Blend two parents gene by gene (geometric for log genes, linear else)."""
    child = {}
    for name, (lo, hi, scale) in PARAMS.items():
        t = rng.random()
        if scale == "log":
            child[name] = math.exp(t * math.log(a[name]) + (1 - t) * math.log(b[name]))
        else:
            child[name] = t * a[name] + (1 - t) * b[name]
    return child


def mutate(rng, g):
    out = dict(g)
    for name, (lo, hi, scale) in PARAMS.items():
        if rng.random() >= MUT_RATE:
            continue
        if scale == "log":
            out[name] = _clamp(name, out[name] * math.exp(rng.gauss(0, MUT_SIGMA)))
        else:
            out[name] = _clamp(name, out[name] + rng.gauss(0, MUT_SIGMA) * (hi - lo))
    return out


def fmt_config(c):
    return (
        f"sims={c['num_sims']:>5} depth={c['max_depth']:>4} "
        f"W_WIN={c['W_WIN']:>5.2f} W_LOSS={c['W_LOSS']:>6.2f} K={c['K']:>5.3f} "
        f"DIR_PERSIST={c['DIR_PERSIST']:>6.3f}"
    )


# --- parallel battle workers -------------------------------------------------
# Each generation we hand the workers the combined (population + HoF) config list
# as a module global, so battle tasks stay tiny (just indices + seed).
_WORKER_POOL = None


def _init_worker(pool):
    global _WORKER_POOL
    _WORKER_POOL = pool


def _run_one(task):
    idxs, seed = task
    configs = [_WORKER_POOL[i] for i in idxs]
    return idxs, run_battle(configs, seed=seed)


# --- evaluation --------------------------------------------------------------
def evaluate(pop_configs, hof_configs, rng, gen):
    """Coevolutionary fitness: win rate over battles salted with HoF anchors.

    Returns a fitness list aligned with pop_configs (smoothed win rate), plus the
    raw (wins, games) for logging. Only population members are scored; the HoF
    champions are there purely as a stable yardstick.
    """
    P = len(pop_configs)
    combined = pop_configs + hof_configs  # pop -> [0,P), hof -> [P, P+H)
    hof_idx = list(range(P, P + len(hof_configs)))

    wins = [0] * len(combined)
    games = [0] * len(combined)

    # Pre-roll matchups deterministically. Each battle pulls a couple of random
    # HoF anchors plus the population members that have been seen least so far,
    # so every config gets a comparable number of games against the archive.
    seen = [0] * P
    tasks = []
    for _ in range(BATTLES_PER_GEN):
        n = rng.randint(MIN_PLAYERS, MAX_PLAYERS)
        anchors = rng.sample(hof_idx, min(HOF_ANCHORS, len(hof_idx))) if hof_idx else []
        n_peers = max(2, n - len(anchors))
        order = sorted(range(P), key=lambda i: (seen[i], rng.random()))
        peers = order[:n_peers]
        for i in peers:
            seen[i] += 1
        idxs = peers + anchors
        rng.shuffle(idxs)  # don't bias the winner index by how we built the list
        tasks.append((idxs, rng.randrange(1, 2**32)))

    t0 = time.time()
    done = 0
    with mp.Pool(NUM_WORKERS, initializer=_init_worker, initargs=(combined,)) as mpool:
        for idxs, local_winner in mpool.imap_unordered(_run_one, tasks):
            done += 1
            n = len(idxs)
            for i in idxs:
                games[i] += 1
            if local_winner == -1:
                winner_global = -1
                win_str = "draw  "
            else:
                winner_global = idxs[local_winner]
                wins[winner_global] += 1
                # Label the winner by where it lives: a population member or a
                # Hall-of-Fame anchor (the latter don't get bred, just measured).
                if winner_global < P:
                    win_str = f"pop {winner_global:>3}"
                else:
                    win_str = f"hof {winner_global - P:>3}"
            n_anchors = sum(1 for i in idxs if i >= P)
            rate = done / (time.time() - t0)
            print(
                f"  gen {gen:>2} battle {done:>4}/{BATTLES_PER_GEN} | "
                f"n={n:>2} ({n_anchors} hof) | winner {win_str} | "
                f"{rate:5.1f} battles/s"
            )

    fitness = [
        (wins[i] + SMOOTH) / (games[i] + 2 * SMOOTH) if games[i] else 0.0
        for i in range(P)
    ]
    return fitness, wins[:P], games[:P]


# --- selection ---------------------------------------------------------------
def tournament(rng, fitness):
    """Pick one parent index via tournament selection (robust to noisy fitness)."""
    contenders = rng.sample(range(len(fitness)), min(TOURNAMENT_K, len(fitness)))
    return max(contenders, key=lambda i: fitness[i])


# --- main loop ---------------------------------------------------------------
def optimize(seed=0):
    rng = random.Random(seed)

    population = [random_genes(rng) for _ in range(POP_SIZE)]
    hof = []          # list of champion gene dicts
    hof_fitness = []  # their fitness at archival time, for pruning ties

    print(f"=== MCMC genetic search: pop={POP_SIZE}, gens={GENERATIONS} ===")
    print(f"budget(depth*sims)={BUDGET}, battles/gen={BATTLES_PER_GEN}, "
          f"players/battle={MIN_PLAYERS}..{MAX_PLAYERS}, "
          f"HoF={HOF_SIZE} (anchors={HOF_ANCHORS}), workers={NUM_WORKERS}\n")

    best_overall = None
    best_overall_fit = -1.0

    for gen in range(GENERATIONS):
        t0 = time.time()
        pop_configs = [_finish(g) for g in population]
        hof_configs = [_finish(g) for g in hof]
        fitness, wins, games = evaluate(pop_configs, hof_configs, rng, gen)

        ranked = sorted(range(POP_SIZE), key=lambda i: fitness[i], reverse=True)
        best = ranked[0]
        if fitness[best] > best_overall_fit:
            best_overall_fit = fitness[best]
            best_overall = pop_configs[best]

        dt = time.time() - t0
        print(f"gen {gen:>2}/{GENERATIONS} | best wr={fitness[best]:6.1%} "
              f"({wins[best]}/{games[best]}) | "
              f"mean wr={sum(fitness) / POP_SIZE:6.1%} | "
              f"HoF={len(hof)} | {dt:4.1f}s")
        print(f"        best: {fmt_config(pop_configs[best])}")

        # Archive this generation's champion, then keep the strongest HOF_SIZE.
        hof.append(dict(population[best]))
        hof_fitness.append(fitness[best])
        if len(hof) > HOF_SIZE:
            keep = sorted(range(len(hof)), key=lambda i: hof_fitness[i],
                          reverse=True)[:HOF_SIZE]
            hof = [hof[i] for i in keep]
            hof_fitness = [hof_fitness[i] for i in keep]

        if gen == GENERATIONS - 1:
            break

        # Build the next generation: elites carried over, the rest bred from
        # tournament-selected parents with crossover + mutation.
        next_pop = [dict(population[i]) for i in ranked[:ELITES]]
        while len(next_pop) < POP_SIZE:
            pa = population[tournament(rng, fitness)]
            if rng.random() < CROSS_RATE:
                pb = population[tournament(rng, fitness)]
                child = crossover(rng, pa, pb)
            else:
                child = dict(pa)
            next_pop.append(mutate(rng, child))
        population = next_pop

    print("\n=== final Hall of Fame (top 10 by archival fitness) ===")
    order = sorted(range(len(hof)), key=lambda i: hof_fitness[i], reverse=True)
    for rank, i in enumerate(order[:10]):
        cfg = _finish(hof[i])
        print(f"#{rank + 1:>2} wr={hof_fitness[i]:6.1%} | {fmt_config(cfg)}")
        print(f"     {cfg}")

    print(f"\nBEST CONFIG (wr={best_overall_fit:.1%}):\n  {best_overall}")
    return best_overall


if __name__ == "__main__":
    optimize()
