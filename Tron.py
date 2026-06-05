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
        self.host = '151.216.211.107'
        self.port = 4000
        self.username = "Mr. Markov"  # scarab hieroglyph #"\U000131BD"  # Egyptian hieroglyph A52 (bird)
        self.password = "asgoisahg"
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
        self.board = None
        self.player_id = None
        self.dead = False
        self.player_names = {}
        # Incremental decoder so a multi-byte char (emoji, hieroglyph) split
        # across two recv() chunks doesn't raise UnicodeDecodeError and crash.
        self._decoder = codecs.getincrementaldecoder('utf-8')()
        # State verification: last (x, y) we saw per player, used to compare the
        # state the server reports against what we expect each tick.
        self.messages = queue.Queue()  # for testing: store messages received from the server
        self.num_players = None
        threading.Thread(
            target=self._receiver_loop,
            daemon=True
        ).start()

    def _receiver_loop(self):
        print("started receiver thread.")
        buffer = ""

        while True:
            chunk = self.sock.recv(4096)

            if not chunk:
                print("server closed connection.")
                return

            buffer += self._decoder.decode(chunk)
            print(f"[RECV] {buffer}")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                self.messages.put(line.split("|"))

    def join(self):
        print(f"joining as {self.username}...")
        self.send(f"join|{self.username}|{self.password}")

    def send(self, msg):
        print(msg)
        self.sock.sendall((msg + "\n").encode('utf-8'))

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
        print("computing move...")
        start_time = time.time()
        move = self.board.get_player_move()
        if move == "rip":
            print("no possible moves, i'm dead :(")
            self.chat(i_died_msg())
            self.send("move|up")
        compute = time.time() - start_time
        print(f"move computed in {compute} seconds.")
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
        print("tick received, updating board state...")
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
            msg = self.messages.get() #blocking wait for the next message
            print(msg)
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
