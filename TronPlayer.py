import socket
import numpy as np
from concepts import gen
from TronGame import TronGame

class TronPlayer:
    def __init__(self):
        self.host = '2001:67c:20a1:232:c5bb:64f8:b45f:9c38' #'2001:67c:20a1:232:eb97:759e:8b4a:6d0e'  # 'fe80::42d2:42e7:4090:e66'#'gpn-tron.duckdns.org'
        self.port = 4000
        self.username = "pineapple internet v1.2"  # scarab hieroglyph #"\U000131BD"  # Egyptian hieroglyph A52 (bird)
        self.password = "yousorandomxd"
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port, 0, 0))
        self.game = None
        self.message_count = 0
        self.fun_frequency = 312
        self.max_floodfill_search_count = 500
        # np.random.shuffle(self.directions)
        print("connected.")

    def recv(self):
        buffer = ""
        while True:
            while "\n" in buffer:
                # split the buffer at the first newline, yielding the first part
                line, buffer = buffer.split("\n", 1)
                # print(line)
                yield line.split("|")  # line
            # when no more newlines are in the buffer, read more data
            chunk = self.sock.recv(1024)
            if chunk == '':
                raise RuntimeError("socket connection broken")
            buffer += chunk.decode('utf-8')

    def join(self):
        self.send(f"join|{self.username}|{self.password}")

    def send(self, msg):
        print(msg)
        self.sock.sendall((msg + "\n").encode('utf-8'))

    def set_game(self, msg):
        #width, height and self player id
        self.game = TronGame(int(msg[1]), int(msg[2]), int(msg[3]))
        print(f"set game with {msg}")

    def update_pos(self, msg):
        player_id = int(msg[1])
        x = int(msg[2])
        y = int(msg[3])
        self.game.update_pos(player_id, x, y)

    def someone_died(self, msg):
        player_ids = msg[1:]
        print("someone died. removing their trace.")
        for player_id in player_ids:
            player_id = int(player_id)
            self.game.remove_player(player_id)

    def move(self):
        the_move = self.game.get_move()
        self.send(f"move|{the_move}")  # send final move command

    def run(self):
        tp.join()
        print("joined.")
        for msg in self.recv():
            self.message_count += 1
            if msg[0] == "game":
                self.set_game(msg)
            if self.game is None:
                continue
            # -------------------------------- handling of in-game stuff: -----------------------------
            if msg[0] == "pos":
                self.update_pos(msg)
            if msg[0] == "die":
                self.someone_died(msg)
            if msg[0] == "tick":
                self.move()
            if msg[0] == "lose":
                print("i lost.")
                self.game = None
            if msg[0] == "win":
                print("i WON :D")
                self.game = None
            if (self.message_count % self.fun_frequency) == 0:
                self.send_fun()
            if msg[0] == "error":
                print(msg)

    def send_fun(self):
        self.send(f"chat|{gen()}")


tp = TronPlayer()
tp.run()
