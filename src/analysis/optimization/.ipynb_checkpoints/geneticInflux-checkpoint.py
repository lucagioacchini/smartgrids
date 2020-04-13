# -*- coding: utf-8 -*-
from influxdb import InfluxDBClient
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from intersection import intersection
from matplotlib import rcParams 


def getData(market):
    client = InfluxDBClient('localhost', 8086, 'root', 'root', clientID)
    # Demand
    res = client.query(f"SELECT * FROM demand{market} WHERE time = '{targetDay}'").raw
    dem =(
        pd
        .DataFrame(
            res['series'][0]['values'], 
            columns = ['time', 'P', 'Q', 'OPS']
        )
        .drop(columns=['time'])
        .set_index('OPS')
    )
    
    # Supply
    res = client.query(f"SELECT * FROM supply{market} WHERE time = '{targetDay}'").raw
    sup =(
        pd
        .DataFrame(
            res['series'][0]['values'], 
            columns = ['time', 'P', 'Q', 'OPS']
        )
        .drop(columns=['time'])
        .set_index('OPS')
    )
    
    return dem, sup


def computeClearing(bid, off):
    sup = off.sort_values('P', ascending=True)
    dem = bid.sort_values('P', ascending=False)
    # Cumulative sums of quantity
    sup_cum = np.cumsum(sup['Q'])
    dem_cum = np.cumsum(dem['Q'])
    # Find the curves intersection
    clearing = intersection(
        sup_cum.values, 
        sup.P.values, 
        dem_cum.values, 
        dem.P.values
    )[1][0]
    
    return clearing

def getFitness(dem, sup, pop):
    fitness = np.zeros((CHROMOSOMES))
    cnt = 0
    for individual in pop:
        # Determine the new curves
        sup.loc[target] = [individual[0], individual[1]]
        dem.loc[target] = [individual[2], individual[3]]
        # Set the 0 demanded price as the default one
        dem.P = dem.P.replace(0, 3000)
        # Determine the clearing price
        pun = computeClearing(dem, sup)
        
        # Compute the profits
        if sup.loc[target].P > pun:
            # Rejected bid for the supply
            Qsup = 0.0
        else:
            # Accepted bid for the supply
            Qsup = sup.loc[target].Q
        if dem.loc[target].P < pun:
            # Rejected bid for the demand
            Qdem = 0.0
        else:
            # Accepted bid for the demand
            Qdem = dem.loc[target].Q

        # Compute the profit
        profit = (Qsup - Qdem)*pun
        
        # Determine the fitness
        fitness[cnt] = profit
        cnt+=1
        
    return fitness


def crossover(parents, offspring_size):
    offspring = np.empty(offspring_size)
    # The point at which crossover takes place between two parents. Usually, it is at the center.
    crossover_point = np.uint8(offspring_size[1]/2)

    for k in range(offspring_size[0]):
        # Index of the first parent to mate.
        parent1_idx = k%parents.shape[0]
        # Index of the second parent to mate.
        parent2_idx = (k+1)%parents.shape[0]
        # The new offspring will have its first half of its genes taken from the first parent.
        offspring[k, 0:crossover_point] = parents[parent1_idx, 0:crossover_point]
        # The new offspring will have its second half of its genes taken from the second parent.
        offspring[k, crossover_point:] = parents[parent2_idx, crossover_point:]
    return offspring


def select_mating_pool(pop, fitness, num_parents):
    # Selecting the best individuals in the current generation as parents for producing the offspring of the next generation.
    parents = np.empty((num_parents, pop.shape[1]))
    for parent_num in range(num_parents):
        max_fitness_idx = np.where(fitness == np.max(fitness))
        max_fitness_idx = max_fitness_idx[0][0]
        parents[parent_num, :] = pop[max_fitness_idx, :]
        fitness[max_fitness_idx] = -99999999999
    return parents


