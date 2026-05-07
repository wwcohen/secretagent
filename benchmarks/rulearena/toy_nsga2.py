"""Toy NSGA-II with categorical variables to verify DEAP setup.

3 categorical dimensions, 2 objectives (maximize accuracy, minimize cost).
The toy objective is a lookup table with a known Pareto frontier.

Dimensions:
  method:  [A, B, C]       (index 0-2)
  model:   [cheap, mid, expensive]  (index 0-2)
  n_demos: [0, 3, 5]       (index 0-2)

Objective function (deterministic lookup):
  accuracy = method_acc[m] + model_acc[m] + demo_acc[d]
  cost     = method_cost[m] + model_cost[m] + demo_cost[d]

The search space has 3*3*3 = 27 configs. We enumerate all of them to
find the true Pareto frontier, then run NSGA-II and check it recovers
the same frontier.
"""

import random
from deap import base, creator, tools, algorithms

# --- Toy objective components ---

METHOD_ACC  = [0.3, 0.5, 0.7]   # A, B, C
METHOD_COST = [0.01, 0.05, 0.10]

MODEL_ACC   = [0.0, 0.1, 0.2]   # cheap, mid, expensive
MODEL_COST  = [0.001, 0.01, 0.05]

DEMO_ACC    = [0.0, 0.05, 0.10]  # 0, 3, 5 demos
DEMO_COST   = [0.0, 0.005, 0.02]

N_DIMS = 3
DIM_SIZES = [3, 3, 3]  # number of choices per dimension


def evaluate(individual):
    m, d, n = individual
    accuracy = METHOD_ACC[m] + MODEL_ACC[d] + DEMO_ACC[n]
    cost = METHOD_COST[m] + MODEL_COST[d] + DEMO_COST[n]
    return accuracy, cost


# --- Brute-force: enumerate all 27 configs, find true Pareto frontier ---

def dominates(a, b):
    """a dominates b if a has >= accuracy AND <= cost, with strict on at least one."""
    return (a[0] >= b[0] and a[1] <= b[1]) and (a[0] > b[0] or a[1] < b[1])


def brute_force_frontier():
    all_configs = []
    for m in range(3):
        for d in range(3):
            for n in range(3):
                ind = (m, d, n)
                acc, cost = evaluate(ind)
                all_configs.append((ind, acc, cost))

    frontier = []
    for i, (ind_i, acc_i, cost_i) in enumerate(all_configs):
        dominated = False
        for j, (ind_j, acc_j, cost_j) in enumerate(all_configs):
            if i != j and dominates((acc_j, cost_j), (acc_i, cost_i)):
                dominated = True
                break
        if not dominated:
            frontier.append((ind_i, acc_i, cost_i))

    return sorted(frontier, key=lambda x: x[1]), all_configs


# --- DEAP setup ---

# Fitness: maximize accuracy (weight +1), minimize cost (weight -1)
creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0))
creator.create("Individual", list, fitness=creator.FitnessMulti)

toolbox = base.Toolbox()

# Attribute generators: random int for each categorical dimension
toolbox.register("attr_method", random.randint, 0, DIM_SIZES[0] - 1)
toolbox.register("attr_model", random.randint, 0, DIM_SIZES[1] - 1)
toolbox.register("attr_demos", random.randint, 0, DIM_SIZES[2] - 1)

# Individual: list of 3 categorical indices
def make_individual():
    return creator.Individual([
        toolbox.attr_method(),
        toolbox.attr_model(),
        toolbox.attr_demos(),
    ])

toolbox.register("individual", make_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)


# --- Categorical operators ---

def uniform_crossover(ind1, ind2):
    """For each gene, randomly pick from parent A or B."""
    for i in range(len(ind1)):
        if random.random() < 0.5:
            ind1[i], ind2[i] = ind2[i], ind1[i]
    return ind1, ind2


def random_reset_mutation(individual, indpb=0.3):
    """Replace each gene with a random valid value with probability indpb."""
    for i in range(len(individual)):
        if random.random() < indpb:
            individual[i] = random.randint(0, DIM_SIZES[i] - 1)
    return individual,


