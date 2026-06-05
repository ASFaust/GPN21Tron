"""Visualize an MCMC self-play battle with cv2.

Standalone viewer built on eval_battle's game loop: it plays one game between a
set of MCMC configs and renders the board state each tick using the new
Board.get_trail_grid / get_head_grid / get_alive readouts.

The default config is the tuned one from Tron.py's leaderboard:

    # 1 cfg 42 | wr= 34.6% | sims= 319 depth= 47 W_WIN= 0.11 W_LOSS=28.05 K=-0.985
    {'num_sims': 319, 'max_depth': 47, 'W_WIN': 0.11, 'W_LOSS': 28.05, 'K': -0.985}

Controls (while the cv2 window is focused):
    space / right : step one tick
    p             : toggle auto-play
    r             : restart with a new random seed
    q / esc       : quit

Usage:
    python visualize_battle.py                 # 2 copies of the default config
    python visualize_battle.py --players 4     # 4 copies
    python visualize_battle.py --cell 32 --fps 8 --auto
"""

#{'num_sims': 142, 'max_depth': 211, 'W_WIN': 0.01, 'W_LOSS': 0.55, 'K': 0.122, 'DIR_PERSIST': 0.011}
import argparse
import random

import cv2
import numpy as np

import TronBoard


# The tuned config from the Tron.py leaderboard (cfg 42).
#DEFAULT_CONFIG = dict(num_sims=319, max_depth=47, W_WIN=0.11, W_LOSS=28.05, K=-0.985)
DEFAULT_CONFIG = dict(num_sims=1000, max_depth=300, W_WIN=0.0, W_LOSS=0.0, K=0.0, DIR_PERSIST=2.0)

# Distinct BGR colors per player (cv2 uses BGR order).
PLAYER_COLORS = [
    (60, 60, 255),    # red
    (255, 200, 0),    # cyan-blue
    (60, 220, 60),    # green
    (0, 200, 255),    # amber
    (255, 80, 220),   # magenta
    (200, 255, 60),   # teal
    (40, 140, 255),   # orange
    (255, 120, 120),  # periwinkle
]
EMPTY_COLOR = (24, 24, 24)
GRID_COLOR = (40, 40, 40)


def _color(q):
    return PLAYER_COLORS[q % len(PLAYER_COLORS)]


def _dim(bgr, factor=0.55):
    return tuple(int(c * factor) for c in bgr)


