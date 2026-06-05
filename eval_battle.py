"""Local self-play battles between MCMC configurations.

Each entry in `configs` is a dict of MCMC hyperparameters (the kwargs accepted
by Board.get_move: num_sims, max_depth, W_WIN, W_LOSS, K). One game is played
on a torus board sized to the field: width = 2 * len(configs), with player q
starting on the diagonal at (2q, 2q) so every player has all four moves open.

Player q is controlled by configs[q]. Every player makes a random first move,
then is driven by its own MCMC config each tick until one survivor remains.

This is just the tooling -- no optimizer here. `run_battle` returns the winning
config index (or -1 for a mutual-death draw).
"""

import random

import numpy as np

import TronBoard


def run_battle(configs, seed=None, max_ticks=None, verbose=False):
    """Play one game between `configs`; return the winning index (-1 == draw).

    seed:      per-game RNG seed (random if None). Controls both the random
               first moves and the per-move rollout seeds, so a game is fully
               reproducible from this one number.
    max_ticks: hard cap on ticks before declaring a draw (defaults to a value
               large enough that the board always fills up first).
    """
    n = len(configs)
    if n < 2:
        raise ValueError("need at least 2 configs to battle")

    width = 2 * n
    if max_ticks is None:
        max_ticks = width * width  # board has width*width cells; it fills first

    rng = random.Random(seed)

    xs = np.array([2 * q for q in range(n)], dtype=np.uint32)
    ys = np.array([2 * q for q in range(n)], dtype=np.uint32)
    # player_id is irrelevant for eval; every player is driven explicitly.
    board = TronBoard.Board(width=width, num_players=n, player_id=0, xs=xs, ys=ys)

    # First move: every player commits to a random direction (all four are free
    # from the diagonal start).
    first = [rng.randrange(4) for _ in range(n)]
    board.step_dirs(first)
    if verbose:
        print(f"[battle] first moves: {first}")

    tick = 1
    while board.count_alive() > 1 and tick < max_ticks:
        dirs = []
        for q in range(n):
            if board.is_alive(q):
                d = board.get_move(q, seed=rng.randrange(1, 2**32), **configs[q])
            else:
                d = -1  # dead: ignored by step_dirs
            dirs.append(d)
        board.step_dirs(dirs)
        tick += 1
        if verbose:
            print(f"[battle] tick {tick}: alive={board.count_alive()} dirs={dirs}")

    result = board.winner()
    if verbose:
        print(f"[battle] finished after {tick} ticks, winner={result}")
    return result


def battle_series(configs, games, base_seed=0, verbose=False):
    """Play `games` battles and tally wins per config index (-1 == draws)."""
    wins = {q: 0 for q in range(len(configs))}
    wins[-1] = 0
    for g in range(games):
        w = run_battle(configs, seed=base_seed + g, verbose=verbose)
        wins[w] += 1
    return wins


if __name__ == "__main__":
    # Demo: an aggressive deep-search config vs. a shallow cheap one vs. a
    # variance-averse one.
    demo_configs = [
        dict(num_sims=300, max_depth=60, W_WIN=10.0, W_LOSS=10.0, K=0.0, DIR_PERSIST=0.0),
        dict(num_sims=50, max_depth=20, W_WIN=10.0, W_LOSS=10.0, K=0.0, DIR_PERSIST=0.0),
        dict(num_sims=200, max_depth=50, W_WIN=10.0, W_LOSS=10.0, K=1.0, DIR_PERSIST=0.0),
    ]
    tally = battle_series(demo_configs, games=10, base_seed=0)
    print("win tally (index -> wins, -1 == draw):", tally)
