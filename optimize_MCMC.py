"""Random search over MCMC hyperparameters using self-play battles.

We sample a pool of random MCMC configs, then repeatedly throw a random subset
of them into a free-for-all battle (see eval_battle.run_battle). Win rates are
tallied per config across all battles it took part in, and the config with the
highest win rate wins the search.

Fairness: every config gets the same compute budget. We hold the product
max_depth * num_sims constant at BUDGET (30k) so a deep-shallow config and a
wide-shallow config are doing roughly the same amount of work per move.
"""

import math
import multiprocessing as mp
import os
import random
import time

from eval_battle import run_battle

BUDGET = 30000  # max_depth * num_sims, held constant across all configs

# How many distinct configs to sample and how hard to test them.
POOL_SIZE = 100
NUM_BATTLES = 300
MIN_PLAYERS = 10
MAX_PLAYERS = 16
NUM_WORKERS = os.cpu_count()  # battles run in parallel across this many processes


def loguniform(rng, lo, hi):
    """Sample uniformly in log-space, so each order of magnitude is equally likely."""
    return math.exp(rng.uniform(math.log(lo), math.log(hi)))


def sample_config(rng):
    """Draw one random MCMC config with max_depth * num_sims == BUDGET."""
    # Pick max_depth first (log-uniform: shallow and deep get equal weight),
    # then derive num_sims so the product hits the budget.
    max_depth = round(loguniform(rng, 3, 400))
    num_sims = max(1, round(BUDGET / max_depth))
    # Snap max_depth so the product is exactly BUDGET (keeps the budget honest
    # rather than drifting with the rounding above).
    max_depth = max(1, round(BUDGET / num_sims))
    return dict(
        num_sims=num_sims,
        max_depth=max_depth,
        W_WIN=round(loguniform(rng, 0.01, 10.0), 2),
        W_LOSS=round(loguniform(rng, 0.1, 200.0), 2),
        K=round(rng.uniform(0.0, 3.0), 3),
        # W_PLAYERS: reward (or, if negative, discourage) a change in the number
        # of players alive over a rollout.
        W_PLAYERS=round(loguniform(rng, 0.01, 20.0), 3),
        # W_FREE: weight on the free (reachable) cell fraction.
        W_FREE=round(loguniform(rng, 0.01, 20.0), 3),
    )


def fmt_config(c):
    return (
        f"sims={c['num_sims']:>5} depth={c['max_depth']:>4} "
        f"W_WIN={c['W_WIN']:>5.2f} W_LOSS={c['W_LOSS']:>5.2f} K={c['K']:>5.3f} "
        f"W_PLAYERS={c['W_PLAYERS']:>5.3f} W_FREE={c['W_FREE']:>5.3f}"
    )


# --- parallel battle workers -------------------------------------------------
# Each worker process holds the config pool in a module global so we only ship
# small (idxs, seed) tasks over the pipe rather than the full configs per battle.
_WORKER_POOL = None


def _init_worker(pool):
    global _WORKER_POOL
    _WORKER_POOL = pool


def _run_one(task):
    """Run a single battle in a worker; returns (idxs, seed, local_winner)."""
    idxs, seed = task
    configs = [_WORKER_POOL[i] for i in idxs]
    local_winner = run_battle(configs, seed=seed)
    return idxs, local_winner


def optimize(seed=0):
    rng = random.Random(seed)

    pool = [sample_config(rng) for _ in range(POOL_SIZE)]
    wins = [0] * POOL_SIZE
    draws = [0] * POOL_SIZE       # battles this config was in that ended in a draw
    games = [0] * POOL_SIZE       # battles this config participated in
    opps = [0] * POOL_SIZE        # total opponents this config has faced

    print(f"=== MCMC random search: {POOL_SIZE} configs, {NUM_BATTLES} battles ===")
    print(f"budget (depth*sims) = {BUDGET}, players/battle = "
          f"{MIN_PLAYERS}..{MAX_PLAYERS}, workers = {NUM_WORKERS}\n")
    for i, c in enumerate(pool):
        print(f"  config {i:>2}: {fmt_config(c)}")
    print()

    # Pre-roll every battle's matchup and seed up front so the parallel runs are
    # deterministic w.r.t. `seed` regardless of completion order. Matchups are
    # balanced by *opponents seen* (not battle count): each battle is filled with
    # the configs that have faced the fewest opponents so far, random tiebreak so
    # the pairings still vary. A config in an n-player battle gains n-1 opponents.
    planned_opps = [0] * POOL_SIZE
    tasks = []
    for _ in range(NUM_BATTLES):
        n = rng.randint(MIN_PLAYERS, MAX_PLAYERS)
        order = sorted(range(POOL_SIZE), key=lambda i: (planned_opps[i], rng.random()))
        idxs = order[:n]
        for i in idxs:
            planned_opps[i] += n - 1
        rng.shuffle(idxs)  # don't bias the local winner index by exposure rank
        tasks.append((idxs, rng.randrange(1, 2**32)))

    t0 = time.time()
    done = 0
    with mp.Pool(NUM_WORKERS, initializer=_init_worker, initargs=(pool,)) as mpool:
        # imap_unordered streams results back as battles finish, keeping all
        # cores busy and the leaderboard live.
        for idxs, local_winner in mpool.imap_unordered(_run_one, tasks):
            done += 1
            n = len(idxs)
            for i in idxs:
                games[i] += 1
                opps[i] += n - 1
            if local_winner == -1:
                for i in idxs:
                    draws[i] += 1
                winner_global = -1
            else:
                winner_global = idxs[local_winner]
                wins[winner_global] += 1

            elapsed = time.time() - t0
            rate = done / elapsed
            # Live leaderboard: best config so far by win rate (>=1 game played).
            played = [i for i in range(POOL_SIZE) if games[i] > 0]
            best = max(played, key=lambda i: wins[i] / games[i])
            wr = wins[best] / games[best]
            win_str = "draw" if winner_global == -1 else f"cfg {winner_global:>2}"
            print(
                f"battle {done:>4}/{NUM_BATTLES} | n={n:>2} | winner {win_str} | "
                f"best cfg {best:>2} wr={wr:6.1%} ({wins[best]}/{games[best]}) | "
                f"{rate:4.1f} battles/s"
            )

    print("\n=== top 10 configs (by win rate, min 1 game) ===")
    ranked = sorted(
        (i for i in range(POOL_SIZE) if games[i] > 0),
        key=lambda i: wins[i] / games[i],
        reverse=True,
    )
    for rank, i in enumerate(ranked[:10]):
        wr = wins[i] / games[i]
        print(
            f"#{rank + 1:>2} cfg {i:>2} | wr={wr:6.1%} "
            f"({wins[i]}/{games[i]}, {draws[i]} draws, {opps[i]} opps) | {fmt_config(pool[i])}"
        )
        print(f"     {pool[i]}")

    best = ranked[0]
    print(f"\nBEST CONFIG (cfg {best}, "
          f"wr={wins[best] / games[best]:.1%}):\n  {pool[best]}")
    return pool[best]


if __name__ == "__main__":
    optimize()
