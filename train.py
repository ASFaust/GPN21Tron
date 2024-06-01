from Controller import Controller
from Game import Game
import numpy as np
import cv2
import pickle
from multiprocessing import Pool, cpu_count

n_neurons = 8
n_individuals = 2000
n_weights = 13 * n_neurons
n_evals_per_individual = 20
n_opponents = 20

def simulate_world(weights, draw=False):
    controllers = [Controller() for _ in range(len(weights))]
    game = Game(len(controllers)*2, len(controllers)*2)
    for i, controller in enumerate(controllers):
        controller.init(game, i, weights[i], n_neurons)
    fitness_counter = np.zeros(len(controllers))

    while len(game.players) > 1:
        if draw:
            cv2.imshow("game", game.draw())
            cv2.waitKey(1)
        new_positions = []
        for i, controller in enumerate(controllers):
            if not i in game.players:
                continue
            x, y = controller.move()
            new_positions.append((i, x, y))

        for i, x, y in new_positions:
            game.update_pos(i, x, y)
        game.check_dead()
        game.update_board()
        for player in game.players.keys():
            fitness_counter[player] += 1
    return fitness_counter

def get_opponents(individual_map, n_opponents=n_opponents):
    eligible_individuals = [ind for ind in individual_map if len(individual_map[ind]["fitness"]) < n_evals_per_individual]
    np.random.shuffle(eligible_individuals)
    if len(eligible_individuals) < n_opponents:
        eligible_individuals.extend([ind for ind in individual_map if len(individual_map[ind]["fitness"]) >= n_evals_per_individual])
    return eligible_individuals[:n_opponents]

def evaluate_individual(opponents):
    weights = [np.array(opponent) for opponent in opponents]
    fitnesses = simulate_world(weights)
    fitnesses = np.argsort(fitnesses)
    fitnesses = np.argsort(fitnesses).astype(np.float32) + 1
    fitnesses /= len(opponents)
    return opponents, fitnesses

if __name__ == "__main__":

    individual_map = {}

    for i in range(n_individuals):
        weights = np.random.randn(n_weights) * 0.5
        w_key = tuple(weights)
        individual_map[w_key] = {"fitness": []}

    pool = Pool(cpu_count())

    while any(len(fss["fitness"]) < n_evals_per_individual for fss in individual_map.values()):
        opponents_list = [get_opponents(individual_map) for _ in range(cpu_count())]

        results = pool.map(evaluate_individual, opponents_list)

        for opponents, fitnesses in results:
            for i, opponent in enumerate(opponents):
                individual_map[opponent]["fitness"].append(fitnesses[i])

        progress = sum(len(fss["fitness"]) for fss in individual_map.values())
        print(f"Progress: {progress}/{n_evals_per_individual * n_individuals}")

    pool.close()
    pool.join()

    with open("individual_map.pkl", "wb") as f:
        pickle.dump(individual_map, f)
