"""Utilities for creating and finding experiment output files.

Experiment files are organized as:

    {basedir}/{timestamp}.{file_under}/{name}

where basedir and file_under are looked up from config keys, and a
snapshot of the global configuration is saved in the directory
alongside the output files.
"""

import datetime
import os
import warnings
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from omegaconf import OmegaConf

from secretagent import config

DEFAULT_TAG = '_untagged_'

def filename_list(basedir: str | Path,  names: list[str], file_under: str = DEFAULT_TAG) -> list[Path]:
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


def filename(basedir: str | Path, name: str, file_under: str = DEFAULT_TAG) -> Path:
    """Create a timestamped directory and return a path for a single file.

    Convenience wrapper around filename_list.
    """
    return filename_list(basedir, [name], file_under=file_under)[0]


def file_under_part(p: Path) -> str:
    """Extract the file_under tag from a directory name.

    Directory names have the format '{YYYYMMDD}.{HHMMSS}.{file_under}',
    so the tag is everything after the second dot.
    """
    parts = p.name.split('.', 2)
    return parts[2] if len(parts) > 2 else ''


def filter_paths(paths: Sequence[str | Path], latest: int = 0, dotlist: list[str] = []) -> list[Path]:
    """Filter experiment directory paths.

    Args:
        paths: list of Path objects to filter (should be directories
            containing config.yaml to be included)
        latest: if > 0, keep only the latest k directories
            per file_under tag (sorted newest-first by name)
        dotlist: config constraints like ["llm.model=gpt3.5"];
            only directories whose config.yaml matches all
            constraints are returned

    Returns:
        list of matching Path objects, sorted newest-first
    """
    def _normalize(file_or_dir: str | Path) -> Path:
        p = Path(file_or_dir)
        return p.parent if p.is_file() else p
    norm_paths: list[Path] = [_normalize(p) for p in paths]
    # normalize the dotlist
    constraints = set(config.to_dotlist(OmegaConf.from_dotlist(dotlist)))
    by_tag = defaultdict(list)
    # go through paths most recent first, skipping dirs without config.yaml
    for p in sorted(norm_paths, reverse=True):
        if not (p / 'config.yaml').exists():
            warnings.warn(f'No config.yaml in {p}, skipping')
            continue
        cfg_for_p = config.load_yaml_cfg(p / 'config.yaml')
        active = set(config.to_dotlist(cfg_for_p))
        config.sanity_check('filter_paths', constraints, cfg_for_p)
        if constraints <= active:
            by_tag[file_under_part(p)].append(p)

    candidates = []
    for tag in sorted(by_tag):
        limit = latest or len(by_tag[tag])
        candidates.extend(by_tag[tag][:limit])
    return candidates
