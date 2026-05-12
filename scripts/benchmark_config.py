#!/usr/bin/env python3
"""Show config values across benchmark result directories.

For each task/strategy, loads config.yaml from the latest result
directory and displays the requested config keys in a table.
Supports wildcards in keys (e.g. '*.tools', 'ptools.*').

Usage:

    # find what llm.model each experiment used
    uv run scripts/benchmark_config.py --check llm.model

    # find the number of tools used in each 'react' config
    uv run scripts/benchmark_config.py --check '*.tools' --strategy react --len

    # find how each tool is implemented
    uv run scripts/benchmark_config.py --check '*.method' --strategy workflow
"""

import argparse
import fnmatch
import sys
from pathlib import Path

import pandas as pd
from omegaconf import OmegaConf

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from benchmark_status import TASKS, RESULT_DIR_RE

sys.path.insert(0, str(REPO_ROOT / "src"))
from secretagent.config import to_dotlist

RESULTS_DIR = REPO_ROOT / "paper" / "results" / "results"

STRATEGY_ORDER = ["workflow", "react", "pot", "structured_baseline", "unstructured_baseline"]


def find_latest_result_dir(parent: Path, strategy: str) -> Path | None:
    """Find the latest result directory for a strategy under parent."""
    if not parent.is_dir():
        return None
    matches = []
    for d in parent.iterdir():
        if not d.is_dir():
            continue
        m = RESULT_DIR_RE.match(d.name)
        if m and m.group(1) == strategy:
            matches.append(d)
    if not matches:
        return None
    return sorted(matches)[-1]


def _has_wildcard(pattern):
    return any(c in pattern for c in "*?[]")


def _dotlist_to_dict(dotlist):
    """Convert a list of 'key=value' strings to a dict."""
    result = {}
    for pair in dotlist:
        key, val = pair.split("=", 1)
        result[key] = val
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="append", required=True,
                        help="Config key to display (repeatable, supports wildcards like '*.tools')")
    parser.add_argument("--strategy", default=None, choices=STRATEGY_ORDER,
                        help="Limit to a single strategy")
    parser.add_argument("--len", action="store_true", dest="show_len",
                        help="Show length of list values instead of the values themselves")
    args = parser.parse_args()

    patterns = args.check
    strategies = [args.strategy] if args.strategy else STRATEGY_ORDER

    rows = []
    for task_subtask in TASKS:
        task, subtask = task_subtask.split("/")
        parent = RESULTS_DIR / task / subtask

        for strategy in strategies:
            result_dir = find_latest_result_dir(parent, strategy)
            if result_dir is None:
                continue

            config_file = result_dir / "config.yaml"
            if not config_file.exists():
                continue

            cfg = OmegaConf.load(config_file)
            flat = _dotlist_to_dict(to_dotlist(cfg))

            for pattern in patterns:
                if _has_wildcard(pattern):
                    for key in sorted(flat):
                        if fnmatch.fnmatch(key, pattern):
                            rows.append({"task": task_subtask, "strategy": strategy,
                                         "key": key, "value": str(flat[key])})
                else:
                    val = flat.get(pattern)
                    rows.append({"task": task_subtask, "strategy": strategy,
                                 "key": pattern, "value": str(val) if val is not None else ""})

    if not rows:
        print("No matching result directories found.")
        return

    df = pd.DataFrame(rows).set_index(["task", "strategy", "key"])
    if args.show_len:
        import ast
        def _to_len(val):
            if not val:
                return ""
            try:
                return str(len(ast.literal_eval(val)))
            except (ValueError, SyntaxError, TypeError):
                return val
        df["value"] = df["value"].apply(_to_len)
    print(df.to_string())


if __name__ == "__main__":
    main()
