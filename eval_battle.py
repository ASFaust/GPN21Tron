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


def run_battle_ranked(configs, seed=None, max_ticks=None, verbose=False):
    """Play one game; return a death-tick per config index (placement signal).

    death_tick[q] is the tick at which player q died; survivors get the final
    tick. Higher == survived longer == placed better. Equal ticks == tied
    placement. This is the input to the ELO/placement scoring in the optimizer.
    """
    n = len(configs)
    if n < 2:
        raise ValueError("need at least 2 configs to battle")

    width = 2 * n
    if max_ticks is None:
        max_ticks = width * width

    rng = random.Random(seed)

    xs = np.array([2 * q for q in range(n)], dtype=np.uint32)
    ys = np.array([2 * q for q in range(n)], dtype=np.uint32)
    board = TronBoard.Board(width=width, num_players=n, player_id=0, xs=xs, ys=ys)

    death_tick = [None] * n

    first = [rng.randrange(4) for _ in range(n)]
    board.step_dirs(first)
    tick = 1
    for q in range(n):
        if death_tick[q] is None and not board.is_alive(q):
            death_tick[q] = tick

    while board.count_alive() > 1 and tick < max_ticks:
        dirs = []
        for q in range(n):
            if board.is_alive(q):
                dirs.append(board.get_move(q, seed=rng.randrange(1, 2**32), **configs[q]))
            else:
                dirs.append(-1)
        board.step_dirs(dirs)
        tick += 1
        for q in range(n):
            if death_tick[q] is None and not board.is_alive(q):
                death_tick[q] = tick

    # Survivors (and anyone still flagged alive at the cap) never died, so they
    # placed strictly above everyone who did -- including players who died on the
    # final, game-ending tick. tick+1 keeps multiple cap-survivors tied with each
    # other but above all deaths.
    for q in range(n):
        if death_tick[q] is None:
            death_tick[q] = tick + 1

    if verbose:
        print(f"[battle] finished after {tick} ticks, death_ticks={death_tick}")
    return death_tick


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
        dict(num_sims=300, max_depth=60, W_WIN=10.0, W_LOSS=10.0, K=0.0, W_PLAYERS=0.0, W_FREE=1.0),
        dict(num_sims=50, max_depth=20, W_WIN=10.0, W_LOSS=10.0, K=0.0, W_PLAYERS=0.0, W_FREE=1.0),
        dict(num_sims=200, max_depth=50, W_WIN=10.0, W_LOSS=10.0, K=1.0, W_PLAYERS=0.0, W_FREE=1.0),
    ]
    tally = battle_series(demo_configs, games=10, base_seed=0)
    print("win tally (index -> wins, -1 == draw):", tally)
