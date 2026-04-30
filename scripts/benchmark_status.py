#!/usr/bin/env python3
"""Monitor the status of benchmark experiments in this repo.

Usage:
    uv run scripts/benchmark_status.py [--task TASK] [--subtask SUBTASK]

For every TASK/SUBTASK this code checks that there is a subdirectory D
in the main branch of the repo called benchmarks/results/TASK/SUBTASK
(eg benchmarks/results/musr/team). That subdirectory D should contain
a valid "results directory" for the expt_name S, for each S in
'workflow', 'pot', 'react', 'structured_baseline', and 'unstructured_baseline'.

If there is no such directory print TASK/SUBTASK that subtask gets a
score of 0, with a message saying that the expected result directory
is not found.

For each valid S, the score for TASK/SUBTASK should be computed as
as follows:
 - 5 points if S contains config.yaml
 - 5 points if S contains results.csv
 - 5 points if the local copy of the results directory is checked in: i.e.,
   if benchmarks/TASK/results or benchmarks/TASK/SUBTASK/results contains a copy of S
 - 5 points if the local copy of llm_cache is checked in

"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"

TASKS = [
    "bbh/date_understanding",
    "bbh/geometric_shapes",
    "bbh/penguins_in_a_table",
    "bbh/sports_understanding",
    "designbench/vanilla",
    "designbench/vue",
    "designbench/angular",
    "finqa/finqa",
    "medagentbench/medagentbench",
    "medcalc/equation",
    "medcalc/rule",
    "medcalc/test",
    "musr/murder",
    "musr/object",
    "musr/team",
    "natural_plan/calendar",
    "natural_plan/meeting",
    "natural_plan/trip",
    "rulearena/airline",
    "rulearena/tax",
    "rulearena/nba",
    "tabmwp/tabmwp",
    "tau_bench/retail",
]

TASK_TO_LATEX = {
    "bbh/date_understanding": "BBH Date Understanding",
    "bbh/geometric_shapes": "BBH Geometric Shapes",
    "bbh/penguins_in_a_table": "BBH Penguins in a Table",
    "bbh/sports_understanding": "BBH Sports Understanding",
    "designbench/vanilla": "DesignBench Vanilla",
    "designbench/vue": "DesignBench Vue",
    "designbench/angular": "DesignBench Angular",
    "finqa/finqa": "FinQA",
    "medagentbench/medagentbench": "MedAgentBench",
    "medcalc/equation": "MedCalc Formulas",
    "medcalc/rule": "MedCalc Rules",
    "musr/murder": "MUSR Murder",
    "musr/object": "MUSR Objects",
    "musr/team": "MUSR Teams",
    "natural_plan/calendar": "NaturalPlan Calendar",
    "natural_plan/meeting": "NaturalPlan Meeting",
    "natural_plan/trip": "NaturalPlan Trip",
    "rulearena/airline": "Rulearena Airlines",
    "rulearena/tax": "Rulearena Tax",
    "rulearena/nba": "Rulearena NBA",
    "tabmwp/tabmwp": "Tabular Math WP",
    "tau_bench/retail": "$\\tau$ Bench Retail",
}


STRATEGIES = [
    "workflow",
    "pot",
    "react",
    "structured_baseline",
    "unstructured_baseline",
]

# Pattern: 2026mmdd.hhmmss.STRATEGY
RESULT_DIR_RE = re.compile(r"^2026\d{4}\.\d{6}\.(.+)$")


def _git_ls_tree_names(repo_relative_path: str, branch: str = "main") -> list[str]:
    """Return the names of entries under a directory on the given git branch.

    Uses 'git ls-tree' so it checks what is committed, not what is on disk.
    Returns an empty list if the path does not exist on that branch.
    """
    result = subprocess.run(
        ["git", "ls-tree", "--name-only", f"{branch}:{repo_relative_path}"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        return []
    return result.stdout.strip().splitlines()


def exists_on_branch(repo_relative_path: str, branch: str = "main") -> bool:
    """Check whether a file or directory exists on the given git branch."""
    result = subprocess.run(
        ["git", "cat-file", "-t", f"{branch}:{repo_relative_path}"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return result.returncode == 0


def _git_show_text(repo_relative_path: str, branch: str = "main") -> str | None:
    """Read a committed text file from the given branch."""
    result = subprocess.run(
        ["git", "show", f"{branch}:{repo_relative_path}"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _dataset_split_from_config(config_text: str) -> str | None:
    """Extract dataset.split from simple YAML config text."""
    in_dataset = False
    dataset_indent = 0
    for raw_line in config_text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        stripped = raw_line.strip()
        if re.match(r"^dataset\s*:\s*$", stripped):
            in_dataset = True
            dataset_indent = indent
            continue
        if in_dataset and indent <= dataset_indent:
            in_dataset = False
        if in_dataset:
            match = re.match(r"^split\s*:\s*(.+?)\s*$", stripped)
            if match:
                return match.group(1).strip().strip("'\"")
    return None


def expected_dataset_split(task: str, subtask: str) -> str | None:
    """Return a required dataset.split substring for status checks."""
    if task == "medcalc" and subtask == "test":
        return "test"
    return None


def find_result_dirs(parent_repo_path: str, strategy: str) -> list[str]:
    """Find all result directory names under parent matching the given strategy.

    Checks the main branch via git, not the local working tree.
    """
    matches = []
    for name in _git_ls_tree_names(parent_repo_path):
        m = RESULT_DIR_RE.match(name)
        if m and m.group(1) == strategy:
            matches.append(name)
    return matches


def find_all_result_dirs(parent_repo_path: str) -> list[tuple[str, str]]:
    """Find all timestamped result directory names under parent, returning (name, strategy) pairs."""
    results = []
    for name in sorted(_git_ls_tree_names(parent_repo_path)):
        m = RESULT_DIR_RE.match(name)
        if m:
            results.append((name, m.group(1)))
    return results


def check_benchmark(task_subtask: str, full: bool = False) -> tuple[int, list[str]]:
    """Check a single TASK/SUBTASK and return (score, details)."""
    task, subtask = task_subtask.split("/")
    results_repo_path = f"benchmarks/results/{task}/{subtask}"

    if not exists_on_branch(results_repo_path):
        return 0, [f"  result directory {results_repo_path} not found on main"]

    # Candidate repo-relative paths for local results copy and llm_cache
    local_results_candidates = [
        f"benchmarks/{task}/results",
        f"benchmarks/{task}/{subtask}/results",
    ]
    llm_cache_candidates = [
        f"benchmarks/{task}/llm_cache",
        f"benchmarks/{task}/{subtask}/llm_cache",
    ]

    score = 0
    details = []

    for strategy in STRATEGIES:
        dirs = find_result_dirs(results_repo_path, strategy)
        if not dirs:
            details.append(f"  {strategy}: missing")
            continue

        # Use the latest directory (sorted lexicographically = chronologically)
        dir_name = sorted(dirs)[-1]
        result_repo_path = f"{results_repo_path}/{dir_name}"
        s_score = 0
        s_details = []

        # Check config.yaml, and for explicit test-set subtasks verify
        # dataset.split in that committed config really names the test split.
        config_path = f"{result_repo_path}/config.yaml"
        if exists_on_branch(config_path):
            required_split = expected_dataset_split(task, subtask)
            if required_split is None:
                s_score += 5
            else:
                config_text = _git_show_text(config_path)
                split = _dataset_split_from_config(config_text or "")
                if split is not None and required_split in split:
                    s_score += 5
                else:
                    s_details.append(
                        f"dataset.split={split!r} does not contain {required_split!r}"
                    )
        else:
            s_details.append("no config.yaml")

        # Check results.csv
        if exists_on_branch(f"{result_repo_path}/results.csv"):
            s_score += 5
        else:
            s_details.append("no results.csv")

        # Check local results copy
        has_local_copy = any(
            exists_on_branch(f"{candidate}/{dir_name}")
            for candidate in local_results_candidates
        )
        if has_local_copy:
            s_score += 5
        else:
            s_details.append("no local results copy")

        # Check llm_cache
        has_llm_cache = any(
            exists_on_branch(candidate)
            for candidate in llm_cache_candidates
        )
        if has_llm_cache:
            s_score += 5
        else:
            s_details.append("no llm_cache")

        score += s_score
        status = f"{s_score}/20"
        if s_details:
            status += f" ({', '.join(s_details)})"
        details.append(f"  {strategy}: {status}  [{dir_name}]")

    if full:
        scored_dirs = set()
        for strategy in STRATEGIES:
            scored_dirs.update(find_result_dirs(results_repo_path, strategy))
        all_dirs = find_all_result_dirs(results_repo_path)
        extras = [(name, strat) for name, strat in all_dirs if name not in scored_dirs]
        if extras:
            details.append("  *extra result directories:")
            for name, strat in extras:
                details.append(f"    {name}")

    return score, details


def main():
    parser = argparse.ArgumentParser(description="Monitor benchmark experiment status.")
    parser.add_argument("--task", help="Restrict to a specific task (e.g. musr)")
    parser.add_argument("--subtask", help="Restrict to a specific subtask (e.g. murder)")
    parser.add_argument("--full", action="store_true", help="List extra (non-scored) result directories")
    args = parser.parse_args()

    benchmarks = TASKS
    if args.task:
        benchmarks = [t for t in benchmarks if t.split("/")[0] == args.task]
    if args.subtask:
        benchmarks = [t for t in benchmarks if t.split("/")[1] == args.subtask]

    if not benchmarks:
        print(f"No matching benchmarks found for --task={args.task} --subtask={args.subtask}")
        return 1

    max_possible = len(STRATEGIES) * 20
    total_score = 0
    total_possible = 0

    print("Benchmark Status Report")
    print("=" * 70)
    print()

    for task_subtask in benchmarks:
        total_possible += max_possible
        score, details = check_benchmark(task_subtask, full=args.full)
        total_score += score
        print(f"{task_subtask}: {score}/{max_possible}")
        for line in details:
            print(line)
        print()

    print("=" * 70)
    print(f"Total: {total_score}/{total_possible}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
