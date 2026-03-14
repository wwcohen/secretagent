"""Utilities for creating and finding experiment output files.

Experiment files are organized as:

    {basedir}/{timestamp}.{file_under}/{name}

where basedir and file_under are looked up from config keys, and
a config.yaml snapshot is saved alongside the output files.
"""

import datetime
import os
from pathlib import Path

from omegaconf import OmegaConf

from secretagent import config


def filename_list(
    basedir: str,
    names: list[str],
    file_under: str | None = None,
) -> list[Path]:
    """Create a timestamped directory and return paths for each name.

    Args:
        basedir: a config key whose value is the base directory, e.g. 'evaluate.result_dir'
        names: list of filenames to create paths for, e.g. ['results.csv', 'results.jsonl']
        file_under: optional config key whose value is used as a tag in the directory name,
            e.g. 'evaluate.expt_name'
    """
    base = Path(config.require(basedir))
    tag = config.get(file_under) if file_under else None
    timestamp = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
    if tag:
        dirname = base / f'{timestamp}.{tag}'
    else:
        dirname = base / timestamp
    os.makedirs(dirname, exist_ok=True)
    config.save(dirname / 'config.yaml')
    return [dirname / name for name in names]


def filename(
    basedir: str,
    name: str,
    file_under: str | None = None,
) -> Path:
    """Create a timestamped directory and return a path for a single file.

    Convenience wrapper around filename_list.
    """
    return filename_list(basedir, [name], file_under=file_under)[0]


def getfiles(
    basedir: str,
    file_under: str | None = None,
    most_recent: bool = False,
    **config_kws,
) -> list[Path]:
    """Find experiment directories matching constraints.

    Args:
        basedir: a config key whose value is the base directory
        file_under: if given, a config key; only dirs whose name contains
            the config value for that key are returned
        most_recent: if True, return only the most recent match
        **config_kws: dot-notation config keys that must match the saved
            config.yaml in each directory, e.g. llm__model='claude-haiku-4-5-20251001'
            (use __ for dots in key names)

    Returns:
        list of Path objects pointing to matching directories, sorted
        oldest-first (most_recent=True returns only the last one)
    """
    base = Path(config.require(basedir))
    if not base.is_dir():
        return []

    tag = config.get(file_under) if file_under else None

    # collect candidate directories (those with a config.yaml)
    candidates = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        cfg_file = entry / 'config.yaml'
        if not cfg_file.exists():
            continue
        # filter by tag if requested
        if tag and tag not in entry.name:
            continue
        # filter by config constraints
        if config_kws:
            saved_cfg = OmegaConf.load(cfg_file)
            match = True
            for kw_key, kw_val in config_kws.items():
                # convert __ to . for dot-notation lookup
                dot_key = kw_key.replace('__', '.')
                saved_val = OmegaConf.select(saved_cfg, dot_key)
                if saved_val != kw_val:
                    match = False
                    break
            if not match:
                continue
        candidates.append(entry)

    if most_recent and candidates:
        return [candidates[-1]]
    return candidates
