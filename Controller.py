import numpy as np

class Controller:
    def __init__(self):
        pass
    def init(self, game, player_id):
        self.game = game
        self.player_id = player_id
        self.game.update_pos(player_id, player_id * 2, player_id * 2)
        self.game.update_board()

    def move(self):
        x,y = self.game.players[self.player_id]
        w,h = self.game.width, self.game.height
        possible_moves = []

        for move in [((x+1)%w,y), ((x-1+w)%w,y), (x,(y+1)%h), (x,(y-1+h)%h)]:
            if self.game.board[move] == -1:
                possible_moves.append(move)
        if len(possible_moves) == 0:
            return ((x+1)%w,y)
        elif len(possible_moves) == 1:
            return possible_moves[0]
        else:
            move_scores = self.get_move_scores(possible_moves)
            #there might be moves that score equally, so we take a random one of those
            max_score = np.max(move_scores)
            best_moves = [possible_moves[i] for i in range(len(possible_moves)) if move_scores[i] == max_score]
            return best_moves[np.random.randint(0, len(best_moves))]

    def get_move_scores(self, possible_moves):
        """
        :param possible_moves:
        a list of at least 2 possible moves, represented as the x,y coordinates of the respective move
        :return:
        a list of scores for each move
        """
        score_01 = self.score_01(possible_moves)
        score_02 = self.score_02(possible_moves)
        print(f"score_01: {score_01}")
        print(f"score_02: {score_02}")
        sum_scores = score_01 + score_02
        print(f"sum_scores: {sum_scores}")
        return sum_scores

    def score_01(self,possible_moves):
        """
        This score function returns the number of empty fields around a move.
        :param possible_moves:
        :return:
        """
        scores = []
        for move in possible_moves:
            x, y = move
            # how many empty fields are around this move?
            empty_fields = 0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    if dx != 0 and dy != 0:
                        continue #dont count diagonals
                    if self.game.board[(x + dx) % self.game.width, (y + dy) % self.game.height] == -1:
                        empty_fields += 1
            scores.append(empty_fields)
        return np.array(scores) / 3.0

    def score_02(self, possible_moves):
        """
        This score function returns for each move the distance to the nearest player, using the Manhattan distance.
        Considering the wrap-around property of the torus.
        :param possible_moves:
        :return:
        """
        scores = []
        for move in possible_moves:
            x, y = move
            distances = []
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
            score = 1 / (1 + min_distance)  # Inverse transformation, higher distance is less significant
            scores.append(score)

        return np.array(scores)

    def score_03(self, possible_moves):
        """
        This score function does flood fill to determine the size of the area reachable after each move.
        for this pur