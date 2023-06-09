import socket
import numpy as np
from concepts import gen


class TronPlayer:
    def __init__(self):
        self.host = '2001:67c:20a1:232:c5bb:64f8:b45f:9c38' #'2001:67c:20a1:232:eb97:759e:8b4a:6d0e'  # 'fe80::42d2:42e7:4090:e66'#'gpn-tron.duckdns.org'
        self.port = 4000
        # U+131A3#bug
        self.username = "pineapple internet v1.2"  # scarab hieroglyph #"\U000131BD"  # Egyptian hieroglyph A52 (bird)
        self.password = "yousorandomxd"
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port, 0, 0))
        self.game = None
        self.message_count = 0
        self.fun_frequency = 312
        self.max_floodfill_search_count = 20000
        self.directions = ["left", "right", "up", "down"]
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
        self.game = np.zeros(shape=(int(msg[1]), int(msg[2])))
        self.game[:, :] = -1  # -1 indicates free
        self.id = int(msg[3])
        self.heads = {}
        print(f"set game with {msg}")

    def update_pos(self, msg):
        player_id = int(msg[1])
        x = int(msg[2])
        y = int(msg[3])
        self.heads[player_id] = np.array((x, y), dtype=np.int32)
        self.game[x, y] = player_id

    def someone_died(self, msg):
        player_ids = msg[1:]
        print("someone died. removing their trace.")
        for player_id in player_ids:
            self.game[self.game == int(player_id)] = -1
            self.heads.pop(int(player_id))

    def get_possible_directions(self, board):
        # returns possible directions given this board. so we can use
        # multiple boards to eval this in case one doesnt return any dir.
        possible_directions = []
        own_pos = self.heads[self.id]
        for direction in self.directions:
            new_pos = self.move_(own_pos, direction)
            state = board[new_pos[0], new_pos[1]]
            if state == -1:
                possible_directions.append(direction)
        return possible_directions

    def get_possible_better_directions(self, board):
        # we check the number of directions we can go in after we moved
        # dont discern between 2 and 3
        possible_directions = []
        own_pos = self.heads[self.id]
        max_free = -1
        for direction in self.directions:
            new_pos = self.move_(own_pos, direction)
            state = board[new_pos[0], new_pos[1]]
            if state == -1:
                free_count = 0
                # now we count the number of adjacent free cells.
                for delta in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                    lat = self.wrap(np.array(delta) + new_pos)
                    ls = board[lat[0], lat[1]]
                    if ls == -1:
                        if free_count < 2:  # dont discern between 2 and 3
                            free_count += 1
                if max_free < free_count:
                    possible_directions = [direction]
                    max_free = free_count
                elif max_free == free_count:
                    possible_directions.append(dir)
        return possible_directions, max_free

    def next_enemy_positions(self):
        board = self.game.copy()
        for player_id in self.heads:
            if player_id == self.id:
                continue
            for direction in self.directions:
                new_pos = self.move_(self.heads[player_id], direction)
                board[new_pos[0], new_pos[1]] = player_id
        return board

    def floodfill(self, board, from_positions, max_count, count):
        next_board = board.copy()
        next_positions = []
        for position in from_positions:
            for delta in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                lat = self.wrap(np.array(delta) + position)
                already_checked = False
                for arr in next_positions:
                    if np.array_equal(arr, lat):
                        already_checked = True
                        break
                if already_checked:
                    continue
                ls = board[lat[0], lat[1]]
                if ls == -1:
                    next_board[lat[0], lat[1]] = self.id
                    next_positions.append(lat)
                    count += 1
        if (count < max_count) and (len(next_positions) > 0):
            return self.floodfill(next_board, next_positions, max_count, count)
        else:
            return count

    def get_floodfill_directions(self, game):
        own_pos = self.heads[self.id]
        pdirs = self.get_possible_directions(game)
        max_flood_val = -1
        max_flood_dirs = []
        for direction in pdirs:
            board = game.copy()
            next_own_pos = self.move_(own_pos, direction)
            board[next_own_pos[0], next_own_pos[1]] = self.id
            flood_val = self.floodfill(board, [next_own_pos], self.max_floodfill_search_count, 0)
            if flood_val > max_flood_val:
                max_flood_val = flood_val
                max_flood_dirs = [direction]
            elif flood_val == max_flood_val:
                max_flood_dirs.append(direction)
        print(f"best flood val: {max_flood_val}")
        return max_flood_dirs, max_flood_val

    def move(self):
        dir0 = self.get_possible_directions(self.game)
        if len(dir0) == 0:
            print("it's over :<")
            self.send("move|left")  # send final move command
            return
        elif len(dir0) == 1:
            print("just one field possible")
            self.send(f"move|{dir0[0]}")
        else:
            flood_dirs_0, floodval = self.get_floodfill_directions(self.next_enemy_positions())
            if (len(flood_dirs_0) > 0) and (floodval > 1):
                self.send(f"move|{flood_dirs_0[0]}")
            else:
                print("reeval")
                flood_dirs_1,_ = self.get_floodfill_directions(self.game)
                self.send(f"move|{flood_dirs_1[0]}")

    def move_(self, pos, direction):
        pos2 = pos.copy()
        if direction == "left":
            pos2[0] -= 1
        elif direction == "right":
            pos2[0] += 1
        elif direction == "up":
            pos2[1] -= 1
        elif direction == "down":
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
        return np.array((x, y), dtype=np.int32)

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
