"""Ptool orchestrator: auto-generate pipelines from ptools + task descriptions.

Given a set of implemented ptools and a task description, the orchestrator
uses a powerful LLM to generate a Python workflow function that composes
the ptools into a pipeline. The generated code is compiled and bound to
an Interface via OrchestrateFactory.

Quick usage::

    from secretagent.orchestrate import PtoolCatalog, compose, build_pipeline

Or via config::

    ptools:
      my_workflow:
        method: orchestrate
        task_description: "Solve the problem by ..."
"""

from typing import Any

from secretagent import config
from secretagent.core import (
    Implementation, all_interfaces, register_factory,
)
from secretagent.orchestrate.catalog import PtoolCatalog, PtoolInfo
from secretagent.orchestrate.composer import compose, compose_with_retry
from secretagent.orchestrate.pipeline import (
    Pipeline, build_pipeline, _entry_signature_from_interface,
)

from secretagent.orchestrate.profiler import (  # noqa: E402
    PipelineProfile, PtoolProfile, profile_from_results,
)
from secretagent.orchestrate.improve import (  # noqa: E402
    improve_pipeline, ImprovementReport,
)

__all__ = [
    'PtoolCatalog', 'PtoolInfo',
    'compose', 'compose_with_retry',
    'Pipeline', 'build_pipeline',
    'OrchestrateFactory',
    'PipelineProfile', 'PtoolProfile', 'profile_from_results',
    'improve_pipeline', 'ImprovementReport',
]


class OrchestrateFactory(Implementation.Factory):
    """Generate a pipeline implementation using an LLM orchestrator.

    The factory collects all currently-implemented interfaces (excluding
    the target interface), sends their signatures to a powerful LLM along
    with a task description, and compiles the generated code into the
    implementation.

    Config keys:
        orchestrate.model: LLM model for composition (default: together_ai/Qwen/Qwen3.5-397B-A17B)
        orchestrate.max_retries: max retry attempts (default: 3)
        echo.orchestrate: print the generated pipeline code
    """

    pipeline: Any = None

    def setup(
        self,
        task_description: str | None = None,
        exclude: list[str] | None = None,
        test_case: dict | list | None = None,
        **kw,
    ):
        """Build a pipeline by having an LLM compose available ptools.

        Args:
            task_description: what the pipeline should accomplish;
                defaults to the interface's docstring
            exclude: additional interface names to exclude from the catalog
            test_case: if provided, used as a smoke test for retry logic.
                Should be a dict with 'input_args' (list) and optionally
                'expected_output', or just a list of positional args.
        """
        interface = self.bound_interface
        task_description = task_description or interface.doc

        # Build catalog from all implemented interfaces, excluding this one
        exclude_names = (exclude or []) + [interface.name]
        catalog = PtoolCatalog.from_interfaces(
            all_interfaces(), exclude=exclude_names
        )

        if not catalog.ptools:
            raise ValueError(
                f'No implemented ptools available for orchestration '
                f'(excluded: {exclude_names}). Make sure other ptools are '
                f'implemented before the orchestrated interface.'
            )

        entry_signature = _entry_signature_from_interface(interface)

        # Build the tool interfaces list for the Pipeline namespace
        tool_interfaces = [
            iface for iface in all_interfaces()
            if iface.name not in set(exclude_names)
            and iface.implementation is not None
        ]

        if test_case is not None:
            # Use compose_with_retry with smoke test
            test_args = (
                test_case.get('input_args', []) if isinstance(test_case, dict)
                else list(test_case)
            )

            def test_fn(code: str):
                p = build_pipeline(code, interface, tool_interfaces)
                p(*test_args)

            code, attempt = compose_with_retry(
                task_description, catalog, entry_signature,
                test_fn=test_fn, **kw,
            )
            if config.get('echo.orchestrate'):
                print(f'[orchestrate] pipeline generated on attempt {attempt}')
        else:
            code = compose(task_description, catalog, entry_signature, **kw)

        self.pipeline = build_pipeline(code, interface, tool_interfaces)

        if config.get('echo.orchestrate'):
            from secretagent.llm_util import echo_boxed
            echo_boxed(self.pipeline.source, 'orchestrated pipeline')

    def __call__(self, *args, **kw):
        return self.pipeline._fn(*args, **kw)


register_factory('orchestrate', OrchestrateFactory())

from secretagent.orchestrate import transforms  # noqa: F401, E402