class BattleViz:
    def __init__(self, configs, cell=24, seed=None):
        self.configs = configs
        self.n = len(configs)
        self.cell = cell
        self.reset(seed)

    def reset(self, seed=None):
        self.seed = random.randrange(2**32) if seed is None else seed
        self.rng = random.Random(self.seed)
        self.width = 2 * self.n

        xs = np.array([2 * q for q in range(self.n)], dtype=np.uint32)
        ys = np.array([2 * q for q in range(self.n)], dtype=np.uint32)
        self.board = TronBoard.Board(
            width=self.width, num_players=self.n, player_id=0, xs=xs, ys=ys
        )

        # Every player commits to a random first move (all four free at start).
        first = [self.rng.randrange(4) for _ in range(self.n)]
        self.board.step_dirs(first)
        self.tick = 1
        self.finished = False
        self.result = None

    def step(self):
        if self.finished:
            return
        if self.board.count_alive() <= 1:
            self._finish()
            return

        dirs = []
        for q in range(self.n):
            if self.board.is_alive(q):
                d = self.board.get_move(
                    q, seed=self.rng.randrange(1, 2**32), **self.configs[q]
                )
            else:
                d = -1
            dirs.append(d)
        self.board.step_dirs(dirs)
        self.tick += 1

        if self.board.count_alive() <= 1:
            self._finish()

    def _finish(self):
        self.finished = True
        self.result = self.board.winner()

    def render(self):
        w = self.width
        cell = self.cell
        trail = np.array(self.board.get_trail_grid()).reshape(w, w)
        head = np.array(self.board.get_head_grid()).reshape(w, w)

        img = np.full((w * cell, w * cell, 3), EMPTY_COLOR, dtype=np.uint8)
        for gy in range(w):
            for gx in range(w):
                t = trail[gy, gx]
                h = head[gy, gx]
                if h >= 0:
                    color = _color(h)
                elif t >= 0:
                    color = _dim(_color(t))
                else:
                    continue
                y0, x0 = gy * cell, gx * cell
                img[y0:y0 + cell, x0:x0 + cell] = color
                if h >= 0:
                    # outline the head cell so it pops above its trail
                    cv2.rectangle(
                        img, (x0, y0), (x0 + cell - 1, y0 + cell - 1),
                        (255, 255, 255), max(1, cell // 12)
                    )

        # grid lines
        for i in range(w + 1):
            p = i * cell
            cv2.line(img, (p, 0), (p, w * cell), GRID_COLOR, 1)
            cv2.line(img, (0, p), (w * cell, p), GRID_COLOR, 1)

        return self._with_hud(img)

    def _with_hud(self, board_img):
        hud_h = 24 + 18 * self.n
        # Keep the canvas wide enough that the HUD text never clips on small
        # boards (a 2-player board is only ~4 cells wide).
        canvas_w = max(board_img.shape[1], 280)
        x_off = (canvas_w - board_img.shape[1]) // 2
        canvas = np.full(
            (board_img.shape[0] + hud_h, canvas_w, 3), 16, dtype=np.uint8
        )
        canvas[hud_h:, x_off:x_off + board_img.shape[1]] = board_img

        alive = self.board.get_alive()
        status = f"seed={self.seed}  tick={self.tick}  alive={self.board.count_alive()}"
        if self.finished:
            status += f"  WINNER={self.result if self.result >= 0 else 'DRAW'}"
        cv2.putText(canvas, status, (6, 16), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (230, 230, 230), 1, cv2.LINE_AA)

        for q in range(self.n):
            y = 24 + 18 * q + 12
            sw = (255, 255, 255) if (q < len(alive) and alive[q]) else (90, 90, 90)
            cv2.rectangle(canvas, (8, y - 10), (22, y + 2), _color(q), -1)
            cfg = self.configs[q]
            label = (f"P{q} sims={cfg['num_sims']} d={cfg['max_depth']} "
                     f"K={cfg['K']}" + ("" if alive[q] else "  [dead]"))
            cv2.putText(canvas, label, (30, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, sw, 1, cv2.LINE_AA)
        return canvas


def main():
    ap = argparse.ArgumentParser(description="Visualize an MCMC Tron battle.")
    ap.add_argument("--players", type=int, default=16,
                    help="number of players, all using the default config")
    ap.add_argument("--cell", type=int, default=24, help="pixel size per board cell")
    ap.add_argument("--fps", type=float, default=6.0, help="auto-play ticks per second")
    ap.add_argument("--auto", action="store_true", help="start in auto-play mode")
    ap.add_argument("--seed", type=int, default=None, help="initial game seed")
    args = ap.parse_args()

    configs = [dict(DEFAULT_CONFIG) for _ in range(args.players)]
    viz = BattleViz(configs, cell=args.cell, seed=args.seed)

    import time

    win = "Tron MCMC battle"
    cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)
    auto = args.auto
    interval = 1.0 / args.fps  # seconds between auto-play ticks
    dirty = True               # only re-render when state changed
    next_tick = time.monotonic() + interval

    try:
        while True:
            if dirty:
                cv2.imshow(win, viz.render())
                dirty = False

            # Always poll on a short interval (never waitKey(0)): a blocking
            # wait swallows SIGINT, so Ctrl-C wouldn't work until a key/event.
            key = cv2.waitKey(20) & 0xFF

            # Window closed via the X button: getWindowProperty drops below 1.
            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                break

            if key in (ord("q"), 27):
                break
            elif key in (ord(" "), 83):  # space / right arrow: single step
                viz.step()
                dirty = True
            elif key == ord("p"):
                auto = not auto
                next_tick = time.monotonic() + interval
            elif key == ord("r"):
                viz.reset(None)
                auto = args.auto
                dirty = True

            # Auto-advance on the wall-clock schedule.
            if auto and not viz.finished and time.monotonic() >= next_tick:
                viz.step()
                dirty = True
                next_tick += interval
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        # destroyAllWindows is lazy on some backends; pump the event loop so
        # the window actually goes away and the process can exit cleanly.
        for _ in range(4):
            cv2.waitKey(1)


if __name__ == "__main__":
    main()
