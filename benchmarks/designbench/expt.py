"""DesignBench benchmark experiment.

Example CLI commands:

    # run with default config
    uv run python benchmarks/designbench/expt.py run --config-file conf/conf.yaml

    # run first 10 examples
    uv run python benchmarks/designbench/expt.py run --config-file conf/conf.yaml dataset.n=10

    # change model
    uv run python benchmarks/designbench/expt.py run --config-file conf/conf.yaml llm.model=gpt-4o-mini

    # skip visual evaluation (generation only)
    uv run python benchmarks/designbench/expt.py run --config-file conf/conf.yaml benchmark.skip_eval=true

    # Rerun only prior failures (non-empty error/eval_error or render_failed); use a new expt_name.
    # Use the real directory from the prior run (printed as ``saved in .../results.csv``), e.g.
    # ``results/20260501.153000.my_expt/results.csv`` under this benchmark, not a placeholder name.
    uv run python benchmarks/designbench/expt.py run --config-file conf/react_gemini_echo_all_ptools.yaml \\
      dataset.framework=vanilla \\
      dataset.rerun_from_csv=results/20260501.153000.my_expt/results.csv \\
      evaluate.expt_name=my_expt_retry_failed

    # Fixed pipeline: ``propose_code`` once, then up to ``benchmark.refine_rounds`` ×
    # (``render_generated_image`` + ``fix_code_from_rendered_and_reference``); see
    # ``ptools.propose_then_refine_loop`` (early exit on ``REFINE_DONE`` / unchanged code).
    uv run python benchmarks/designbench/expt.py run --config-file conf/refine_loop_gemini.yaml dataset.n=2

    # Refine loop on vanilla / react / vue only (no angular); run from ``benchmarks/designbench/``:
    # for fw in vanilla react vue; do
    #   uv run python expt.py run --config-file conf/refine_loop_gemini.yaml \\
    #     dataset.framework=$fw evaluate.expt_name=refine_loop_gemini_${fw}
    # done
"""

import json
import sys
import base64
import signal
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
import typer
from tqdm import tqdm

# Allow running from any directory: add project src/ and this benchmark dir to path
_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config, savefile, record
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator
import secretagent.implement.vlm

import ptools
from eval_util import render_to_screenshot, evaluate_visual

FRAMEWORK_TO_EXT = {
    'vanilla': 'html',
    'react': 'jsx',
    'vue': 'vue',
    'angular': 'html',
}


@contextmanager
def _deadline_timeout(seconds: float | None):
    """Raise TimeoutError if a block exceeds the deadline."""
    if not seconds or seconds <= 0:
        yield
        return
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def _raise_timeout(_signum, _frame):
        raise TimeoutError(f'Case timed out after {seconds:.1f}s')

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _configure_designbench_imports() -> None:
    """Add DesignBench evaluator package to sys.path."""
    cfg_root = config.get('designbench.root')
    if cfg_root:
        root = Path(cfg_root)
    else:
        # Default: sibling repository at ../DesignBench relative to secretagent root
        root = _PROJECT_ROOT.parent / 'DesignBench'

    evaluator_dir = root / 'code' / 'evaluator'
    code_dir = root / 'code'
    sys.path.insert(0, str(evaluator_dir))
    sys.path.insert(0, str(code_dir))


def get_designbench_generation_prompt_text(framework: str) -> str | None:
    """Return DesignBench ``get_design_generation_prompt`` text, or ``None`` if unavailable."""
    try:
        from prompt.generation_prompt import get_design_generation_prompt  # type: ignore
        from utils import Framework  # type: ignore
    except ImportError:
        return None
    text, _ = get_design_generation_prompt(Framework(framework))
    return text


def _set_designbench_generate_code_doc(framework: str) -> None:
    """Set ``generate_code`` and ``propose_code`` docs from the sibling DesignBench repo.

    Uses ``prompt.generation_prompt.get_design_generation_prompt`` so React / Vue / etc.
    instructions match the official DesignBench evaluator (not the vanilla-only stubs in ``ptools.py``).
    """
    text = get_designbench_generation_prompt_text(framework)
    if text is None:
        return
    ptools.generate_code.doc = text
    ptools.propose_code.doc = text


def _encode_image_base64(path: Path) -> str:
    """Encode an image file for multimodal model input."""
    return base64.b64encode(path.read_bytes()).decode('ascii')


