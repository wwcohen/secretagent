"""Find every llm_cache directory across all git branches and sum total LLM cost.

Uses git to discover llm_cache directories in any branch, extracts their
cached pickle files to a temp directory, and runs extract_cached_stats
to compute total cost.

Usage:
    uv run python scripts/total_llm_cost.py
"""

import os
import subprocess
import tempfile
from collections import defaultdict

from secretagent.cache_util import extract_cached_stats


def find_llm_cache_dirs():
    """Find all llm_cache directory paths that ever existed across all branches."""
    result = subprocess.run(
        ["git", "log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:", "--", "*/llm_cache/*"],
        capture_output=True, text=True, check=True,
    )
    dirs = set()
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # strip the filename to get the directory
        d = os.path.dirname(line)
        if d.endswith("llm_cache"):
            dirs.add(d)
    return sorted(dirs)


def find_creator(cache_dir):
    """Find the git author who first added files to this llm_cache directory."""
    result = subprocess.run(
        ["git", "log", "--all", "--diff-filter=A", "--format=%aN", "--reverse", "--", cache_dir + "/*"],
        capture_output=True, text=True, check=True,
    )
    lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
    return lines[0] if lines else "unknown"


def find_branch_for_path(path):
    """Find a branch/ref whose tree contains the given path."""
    # Try all refs and return the first one that has this path
    refs_result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/heads/", "refs/remotes/"],
        capture_output=True, text=True, check=True,
    )
    for ref in refs_result.stdout.strip().splitlines():
        ref = ref.strip()
        if not ref:
            continue
        check = subprocess.run(
            ["git", "ls-tree", "-d", ref, "--", path],
            capture_output=True, text=True,
        )
        if check.returncode == 0 and check.stdout.strip():
            return ref
    return None


def extract_dir_from_git(ref, dir_path, dest):
    """Extract all files from a git tree path into a local destination directory."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "--", dir_path + "/"],
        capture_output=True, text=True, check=True,
    )
    files = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
    for fpath in files:
        blob = subprocess.run(
            ["git", "show", f"{ref}:{fpath}"],
            capture_output=True, check=True,
        )
        basename = os.path.basename(fpath)
        dest_file = os.path.join(dest, basename)
        with open(dest_file, "wb") as f:
            f.write(blob.stdout)
    return len(files)


def main():
    cache_dirs = find_llm_cache_dirs()
    print(f"Found {len(cache_dirs)} llm_cache directories across all branches:\n")

    grand_total_cost = 0.0
    grand_total_calls = 0
    grand_total_input_tokens = 0
    grand_total_output_tokens = 0

    # Per-user aggregation
    by_user = defaultdict(lambda: {"cost": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0})

    for cache_dir in cache_dirs:
        ref = find_branch_for_path(cache_dir)
        if ref is None:
            print(f"  {cache_dir}: no ref found, skipping")
            continue

        creator = find_creator(cache_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            n_files = extract_dir_from_git(ref, cache_dir, tmpdir)
            if n_files == 0:
                print(f"  {cache_dir} ({ref}, {creator}): empty, skipping")
                continue

            stats_list = extract_cached_stats(cache_dir=tmpdir)
            total_cost = sum(s.get("cost", 0) or 0 for s in stats_list)
            total_input = sum(s.get("input_tokens", 0) or 0 for s in stats_list)
            total_output = sum(s.get("output_tokens", 0) or 0 for s in stats_list)
            n_calls = len(stats_list)

            print(f"  {cache_dir} ({ref}, {creator})")
            print(f"    files={n_files}  calls={n_calls}  cost=${total_cost:.4f}"
                  f"  input_tokens={total_input}  output_tokens={total_output}")

            grand_total_cost += total_cost
            grand_total_calls += n_calls
            grand_total_input_tokens += total_input
            grand_total_output_tokens += total_output

            by_user[creator]["cost"] += total_cost
            by_user[creator]["calls"] += n_calls
            by_user[creator]["input_tokens"] += total_input
            by_user[creator]["output_tokens"] += total_output

    print(f"\n{'='*60}")
    print(f"Grand total: {grand_total_calls} cached calls, ${grand_total_cost:.4f}")
    print(f"  input_tokens:  {grand_total_input_tokens:,}")
    print(f"  output_tokens: {grand_total_output_tokens:,}")

    print(f"\n{'='*60}")
    print("By user:\n")
    for user in sorted(by_user, key=lambda u: by_user[u]["cost"], reverse=True):
        u = by_user[user]
        print(f"  {user}")
        print(f"    calls={u['calls']}  cost=${u['cost']:.4f}"
              f"  input_tokens={u['input_tokens']:,}  output_tokens={u['output_tokens']:,}")


if __name__ == "__main__":
    main()
