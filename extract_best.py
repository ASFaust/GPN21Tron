import pickle
import numpy as np
import matplotlib.pyplot as plt

def aggregate_fitness(fitness_list, method):
    if method == 'mean':
        return sum(fitness_list) / len(fitness_list)
    elif method == 'max':
        return max(fitness_list)
    elif method == 'min':
        return min(fitness_list)
    else:
        raise ValueError("Unsupported aggregation method: choose 'mean', 'max', or 'min'")


def get_top_n_individuals(individual_map, n=1, aggregation_method='mean'):
    ind_keys = list(individual_map.keys())

    ind_agg_fitness = []
    for key in ind_keys:
        fitness = individual_map[key]["fitness"]
        aggregated_fitness = aggregate_fitness(fitness, aggregation_method)
        ind_agg_fitness.append(aggregated_fitness)

    # Get the top n individuals based on the aggregated fitness
    sorted_indices = sorted(range(len(ind_agg_fitness)), key=lambda i: ind_agg_fitness[i], reverse=True)
    top_n_indices = sorted_indices[:n]

    top_n_individuals = [ind_keys[i] for i in top_n_indices]
    top_n_fitnesses = [ind_agg_fitness[i] for i in top_n_indices]

    return top_n_individuals, top_n_fitnesses


# Load the individual map
with open("individual_map.pkl", "rb") as f:
    individual_map = pickle.load(f)

# Parameters
n = 3  # Number of top individuals to retrieve
aggregation_method = 'mean'  # Aggregation method: 'mean', 'max', or 'min'

# Get top n individuals
top_individuals, top_fitnesses = get_top_n_individuals(individual_map, n, aggregation_method)

for i in range(n):
    print(f"Individual {i + 1}: {top_individuals[i]} with {aggregation_method} fitness: {top_fitnesses[i]}")


fitness_array = []
for key in individual_map.keys():
    fitness_array.append(individual_map[key]["fitness"][:19])

fitness_array = np.array(fitness_array)

print(fitness_array)

#sort fitness array by mean fitness
mean_fitness = np.mean(fitness_array, axis=1)
sorted_indices = np.argsort(mean_fitness)[::-1]
fitness_array = fitness_array[sorted_indices]

#plot the fitness array: scatter indices vs fitness values
means = fitness_array.mean(axis=1)
std_devs = fitness_array.std(axis=1)

# Create a range for the x-axis
x = range(len(fitness_array))

# Plot the means with error bars
plt.errorbar(x, means, yerr=std_devs, fmt='o', ecolor='red', capsize=5, capthick=1, marker='o', linestyle='None')

# Display the plot
plt.xlabel('Index')
plt.ylabel('Mean Fitness')
plt.title('Mean Fitness with Standard Deviation')
plt.show()
