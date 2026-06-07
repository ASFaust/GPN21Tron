import socket
import select
import codecs
import time
import random
import numpy as np
import threading
import queue

import TronBoard
from chat_messages import i_died_msg, other_player_died_msg, i_won_msg

class Tron:
    def __init__(self):
        self.username = "Mr. Markov v6" 
        self.password = "2v2"
        #self.host = '2a0e:c5c1:0:100:4ef2:71ed:4d70:40fd'
        self.port = 4000
        #self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.host = 'tron.erik.gdn'
        #self.host = '151.216.211.107'
        # How long recv() may block before we treat the connection as dead and
        # reconnect. Generous enough to span the gap between games (where the
        # server is quiet) without false-positiving.
        self.recv_timeout = 30.0
        self.sock = None
        self._decoder = None
        self._connect()
        self.board = None
        self.player_id = None
        self.dead = False
        self.player_names = {}
        # NB: the incremental UTF-8 decoder (so a multi-byte char split across
        # two recv() chunks can't crash us) is created in _connect().
        # State verification: last (x, y) we saw per player, used to compare the
        # state the server reports against what we expect each tick.
        self.messages = queue.Queue()  # for testing: store messages received from the server
        self.num_players = None
        # MCMC hyperparameters, passed straight through to get_player_move.
        # This one is really good:
        #        best: sims=   80 depth= 375 W_WIN= 52.03 W_LOSS=-65.11 K= 0.604 W_PLAYERS= 84.166 W_FREE= 33.887
        # Experimental ones:
        #         best: sims=  280 depth= 107 W_WIN= 83.42 W_LOSS=-30.75 K= 0.018 W_PLAYERS= 27.069 W_FREE= 91.789
        self.mcmc_params = dict(
            num_sims=2000,
            max_depth=400,
            W_WIN=83.42,
            W_LOSS=-30.75,
            K=0.018,
            W_PLAYERS=27.069,
            W_FREE=91.789,
        )
        threading.Thread(
            target=self._receiver_loop,
            daemon=True
        ).start()

    def _connect(self):
        """(Re)establish the TCP connection, retrying until it succeeds.

        Also (re)creates the incremental UTF-8 decoder so a half-decoded
        multi-byte char from a dead connection can't corrupt the new stream.
        """
        # Close any previous socket so we don't leak the dead one.
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        backoff = 1.0
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                # Disable Nagle: our messages are tiny (move|up\n) and strictly
                # request/response, so Nagle + the server's delayed-ACK would
                # otherwise stall each send by tens of ms -- the real cause of
                # "lost" moves.
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # Detect a silently-dead connection (wifi drop / NAT timeout)
                # instead of blocking in recv() forever.
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # Bound recv() so a dead connection surfaces as a timeout.
                sock.settimeout(self.recv_timeout)
                self.sock = sock
                self._decoder = codecs.getincrementaldecoder('utf-8')()
                print("connected.")
                return
            except OSError as e:
                print(f"connect failed ({e}); retrying in {backoff:.0f}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    def _receiver_loop(self):
        print("started receiver thread.")
        buffer = ""

        while True:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                print("connection timed out; reconnecting...")
                chunk = b""
            except OSError as e:
                print(f"connection error ({e}); reconnecting...")
                chunk = b""

            if not chunk:
                # Empty chunk == server closed the connection (or we forced it
                # above on timeout/error). Drain stale messages from the dead
                # connection, tell the main loop to reset to "wait for next
                # game", then reconnect and re-join.
                self._drain_messages()
                self.messages.put(["disconnected"])
                self._connect()
                self.join()
                buffer = ""
                continue

            buffer += self._decoder.decode(chunk)

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                self.messages.put(line.split("|"))

    def _drain_messages(self):
        """Discard any messages still queued from a now-dead connection."""
        try:
            while True:
                self.messages.get_nowait()
        except queue.Empty:
            pass

    def join(self):
        print(f"joining as {self.username}...")
        self.send(f"join|{self.username}|{self.password}")

    def send(self, msg):
        # The connection may be down (the receiver thread reconnects in the
        # background). Don't crash the main loop on a transient send failure --
        # the "disconnected" sentinel will drive us back to init_board anyway.
        try:
            self.sock.sendall((msg + "\n").encode('utf-8'))
        except OSError as e:
            print(f"send failed ({e}); connection likely down.")

    def chat(self, msg):
        self.send(f"chat|{msg}")

    def someone_died(self, msg):
        player_ids = msg[1:]
        for player_id in player_ids:
            player_id = int(player_id)
            self.board.remove_player(player_id)
            player_name = self.player_names.get(player_id, f"Player {player_id}")
            self.chat(other_player_died_msg(player_name))

    def move(self):
        start_time = time.time()
        move = self.board.get_player_move(**self.mcmc_params)
        compute = time.time() - start_time
        print(f"move computed in {compute} seconds.")
        if move == "rip":
            print("no possible moves, i'm dead :(")
            self.chat(i_died_msg())
            self.send("move|up")
            return            

        self.send(f"move|{move}")  # send final move command

    def init_board(self):
        print("waiting for next game start...")
        self.board = None
        self.player_id = None
        self.num_players = None
        game_dim = None
        positions_x = []
        positions_y = []
        self.player_names = {}
        n_players = 0
        game_message_received = False
        #then we wait for the rest of the init messages until the first tick
        while self.board is None:
            msg = self.messages.get() #blocking wait for the next message
            if msg[0] == "disconnected":
                # Reconnected mid-init: discard the partially-collected game
                # state and start waiting for the (new) game from scratch.
                print("reconnected while waiting; resetting game state.")
                game_dim = None
                positions_x = []
                positions_y = []
                self.player_names = {}
                game_message_received = False
                continue
            if msg[0] == "game":
                print("game start message received.")
                game_dim = (int(msg[1]), int(msg[2]))
                self.player_id = int(msg[3]) # our own player id
                game_message_received = True
            if not game_message_received:
                continue 
            if msg[0] == "player":
                player_id = int(msg[1])
                player_name = msg[2]
                self.player_names[player_id] = player_name
            if msg[0] == "pos":
                player_id = int(msg[1])
                x = int(msg[2])
                y = int(msg[3])
                positions_x.append(x)
                positions_y.append(y)
            if msg[0] == "tick": #the trigger to create the board
                #we assert that we have all the info
                assert game_dim is not None, "game_dim is None"
                #the number of player messages is the authoritative player count;
                #width//2 is only a server-side guarantee we cross-check against.
                n_players = len(self.player_names)
                assert n_players == game_dim[0] // 2, f"expected width//2={game_dim[0] // 2} players but got {n_players}"
                assert len(positions_x) == n_players, f"expected {n_players} position messages but got {len(positions_x)}"
                assert len(positions_y) == n_players, f"expected {n_players} position messages but got {len(positions_y)}"
                assert set(self.player_names.keys()) == set(range(n_players)), f"expected player ids to be contiguous and start at 0, but got {list(self.player_names.keys())}"
                positions_x = np.array(positions_x, dtype=np.uint32)
                positions_y = np.array(positions_y, dtype=np.uint32)
                self.board = TronBoard.Board(width=game_dim[0], num_players=n_players,
                                                player_id=self.player_id, xs=positions_x, ys=positions_y)
                #send a down move after the first tick.
                self.send(f"move|down")
                break
        self.dead = False
        print(f"board initialized: {game_dim[0]}x{game_dim[1]}, players: {list(self.player_names.values())}")
        self.num_players = n_players

    def update_board(self, position_updates):
        #we need two numpy arrays, of shape (num_players,)
        #one for x and one for y, to call the board update function
        #we only have partial position updates, but that's okay: everybody else is dead
        xs = np.zeros(self.num_players, dtype=np.uint32)
        ys = np.zeros(self.num_players, dtype=np.uint32)
        for player_id, (x, y) in position_updates.items():
            if player_id >= self.num_players:
                #ignore stray updates for players beyond our known roster
                continue
            xs[player_id] = x
            ys[player_id] = y
        self.board.update_positions(xs, ys)

    def run(self):
        last_tick = time.time()
        self.join()
        self.init_board() 
        position_updates = {}
        while True:
            if self.dead:
                self.init_board() #wait for the next game to start
                continue
            msg = self.messages.get() #blocking wait for the next message            print(msg)
            if msg[0] == "disconnected":
                # Connection dropped (timeout or server close). The receiver
                # thread has already reconnected and re-joined; go back to
                # waiting for the next game to start.
                print("connection dropped; waiting for next game...")
                self.init_board()
                position_updates = {}
                continue
            if msg[0] == "die":
                self.someone_died(msg)
            if msg[0] == "tick":
                self.update_board(position_updates)
                now = time.time()
                interval = now - last_tick
                print(f"tick took {interval} seconds.")
                last_tick = now
                self.move()
            if msg[0] == "lose":
                print("i lost.")
                self.dead = True
            if msg[0] == "win":
                print("i WON :D")
                self.chat(i_won_msg())
                self.dead = True # to trigger the wait again for the next game start
            if msg[0] == "error":
                print(msg)
            if msg[0] == "pos":
                player_id = int(msg[1])
                x = int(msg[2])
                y = int(msg[3])
                position_updates[player_id] = (x, y)
                #we wait for the tick message to update the board, to make sure we have all the position updates for this tick before we update the board state.

if __name__ == "__main__":
    tp = Tron()
    tp.run()
