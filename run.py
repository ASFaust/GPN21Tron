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
        self.username = "Snek"
        self.password = "yousorandomxd"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print("connected.")
        #self.weights = (-0.030564719524807514, 1.0051631219522386, 0.39656536679234267, 0.6173943302186865, 0.15642170918508655, 0.9554791832045848)
        #self.weights = (0.8030745481505493, 0.33864959471144396, 0.49828087898209317, 0.08939906100425099, -0.14830573064071664, 1.2507451665305211)
        #self.weights = (-0.0270007979079513, 0.828252131131214, 0.5039031305967274, 0.16356345117206306, 0.15951748736838017, 0.8628544581024385)
        #self.weights = (0.4164104402724594, -1.598031090424554, 1.1369466382029623, 0.5755494295759612, 1.8202950397758597, 0.24797226230673527, 1.1689749764522475, 0.008797048841106202, 1.3975230969583319, 2.4932034181433993, -0.726365215769179, 0.9490725296440652, -1.097085982870446, 1.3352498579707341, -1.2564884986581775, -1.8460994658312992, 1.5601898238481937, 1.7244503664884265, -0.8461168282293606, 1.6394751337477707, 0.733636364061387, 0.29760812815104315, 0.5206680499345095, 1.6366222221847677, 0.22349988171880195, -0.7261340420529078, 0.0430319165307107, -0.5317302156882985, 1.6597463731379694, 1.5970932750353148, -0.567256080495172, -0.1190953679366266)
        #unrefined, 20 enemies, 90% rank extraction
        #self.weights = (1.2696243840377026, 0.6055145706204373, 1.0130858122691004, 1.559375689535413, -0.15367459899353111, 1.7450012265645825, -0.5612036217116675, 0.08467699944517816, 1.0089978415136458, 0.16188627525591673, 0.670236322287019, -1.1432665890881466, -1.4129363170741809, 0.032107318516881624, 1.1184858285117358, -0.25005527577490505, -1.6487081934934582, 2.2161050087872085, 0.23463881089735003, 1.3674315898817735, -0.2348790614453209, 1.0733707443673381, -0.11374000537577508, -0.6799906038686019, 1.934875659848384, -0.5340623583043264, -0.14275173563758442, 0.2029481352230752, -1.2889712964283326, 2.9051844069920034, 0.57137782269059, -0.3336242663822117)
        #unrefined, 20 enemies, 40% WR extraction
        #self.weights = (0.025131421289588837, -2.0252085207992936, 0.47412635727652436, 1.3244271288771734, 0.3288951131338792, 0.06407660380548652, 0.46890898521812313, 0.8377293462631007, -0.4294024896398693, -0.804529001748123, 1.7522699464987865, -1.6137352338504278, 1.070335960843388, 0.5838230589471456, -0.03661359523710329, -1.135834102667944, 3.133728710069223, 0.11431927265380575, -0.28299533368452334, -0.16654628346454106, -1.165402878231832, 0.40386632488309593, 1.1979528237365593, -0.32045924175408047, 0.7951672114651036, -0.7992719965335287, -0.7954771481003965, 0.7327545368512258, 0.4659730134627029, 0.0862441332447461, 0.091097848803046, -0.20169545516865234)
        #refined, 20 enemies, 60% rank extraction (better enemies -> lower overall rank) AND refined, 20 enemies, 16% WR extraction
        self.weights = (-0.3431393401969582, -0.5889034691504542, -1.1369519236959587, -0.17927299786102405, 1.5528979312165567, -1.245398925665014, -0.11318421449768448, -0.01562874158943733, 2.096946990019249, -1.0288594850505104, -0.575128381914481, 2.837423929812102, -0.7111604224503522, 0.5307302096718722, 1.3768648193695092, -1.4620377979658359, -0.4201316351735732, -1.1960817213412278, -1.164943224451217, -0.2119668484733715, 0.9325578081319053, 1.1990175879447198, -0.26003366956819424, 0.1969109351500523, -0.032542660488523764, 0.4254293388801167, -0.2763772506851758, 0.122430025604848, 1.760091700385811, 0.3541240772493791, -0.5623299049160346, -0.7931294911453518)
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
                self.send("chat|my 4 hidden neurons are just too powerful")
                self.dead = True

tp = Tron()
tp.run()