def mutation(offspring_crossover, num_mutations):
    mutations_counter = np.uint8(offspring_crossover.shape[1] / num_mutations)
    # Mutation changes a number of genes as defined by the num_mutations argument. The changes are random.
    for idx in range(offspring_crossover.shape[0]):
        gene_idx = mutations_counter - 1
        for mutation_num in range(num_mutations):
            # The random value to be added to the gene.
            random_value = np.random.uniform(-20.0, 20.0, 1)
            offspring_crossover[idx, gene_idx] = offspring_crossover[idx, gene_idx] + random_value
            # Check if all values are non-negatives or if the production limit is not exceeded.
            # Otherwise mutate again until the constraints are not respected.
            while (not np.all(offspring_crossover[idx, gene_idx])>=0) and offspring_crossover[idx, 1]<offspring_crossover[idx, 3]+PRODUCTION_LIMIT:
                random_value = np.random.uniform(-20.0, 20.0, 1)
                offspring_crossover[idx, gene_idx] = offspring_crossover[idx, gene_idx] + random_value
            gene_idx = gene_idx + mutations_counter
            
    return offspring_crossover


def generateObs(fitness, pop):
    client = InfluxDBClient('localhost', 8086, 'root', 'root', clientID)
    best_match = np.where(fitness == np.max(fitness))
    sol = pop[best_match,:]
    
    body = [{
        'tags':{
            'op':target
        },
        'measurement':f'optimization',
        'fields':{
            'Psup':sol[0][0][0],
            'Qsup':sol[0][0][1],
            'Pdem':sol[0][0][2],
            'Qdem':sol[0][0][3],
            'Profit':fitness[best_match][0]
        }
    }]
    client.write_points(body)


# +
# Target operator
target = 'IREN ENERGIA SPA'
clientID = 'PublicBids'
targetDay = datetime.strptime('20170210','%Y%m%d')

client = InfluxDBClient('localhost', 8086, 'root', 'root', clientID)
client.query(f"DELETE FROM optimization where op = '{target}'")

# Number of genes
GENES = 4
# Number of chromosome
CHROMOSOMES = 8
# Population size
POP_SIZE = (CHROMOSOMES, GENES)
# Number of parents mating
N_PARENTS = 4
# Number of generations
N_GENERATIONS = 6000
# Number of mutations
MUTATIONS = 2


best_out = []

# Initialization
dem, sup = getData('MGP')
# Define the production limit
PRODUCTION_LIMIT = sup.loc[target].Q - dem.loc[target].Q

# Determine the forecasted/original profit to check
# the optimization in the end.
zero_pop = np.asarray(
    [sup.loc[target].P,
    sup.loc[target].Q,
    dem.loc[target].P,
    dem.loc[target].Q]
)
zero_profit = getFitness(dem, sup, np.asarray([zero_pop]))[0]
# Start from the forcasted/original solution and
# create the first population by perturbating it
# in the [-4, 4] range
new_pop = np.copy(zero_pop)
for i in range(CHROMOSOMES-1):
    temp_pop = zero_pop+np.random.uniform(low = -4.0, high=4.0)
    new_pop = np.vstack((new_pop, temp_pop))
# +
# Start the algorithm
for generation in range(N_GENERATIONS):
    if generation%100 == 0:
        print(f'Generation: {generation}')
    fitness = getFitness(dem, sup, new_pop)
    # Generate Observations
    generateObs(fitness, new_pop)
    
    best_out.append(np.max(fitness))
    
    parents = select_mating_pool(new_pop, fitness, N_PARENTS)
    
    offspring_crossover = crossover(parents, offspring_size=(POP_SIZE[0]-parents.shape[0], GENES))
    
    offspring_mutation = mutation(offspring_crossover, MUTATIONS)
    
    new_pop[0:parents.shape[0], :] = parents
    new_pop[parents.shape[0]:, :] = offspring_mutation
    
fitness = getFitness(dem, sup, new_pop)
best_match = np.where(fitness == np.max(fitness))

print(f'Best Solution: {new_pop[best_match,:]}')
print(f'Best Solution Fitness: {fitness[best_match]}')
    
# -


plt.figure()
plt.plot(best_out, linewidth=2, label='Optimization')
plt.axhline(y = zero_profit, linewidth=2, linestyle='-.', color='k', label='Generation 0')
plt.xlabel("Iteration")
plt.ylabel("Fitness")
plt.grid(linestyle='-.')
plt.legend()
plt.show()
plt.savefig('fig/genetic.png', transparent=True)

