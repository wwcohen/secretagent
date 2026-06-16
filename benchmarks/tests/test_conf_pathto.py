"""Regression guard for the ${oc.env:PATHTO_REPO} conf migration.

Every source conf that opted into env-var path resolution must (a) no longer
reference the old ${pathto...} namespace and (b) resolve its path keys to
absolute locations under the repo root. Runs identically in any shell
(cmd / PowerShell / bash) via `uv run pytest`, replacing the manual,
shell-specific env-var checks.
"""

import glob
import os
from pathlib import Path

import pytest

from secretagent import config

BENCH = Path(__file__).resolve().parent.parent
_ALL = sorted(glob.glob(str(BENCH / "**" / "conf" / "**" / "*.yaml"), recursive=True))
ENV_CONFS = [
    f for f in _ALL
    if "${oc.env:PATHTO_REPO}" in Path(f).read_text(encoding="utf-8")
]


def _under(child: str, parent: str) -> bool:
    """True if `child` is `parent` or a path beneath it (sep/case-insensitive)."""
    c = os.path.normcase(os.path.normpath(child))
    p = os.path.normcase(os.path.normpath(parent))
    return c == p or c.startswith(p + os.sep)


def test_migration_happened():
    """Sanity: at least one source conf uses ${oc.env:PATHTO_REPO}."""
    assert ENV_CONFS, "no source conf references ${oc.env:PATHTO_REPO}"


@pytest.mark.parametrize(
    "conf", ENV_CONFS,
    ids=[str(Path(f).relative_to(BENCH)) for f in ENV_CONFS],
)
def test_conf_resolves_under_repo_root(conf):
    """No leftover ${pathto.repo}; path keys resolve to absolute paths under root."""
    assert "${pathto.repo}" not in Path(conf).read_text(encoding="utf-8"), \
        f"{conf} still references the deprecated ${{pathto.repo}} interpolation"
    config.reset()
    config.configure(yaml_file=conf)
    root = config.repo_root()
    for key in ("cachier.cache_dir", "evaluate.result_dir", "dataset.json_data_dir"):
        val = config.get(key)
        if val is None:
            continue
        s = str(val)
        assert "${" not in s, f"{conf}:{key} did not resolve -> {s}"
        assert _under(s, root), f"{conf}:{key} not under repo root -> {s}"