toolbox.register("mate", uniform_crossover)
toolbox.register("mutate", random_reset_mutation, indpb=0.3)
toolbox.register("select", tools.selNSGA2)
toolbox.register("evaluate", evaluate)


# --- Main loop ---

def run_nsga2(pop_size=20, n_gen=12, seed=42):
    random.seed(seed)

    pop = toolbox.population(n=pop_size)

    # Evaluate initial population
    fitnesses = list(map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    print(f"NSGA-II: pop={pop_size}, generations={n_gen}, "
          f"search space={DIM_SIZES[0]*DIM_SIZES[1]*DIM_SIZES[2]} configs")
    print()

    # Assign crowding distance on initial pop so tournament selection works
    pop = toolbox.select(pop, pop_size)

    for gen in range(n_gen):
        # Parent selection: tournament on crowding distance (now assigned by selNSGA2)
        offspring = tools.selTournamentDCD(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))

        # Crossover
        for i in range(0, len(offspring) - 1, 2):
            if random.random() < 0.8:
                toolbox.mate(offspring[i], offspring[i + 1])
                del offspring[i].fitness.values
                del offspring[i + 1].fitness.values

        # Mutation (higher rate to explore the small space thoroughly)
        for mutant in offspring:
            if random.random() < 0.5:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        # Evaluate offspring that need it
        invalids = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = list(map(toolbox.evaluate, invalids))
        for ind, fit in zip(invalids, fitnesses):
            ind.fitness.values = fit

        # Select next generation from combined parents + offspring
        pop = toolbox.select(pop + offspring, pop_size)

        # Report front size
        front = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
        print(f"  gen {gen+1}/{n_gen}: front size = {len(front)}")

    # Extract final Pareto front
    front = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
    return front


if __name__ == "__main__":
    # Get true frontier
    true_frontier, all_configs = brute_force_frontier()

    print("TRUE PARETO FRONTIER (brute force over all 27 configs):")
    print(f"{'Config':<12} {'Accuracy':>10} {'Cost':>10}")
    for ind, acc, cost in true_frontier:
        print(f"  {str(ind):<10} {acc:>10.3f} {cost:>10.4f}")
    print()

    # Run NSGA-II
    front = run_nsga2()

    print()
    print("NSGA-II FRONTIER (deduplicated):")
    print(f"{'Config':<12} {'Accuracy':>10} {'Cost':>10}")
    nsga_results = set()
    for ind in front:
        config_tuple = tuple(ind)
        if config_tuple in nsga_results:
            continue
        nsga_results.add(config_tuple)
        acc, cost = ind.fitness.values
        print(f"  {str(list(ind)):<10} {acc:>10.3f} {cost:>10.4f}")

    # Compare
    true_configs = {entry[0] for entry in true_frontier}
    print()
    print("VERIFICATION:")
    print(f"  True frontier size:  {len(true_configs)}")
    print(f"  NSGA-II frontier size: {len(nsga_results)}")
    print(f"  True configs found:  {len(nsga_results & true_configs)}/{len(true_configs)}")
    missing = true_configs - nsga_results
    extra = nsga_results - true_configs
    if missing:
        print(f"  Missing: {missing}")
    if extra:
        print(f"  Extra (dominated): {extra}")
    recall = len(nsga_results & true_configs) / len(true_configs)
    precision = len(nsga_results & true_configs) / len(nsga_results) if nsga_results else 0
    if nsga_results >= true_configs:
        print("  PASS: NSGA-II recovered the full Pareto frontier.")
    else:
        print(f"  Recall: {recall:.0%} ({len(nsga_results & true_configs)}/{len(true_configs)})")
        print(f"  Precision: {precision:.0%} ({len(nsga_results & true_configs)}/{len(nsga_results)})")
        if recall >= 0.8 and precision == 1.0:
            print("  OK: high recall, perfect precision. Expected for pop < space size.")
