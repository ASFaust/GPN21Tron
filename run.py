import socket
import numpy as np
import time
from Game import Game
from Controller import Controller
import cv2

class Tron:
    def __init__(self):
        self.host = 'gpn-tron.duckdns.org'
        self.port = 4000
        self.username = "Chocolate Starfish"
        self.password = "yousorandomxd"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print("connected.")
        #self.weights = (-0.030564719524807514, 1.0051631219522386, 0.39656536679234267, 0.6173943302186865, 0.15642170918508655, 0.9554791832045848)
        #self.weights = (0.8030745481505493, 0.33864959471144396, 0.49828087898209317, 0.08939906100425099, -0.14830573064071664, 1.2507451665305211)
        self.weights = (-0.0270007979079513, 0.828252131131214, 0.5039031305967274, 0.16356345117206306, 0.15951748736838017, 0.8628544581024385)
        self.weights = np.array(self.weights)
        self.dead = True

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
        self.game = Game(width,height)
        self.controller = Controller()
        self.controller.init(self.game,self.player_id,self.weights)
        self.dead = False

    def update_pos(self, msg):
        player_id = int(msg[1])
        x = int(msg[2])
        y = int(msg[3])
        self.game.update_pos(player_id,x,y)

    def someone_died(self, msg):
        self.send("chat|womp womp")
        #we need to remove the player from the game
        player_ids = msg[1:]
        print("someone died. removing their trace.")
        for player_id in player_ids:
            self.game.board[self.game.board == int(player_id)] = -1
            del self.game.players[int(player_id)]

    def move(self):
        start_time = time.time()
        move = self.controller.move(as_string=True)
        end_time = time.time()
        #print(f"moving took {end_time - start_time} seconds.")
        self.send(f"move|{move}")  # send final move command

    def run(self):
        last_tick = time.time()
        tp.join()
        print("joined.")
        for msg in self.recv():
            if msg[0] == "error":
                print(msg)
            if msg[0] == "game":
                self.set_game(msg)
            if self.dead:
                #print("self is dead")
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
                self.game.update_board()
                img = self.game.draw()
                cv2.imshow("game", img)
                cv2.waitKey(1)
                self.move()
            if msg[0] == "lose":
                print("i lost.")
                self.dead = True
            if msg[0] == "win":
                print("i WON :D")
                self.dead = True

tp = Tron()
tp.run()