def _find_dataset_reference_image(item_dir: Path, item_id: str) -> Path | None:
    """Find an existing reference image shipped with DesignBench data."""
    candidates = [
        item_dir / f'{item_id}.png',
        item_dir / f'{item_id}_p.png',
        item_dir / f'{item_id}.jpg',
        item_dir / f'{item_id}.jpeg',
        item_dir / f'{item_id}.webp',
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_dataset(
    framework: str,
    code_framework: str | None = None,
    *,
    generation_root: Path | None = None,
) -> Dataset:
    """Load DesignBench generation data for one framework.

    ``framework`` selects which split directory to read. ``code_framework``,
    if set, is passed as ``framework`` into ``generate_code`` / ``propose_code``
    (target syntax); when omitted it defaults to the split name.

    ``generation_root``, if set, must be the parent of per-framework folders
    (i.e. ``generation_root / framework / <item_id>/``). Defaults to
    ``<designbench>/data/generation``.

    **Model input:** ``generate_code(framework, reference_screenshot=\"\")`` with
    pixels only in ``input_kw['images']['reference_screenshot']`` (base64).
    Golden HTML is never passed to the model (HTML files on disk are for eval /
    bookkeeping only). Items without a reference image next to the HTML are skipped.
    """
    base = generation_root if generation_root is not None else _BENCHMARK_DIR / 'data' / 'generation'
    data_root = Path(base) / framework
    if not data_root.exists():
        raise FileNotFoundError(f'Framework directory not found: {data_root}')

    cases: list[Case] = []
    for item_dir in sorted(
        data_root.iterdir(),
        key=lambda p: (0, int(p.name)) if p.name.isdigit() else (1, p.name),
    ):
        if not item_dir.is_dir():
            continue

        item_id = item_dir.name
        html_path = item_dir / f'{item_id}.html'
        meta_path = item_dir / f'{item_id}.json'
        if not html_path.exists() or not meta_path.exists():
            continue

        with open(meta_path) as f:
            json.load(f)  # require valid sidecar JSON; contents not passed to ``generate_code``

        reference_image = _find_dataset_reference_image(item_dir, item_id)
        if reference_image is None:
            continue

        encoded_image = _encode_image_base64(reference_image)
        expected = {
            'id': item_id,
            'framework': framework,
            'reference_html_path': str(html_path),
            'reference_image_path': str(reference_image),
        }
        input_kw = {'images': {'reference_screenshot': encoded_image}}
        gen_fw = code_framework if code_framework else framework
        cases.append(Case(
            name=f'{framework}.{item_id}',
            input_args=(gen_fw, ''),
            input_kw=input_kw,
            expected_output=expected,
        ))

    if not cases:
        raise FileNotFoundError(
            f'No generation cases with a reference image under {data_root} '
            '(expected a .png / .jpg / .webp next to each item HTML).'
        )

    return Dataset(name='designbench', split=framework, cases=cases)


def _results_row_failed(row: pd.Series) -> bool:
    for col in ('error', 'eval_error'):
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            return True
    if 'render_failed' in row.index and pd.notna(row['render_failed']):
        v = row['render_failed']
        if v is True or str(v).strip().lower() in ('true', '1', 'yes'):
            return True
    return False


def _failed_case_names_from_results_csv(csv_path: Path) -> set[str]:
    """Collect ``case_name`` values for rows that look failed in a prior ``results.csv``."""
    df = pd.read_csv(csv_path)
    if df.empty:
        return set()
    if 'case_name' not in df.columns:
        if df.index.name == 'case_name':
            df = df.reset_index()
        else:
            first = df.columns[0]
            df = df.rename(columns={first: 'case_name'})
    out: set[str] = set()
    for _, row in df.iterrows():
        if not _results_row_failed(row):
            continue
        cn = row.get('case_name')
        if cn is None or (isinstance(cn, float) and pd.isna(cn)):
            continue
        out.add(str(cn).strip())
    return out


def _resolve_prior_results_csv(
    user_path: str,
    benchmark_dir: Path,
) -> tuple[list[Path], Path | None]:
    """Resolve ``dataset.rerun_from_csv`` relative to the benchmark dir or to ``benchmarks/``."""
    raw = Path(user_path.strip()).expanduser()
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw.resolve())
    else:
        candidates.append((benchmark_dir / raw).resolve())
        alt = (benchmark_dir.parent / raw).resolve()
        if alt not in candidates:
            candidates.append(alt)
    for c in candidates:
        if c.exists():
            return candidates, c
    return candidates, None


def _subset_dataset_to_failed_rerun(dataset: Dataset, prior_csv: Path) -> None:
    failed = _failed_case_names_from_results_csv(prior_csv)
    before = len(dataset.cases)
    dataset.cases = [c for c in dataset.cases if c.name in failed]
    after = len(dataset.cases)
    print(
        f'[designbench] rerun_from_csv={prior_csv} failed_rows={len(failed)} '
        f'matched_cases={after}/{before}',
        flush=True,
    )


