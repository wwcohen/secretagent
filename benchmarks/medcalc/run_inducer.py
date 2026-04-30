"""Thin wrapper around PtoolInducer that bypasses base.Learner.learn().

The base learn() method in secretagent.learn.base prints
len(self.dataset.cases) immediately after collect_distillation_data, but
PtoolInducer's override populates self._items (thoughts), not
self.dataset. This wrapper calls the pipeline methods directly so we
don't crash on that line.

Mirrors the CLI flags of `secretagent.cli.learn induce-ptools` for the
flags we actually need.

Example:
    uv run python run_inducer.py \\
      --interface calculate_medical_value \\
      --task-desc "Solve a medical-calculator question..." \\
      --max-ptools 5 --min-count 3 \\
      --learned-dir learned \\
      results/*.react_train
"""

from pathlib import Path
from typing import Optional, List

import typer

from secretagent.learn.ptool_inducer import PtoolInducer

app = typer.Typer(no_args_is_help=True)


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": True})
def main(
    ctx: typer.Context,
    interface: str = typer.Option(..., help='Top-level interface name'),
    task_desc: str = typer.Option(..., help='Natural-language task description'),
    trace_mode: str = typer.Option('react', help="'react' or 'cot'"),
    state_module: Optional[str] = typer.Option(None, help='Module to import state from'),
    state_expr: Optional[str] = typer.Option(None, help='State expression at call time'),
    only_correct: bool = typer.Option(False, help='Only use correct rollouts'),
    max_ptools: int = typer.Option(5, help='Max ptools to synthesize'),
    min_count: int = typer.Option(3, help='Min category count'),
    model: Optional[str] = typer.Option(None, help='LLM model'),
    latest: int = typer.Option(1, help='Keep latest k dirs per tag'),
    check: Optional[List[str]] = typer.Option(None, help='Config filter'),
    learned_dir: str = typer.Option('learned', help='Where to store learned ptools'),
):
    learner = PtoolInducer(
        interface_name=interface,
        train_dir=learned_dir,
        task_desc=task_desc,
        trace_mode=trace_mode,
        state_module=state_module,
        state_expr=state_expr,
        only_correct=only_correct,
        max_ptools=max_ptools,
        min_count=min_count,
        model=model,
    )
    dirs = [Path(a) for a in ctx.args]
    learner.collect_distillation_data(dirs, latest=latest, check=check)
    print(f'collected {len(learner._items)} thoughts in {learner.out_dir}')
    learner.fit()
    output_file = learner.save_implementation()
    print(learner.report())
    print(f'saved output to {output_file}')


if __name__ == '__main__':
    app()
