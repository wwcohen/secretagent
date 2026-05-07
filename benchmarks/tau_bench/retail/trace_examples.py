"""Run a few tasks and save full conversation traces to traces/.

Usage (from project root):
    uv run python benchmarks/tau_bench_retail/trace_examples.py --config-file conf/ptp.yaml
    uv run python benchmarks/tau_bench_retail/trace_examples.py --config-file conf/react.yaml
    uv run python benchmarks/tau_bench_retail/trace_examples.py --config-file conf/ptp.yaml --n 3 --tasks 5 12 70
"""

import json
import sys
from pathlib import Path

import typer

_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config, record
from secretagent.core import implement_via_config

import ptools
from tau_env import TauEnv
from expt import _setup, load_dataset

app = typer.Typer()


def _print_annotated_trace(task_id: str, records: list, reward: str, task) -> None:
    """Print full turn-by-turn trace with tool calls visible."""
    inst = task.user_scenario.instructions if task.user_scenario else None
    if inst:
        print(f"Request: {inst.reason_for_call}")
        print(f"Known:   {inst.known_info}")

    turn = 0
    for rec in records:
        fn = rec.get("func", "")
        cost = rec.get("stats", {}).get("cost", 0)

        if fn in ("retail_agent", "retail_agent_ptp"):
            turn += 1
            print(f"\n{'─'*60}")
            print(f"AGENT TURN {turn}  [{fn}]  cost=${cost:.4f}")
            print(f"{'─'*60}")

            # Print prompt (llm_input equivalent)
            args = rec.get("args", ())
            if args:
                conv_lines = str(args[0]).split("\n")
                last_customer = next(
                    (l for l in reversed(conv_lines) if l.startswith("Customer:")), "")
                print(f"\nINPUT (last customer msg):\n  {last_customer}")

            # Print pydantic-ai internal steps (tool calls + returns)
            step_info = rec.get("step_info", [])
            if step_info:
                print(f"\nINTERNAL STEPS ({len(step_info)} steps):")
                for s in step_info:
                    if "thought" in s:
                        thought = s["thought"][:120].replace("\n", " ")
                        print(f"  [think] {thought}...")
                    elif "tool_call" in s:
                        args_str = str(s.get("args", {}))[:100]
                        print(f"  [call ] {s['tool_call']}({args_str})")
                    elif "tool_return" in s:
                        out = str(s.get("output", ""))[:120].replace("\n", " ")
                        print(f"  [ret  ] {s['tool_return']} → {out}")

            # Print final output
            output = rec.get("output", "")
            print(f"\nOUTPUT:\n  {output[:300]}")

        elif fn == "user_simulator":
            output = rec.get("output", "")
            cost = rec.get("stats", {}).get("cost", 0)
            print(f"\nUSER SIM  cost=${cost:.4f}")
            print(f"  {output[:200]}")

    print(f"\n{'='*60}")
    print(f"FINAL REWARD: {reward}")
    print(f"{'='*60}\n")