class DesignBenchEvaluator(Evaluator):
    """Evaluator for DesignBench visual similarity."""

    def __init__(self, output_framework: str, skip_eval: bool):
        self.output_framework = output_framework
        self.skip_eval = skip_eval
        self.artifacts_dir: Path | None = None
        self.visual_eval_enabled = not skip_eval
        self.visual_eval_skip_reason: str | None = None

    def _log(self, stage: str, case_name: str, detail: str = '') -> None:
        detail_text = f' | {detail}' if detail else ''
        print(f'[designbench] {stage} | {case_name}{detail_text}', flush=True)

    def compare_predictions(self, predicted_output: Any, expected_output: Any) -> dict[str, Any]:
        if self.artifacts_dir is None:
            raise RuntimeError('Evaluator artifacts_dir not initialized')

        item_id = str(expected_output['id'])
        case_name = str(expected_output.get('case_name') or item_id)
        framework = str(expected_output['framework'])
        reference_image_path = expected_output.get('reference_image_path')
        ext = FRAMEWORK_TO_EXT.get(self.output_framework, FRAMEWORK_TO_EXT.get(framework, 'html'))

        code_path = self.artifacts_dir / f'{item_id}.{ext}'
        raw_path = self.artifacts_dir / f'{item_id}_raw.txt'
        generated_png = self.artifacts_dir / f'{item_id}_generated.png'
        metrics_path = self.artifacts_dir / f'{item_id}_metrics.json'

        raw_text = str(predicted_output)
        raw_path.write_text(raw_text, encoding='utf-8')
        if raw_text.startswith('**exception raised**'):
            self._log('model_error', case_name, raw_text)
            result = {
                'error': raw_text,
                'code_path': str(code_path),
                'raw_path': str(raw_path),
            }
            metrics_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
            return result

        # Model outputs may be fenced markdown (e.g. ```html ... ```).
        # Strip fences so the renderer sees only source code.
        code_text = ptools.extract_code(raw_text, self.output_framework)
        code_path.write_text(code_text, encoding='utf-8')
        reference_png = Path(reference_image_path) if reference_image_path else None
        result: dict[str, Any] = {
            'code_path': str(code_path),
            'raw_path': str(raw_path),
            'reference_screenshot': str(reference_png) if reference_png else None,
            'generated_screenshot': str(generated_png),
        }

        if not self.visual_eval_enabled:
            self._log('eval_skipped', case_name, self.visual_eval_skip_reason or 'skip_eval=true')
            result['eval_skipped'] = True
            if self.visual_eval_skip_reason:
                result['eval_skip_reason'] = self.visual_eval_skip_reason
            metrics_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
            return result

        try:
            if reference_png is None or not reference_png.exists():
                result['render_failed'] = True
                result['eval_error'] = 'missing reference_image_path for visual comparison'
                self._log('eval_error', case_name, result['eval_error'])
                metrics_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
                return result

            self._log('render_start', case_name, f'framework={self.output_framework}')
            rendered = render_to_screenshot(
                code_path=str(code_path),
                save_path=str(generated_png),
                framework=self.output_framework,
            )
            self._log('render_done', case_name, f'rendered={rendered}')
            if rendered and generated_png.exists():
                self._log('visual_eval_start', case_name)
                result.update(evaluate_visual(str(reference_png), str(generated_png)))
                clip = result.get('clip_similarity')
                self._log('visual_eval_done', case_name, f'clip_similarity={clip}')
            else:
                result['render_failed'] = True
                self._log('render_failed', case_name)
        except ImportError as ex:
            # Disable visual eval after first dependency failure.
            self.visual_eval_enabled = False
            self.visual_eval_skip_reason = f'{type(ex).__name__}: {ex}'
            result['eval_skipped'] = True
            result['eval_skip_reason'] = self.visual_eval_skip_reason
            self._log('eval_skipped', case_name, self.visual_eval_skip_reason)
        except Exception as ex:
            result['eval_error'] = f'{type(ex).__name__}: {ex}'
            self._log('eval_error', case_name, result['eval_error'])

        metrics_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        return result

    def measure(self, example: Case, interface) -> dict[str, Any]:
        """Measure one case, forwarding args and kwargs from Dataset.Case."""
        input_args = tuple(example.input_args or ())
        input_kw = dict(example.input_kw or {})
        self._log('case_start', example.name)
        model_start = time.time()
        case_timeout_seconds = float(config.get('benchmark.case_timeout_seconds', 180) or 180)
        with record.recorder() as records:
            try:
                with _deadline_timeout(case_timeout_seconds):
                    predicted_output = interface(*input_args, **input_kw)
            except Exception as ex:
                predicted_output = f'**exception raised**: {ex}'
        self._log('model_done', example.name, f'seconds={time.time() - model_start:.2f}')
        llm_usage_stats = self.aggregate_usage_stats(records)
        expected_output = dict(example.expected_output or {})
        expected_output['case_name'] = example.name
        eval_start = time.time()
        metrics = self.compare_predictions(predicted_output, expected_output)
        self._log('case_done', example.name, f'eval_seconds={time.time() - eval_start:.2f}')
        return dict(
            predicted_output=predicted_output,
            expected_output=expected_output,
            **metrics,
            **llm_usage_stats,
        )

    def evaluate(self, dataset: Dataset, interface) -> Path:
        expt_name = config.get('evaluate.expt_name')
        result_dir = config.require('evaluate.result_dir')
        csv_path, jsonl_path = savefile.filename_list(
            result_dir, ['results.csv', 'results.jsonl'], file_under=expt_name)
        self.artifacts_dir = csv_path.parent / 'artifacts'
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        results = []
        with open(jsonl_path, 'w') as fp:
            for row in tqdm(self.measurements(dataset, interface)):
                row.update(expt_name=expt_name)
                fp.write(json.dumps(row) + '\n')
                csv_row = dict(row)
                if 'predicted_output' in csv_row:
                    csv_row['predicted_output_path'] = csv_row.get('code_path')
                    del csv_row['predicted_output']
                results.append(csv_row)

        df = pd.DataFrame(results).set_index('case_name')
        df.to_csv(csv_path)
        print(f'saved in {csv_path}')
        return csv_path


