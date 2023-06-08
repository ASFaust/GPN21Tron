import socket
import numpy as np


class TronPlayer:
    def __init__(self):
        self.host = '2001:67c:20a1:232:eb97:759e:8b4a:6d0e'  # 'fe80::42d2:42e7:4090:e66'#'gpn-tron.duckdns.org'
        self.port = 4000
        # U+131A3#bug
        self.username = "hypersonic pickle"  # scarab hieroglyph #"\U000131BD"  # Egyptian hieroglyph A52 (bird)
        self.password = "yousorandomxd"
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port, 0, 0))
        self.game = None
        self.it = 0
        self.directions = ["left","right","up","down"]
        print("connected.")

    def recv(self):
        buffer = ""
        while True:
            while "\n" in buffer:
                # split the buffer at the first newline, yielding the first part
                line, buffer = buffer.split("\n", 1)
                print(line)
                yield line.split("|")  # line
            # when no more newlines are in the buffer, read more data
            chunk = self.sock.recv(1024)
            if chunk == '':
                raise RuntimeError("socket connection broken")
            buffer += chunk.decode('utf-8')

    def join(self):
        self.send(f"join|{self.username}|{self.password}")

    def send(self,msg):
        self.sock.sendall((msg + "\n").encode('utf-8'))

    def set_game(self, msg):
        self.game = np.zeros(shape=(int(msg[1]), int(msg[2])))
        self.game[:, :] = -1  # -1 indicates free
        self.id = int(msg[3])
        self.heads = {}
        self.it = 0
        print(f"set game with {msg}")

    def update_pos(self, msg):
        player_id = int(msg[1])
        x = int(msg[2])
        y = int(msg[3])
        self.heads[player_id] = np.array((x, y),dtype = np.int32)
        self.game[x, y] = player_id

    def someone_died(self, msg):
        player_ids = msg[1:]
        print("someone died. removing their trace.")
        for player_id in player_ids:
            self.game[self.game == int(player_id)] = -1
            self.heads.pop(int(player_id))

    def get_possible_directions(self, board):
        #returns possible directions given this board. so we can use
        #multiple boards to eval this in case one doesnt return any dir.
        possible_directions = []
        own_pos = self.heads[self.id]
        for dir in self.directions:
            new_pos = self.move_(own_pos, dir)
            state = board[new_pos[0], new_pos[1]]
            if state == -1:
                possible_directions.append(dir)
        return possible_directions

    def next_enemy_positions(self):
        board = self.game.copy()
        for player_id in self.heads:
            if player_id == self.id:
                continue
            for direction in self.directions:
                new_pos = self.move_(self.heads[player_id], direction)
                board[new_pos[0], new_pos[1]] = player_id
        return board

    def move(self):
        dir0 = self.get_possible_directions(self.game.copy())
        if len(dir0) == 0:
            print("it's over :<")
            self.send("move|left") #send final move command
            return
        elif len(dir0) == 1:
            self.send(f"move|{dir0[0]}")
        else:
            board0 = self.next_enemy_positions()
            dir1 = self.get_possible_directions(board0)
            if len(dir1) == 0:
                print("all neighbours are potentially shite.")
                self.send(f"move|{dir0[0]}")
            elif len(dir1) == 1:
                self.send(f"move|{dir1[0]}")
            else:
                self.send(f"move|{dir1[0]}")
        #self.it += 1
        #if (self.it % 5) == 0:
        #    self.directions = self.directions[1:] + self.directions[:1]

    def move_(self,pos,dir):
        pos2 = pos.copy()
        if dir == "left":
            pos2[0] -= 1
        elif dir == "right":
            pos2[0] += 1
        elif dir == "up":
            pos2[1] -= 1
        elif dir == "down":
            pos2[1] += 1
        return self.wrap(pos2)

    def wrap(self, xy):
        x = xy[0]
        y = xy[1]
        while x < 0:
            x += self.game.shape[0]
        while y < 0:
            y += self.game.shape[1]
        while x >= self.game.shape[0]:
            x -= self.game.shape[0]
        while y >= self.game.shape[1]:
            y -= self.game.shape[1]
        return np.array((x, y), dtype = np.int32)


    def run(self):
        tp.join()
        print("joined.")
        for msg in self.recv():
            if msg[0] == "game":
                self.set_game(msg)
            if self.game is None:
                continue
            #-------------------------------- handling of in-game stuff: -----------------------------
            if msg[0] == "pos":
                self.update_pos(msg)
            if msg[0] == "die":
                self.someone_died(msg)
            if msg[0] == "tick":
                self.move()
            if msg[0] == "lose":
                print("it's over.")
                self.game = None

tp = TronPlayer()
tp.run()