def _render_trace(task_id: str, records: list, reward: str, task) -> str:
    """Render a full conversation trace as markdown."""
    lines = []

    # Header
    inst = task.user_scenario.instructions if task.user_scenario else None
    lines.append(f"# Task {task_id}")
    if inst:
        lines.append(f"**Request:** {inst.reason_for_call}")
        if inst.known_info:
            lines.append(f"**Known:** {inst.known_info}")
        if inst.unknown_info:
            lines.append(f"**Unknown:** {inst.unknown_info}")
    reward_basis = task.evaluation_criteria.reward_basis if task.evaluation_criteria else []
    lines.append(f"**Reward basis:** {reward_basis}")
    lines.append(f"**Final reward:** {reward}")
    lines.append("")

    # Walk records to reconstruct turns
    turn = 0
    for rec in records:
        fn = rec.get("func", "")
        cost = rec.get("stats", {}).get("cost", 0)

        if fn in ("retail_agent", "retail_agent_ptp"):
            turn += 1
            lines.append(f"---\n## Agent Turn {turn}  (cost ${cost:.4f})")

            # Show conversation input (abbreviated)
            args = rec.get("args", ())
            if args:
                conv = str(args[0])
                # Show last customer message only to keep it readable
                last_customer = ""
                for line in conv.split("\n"):
                    if line.startswith("Customer:"):
                        last_customer = line
                if last_customer:
                    lines.append(f"\n**Customer said:** {last_customer[len('Customer:'):].strip()}")

            # Tool calls from step_info
            step_info = rec.get("step_info", [])
            tool_calls = [(s["tool_call"], s["args"]) for s in step_info if "tool_call" in s]
            tool_returns = {s["tool_return"]: s["output"] for s in step_info if "tool_return" in s}

            if tool_calls:
                lines.append("\n**Tool calls:**")
                for name, args_dict in tool_calls:
                    # Truncate long outputs
                    ret = tool_returns.get(name, "")
                    ret_short = ret[:200].replace("\n", " ") + ("..." if len(ret) > 200 else "")
                    lines.append(f"- `{name}({_fmt_args(args_dict)})` → `{ret_short}`")

            # Agent response
            output = rec.get("output", "")
            lines.append(f"\n**Agent response:**\n> {output}")

        elif fn == "user_simulator":
            cost = rec.get("stats", {}).get("cost", 0)
            output = rec.get("output", "")
            lines.append(f"\n**Customer:** {output}  *(sim cost ${cost:.4f})*")

    lines.append("\n---")
    return "\n".join(lines)


def _fmt_args(args_dict) -> str:
    if not isinstance(args_dict, dict):
        return str(args_dict)[:80]
    parts = []
    for k, v in args_dict.items():
        v_str = repr(v)
        if len(v_str) > 40:
            v_str = v_str[:40] + "..."
        parts.append(f"{k}={v_str}")
    return ", ".join(parts)


@app.command()
def run(
    config_file: str = typer.Option(..., help="Config YAML file"),
    n: int = typer.Option(2, help="Number of tasks to trace"),
    tasks: list[str] = typer.Option(None, help="Specific task IDs to trace"),
):
    """Run N tasks and save conversation traces to traces/."""
    dataset = _setup(config_file, [f"dataset.n={n}"])

    # Override with specific task ids if provided
    if tasks:
        cases = [c for c in dataset.cases if c.name in tasks]
    else:
        cases = dataset.cases[:n]

    # Determine experiment name from config
    expt_name = config.get("evaluate.expt_name", "trace")
    traces_dir = _BENCHMARK_DIR / "traces"
    traces_dir.mkdir(exist_ok=True)
    out_path = traces_dir / f"{expt_name}.md"

    all_traces = []
    all_traces.append(f"# Conversation Traces — {expt_name}\n")
    all_traces.append(f"Config: `{config_file}`  |  Tasks: {[c.name for c in cases]}\n\n")

    for case in cases:
        task_id = case.input_args[0]
        task = ptools._CURRENT_ENV.get_task(task_id)

        print(f"Running task {task_id}...")
        print(f"\n{'='*60} TASK {task_id} {'='*60}\n")

        with config.configuration(cachier={"enable_caching": False}):
            with record.recorder() as records:
                try:
                    reward = ptools.tau_solve(task_id)
                except Exception as e:
                    reward = f"ERROR: {e}"

        # Print annotated trace to stdout
        _print_annotated_trace(task_id, records, reward, task)

        trace_md = _render_trace(task_id, records, reward, task)
        all_traces.append(trace_md)
        all_traces.append("\n\n")
        print(f"\n  >>> reward={reward}, steps={len(records)}")

    out_path.write_text("\n".join(all_traces))
    print(f"\nTraces saved to {out_path}")


if __name__ == "__main__":
    app()
