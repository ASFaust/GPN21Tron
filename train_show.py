from Controller import Controller
from Game import Game
import numpy as np
import cv2
import pickle

def simulate_world(weights,draw=False):
    controllers = [Controller() for _ in range(len(weights))]
    game = Game(len(controllers)*2, len(controllers)*2)
    for i,controller in enumerate(controllers):
        controller.init(game,i,weights[i])
    fitness_counter = np.zeros(len(controllers))

    while len(game.players) > 1:
        if draw:
            cv2.imshow("game", game.draw())
            cv2.waitKey(1)
        new_positions = []
        for i,controller in enumerate(controllers):
            if not i in game.players:
                continue
            x,y = controller.move()
            new_positions.append((i,x,y))

        for i,x,y in new_positions: #needs to be separate loop to avoid
            # changing the board while iterating over it
            game.update_pos(i, x, y)
        game.check_dead()
        game.update_board()
        for player in game.players.keys():
            fitness_counter[player] += 1
    return fitness_counter #returns the number of steps each player survived

def get_opponents(individual_map,n_opponents):
    #get the individuals with the lowest number of evaluations
    individuals = list(individual_map.keys())
    #shuffle the individuals to avoid always selecting the same ones
    np.random.shuffle(individuals)
    individuals = sorted(individuals,key=lambda x: len(individual_map[x]["fitness"]))
    return individuals[:n_opponents]

if __name__ == "__main__":
    n_individuals = 1000
    n_weights = 6
    #min_opponents = 24
    #max_opponents = 25
    n_evals_per_individual = 20
    individual_map = {}

    for i in range(n_individuals):
        weights = np.random.randn(n_weights)
        w_key = tuple(weights)
        individual_map[w_key] = {"fitness":[]}

    while True:
        #select a number of opponents
        n_opponents = 25 #np.random.randint(min_opponents,max_opponents)

        opponents = get_opponents(individual_map,n_opponents)

        if len(individual_map[opponents[0]]["fitness"]) >= n_evals_per_individual:
            break

        #evaluate each individual against the opponents
        fitnesses = simulate_world(opponents,draw=True)
        #we need to transform the fitness into a rank.
        fitnesses = np.argsort(fitnesses)
        fitnesses = np.argsort(fitnesses).astype(np.float32) + 1
        fitnesses /= n_opponents
        #update the fitness of each individual
        for i,opponent in enumerate(opponents):
            individual_map[opponent]["fitness"].append(fitnesses[i])
        progress = 0

        for fss in individual_map.values():
            progress += len(fss["fitness"])
        print(f"Progress: {progress}/{n_evals_per_individual*n_individuals}")
    #then save the results
    with open("individual_map.pkl","wb") as f:
        pickle.dump(individual_map,f)