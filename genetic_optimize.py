"""Win-rate Gaussian-EDA optimizer over MCMC hyperparameters.

Fitness in self-play is *relative*, so each individual keeps a single,
persistent win rate. A game of N players is scored from death order (survive
longer == place better): a participant's per-game score is the fraction of
opponents it outlasts (ties count as half), i.e. the fraction of the implicit
pairwise duels it wins. These per-game scores accumulate across every
re-evaluation, so an individual's win rate keeps refining rather than starting
from scratch.

Search proceeds as an Estimation-of-Distribution Algorithm (EDA): the PARENTS
best-rated individuals (by win rate over the whole persistent archive) are
re-entered into the population each generation and a multivariate Gaussian is
fitted to their genes. The remaining POP_SIZE - PARENTS slots are fresh samples
from that Gaussian. There is no crossover/mutation -- the Gaussian *is* the
variation operator.

Everything ever evaluated is stored in a persistent JSON archive (ARCHIVE_PATH)
that accumulates across runs; per-generation YAML snapshots go to OUTPUT_DIR.

Genome = the kwargs Board.get_move accepts (see PARAMS). max_depth * num_sims is
held at BUDGET so every config gets the same compute per move.

Run: /home/andreas/venv/bin/python genetic_optimize.py
"""

import json
import multiprocessing as mp
import os
import random
import time

import numpy as np
import yaml

from eval_battle import run_battle_ranked

# --- search space ------------------------------------------------------------
BUDGET = 100000  # max_depth * num_sims, held constant across all configs

# Each gene: (low, high). The EDA fits/samples in this raw, linear space and
# clamps to [low, high]. max_depth is the compute knob; num_sims is derived.
PARAMS = {
    "max_depth":   (10.0,    500.0),
    "W_WIN":       (-100.0, 100.0),
    "W_LOSS":      (-100.0, 100.0),
    "K":           (-5.0,   5.0),
    "W_PLAYERS":   (-100.0, 100.0),
    "W_FREE":      (-100.0, 100.0),
}

PARAM_NAMES = list(PARAMS.keys())

# --- EDA / population knobs --------------------------------------------------
POP_SIZE = 200            # individuals alive each generation
PARENTS = 20              # best-by-win-rate re-entered + used to fit the Gaussian
GENERATIONS = 25
EDA_RIDGE = 1e-6          # covariance regularization (fraction of range^2)
EDA_VAR_FLOOR = 0.02      # per-gene stdev floor as a fraction of its range
EDA_COV_SCALE = 1.0       # inflate/deflate the sampling covariance

# --- win-rate knobs ----------------------------------------------------------
# Win rate = accumulated per-game placement score / games played. An individual
# needs at least this many games before it is eligible to be selected as a
# parent, so a lucky 1/1 run can't dominate the Gaussian fit.
MIN_GAMES_FOR_PARENT = 30

# Per-game score blends two estimators (see score_from_battle):
#   score = (1 - SCORE_LAMBDA) * borda_fraction + SCORE_LAMBDA * 1[sole winner]
# SCORE_LAMBDA = 0 -> dense placement (Borda, estimates P(beat a random opp));
# SCORE_LAMBDA = 1 -> sparse last-win rate (the true objective, P(finish 1st)).
# Intermediate values trade density for fidelity to sole-survivorship.
SCORE_LAMBDA = 0.0

# --- evaluation knobs --------------------------------------------------------
BATTLES_PER_GEN = 300
MIN_PLAYERS = 16
MAX_PLAYERS = 16
NUM_WORKERS = os.cpu_count()

# --- persistence / reporting -------------------------------------------------
ARCHIVE_PATH = "ga_archive.json"  # persistent, accumulates across runs
OUTPUT_DIR = "ga_reports"          # one snapshot YAML per generation


# --- genome helpers ----------------------------------------------------------
def random_genes(rng):
    return {n: rng.uniform(lo, hi) for n, (lo, hi) in PARAMS.items()}


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
        W_PLAYERS=round(genes["W_PLAYERS"], 3),
        W_FREE=round(genes["W_FREE"], 3),
    )


def fmt_config(c):
    return (
        f"sims={c['num_sims']:>5} depth={c['max_depth']:>4} "
        f"W_WIN={c['W_WIN']:>6.2f} W_LOSS={c['W_LOSS']:>6.2f} K={c['K']:>6.3f} "
        f"W_PLAYERS={c['W_PLAYERS']:>7.3f} W_FREE={c['W_FREE']:>7.3f}"
    )


