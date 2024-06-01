from Controller import Controller
from Game import Game
import numpy as np
import cv2
import pickle

def simulate_world(weights, draw=False):
    controllers = [Controller() for _ in range(len(weights))]
    game = Game(len(controllers)*2, len(controllers)*2)
    for i, controller in enumerate(controllers):
        controller.init(game, i, weights[i], 8)
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
        #weights = (0.8030745481505493, 0.33864959471144396, 0.49828087898209317, 0.08939906100425099, -0.14830573064071664, 1.2507451665305211)
        weights = (0.4762431752651239, 0.9055161105264022, -0.7790163023537177, 0.522438868292459, -0.26277688152484524, 0.9017825611815647, 0.030507334178462464, -1.0529234714299636, 0.23872935382502838, 1.6878815613543514, 1.6357643986302224, 1.0209395650811672, -1.7993930940113951, -1.1304898591387582, -1.0317896095293004, 1.4263219990299327, -1.8249232499565315, -0.9961391131193531, 0.0867351187101912, 0.2057769231865904, 0.7710262560608895, 1.3748488735030038, 1.590362007817909, 1.1962761637055197, -0.09179165408429617, 0.9033307404458015, 2.381289231089082, -1.9044965405353678, 1.1831341261804804, -1.497214715068207, 0.5630384187979826, -0.9887517924306016, -0.6545665595052572, -1.1996019178468207, 0.16965089859359572, 1.2616354373758032, -1.1923367522589352, -0.27629366506613334, 0.3465633158268876, -1.3518363743251522, -1.3871800734413244, -0.22399470833085217, 1.2755993095731153, 0.12540698066023206, -0.16194092236160262, 0.07297099305704652, -1.5357152013555493, 0.08004671878517487, 0.8229493399216417, -1.1700554051219045, -0.5812319635060124, 0.16337121045368358, -2.1686197242326486, -0.35101707782220526, -0.8252730262144278, -0.8591981714394626, 0.021115610231300517, -0.13325581317373728, 1.1264078488300104, 0.7040315872173712, 0.311835863043621, -1.4008664904896597, -0.5054775922973638, 0.8817712937399499)

        weights =np.array(weights) +  np.random.randn() * 0.01
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