from Controller import Controller
from Game import Game
import numpy as np
import cv2
import pickle

def simulate_world(weights, draw=False):
    controllers = [Controller() for _ in range(len(weights))]
    game = Game(len(controllers)*2, len(controllers)*2)
    for i, controller in enumerate(controllers):
        controller.init(game, i, weights[i])
    fitness_counter = np.zeros(len(controllers))

    while len(game.players) > 1:
        if draw:
            cv2.imshow("game", game.draw())
            cv2.waitKey(100)
        new_positions = []
        for i, controller in enumerate(controllers):
            if not i in game.players:
                continue
            x, y = controller.move()
            new_positions.append((i, x, y))

        for i, x, y in new_positions:  # needs to be separate loop to avoid
            # changing the board while iterating over it
            game.update_pos(i, x, y)
        game.check_dead()
        game.update_board()
        for player in game.players.keys():
            fitness_counter[player] += 1
    return fitness_counter  # returns the number of steps each player survived

if __name__ == "__main__":
    n_individuals = 25
    n_weights = 6
    #min_opponents = 24
    #max_opponents = 25
    n_evals_per_individual = 20
    individual_map = {}

    for i in range(n_individuals):
        weights = (0.8030745481505493, 0.33864959471144396, 0.49828087898209317, 0.08939906100425099, -0.14830573064071664, 1.2507451665305211)
        weights =np.array(weights) +  np.random.rand() * 0.0001
        w_key = tuple(weights)
        individual_map[w_key] = {"fitness":[]}

    while True:
        #select a number of opponents
        n_opponents = 25
        opponents = list(individual_map.keys())

        #evaluate each individual against the opponents
        fitnesses = simulate_world(opponents,draw=True)
        #we need to transform the fitness into a rank.
        fitnesses = np.argsort(fitnesses)
        fitnesses = np.argsort(fitnesses).astype(np.float32) + 1
        fitnesses /= n_opponents
        #update the fitness of each individual
        for i,opponent in enumerate(opponents):
            individual_map[opponent]["fitness"].append(fitnesses[i])

    #then save the results
    with open("individual_map.pkl","wb") as f:
        pickle.dump(individual_map,f)