# --- Gaussian EDA ------------------------------------------------------------
def _genes_to_vec(genes):
    return np.array([genes[n] for n in PARAM_NAMES], dtype=float)


def _vec_to_genes(vec):
    return {n: float(vec[i]) for i, n in enumerate(PARAM_NAMES)}


def fit_gaussian(parent_genes):
    """Fit (mean, cov) to the parent genes, with ridge + per-gene variance floor."""
    X = np.array([_genes_to_vec(g) for g in parent_genes], dtype=float)
    mean = X.mean(axis=0)
    cov = np.cov(X, rowvar=False)
    cov = np.atleast_2d(cov)

    ranges = np.array([hi - lo for (lo, hi) in PARAMS.values()], dtype=float)
    # Regularize and enforce a variance floor so the search can't collapse.
    cov += np.diag((EDA_RIDGE * ranges**2))
    floor = (EDA_VAR_FLOOR * ranges) ** 2
    diag = np.maximum(np.diag(cov), floor)
    np.fill_diagonal(cov, diag)
    return mean, cov * EDA_COV_SCALE


def eda_sample(parent_genes, n, np_rng):
    mean, cov = fit_gaussian(parent_genes)
    raw = np_rng.multivariate_normal(mean, cov, size=n, check_valid="ignore")
    return [_vec_to_genes(v) for v in raw], mean, cov


# --- persistent archive ------------------------------------------------------
def load_archive(path):
    if not os.path.exists(path):
        return {"next_id": 0, "individuals": {}}
    with open(path) as f:
        archive = json.load(f)
    # Migration: older archives stored a single "win_score" that was always the
    # pure Borda sum (lambda was implicitly 0). That total is exactly the
    # lambda-independent borda_score we now store, so the data is preserved
    # losslessly and stays recomputable for any lambda.
    for rec in archive.get("individuals", {}).values():
        if "borda_score" not in rec:
            rec["borda_score"] = rec.pop("win_score", 0.0)
    return archive


def save_archive(path, archive):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(archive, f)
    os.replace(tmp, path)  # atomic, so a crash mid-write can't corrupt the archive


def new_individual(archive, genes, born_gen):
    iid = str(archive["next_id"])
    archive["next_id"] += 1
    archive["individuals"][iid] = {
        "id": iid,
        "genes": genes,
        "borda_score": 0.0,  # accumulated Borda fraction (lambda-independent)
        "games": 0,
        "wins": 0,           # accumulated sole-survivor count (lambda-independent)
        "born_gen": born_gen,
    }
    return iid


def win_rate(rec):
    """Mean per-game score under the current SCORE_LAMBDA blend; 0 if unplayed.

    Recomputed from the stored sufficient statistics (borda_score and wins), so
    changing SCORE_LAMBDA re-scores the whole archive without replaying games.
    """
    if not rec["games"]:
        return 0.0
    blended = (1.0 - SCORE_LAMBDA) * rec["borda_score"] + SCORE_LAMBDA * rec["wins"]
    return blended / rec["games"]


# --- win-rate scoring --------------------------------------------------------
def score_from_battle(records, ids, death_ticks):
    """Apply one battle's placement result to the participants' win rate.

    Per-game score is a convex blend of two estimators (see SCORE_LAMBDA):
      borda  = fraction of opponents outlasted (ties count as half), a dense
               estimate of P(beat a random opponent);
      sole   = 1 if this participant is the unique last survivor, else 0, the
               true sole-survivorship objective but a sparse signal.
      score  = (1 - SCORE_LAMBDA) * borda + SCORE_LAMBDA * sole
    SCORE_LAMBDA = 0 reproduces the pure-placement scoring. Scores accumulate
    into win_score / games.

    records: id -> individual dict (mutated in place).
    ids:     participant ids, aligned with death_ticks.
    """
    m = len(ids)
    best = max(death_ticks)
    sole_winner = death_ticks.count(best) == 1
    for a in range(m):
        outlasted = 0.0
        for b in range(m):
            if a == b:
                continue
            if death_ticks[a] > death_ticks[b]:
                outlasted += 1.0
            elif death_ticks[a] == death_ticks[b]:
                outlasted += 0.5
        borda = outlasted / (m - 1)
        sole = 1.0 if (sole_winner and death_ticks[a] == best) else 0.0
        rec = records[ids[a]]
        # Accumulate the two estimators separately so win_rate can be recomputed
        # for any SCORE_LAMBDA later (borda_score and wins are the sufficient
        # statistics; the blend is applied only at read time in win_rate).
        rec["borda_score"] += borda
        rec["games"] += 1
        if sole == 1.0:
            rec["wins"] += 1


