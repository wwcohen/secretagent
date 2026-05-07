"""Multi-objective config search over categorical spaces.

Two modes:
  - Exhaustive: enumerate all configs when space is small (default threshold: 20)
  - NSGA-II: evolutionary search when space is too large to enumerate
"""

import math
import os
import random
import subprocess
import time
from itertools import product
from pathlib import Path

import pandas as pd
from deap import base, creator, tools

from secretagent.optimize.encoder import (
    SearchDimension, decode, decode_modular, decode_dict, dim_sizes, space_size,
)

# ---------------------------------------------------------------------------
# Categorical genetic operators
# ---------------------------------------------------------------------------

def uniform_crossover(ind1, ind2):
    """Swap each gene with 50% probability."""
    for i in range(len(ind1)):
        if random.random() < 0.5:
            ind1[i], ind2[i] = ind2[i], ind1[i]
    return ind1, ind2


def random_reset_mutation(individual, dsizes, indpb=0.2):
    """Replace each gene with a random valid value with probability indpb."""
    for i in range(len(individual)):
        if random.random() < indpb:
            individual[i] = random.randint(0, dsizes[i] - 1)
    return individual,


# ---------------------------------------------------------------------------
# Evaluation cache (subprocess-based)
# ---------------------------------------------------------------------------

class EvalCache:
    """Evaluate configs via subprocess, caching results by chromosome."""

    def __init__(
        self,
        dims: list[SearchDimension],
        fixed_overrides: list[str],
        base_command: str | list[str],
        base_dotlist: list[str] | None = None,
        cwd: str | None = None,
        timeout: int = 1800,
        metric: str = "correct",
        expt_prefix: str = "nsga",
        label_fn=None,
        compound_overrides: dict | None = None,
    ):
        self.dims = dims
        self.fixed_overrides = fixed_overrides
        if isinstance(base_command, str):
            import shlex
            base_command = shlex.split(base_command)
        self.base_command = base_command
        self.base_dotlist = base_dotlist or []
        self.cwd = cwd
        self.timeout = timeout
        self.metric = metric
        self.expt_prefix = expt_prefix
        self.label_fn = label_fn
        self.compound_overrides = compound_overrides
        self.cache: dict[tuple, tuple[float, float]] = {}
        self.eval_count = 0
        self.cache_hits = 0

    def _decode(self, individual) -> list[str]:
        vec = list(individual)
        if self.compound_overrides:
            return decode_modular(self.dims, vec, self.compound_overrides)
        return decode(self.dims, vec)

    def _label(self, individual):
        if self.label_fn:
            return self.label_fn(self.dims, list(individual))
        if self.compound_overrides:
            d = decode_dict(self.dims, list(individual))
            return ", ".join(f"{k}={v}" for k, v in d.items())
        return ", ".join(decode(self.dims, list(individual)))

    def __call__(self, individual) -> tuple[float, float]:
        key = tuple(individual)
        if key in self.cache:
            self.cache_hits += 1
            return self.cache[key]

        self.eval_count += 1
        dotlist = self._decode(individual)
        all_overrides = dotlist + self.fixed_overrides
        expt_name = f"{self.expt_prefix}_{self.eval_count:03d}"

        cmd = (
            self.base_command
            + self.base_dotlist
            + all_overrides
            + [f"evaluate.expt_name={expt_name}"]
        )

        label = self._label(individual)
        print(f"  [eval {self.eval_count}] {expt_name}: {label}")

        accuracy = 0.0
        cost_per_q = math.inf

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=self.timeout,
                env=os.environ.copy(),
            )
            elapsed = time.time() - start

            if result.returncode != 0:
                stderr_tail = "\n".join(result.stderr.strip().split("\n")[-3:])
                print(f"    FAILED (exit {result.returncode}): {stderr_tail[:200]}")
            else:
                csv_path = None
                for line in result.stdout.split("\n"):
                    if "saved in" in line and ".csv" in line:
                        csv_path = line.split("saved in ")[-1].strip()

                if csv_path and Path(csv_path).exists():
                    df = pd.read_csv(csv_path)
                    accuracy = df[self.metric].mean()
                    raw_cost = df["cost"].mean() if "cost" in df.columns else 0.0
                    if math.isnan(raw_cost) or math.isnan(accuracy):
                        cost_per_q = math.inf
                        print(f"    NaN in results — treating as failed ({elapsed:.0f}s)")
                    elif accuracy == 0.0 and raw_cost < 1e-9:
                        cost_per_q = math.inf
                        print(f"    0.0% accuracy, $0.00/q — treating as failed ({elapsed:.0f}s)")
                    else:
                        cost_per_q = raw_cost
                        print(f"    {accuracy:.1%} accuracy, ${cost_per_q:.4f}/q ({elapsed:.0f}s)")
                else:
                    print(f"    no results CSV found ({elapsed:.0f}s)")

        except subprocess.TimeoutExpired:
            print(f"    TIMEOUT after {self.timeout}s")
        except Exception as e:
            print(f"    ERROR: {e}")

        fitness = (accuracy, cost_per_q)
        self.cache[key] = fitness
        return fitness


