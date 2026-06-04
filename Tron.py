import socket
import select
import codecs
import numpy as np
from TronGamer import TronListener, TronAI
from chat_messages import i_died_msg, other_player_died_msg, i_won_msg
import time
import random

class Tron:
    def __init__(self):
        self.host = '151.216.211.107'
        self.port = 4000
        self.username = "Gorgel"  # scarab hieroglyph #"\U000131BD"  # Egyptian hieroglyph A52 (bird)
        self.password = "testtests"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        # Disable Nagle: our messages are tiny (move|up\n) and strictly
        # request/response, so Nagle + the server's delayed-ACK would otherwise
        # stall each send by tens of ms -- the real cause of "lost" moves.
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # Detect a silently-dead connection (wifi drop / NAT timeout) instead of
        # blocking in recv() forever.
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        print("connected.")
        self.AI = TronAI(0.07,1000) #max_time (seconds), max_steps :O
        print("c++ init done.")
        self.listener = None
        self.player_names = {}
        # Incremental decoder so a multi-byte char (emoji, hieroglyph) split
        # across two recv() chunks doesn't raise UnicodeDecodeError and crash.
        self._decoder = codecs.getincrementaldecoder('utf-8')()
        # State verification: last (x, y) we saw per player, used to compare the
        # state the server reports against what we expect each tick.
        self.last_pos = {}
        # Read-timeout handling. The idle between rounds can be several minutes,
        # so the socket only gets a timeout while a round is actively running.
        # read_timeout is adapted from the observed tick interval (see run()).
        self.in_round = False
        self.read_timeout = 2.0  # seconds, floor; refined once ticks are seen
        print("init complete.")

    def _set_active(self, active):
        """Arm a read timeout during a round, none during the idle between."""
        self.in_round = active
        self.sock.settimeout(self.read_timeout if active else None)

    def _data_pending(self):
        """True if the socket has bytes ready to read right now (non-blocking).
        Used to tell whether more ticks are already queued so we can drain the
        whole backlog and only act on the freshest one."""
        return bool(select.select([self.sock], [], [], 0)[0])

    def recv(self):
        buffer = ""
        while True:
            while "\n" in buffer:
                # split the buffer at the first newline, yielding the first part
                line, buffer = buffer.split("\n", 1)
                # `more` is True when another complete line is already buffered,
                # or the kernel has more bytes waiting -- i.e. we are behind and
                # should keep draining before reacting.
                more = ("\n" in buffer) or self._data_pending()
                yield line.split("|"), more
            # when no more newlines are in the buffer, read more data
            print(f"[recv] blocking on recv, buffer so far={buffer!r}", flush=True)
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                # Only armed mid-round, so this means the server went quiet for
                # several ticks' worth of time -- a real, actionable stall.
                print(f"WARNING: no data for >{self.sock.gettimeout()}s during "
                      f"active play -- possible network stall.")
                continue
            print(f"[recv] got {len(chunk)} bytes: {chunk!r}", flush=True)
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            buffer += self._decoder.decode(chunk)

    def join(self):
        self.send(f"join|{self.username}|{self.password}")

    def send(self, msg):
        print(msg)
        self.sock.sendall((msg + "\n").encode('utf-8'))

    def set_player_name(self, msg):
        player_id = int(msg[1])
        player_name = msg[2]
        self.player_names[player_id] = player_name

    def chat(self, msg):
        self.send(f"chat|{msg}")

    def set_game(self, msg):
        #width, height and self player id
        width = int(msg[1])
        height = int(msg[2])
        self.player_id = int(msg[3])
        self.listener = TronListener(width, height, self.player_id)
        self.AI.set_listener(self.listener)
        self.last_pos = {}  # fresh state for the new round

    def update_pos(self, msg):
        player_id = int(msg[1])
        x = int(msg[2])
        y = int(msg[3])
        # Compare reported state against expectation: each tick a player should
        # advance exactly one cell. A jump > 1 means we skipped a pos update
        # (lost messages / parser desync); standing still can mean a move that
        # never registered. Either is a signal something went wrong on the wire.
        prev = self.last_pos.get(player_id)
        if prev is not None:
            delta = abs(x - prev[0]) + abs(y - prev[1])
            if delta > 1:
                who = self.player_names.get(player_id, f"Player {player_id}")
                print(f"WARNING: {who} jumped {delta} cells "
                      f"{prev} -> {(x, y)} (skipped a pos update?)")
        self.last_pos[player_id] = (x, y)
        self.listener.update_pos(player_id, x, y)

    def someone_died(self, msg):
        player_ids = msg[1:]
        for player_id in player_ids:
            player_id = int(player_id)
            self.listener.remove_player(player_id)
            player_name = self.player_names.get(player_id, f"Player {player_id}")
            self.chat(other_player_died_msg(player_name))

    def move(self):
        start_time = time.time()
        the_move = self.AI.get_move()
        end_time = time.time()
        compute = end_time - start_time
        # The AI budget is 0.07s; if compute creeps toward that, the move risks
        # missing the server's tick deadline and looking like a "lost" move.
        if compute > 0.05:
            print(f"WARNING: move computation took {compute:.3f}s "
                  f"(close to the 0.07s budget).")
        else:
            print(f"moving took {compute:.4f} seconds.")
        self.send(f"move|{the_move}")  # send final move command

    def run(self):
        last_tick = time.time()
        tp.join()
        print("joined.")
        # A tick obliges us to send exactly one move before the server's next
        # tick deadline. But recv() can hand us several already-elapsed ticks in
        # one batch (we fell behind); the server already logged ERROR_NO_MOVE for
        # those and only the newest game state matters. So we never act on a
        # buffered tick while more data is pending -- we drain everything first,
        # then compute a single move from the freshest state.
        pending_move = False
        for msg, more in self.recv():
            print(msg)
            if msg[0] == "game":
               self.set_game(msg)
               self._set_active(True)  # arm the read timeout for the round
               pending_move = False  # fresh round, drop any stale obligation
            if msg[0] == "player":
                self.set_player_name(msg)
            if self.listener is None:
                print("listener is None")
                continue
            if self.listener.dead:
                print("listener is dead")
                continue
            # -------------------------------- handling of in-game stuff: -----------------------------
            if msg[0] == "pos":
                self.update_pos(msg)
            if msg[0] == "die":
                self.someone_died(msg)
            if msg[0] == "tick":
                next_tick = time.time()
                interval = next_tick - last_tick
                print(f"tick took {interval} seconds.")
                last_tick = next_tick
                # Refine the read timeout to a few ticks' worth of slack, so a
                # genuine mid-round stall trips it without false positives.
                self.read_timeout = max(2.0, interval * 4)
                if self.in_round:
                    self.sock.settimeout(self.read_timeout)
                pending_move = True  # owe a move; sent once the backlog drains
            # Only move when we have caught up to the latest available state.
            # If more data is already waiting, keep draining so we react to the
            # freshest tick instead of a stale one.
            if pending_move and not more:
                pending_move = False
                self.move()
            if msg[0] == "lose":
                print("i lost.")
                self.chat(i_died_msg())
                self.listener.death()
                self._set_active(False)  # back to blocking idle between rounds
            if msg[0] == "win":
                print("i WON :D")
                self.chat(i_won_msg())
                self._set_active(False)  # back to blocking idle between rounds
            if msg[0] == "error":
                print(msg)


tp = Tron()
tp.run()