app = typer.Typer()


@app.callback()
def callback():
    """DesignBench benchmark."""


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def run(
    ctx: typer.Context,
    config_file: str = typer.Option(..., help="Config YAML file"),
):
    """Run DesignBench evaluation. Extra args are config overrides in dot notation."""
    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path

    config.configure(yaml_file=str(cfg_path), dotlist=ctx.args)
    config.set_root(_BENCHMARK_DIR)
    _configure_designbench_imports()

    framework = config.require('dataset.framework')
    output_framework = config.get('benchmark.output_framework') or framework
    _set_designbench_generate_code_doc(output_framework)
    implement_via_config(ptools, config.require('ptools'))
    dataset = load_dataset(
        framework=framework,
        code_framework=config.get('benchmark.code_framework'),
    )
    dataset = dataset.configure(
        n=config.get('dataset.n'),
    )
    rerun_csv = config.get('dataset.rerun_from_csv')
    if rerun_csv:
        tried, rp = _resolve_prior_results_csv(str(rerun_csv), _BENCHMARK_DIR)
        if rp is None:
            result_dir = Path(config.require('evaluate.result_dir'))
            tried_s = ', '.join(str(p) for p in tried)
            raise FileNotFoundError(
                'dataset.rerun_from_csv: file not found.\n'
                f'  Tried: {tried_s}\n'
                '  Use the actual run folder name from your prior experiment (the path printed as '
                '"saved in .../results.csv"), not a placeholder like PRIOR_RUN.\n'
                f'  Typical layout: {result_dir}/<timestamp>.<evaluate.expt_name>/results.csv'
            )
        _subset_dataset_to_failed_rerun(dataset, rp)
        if not dataset.cases:
            print(
                '[designbench] No cases to rerun (no failed rows matched dataset case names).',
                flush=True,
            )
            return

    print('dataset:', dataset.summary())
    entry_point = config.require('evaluate.entry_point')
    interface = getattr(ptools, entry_point)

    evaluator = DesignBenchEvaluator(
        output_framework=output_framework,
        skip_eval=bool(config.get('benchmark.skip_eval')),
    )
    csv_path = evaluator.evaluate(dataset, interface)

    df = pd.read_csv(csv_path)
    if 'clip_similarity' in df.columns:
        scored = df['clip_similarity'].notna()
        n_scored = int(scored.sum())
        if n_scored > 0:
            print(f"Avg CLIP: {df.loc[scored, 'clip_similarity'].mean():.4f}")
            for _, row in df.loc[scored, ['case_name', 'clip_similarity']].iterrows():
                print(f"CLIP {row['case_name']}: {float(row['clip_similarity']):.4f}")
            print(f"Evaluated: {n_scored}/{len(df)}")
        else:
            print('CLIP unavailable: no scored rows in results.')
    else:
        print('CLIP unavailable: clip_similarity missing from results.')
    if 'eval_error' in df.columns:
        errors = [e for e in df['eval_error'].dropna().unique() if str(e).strip()]
        for err in errors:
            print(f"eval_error: {err}")


if __name__ == '__main__':
    app()
