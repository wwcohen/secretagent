"""Generated staging ptools for MuSR murder induced seed orchestration."""

from pathlib import Path

from ptools_murder import *  # noqa: F401,F403


def _load_induced(relative_path: str) -> None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "src/secretagent/learn/inducer_results").exists():
            path = parent / "src/secretagent/learn/inducer_results" / relative_path
            break
    else:
        raise RuntimeError("Could not locate repo root for induced ptools")

    source = path.read_text()
    source = source.replace(
        "from ptools.ptools_common import _REACT_STATE",
        "_REACT_STATE = {}",
    )
    exec(compile(source, str(path), "exec"), globals())


_load_induced("musr/induced_ptools_seed42_correct_murder.py")
