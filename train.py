from Controller import Controller
from Game import Game
import numpy as np
import cv2

def simulate_world(controllers,draw=False):
    game = Game(len(controllers)*2, len(controllers)*2)
    for i,controller in enumerate(controllers):
        controller.init(game,i)
    fitness_counter = np.zeros(len(controllers))

    while len(game.players) > 1:
        if draw:
            cv2.imshow("game", game.draw())
            cv2.waitKey(500)

        for i,controller in enumerate(controllers):
            if not i in game.players:
                continue
            x,y = controller.move()
            game.update_pos(i, x, y)
        game.check_dead()
        game.update_board()
        for player in game.players.keys():
            fitness_counter[player] += 1
    return fitness_counter #returns the number of steps each player survived

if __name__ == "__main__":
    controllers = [Controller() for _ in range(20)]
    fitnesses = simulate_world(controllers,draw=True)
    print(fitnesses)
