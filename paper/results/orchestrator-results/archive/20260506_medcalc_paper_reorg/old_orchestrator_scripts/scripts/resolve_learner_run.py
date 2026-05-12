#!/usr/bin/env python3
"""Resolve an orch_learner train-dir index entry.

The index may contain normal directory symlinks, real directories, or portable
text pointer files. Pointer files contain one absolute or repo-relative path on
their first non-empty line.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    for path in (start, *start.parents):
        if (path / ".git").exists() or (path / "pyproject.toml").exists():
            return path
    return None


def resolve_pointer(path: Path, repo_root: Path | None) -> Path | None:
    try:
        target_text = next(
            line.strip() for line in path.read_text().splitlines()
            if line.strip()
        )
    except (OSError, StopIteration, UnicodeDecodeError):
        return None

    raw = Path(target_text)
    if raw.is_absolute():
        return raw.resolve()

    candidates = []
    if repo_root is not None:
        candidates.append(repo_root / raw)
    candidates.append(path.parent / raw)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve() if candidates else raw


def resolve_train_dir(train_dir: Path, repo_root: Path | None) -> Path:
    candidates: list[tuple[str, Path]] = []
    for entry in sorted(train_dir.glob("*.orch_learner")):
        if entry.is_dir():
            candidates.append((entry.name, entry.resolve()))
            continue
        if entry.is_file():
            target = resolve_pointer(entry, repo_root)
            if target is not None:
                candidates.append((entry.name, target))

    valid = [(name, path) for name, path in candidates if path.is_dir()]
    if not valid:
        raise SystemExit(f"no orch_learner run found under {train_dir}")
    return valid[-1][1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("train_dir", type=Path)
    parser.add_argument("--repo-root", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve() if args.repo_root else find_repo_root(args.train_dir.resolve())
    print(resolve_train_dir(args.train_dir, repo_root))


if __name__ == "__main__":
    main()
