import numpy as np
import matplotlib.pyplot as plt
import random
import cv2

class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.board = np.ones((self.width, self.height)).astype(np.int32) * -1
        self.players = {}
        self._color_init = False
        self.dists = None

    def update_pos(self, player_id, x, y):
        self.players[player_id] = (x, y)

    def update_board(self):
        #gets done after the players have moved and the board is updated according to dead players
        for player_id, (x, y) in self.players.items():
            self.board[x, y] = player_id

    def check_dead(self):
        dead_players = []
        for player_id, (x, y) in self.players.items():
            if self.board[x, y] != -1:
                dead_players.append(player_id) #moved onto a wall
            for other_player_id, (other_x, other_y) in self.players.items():
                if player_id != other_player_id and x == other_x and y == other_y:
                    dead_players.append(player_id)
                    dead_players.append(other_player_id)
        #remove duplicates
        dead_players = list(set(dead_players))
        #then remove them from the players dict
        for player_id in dead_players:
            del self.players[player_id]
        #and their traces from the board
        for player_id in dead_players:
            self.board[self.board == player_id] = -1
        return dead_players

    def _init_colors(self):
        self.colors = []
        while len(self.colors) < len(self.players):
            candidate_color = np.random.randint(0, 255, 3)
            if  np.linalg.norm(candidate_color) > 20 and \
                not any(np.linalg.norm(candidate_color - color) < 10 for color in self.colors):
                    self.colors.append(candidate_color)
        self.colors = np.array(self.colors)

    def draw(self):
        """draw onto a numpy canvas with cv2"""
        #up to 25 colors:
        if not self._color_init:
            self._init_colors()
            self._color_init = True
        canvas = np.zeros((self.width, self.height, 3)).astype(np.uint8)
        #just draw the board, not the players' heads
        canvas[self.board == -1] = 0
        canvas[self.board != -1] = self.colors[self.board[self.board != -1]]
        #resize to 800x800, with clearly visible pixels
        canvas = cv2.resize(canvas, (800, 800), interpolation=cv2.INTER_NEAREST)
        canvas = np.swapaxes(canvas, 0, 1)
        return canvas

    def copy(self):
        new_game = Game(self.width, self.height)
        new_game.board = self.board.copy()
        new_game.players = self.players.copy()
        return new_game