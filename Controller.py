import numpy as np
import cv2
from TronAlgos import flood_fill, distances

class Controller:
    def __init__(self):
        pass
    def init(self, game, player_id, weights, n_neurons):
        self.game = game
        self.player_id = player_id
        self.game.update_pos(player_id, player_id * 2, player_id * 2)
        self.game.update_board()
        self.weights = np.array(weights)
        self.n_neurons = n_neurons
        self.delta_2 = [(x,y) for x in range(-2,3) for y in range(-2,3) if abs(x) + abs(y) == 2]
        self.delta_3 = [(x,y) for x in range(-3,4) for y in range(-3,4) if abs(x) + abs(y) == 3]
        self.delta_4 = [(x,y) for x in range(-4,5) for y in range(-4,5) if abs(x) + abs(y) == 4]

    def move(self,as_string=False):
        x,y = self.game.players[self.player_id]
        w,h = self.game.width, self.game.height
        possible_moves = []
        moves = [(((x+1)%w,y),"right"), (((x-1+w)%w,y),"left"), ((x,(y-1+h)%h),"up"), ((x,(y+1)%h),"down")]
        for move in moves:
            if self.game.board[move[0]] == -1:
                possible_moves.append(move)
        if len(possible_moves) == 0:
            ret = moves[0]
        elif len(possible_moves) == 1:
            ret = possible_moves[0]
        else:
            move_scores = self.get_move_scores(possible_moves)
            max_score = np.max(move_scores)
            best_moves = [possible_moves[i] for i in range(len(possible_moves)) if move_scores[i] == max_score]
            ret = best_moves[np.random.randint(0, len(best_moves))]
            #ret = best_moves[0]
        if as_string:
            return ret[1]
        else:
            return ret[0]

    def get_move_scores(self, possible_moves):
        """
        :param possible_moves:
        a list of at least 2 possible moves, represented as the x,y coordinates of the respective move
        :return:
        a list of scores for each move
        """
        score_01 = self.score_count_empty(possible_moves,[[-1,0],[1,0],[0,-1],[0,1]]) * 4/3 #4/3 is the maximum score possible
        score_02 = self.score_contested(possible_moves)
        score_03 = self.score_count_empty(possible_moves,self.delta_2)
        score_04 = self.score_count_empty(possible_moves,self.delta_3)
        score_05 = self.score_count_empty(possible_moves,self.delta_4)
        score_06 = self.score_flood_fill(possible_moves)
        score_07 = self.score_best_distance(possible_moves)
        score_08,score_09 = self.score_enemy_distance(possible_moves)
        score_10 = self.score_dilated_flood_fill(possible_moves)
        sum_scores = np.array([score_01,score_02,score_03,score_04,score_05,score_06,score_07,score_08,score_09,score_10]).T
        final_scores = []
        for i in range(sum_scores.shape[0]):
            scores = sum_scores[i] #scores is a 6-element array
            w1 = self.weights[0:10*self.n_neurons].reshape(10,self.n_neurons)
            b1 = self.weights[10*self.n_neurons:11*self.n_neurons]
            h1 = np.dot(scores,w1) + b1
            h1 = np.sin(h1)
            w2 = self.weights[12*self.n_neurons:13*self.n_neurons]
            h2 = np.dot(h1,w2)
            final_scores.append(h2)

        return np.array(final_scores).flatten()

    def score_count_empty(self,possible_moves,deltas):
        """
        This score function returns the number of empty fields around a move.
        :param possible_moves:
        :param deltas:
        :return:
        """
        scores = []
        for move in possible_moves:
            x, y = move[0]
            # how many empty fields are around this move?
            empty_fields = 0
            for dx,dy in deltas:
                if self.game.board[(x + dx) % self.game.width, (y + dy) % self.game.height] == -1:
                    empty_fields += 1
            scores.append(empty_fields)
        return np.array(scores) / len(deltas)

    def score_contested(self, possible_moves):
        """
        This score function returns for each move wether an enemy player can move onto the same move
        :param possible_moves:
        :return:
        """
        scores = []
        for move in possible_moves:
            x, y = move[0]
            for player_id, (player_x, player_y) in self.game.players.items():
                if player_id == self.player_id:
                    continue
                # Calculate the Manhattan distance on a torus
                dx = min(abs(x - player_x), self.game.width - abs(x - player_x))
                dy = min(abs(y - player_y), self.game.height - abs(y - player_y))
                distance = dx + dy
                if distance == 1:
                    scores.append(0)
                    break
            else:
                scores.append(1)
        return np.array(scores)

    def score_flood_fill(self, possible_moves):
        """
        This score function returns for each move the size of the area that can be reached by flood fill.
        :param possible_moves:
        :return:
        """
        scores = []
        for move in possible_moves:
            x, y = move[0]
            board = self.game.board.copy()
            scores.append(flood_fill(board, x, y))
        scores = np.array(scores)
        return scores / max(scores.max(),1)

    def score_dilated_flood_fill(self, possible_moves):
        #dilate the walls by 1 field. be careful with the starting position, don't fill it.
        scores = []
        for move in possible_moves:
            x, y = move[0]
            board = self.game.board.copy()
            board[board != -1] = 1
            board[board == -1] = 0
            board = cv2.dilate(board.astype(np.uint8), np.ones((3,3),np.uint8), iterations=1)
            board[x,y] = 0
            board[board == 0] = -1
            board = board.astype(np.int32)
            scores.append(flood_fill(board, x, y))
        scores = np.array(scores)
        return scores / max(scores.max(),1)

    def score_best_distance(self, possible_moves):
        scores = []
        const_far_away = 1000000
        for move in possible_moves:
            x, y = move[0]
            board = self.game.board.copy()
            dists = distances(board, x, y)
            dists[dists == -1] = const_far_away
            for player_id, (player_x, player_y) in self.game.players.items():
                if player_id == self.player_id:
                    continue
                player_dists = distances(board, player_x, player_y) - 1 #-1 because we already did a move.
                player_dists[player_dists == -2] = const_far_away
                dists[player_dists < dists] = const_far_away
            scores.append(len(dists[dists != const_far_away]))
        scores = np.array(scores)
        return scores / max(scores.max(),1)

    def score_enemy_distance(self, possible_moves):
        scores = []
        const_far_away = 1000000

        for move in possible_moves:
            x, y = move[0]
            board = self.game.board.copy()
            dists = distances(board, x, y)
            dists[dists == -1] = const_far_away
            min_dist = const_far_away
            for player_id, (player_x, player_y) in self.game.players.items():
                if player_id == self.player_id:
                    continue
                dist = dists[player_x, player_y]
                if dist < min_dist:
                    min_dist = dist
            if min_dist == const_far_away:
                scores.append(1.0)
            else:
                scores.append(1.0 - 1.0 / min_dist)
        scores = np.array(scores)
        return scores, scores / max(scores.max(),1)

    def best_distance_move(self,possible_moves):
        scores = []
        const_far_away = 1000000
        for move in possible_moves:
            x, y = move[0]
            board = self.game.board.copy()
            dists = distances(board, x, y)
            dists[dists == -1] = const_far_away
            for player_id, (player_x, player_y) in self.game.players.items():
                if player_id == self.player_id:
                    continue
                player_dists = distances(board, player_x, player_y) - 1 #-1 because we already did a move.
                player_dists[player_dists == -2] = const_far_away
                dists[player_dists < dists] = const_far_away
            scores.append(len(dists[dists != const_far_away]))
        scores = np.array(scores)
        return scores / max(scores.max(),1)