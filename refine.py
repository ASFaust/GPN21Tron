import pickle
import numpy as np
from multiprocessing import Pool, cpu_count
from extract_best import get_top_n_individuals
from train import simulate_world, get_opponents, evaluate_individual

with open("individual_map.pkl", "rb") as f:
    individual_map = pickle.load(f)

n_survivors = 10 # Number of top individuals to retrieve

# Get top n individuals
top_individuals, top_fitnesses = get_top_n_individuals(individual_map, n_survivors, 'mean')

for i in range(n_survivors):
    print(f"Individual {i + 1}: {top_individuals[i]} with mean fitness: {top_fitnesses[i]}")

n_children = 1000 - n_survivors  # Number of children to generate

n_evals_per_individual = 20  # Number of evaluations per individual

# Generate children
children = []

for i in range(n_children):
    parent = top_individuals[i % n_survivors]
    child = parent + np.random.randn(6) * 0.1
    children.append(child)

children.extend(top_individuals)

individual_map = {}

for i, child in enumerate(children):
    w_key = tuple(child)
    individual_map[w_key] = {"fitness": []}

n_processes = cpu_count() - 1

pool = Pool(n_processes)

n_individuals = len(individual_map)

while True:
    n_opponents = 25
    opponents_list = [get_opponents(individual_map, n_opponents) for _ in range(n_processes)]

    results = pool.map(evaluate_individual, opponents_list)

    for opponents, fitnesses in results:
        for i, opponent in enumerate(opponents):
            individual_map[opponent]["fitness"].append(fitnesses[i])

    progress = sum(len(fss["fitness"]) for fss in individual_map.values())
    print(f"Progress: {progress}/{n_evals_per_individual * n_individuals}")

    if progress >= n_evals_per_individual * n_individuals:
        break

pool.close()
pool.join()

with open("refined.pkl", "wb") as f:
    pickle.dump(individual_map, f)