# --- parallel battle workers -------------------------------------------------
_WORKER_POOL = None


def _init_worker(pool):
    global _WORKER_POOL
    _WORKER_POOL = pool


def _run_one(task):
    bid, local_idxs, seed = task
    configs = [_WORKER_POOL[i] for i in local_idxs]
    return bid, local_idxs, run_battle_ranked(configs, seed=seed)


# --- evaluation --------------------------------------------------------------
def evaluate(pop_ids, records, rng, gen):
    """Run a round of battles among the population and update win rate in place.

    Battles are pre-rolled deterministically and balanced so every individual
    plays a comparable number of games. Scores are applied in battle-id order
    (not completion order) so a run is reproducible from its seed.
    """
    P = len(pop_ids)
    pop_configs = [_finish(records[i]["genes"]) for i in pop_ids]  # local index space

    seen = [0] * P
    tasks = []
    for bid in range(BATTLES_PER_GEN):
        n = rng.randint(MIN_PLAYERS, min(MAX_PLAYERS, P))
        order = sorted(range(P), key=lambda i: (seen[i], rng.random()))
        local_idxs = order[:n]
        for i in local_idxs:
            seen[i] += 1
        rng.shuffle(local_idxs)
        tasks.append((bid, local_idxs, rng.randrange(1, 2**32)))

    t0 = time.time()
    results = [None] * BATTLES_PER_GEN
    done = 0
    with mp.Pool(NUM_WORKERS, initializer=_init_worker, initargs=(pop_configs,)) as mpool:
        for bid, local_idxs, death_ticks in mpool.imap_unordered(_run_one, tasks):
            results[bid] = (local_idxs, death_ticks)
            done += 1
            rate = done / (time.time() - t0)
            print(
                f"  gen {gen:>2} battle {done:>4}/{BATTLES_PER_GEN} | "
                f"n={len(local_idxs):>2} | {rate:5.1f} battles/s",
                end="\r",
            )
    print()

    # Apply scores deterministically in battle order.
    for local_idxs, death_ticks in results:
        ids = [pop_ids[i] for i in local_idxs]
        score_from_battle(records, ids, death_ticks)


