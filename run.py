import socket
import numpy as np
from TronGamer import TronListener, TronAI
import time

class Tron:
    def __init__(self):
        self.host = 'gpn-tron.duckdns.org'
        self.port = 4000
        self.username = "Tracer 0.1"  # scarab hieroglyph #"\U000131BD"  # Egyptian hieroglyph A52 (bird)
        self.password = "yousorandomxd"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print("connected.")
        self.AI = TronAI(0.07,1000) #max_time (seconds), max_steps :O
        self.listener = None

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
        width = int(msg[1])
        height = int(msg[2])
        self.player_id = int(msg[3])
        self.listener = TronListener(width, height, self.player_id)
        self.AI.set_listener(self.listener)

    def update_pos(self, msg):
        player_id = int(msg[1])
        x = int(msg[2])
        y = int(msg[3])
        self.listener.update_pos(player_id, x, y)

    def someone_died(self, msg):
        player_ids = msg[1:]
        for player_id in player_ids:
            player_id = int(player_id)
            self.listener.remove_player(player_id)

    def move(self):
        start_time = time.time()
        the_move = self.AI.get_move()
        end_time = time.time()
        print(f"moving took {end_time - start_time} seconds.")
        self.send(f"move|{the_move}")  # send final move command

    def run(self):
        last_tick = time.time()
        tp.join()
        print("joined.")
        for msg in self.recv():
            print(msg)
            if msg[0] == "game":
                self.set_game(msg)
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
                print(f"tick took {next_tick - last_tick} seconds.")
                last_tick = next_tick
                self.move()
            if msg[0] == "lose":
                print("i lost.")
                self.listener.death()
            if msg[0] == "win":
                print("i WON :D")
            if msg[0] == "error":
                print(msg)


tp = Tron()
tp.run()
