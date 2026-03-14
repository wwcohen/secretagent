"""Utilities for creating and finding experiment output files.

Experiment files are organized as:

    {basedir}/{timestamp}.{file_under}/{name}

where basedir and file_under are looked up from config keys, and a
snapshot of the global configuration is saved in the directory
alongside the output files.
"""

import datetime
import os
from pathlib import Path

from omegaconf import OmegaConf

from secretagent import config

DEFAULT_TAG = '_untagged_'

def filename_list(basedir: str,  names: list[str], file_under: str = DEFAULT_TAG) -> list[Path]:
    """Create a timestamped directory and return paths for each name.

    Args:
        basedir: the base directory, usually specified as a config, eg config.get('evaluate.result_dir')
        names: list of filenames to create paths for, e.g. ['results.csv', 'results.jsonl']
        file_under: optional string used as a tag in the directory name
    """
    basedir = Path(basedir)
    timestamp = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
    dirname = basedir / f'{timestamp}.{file_under}'
    os.makedirs(dirname, exist_ok=True)
    config.save(dirname / 'config.yaml')
    return [dirname / name for name in names]


def filename(basedir: str, name: str, file_under: str = DEFAULT_TAG) -> Path:
    """Create a timestamped directory and return a path for a single file.

    Convenience wrapper around filename_list.
    """
    return filename_list(basedir, [name], file_under=file_under)[0]


def getfiles(
        basedir: str | Path,
        file_under: str = None,
        most_recent: bool = True,
        dotlist: list[str] = []
) -> list[Path]:
    """Find experiment directories matching constraints.

    Args:
        basedir: the base directory to scan
        file_under: if given, only dirs whose name contains 
         this string are returned
        most_recent: if True, return only the most recent match
        dotlist: a list of strings like "llm.model=gpt3.5",
          constraining the configs of any files returned

    Returns:
        list of Path objects pointing to matching directories, sorted
        newest-first (most_recent=True returns only the first one)

    """
    basedir = Path(basedir)
    if not basedir.is_dir():
        raise ValueError(f'basedir {basedir} is not a directory')

    # collect candidate directories (those with a config.yaml)
    candidates = []
    for entry in sorted(basedir.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        cfg_file = entry / 'config.yaml'
        if not cfg_file.exists():
            continue
        # filter by file_under if requested
        if file_under and file_under not in entry.name:
            continue
        # filter by config constraints
        if dotlist:
            saved_cfg = OmegaConf.load(cfg_file)
            constraints = [pair.split('=') for pair in dotlist]
            match = all(OmegaConf.select(saved_cfg, dot_key)==dot_val
                        for dot_key, dot_val in constraints)
            if not match:
                continue
        candidates.append(entry)

    if most_recent and candidates:
        return [candidates[0]]
    return candidates
