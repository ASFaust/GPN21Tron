import numpy as np
from TronAlgos import flood_fill, distances

class Controller:
    def __init__(self):
        pass
    def init(self, game, player_id, weights):
        self.game = game
        self.player_id = player_id
        self.game.update_pos(player_id, player_id * 2, player_id * 2)
        self.game.update_board()
        self.weights = np.array(weights)

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
        score_02 = self.score_dist_enemy(possible_moves)
        score_03 = self.score_count_empty(possible_moves,[(x,y) for x in range(-2,3) for y in range(-2,3) if abs(x) + abs(y) == 2])
        score_04 = self.score_count_empty(possible_moves,[(x,y) for x in range(-3,4) for y in range(-3,4) if abs(x) + abs(y) == 3])
        score_05 = self.score_flood_fill(possible_moves)
        score_06 = self.score_best_distance(possible_moves)
        sum_scores = np.array([score_01,score_02,score_03,score_04,score_05,score_06]).T
        final_scores = []
        for i in range(sum_scores.shape[0]):
            scores = sum_scores[i] #scores is a 6-element array
            w1 = self.weights[0:24].reshape(6,4)
            b1 = self.weights[24:28]
            h1 = np.dot(scores,w1) + b1
            h1[h1<0] = 0
            w2 = self.weights[28:32]
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

    def score_dist_enemy(self, possible_moves):
        """
        This score function returns for each move the distance to the nearest player, using the Manhattan distance.
        Considering the wrap-around property of the torus.
        :param possible_moves:
        :return:
        """
        scores = []
        for move in possible_moves:
            x, y = move[0]
            distances = [100]
            for player_id, (player_x, player_y) in self.game.players.items():
                if player_id == self.player_id:
                    continue
                # Calculate the Manhattan distance on a torus
                dx = min(abs(x - player_x), self.game.width - abs(x - player_x))
                dy = min(abs(y - player_y), self.game.height - abs(y - player_y))
                distance = dx + dy
                distances.append(distance)

            # Use the minimum distance for the score
            min_distance = np.min(distances)
            # Transform the distance to be between 0 and 1
            # Using a logarithmic transformation with a base +1 to handle distances of 0
            if min_distance < 1:
                raise ValueError("Distance should be at least 1")
            score = 1.0 - 1 / min_distance  # Inverse transformation, higher distance is less significant
            scores.append(score)

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