# ---------------------------------------------------------------------------
# Exhaustive search (for small spaces)
# ---------------------------------------------------------------------------

def _dominates(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """a dominates b: higher accuracy AND lower cost, strict on at least one."""
    return (a[0] >= b[0] and a[1] <= b[1]) and (a[0] > b[0] or a[1] < b[1])


def run_exhaustive(
    dims: list[SearchDimension],
    fixed_overrides: list[str],
    base_command: str | list[str],
    base_dotlist: list[str] | None = None,
    cwd: str | None = None,
    timeout: int = 1800,
    metric: str = "correct",
    expt_prefix: str = "exhaust",
    label_fn=None,
    compound_overrides: dict | None = None,
) -> tuple[list[tuple[list[int], float, float]], list[tuple[list[int], float, float]], list[dict]]:
    """Enumerate and evaluate every config in the space.

    Returns (frontier, all_evaluated, gen_log) same as run_nsga2.
    """
    dsizes = dim_sizes(dims)
    total = space_size(dims)

    print(f"Exhaustive search: {len(dims)} dimensions, {total} total configs")
    print(f"  Dimensions: {[(d.key, d.size) for d in dims]}")
    print(f"  Fixed: {fixed_overrides}")
    print()

    eval_cache = EvalCache(
        dims=dims,
        fixed_overrides=fixed_overrides,
        base_command=base_command,
        base_dotlist=base_dotlist,
        cwd=cwd,
        timeout=timeout,
        metric=metric,
        expt_prefix=expt_prefix,
        label_fn=label_fn,
        compound_overrides=compound_overrides,
    )

    all_evaluated = []
    for vec in product(*(range(s) for s in dsizes)):
        acc, cost = eval_cache(list(vec))
        all_evaluated.append((list(vec), acc, cost))

    # Compute Pareto frontier (deduplicated by fitness)
    frontier = []
    seen_fitness = set()
    for i, (chrom_i, acc_i, cost_i) in enumerate(all_evaluated):
        dominated = False
        for j, (chrom_j, acc_j, cost_j) in enumerate(all_evaluated):
            if i != j and _dominates((acc_j, cost_j), (acc_i, cost_i)):
                dominated = True
                break
        if not dominated and cost_i < math.inf:
            fkey = (acc_i, cost_i)
            if fkey not in seen_fitness:
                seen_fitness.add(fkey)
                frontier.append((chrom_i, acc_i, cost_i))

    frontier.sort(key=lambda x: -x[1])
    gen_log = [{
        "generation": 0,
        "frontier_size": len(frontier),
        "new_evals": len(all_evaluated),
        "cache_hits": 0,
        "total_evals": len(all_evaluated),
        "best_accuracy": max((a for _, a, _ in frontier), default=0.0),
        "cheapest_cost": min((c for _, _, c in frontier if c < math.inf), default=math.inf),
        "elapsed_s": 0.0,
    }]
    return frontier, all_evaluated, gen_log


# ---------------------------------------------------------------------------
# NSGA-II (for large spaces)
# ---------------------------------------------------------------------------

_DEAP_TYPES_CREATED = False


def _unique_front_size(front):
    """Count unique chromosomes in a DEAP front."""
    return len({tuple(ind) for ind in front})


def _run_nsga2_inner(
    dims: list[SearchDimension],
    fixed_overrides: list[str],
    base_command: str | list[str],
    base_dotlist: list[str] | None = None,
    cwd: str | None = None,
    timeout: int = 1800,
    metric: str = "correct",
    expt_prefix: str = "nsga",
    pop_size: int = 10,
    n_gen: int = 5,
    cxpb: float = 0.7,
    mutpb: float = 0.4,
    seed: int = 42,
    label_fn=None,
    compound_overrides: dict | None = None,
) -> tuple[list[tuple[list[int], float, float]], list[tuple[list[int], float, float]], list[dict]]:
    """Run NSGA-II over a categorical config space.

    Returns:
        (frontier, all_evaluated, gen_log) where frontier and all_evaluated
        are lists of (chromosome, accuracy, cost_per_q) tuples, and gen_log
        is a list of per-generation stat dicts.
    """
    random.seed(seed)
    dsizes = dim_sizes(dims)
    total_configs = space_size(dims)

    # selTournamentDCD requires pop_size divisible by 4
    requested_pop = pop_size
    if pop_size % 4 != 0:
        pop_size = ((pop_size // 4) + 1) * 4
        print(f"Requested pop_size={requested_pop}, "
              f"rounded to {pop_size} (selTournamentDCD requires multiple of 4)")

    print(f"NSGA-II: {len(dims)} dimensions, {total_configs} total configs, "
          f"pop={pop_size}, gen={n_gen}")
    print(f"  Dimensions: {[(d.key, d.size) for d in dims]}")
    print(f"  Fixed: {fixed_overrides}")
    print()

    # DEAP type setup (guard against re-creation across multiple calls)
    global _DEAP_TYPES_CREATED
    if not _DEAP_TYPES_CREATED:
        creator.create("FitnessPareto", base.Fitness, weights=(1.0, -1.0))
        creator.create("Individual", list, fitness=creator.FitnessPareto)
        _DEAP_TYPES_CREATED = True

    toolbox = base.Toolbox()

    def make_individual():
        return creator.Individual([random.randint(0, s - 1) for s in dsizes])

    toolbox.register("individual", make_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", uniform_crossover)
    toolbox.register("mutate", random_reset_mutation, dsizes=dsizes, indpb=0.3)
    toolbox.register("select", tools.selNSGA2)

    eval_cache = EvalCache(
        dims=dims,
        fixed_overrides=fixed_overrides,
        base_command=base_command,
        base_dotlist=base_dotlist,
        cwd=cwd,
        timeout=timeout,
        metric=metric,
        expt_prefix=expt_prefix,
        label_fn=label_fn,
        compound_overrides=compound_overrides,
    )

    # Initialize population
    pop = toolbox.population(n=pop_size)

    print("--- Initial population ---")
    gen0_t0 = time.time()
    for ind in pop:
        ind.fitness.values = eval_cache(ind)

    # Assign crowding distance before first tournament selection
    pop = toolbox.select(pop, pop_size)

    prev_cache_hits = eval_cache.cache_hits
    prev_eval_count = eval_cache.eval_count
    gen_log = []

    # Log generation 0 (initial population)
    init_front = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
    init_accs = [ind.fitness.values[0] for ind in init_front]
    init_costs = [ind.fitness.values[1] for ind in init_front if ind.fitness.values[1] < math.inf]
    gen0_elapsed = time.time() - gen0_t0
    gen_log.append({
        "generation": 0,
        "frontier_size": _unique_front_size(init_front),
        "new_evals": eval_cache.eval_count,
        "cache_hits": 0,
        "total_evals": eval_cache.eval_count,
        "best_accuracy": max(init_accs) if init_accs else 0.0,
        "cheapest_cost": min(init_costs) if init_costs else math.inf,
        "elapsed_s": gen0_elapsed,
    })

    for gen in range(1, n_gen + 1):
        gen_t0 = time.time()

        # Parent selection
        offspring = tools.selTournamentDCD(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))

        # Crossover
        for i in range(0, len(offspring) - 1, 2):
            if random.random() < cxpb:
                toolbox.mate(offspring[i], offspring[i + 1])
                del offspring[i].fitness.values
                del offspring[i + 1].fitness.values

        # Mutation
        for mutant in offspring:
            if random.random() < mutpb:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        # Evaluate new individuals
        invalids = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalids:
            ind.fitness.values = eval_cache(ind)

        # Survivor selection: parents + offspring → next generation
        pop = toolbox.select(pop + offspring, pop_size)

        front = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
        unique_front = _unique_front_size(front)
        gen_cache_hits = eval_cache.cache_hits - prev_cache_hits
        gen_evals = eval_cache.eval_count - prev_eval_count
        prev_cache_hits = eval_cache.cache_hits
        prev_eval_count = eval_cache.eval_count

        front_accs = [ind.fitness.values[0] for ind in front]
        front_costs = [ind.fitness.values[1] for ind in front if ind.fitness.values[1] < math.inf]
        best_acc = max(front_accs) if front_accs else 0.0
        cheapest = min(front_costs) if front_costs else math.inf
        gen_elapsed = time.time() - gen_t0

        gen_log.append({
            "generation": gen,
            "frontier_size": unique_front,
            "new_evals": gen_evals,
            "cache_hits": gen_cache_hits,
            "total_evals": eval_cache.eval_count,
            "best_accuracy": best_acc,
            "cheapest_cost": cheapest,
            "elapsed_s": gen_elapsed,
        })

        cost_str = f"${cheapest:.4f}" if cheapest < math.inf else "n/a"
        print(f"  Gen {gen}/{n_gen}: {unique_front} frontier, "
              f"{gen_evals} new evals, {gen_cache_hits} cache hits | "
              f"best {best_acc:.1%}, cheapest {cost_str} ({gen_elapsed:.0f}s)")

    # Extract final frontier (deduplicated by chromosome AND by fitness)
    front = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
    seen_chroms = set()
    seen_fitness = set()
    results = []
    for ind in front:
        key = tuple(ind)
        if key in seen_chroms:
            continue
        seen_chroms.add(key)
        acc, cost = ind.fitness.values
        fkey = (acc, cost)
        if fkey in seen_fitness:
            continue
        seen_fitness.add(fkey)
        results.append((list(ind), acc, cost))

    results.sort(key=lambda x: -x[1])  # sort by accuracy descending

    # All evaluated configs (for plotting dominated points)
    all_evaluated = [
        (list(chrom), acc, cost)
        for chrom, (acc, cost) in eval_cache.cache.items()
    ]

    return results, all_evaluated, gen_log


# ---------------------------------------------------------------------------
# Public entry point: auto-selects exhaustive vs NSGA-II
# ---------------------------------------------------------------------------

EXHAUSTIVE_THRESHOLD = 20


def run_nsga2(
    dims: list[SearchDimension],
    fixed_overrides: list[str],
    base_command: str | list[str],
    base_dotlist: list[str] | None = None,
    cwd: str | None = None,
    timeout: int = 1800,
    metric: str = "correct",
    expt_prefix: str = "nsga",
    pop_size: int = 10,
    n_gen: int = 5,
    cxpb: float = 0.7,
    mutpb: float = 0.4,
    seed: int = 42,
    label_fn=None,
    compound_overrides: dict | None = None,
) -> tuple[list[tuple[list[int], float, float]], list[tuple[list[int], float, float]], list[dict]]:
    """Search for the Pareto frontier over a categorical config space.

    Automatically uses exhaustive enumeration when the space has
    <= EXHAUSTIVE_THRESHOLD configs, NSGA-II otherwise.

    Args:
        compound_overrides: optional dict mapping dim key to
            {value: [dotlist_override, ...]} for compound dimensions
            whose single gene value expands to multiple overrides.

    Returns:
        (frontier, all_evaluated, gen_log) where frontier and all_evaluated
        are lists of (chromosome, accuracy, cost_per_q) tuples, and gen_log
        is a list of per-generation stat dicts.
    """
    total = space_size(dims)

    if total <= EXHAUSTIVE_THRESHOLD:
        print(f"Space has {total} configs (<= {EXHAUSTIVE_THRESHOLD}): using exhaustive search")
        print()
        return run_exhaustive(
            dims=dims,
            fixed_overrides=fixed_overrides,
            base_command=base_command,
            base_dotlist=base_dotlist,
            cwd=cwd,
            timeout=timeout,
            metric=metric,
            expt_prefix=expt_prefix,
            label_fn=label_fn,
            compound_overrides=compound_overrides,
        )
    else:
        print(f"Space has {total} configs (> {EXHAUSTIVE_THRESHOLD}): using NSGA-II")
        print()
        return _run_nsga2_inner(
            dims=dims,
            fixed_overrides=fixed_overrides,
            base_command=base_command,
            base_dotlist=base_dotlist,
            cwd=cwd,
            timeout=timeout,
            metric=metric,
            expt_prefix=expt_prefix,
            pop_size=pop_size,
            n_gen=n_gen,
            cxpb=cxpb,
            mutpb=mutpb,
            seed=seed,
            label_fn=label_fn,
            compound_overrides=compound_overrides,
        )