# --- reporting ---------------------------------------------------------------
def write_gen_report(out_dir, gen, pop_ids, parent_ids, records, mean, cov, dt):
    records_by_wr = sorted(pop_ids, key=lambda i: win_rate(records[i]), reverse=True)
    parent_set = set(parent_ids)
    individuals = [
        {
            "rank": rank,
            "id": i,
            "is_parent": i in parent_set,
            "win_rate": round(win_rate(records[i]), 4),
            "games": records[i]["games"],
            "wins": records[i]["wins"],
            "config": _finish(records[i]["genes"]),
        }
        for rank, i in enumerate(records_by_wr)
    ]
    eda = None
    if mean is not None:
        eda = {
            "mean": {n: round(float(mean[k]), 4) for k, n in enumerate(PARAM_NAMES)},
            "stdev": {n: round(float(np.sqrt(cov[k, k])), 4)
                      for k, n in enumerate(PARAM_NAMES)},
        }
    best = records_by_wr[0]
    report = {
        "generation": gen,
        "generations_total": GENERATIONS,
        "seconds": round(dt, 2),
        "params": {
            "budget": BUDGET,
            "pop_size": POP_SIZE,
            "parents": PARENTS,
            "battles_per_gen": BATTLES_PER_GEN,
            "players_per_battle": [MIN_PLAYERS, MAX_PLAYERS],
            "min_games_for_parent": MIN_GAMES_FOR_PARENT,
        },
        "summary": {
            "best_id": best,
            "best_win_rate": round(win_rate(records[best]), 4),
            "best_config": _finish(records[best]["genes"]),
            "mean_win_rate": round(
                sum(win_rate(records[i]) for i in pop_ids) / len(pop_ids), 4),
        },
        "eda": eda,
        "population": individuals,
    }
    path = os.path.join(out_dir, f"gen_{gen:02d}.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(report, f, sort_keys=False, default_flow_style=False)
    return path


# --- main loop ---------------------------------------------------------------
def optimize(seed=0, out_dir=OUTPUT_DIR, archive_path=ARCHIVE_PATH):
    rng = random.Random(seed)
    np_rng = np.random.RandomState(seed)

    out_dir = os.path.join(out_dir, time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)

    archive = load_archive(archive_path)
    records = archive["individuals"]

    print(f"=== win-rate/EDA MCMC search: pop={POP_SIZE}, parents={PARENTS}, "
          f"gens={GENERATIONS} ===")
    print(f"budget(depth*sims)={BUDGET}, battles/gen={BATTLES_PER_GEN}, "
          f"players/battle={MIN_PLAYERS}..{MAX_PLAYERS}, workers={NUM_WORKERS}")
    print(f"archive -> {os.path.abspath(archive_path)} "
          f"({len(records)} individuals so far)")
    print(f"reports -> {os.path.abspath(out_dir)}\n")

    for gen in range(GENERATIONS):
        t0 = time.time()

        # Parents: the best win-rate individuals across the whole archive that
        # have played enough games to have a trustworthy rate.
        eligible = [r for r in records.values()
                    if r["games"] >= MIN_GAMES_FOR_PARENT]
        ranked_archive = sorted(eligible, key=win_rate, reverse=True)
        parent_recs = ranked_archive[:PARENTS]
        parent_ids = [r["id"] for r in parent_recs]

        # Sample the rest of the population from the Gaussian fitted to parents.
        n_new = POP_SIZE - len(parent_ids)
        mean = cov = None
        if len(parent_recs) >= 2:
            new_genes, mean, cov = eda_sample(
                [r["genes"] for r in parent_recs], n_new, np_rng)
        else:
            new_genes = [random_genes(rng) for _ in range(n_new)]

        new_ids = [new_individual(archive, g, gen) for g in new_genes]
        pop_ids = parent_ids + new_ids

        evaluate(pop_ids, records, rng, gen)

        dt = time.time() - t0
        ranked = sorted(pop_ids, key=lambda i: win_rate(records[i]), reverse=True)
        best = ranked[0]
        mean_wr = sum(win_rate(records[i]) for i in pop_ids) / len(pop_ids)
        print(f"gen {gen:>2}/{GENERATIONS} | best WR={win_rate(records[best]):6.3f} "
              f"({records[best]['wins']} solo wins / {records[best]['games']} games) | "
              f"mean WR={mean_wr:6.3f} | archive={len(records)} | {dt:4.1f}s")
        print(f"        best: {fmt_config(_finish(records[best]['genes']))}")

        report_path = write_gen_report(
            out_dir, gen, pop_ids, parent_ids, records, mean, cov, dt)
        save_archive(archive_path, archive)
        print(f"        report: {report_path}\n")

    print("\n=== top 10 by win rate (whole archive) ===")
    final = sorted(records.values(), key=win_rate, reverse=True)[:10]
    for rank, r in enumerate(final):
        cfg = _finish(r["genes"])
        print(f"#{rank + 1:>2} WR={win_rate(r):6.3f} "
              f"({r['wins']}/{r['games']}) | {fmt_config(cfg)}")
    best_cfg = _finish(final[0]["genes"])
    print(f"\nBEST CONFIG (WR={win_rate(final[0]):.3f}):\n  {best_cfg}")
    return best_cfg


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--lambda", dest="score_lambda", type=float, default=SCORE_LAMBDA,
        metavar="L",
        help="score blend in [0,1]: 0 = dense placement/Borda (default), "
             "1 = sparse sole-survivor win rate. See SCORE_LAMBDA.")
    parser.add_argument("--seed", type=int, default=0,
                        help="RNG seed (default: 0)")
    args = parser.parse_args()

    if not 0.0 <= args.score_lambda <= 1.0:
        parser.error("--lambda must be in [0, 1]")

    SCORE_LAMBDA = args.score_lambda
    print(f"score blend: SCORE_LAMBDA={SCORE_LAMBDA}")
    optimize(seed=args.seed)
