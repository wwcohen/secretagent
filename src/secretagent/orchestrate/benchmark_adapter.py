"""Uniform adapter over per-benchmark dataset loading and evaluator differences.

Used by the orchestration learner to run across all benchmarks via a
``--benchmark`` flag, driven by the central ``benchmarks.yaml`` config.
"""

from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path
from typing import Any

import yaml

from secretagent.dataset import Dataset
from secretagent.evaluate import Evaluator, ExactMatchEvaluator

_YAML_PATH = Path(__file__).parent / 'benchmarks.yaml'
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # secretagent repo root


def _load_registry() -> dict[str, Any]:
    """Load the benchmarks.yaml registry."""
    with open(_YAML_PATH) as f:
        return yaml.safe_load(f)


def _import_module_from_file(name: str, path: Path):
    """Import a Python file as a uniquely-named module."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class BenchmarkAdapter:
    """Uniform interface over per-benchmark load_dataset/evaluator differences.

    Usage::

        adapter = BenchmarkAdapter('sports_understanding')
        adapter.setup_sys_path()
        ptools = adapter.load_ptools_module()
        evaluator = adapter.get_evaluator()
        train_ds, eval_ds = adapter.load_train_eval()
    """

    def __init__(self, name: str, overrides: dict | None = None):
        registry = _load_registry()
        defaults = registry.get('defaults', {})
        benchmarks = registry.get('benchmarks', {})

        if name not in benchmarks:
            available = sorted(benchmarks.keys())
            raise KeyError(
                f'Unknown benchmark: {name!r}. '
                f'Available: {available}'
            )

        self.name = name
        self.spec: dict[str, Any] = {**benchmarks[name]}

        # Merge defaults for keys not explicitly set
        for key, val in defaults.items():
            self.spec.setdefault(key, val)

        # Apply CLI overrides
        if overrides:
            for key, val in overrides.items():
                if val is not None:
                    self.spec[key] = val

    # -- Properties ----------------------------------------------------------

    @property
    def benchmark_dir(self) -> Path:
        return _PROJECT_ROOT / 'benchmarks' / self.spec['directory']

    @property
    def config_file(self) -> Path:
        return self.benchmark_dir / self.spec['config_file']

    @property
    def entry_point_name(self) -> str:
        return self.spec['entry_point']

    @property
    def shuffle_seed(self) -> int:
        return self.spec.get('shuffle_seed', 42)

    # -- Path setup ----------------------------------------------------------

    def setup_sys_path(self):
        """Add benchmark dir and project src/ to sys.path."""
        bdir = str(self.benchmark_dir)
        src_dir = str(_PROJECT_ROOT / 'src')
        if bdir not in sys.path:
            sys.path.insert(0, bdir)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

    # -- Ptools module -------------------------------------------------------

    def load_ptools_module(self, evolved: bool = True):
        """Load the benchmark's ptools module.

        If *evolved* is True (default), looks for ``{ptools_module}_evolved.py``
        first and falls back to ``{ptools_module}.py``.  The module is
        registered as both its own name and ``'ptools'`` in ``sys.modules``
        so existing code that does ``import ptools`` works.

        Returns the module object.
        """
        mod_name = self.spec['ptools_module']
        base_path = self.benchmark_dir / f'{mod_name}.py'
        evolved_path = self.benchmark_dir / f'{mod_name}_evolved.py'

        if evolved and evolved_path.exists():
            load_path = evolved_path
        else:
            load_path = base_path

        if not load_path.exists():
            raise FileNotFoundError(f'ptools file not found: {load_path}')

        # Create evolved copy if it doesn't exist
        if evolved and not evolved_path.exists():
            import shutil
            shutil.copy2(base_path, evolved_path)
            load_path = evolved_path
            print(f'Created {evolved_path.name} from {base_path.name}')

        mod = _import_module_from_file(mod_name, load_path)
        # Also register as 'ptools' so `import ptools` works
        sys.modules['ptools'] = mod
        return mod

    # -- Evaluator -----------------------------------------------------------

    def get_evaluator(self) -> Evaluator:
        """Instantiate the right evaluator class for this benchmark."""
        eval_name = self.spec.get('evaluator')
        if eval_name is None:
            return ExactMatchEvaluator()

        # Determine which module contains the evaluator
        eval_module_name = self.spec.get('evaluator_module')
        if eval_module_name:
            # Evaluator lives in a non-expt module (e.g. ptools.py for penguins).
            # Check sys.modules first — load_ptools_module() may have loaded it.
            if eval_module_name in sys.modules:
                mod = sys.modules[eval_module_name]
            else:
                mod_path = self.benchmark_dir / f'{eval_module_name}.py'
                mod = _import_module_from_file(
                    f'_bench_eval_{self.name}', mod_path)
        else:
            # Default: evaluator lives in expt.py
            mod = self._load_expt_module()

        cls = getattr(mod, eval_name)
        eval_args = self.spec.get('evaluator_args', {}) or {}
        return cls(**eval_args)

    # -- Dataset loading -----------------------------------------------------

    def load_dataset(self, split: str, n: int | None = None) -> Dataset:
        """Load a dataset split, dispatching based on spec['loader']."""
        loader = self.spec['loader']
        seed = self.shuffle_seed
        loader_args = self.spec.get('loader_args', {}) or {}

        if loader == 'medcalc':
            return self._load_medcalc(split, n)
        elif loader == 'musr':
            return self._load_musr(split, n, seed)
        elif loader == 'natural_plan':
            return self._load_natural_plan(split, n, loader_args)
        elif loader == 'rulearena':
            return self._load_rulearena(split, n, seed, loader_args)
        elif loader == 'tabmwp':
            return self._load_tabmwp(split, n, seed)
        elif loader == 'bbh':
            return self._load_bbh(split, n, seed)
        elif loader == 'finqa':
            return self._load_finqa(split, n, seed)
        else:
            raise ValueError(f'Unknown loader: {loader!r}')

    def load_train_eval(
        self, n_train: int | None = None, n_eval: int | None = None,
    ) -> tuple[Dataset, Dataset | None]:
        """Load disjoint train and eval datasets.

        For medcalc with disjoint_split: load one pool, split via
        stratified_split. For all others: load train and eval separately.
        """
        train_spec = self.spec.get('train', {})
        eval_spec = self.spec.get('eval', {})
        n_train = train_spec.get('size') if n_train is None else n_train
        n_eval = eval_spec.get('size') if n_eval is None else n_eval

        if self.spec.get('disjoint_split'):
            if n_eval and n_eval > 0:
                return self._load_medcalc_disjoint(
                    train_spec['split'], n_train, n_eval)
            train_ds = self.load_dataset(train_spec['split'], n_train)
            print(f'Train: {len(train_ds.cases)} cases from {train_spec["split"]}')
            return train_ds, None

        if n_eval and n_eval > 0:
            if train_spec['split'] == eval_spec['split']:
                pool = self.load_dataset(train_spec['split'], None)
                cases = list(pool.cases)
                random.Random(self.shuffle_seed).shuffle(cases)
                train_cases = cases[:min(n_train, len(cases))]
                eval_cases = cases[len(train_cases):len(train_cases) + n_eval]
                train_ds = pool.model_copy(update={
                    'name': pool.name + '_train',
                    'cases': train_cases,
                })
                eval_ds = pool.model_copy(update={
                    'name': pool.name + '_eval',
                    'cases': eval_cases,
                })
                print(f'Train: {len(train_ds.cases)} cases from {train_spec["split"]}')
                print(f'Eval: {len(eval_ds.cases)} cases from {eval_spec["split"]}')
                return train_ds, eval_ds

        train_ds = self.load_dataset(train_spec['split'], n_train)
        print(f'Train: {len(train_ds.cases)} cases from {train_spec["split"]}')

        eval_ds = None
        if n_eval and n_eval > 0:
            eval_ds = self.load_dataset(eval_spec['split'], n_eval)
            print(f'Eval: {len(eval_ds.cases)} cases from {eval_spec["split"]}')

        return train_ds, eval_ds

    # -- Setup hook ----------------------------------------------------------

    def run_setup_hook(self, ptools_module):
        """Run benchmark-specific initialization (e.g. tabmwp table store)."""
        hook = self.spec.get('setup_hook')
        if not hook:
            return

        if hook == 'tabmwp_table_store':
            expt = self._load_expt_module()
            train_split = self.spec.get('train', {}).get('split', 'dev1k')
            raw_data = expt.load_raw_data(train_split)
            ptools_module.load_table_store(raw_data)
            print(f'[adapter] loaded table store from {train_split} '
                  f'({len(raw_data)} entries)')

    # -- Internal helpers ----------------------------------------------------

    def _load_expt_module(self):
        """Import the benchmark's expt.py under a unique module name."""
        mod_name = f'_bench_expt_{self.name}'
        if mod_name in sys.modules:
            return sys.modules[mod_name]
        expt_path = self.benchmark_dir / 'expt.py'
        if not expt_path.exists():
            raise FileNotFoundError(f'expt.py not found: {expt_path}')
        return _import_module_from_file(mod_name, expt_path)

    def _load_medcalc(self, split: str, n: int | None) -> Dataset:
        expt = self._load_expt_module()
        ds = expt.load_dataset(split)
        if n:
            ds.cases = expt.stratified_sample(ds.cases, n, seed=self.shuffle_seed)
        return ds

    def _load_medcalc_disjoint(
        self, split: str, n_train: int, n_eval: int,
    ) -> tuple[Dataset, Dataset | None]:
        expt = self._load_expt_module()
        full_ds = expt.load_dataset(split)
        train_cases, eval_cases = self._exact_medcalc_disjoint_split(
            full_ds.cases, n_train, n_eval, seed=self.shuffle_seed)

        train_ds = full_ds
        train_ds.cases = train_cases
        eval_ds = Dataset(
            name=full_ds.name + '_eval', cases=eval_cases)

        print(f'Train: {len(train_cases)} cases (disjoint split from {split})')
        print(f'Eval: {len(eval_cases)} cases (disjoint split from {split})')
        return train_ds, eval_ds

    @staticmethod
    def _exact_medcalc_disjoint_split(
        cases: list[Any], n_train: int, n_eval: int, seed: int,
    ) -> tuple[list[Any], list[Any]]:
        """Draw exact-size disjoint splits, stratified when size permits."""
        rng = random.Random(seed)
        groups: dict[str, list[Any]] = {}
        for case in cases:
            calc = (case.metadata or {}).get('calculator_name', 'unknown')
            groups.setdefault(calc, []).append(case)
        for items in groups.values():
            rng.shuffle(items)

        def take(n: int) -> list[Any]:
            total = sum(len(items) for items in groups.values())
            n = max(0, min(n, total))
            if n == 0:
                return []

            nonempty = [name for name, items in groups.items() if items]
            if n < len(nonempty):
                flat = [case for items in groups.values() for case in items]
                rng.shuffle(flat)
                selected = flat[:n]
                selected_ids = {id(case) for case in selected}
                for name, items in groups.items():
                    groups[name] = [
                        case for case in items
                        if id(case) not in selected_ids
                    ]
                rng.shuffle(selected)
                return selected

            exact = {
                name: len(items) * n / total
                for name, items in groups.items()
                if items
            }
            counts = {name: max(int(value), 1)
                      for name, value in exact.items()}
            allocated = sum(counts.values())
            remaining = n - allocated

            if remaining > 0:
                remainders = sorted(
                    exact,
                    key=lambda name: exact[name] - counts[name],
                    reverse=True,
                )
                for name in remainders:
                    if remaining <= 0:
                        break
                    if counts[name] < len(groups[name]):
                        counts[name] += 1
                        remaining -= 1
            elif remaining < 0:
                trimmable = sorted(
                    (name for name, count in counts.items() if count > 1),
                    key=lambda name: counts[name],
                    reverse=True,
                )
                for name in trimmable:
                    if remaining >= 0:
                        break
                    counts[name] -= 1
                    remaining += 1

            selected = []
            for name, count in counts.items():
                selected.extend(groups[name][:count])
                groups[name] = groups[name][count:]
            rng.shuffle(selected)
            return selected

        return take(n_train), take(n_eval)

    def _load_musr(self, split: str, n: int | None, seed: int) -> Dataset:
        expt = self._load_expt_module()
        ds = expt.load_dataset(split)
        return ds.configure(shuffle_seed=seed, n=n)

    def _load_natural_plan(
        self, split: str, n: int | None, loader_args: dict,
    ) -> Dataset:
        expt = self._load_expt_module()
        if split in {'calendar', 'meeting', 'trip'}:
            task = split
            partition = None
        elif split in {'train', 'valid', 'test'}:
            task = loader_args.get('task', 'calendar')
            partition = split
        else:
            task = loader_args.get('task', 'calendar')
            partition = split
        prompt_mode = loader_args.get('prompt_mode', '0shot')
        ds = expt.load_dataset(
            task=task, prompt_mode=prompt_mode, partition=partition)
        return ds.configure(n=n)

    def _load_rulearena(
        self, split: str, n: int | None, seed: int, loader_args: dict,
    ) -> Dataset:
        expt = self._load_expt_module()
        domain = loader_args.get('domain', 'airline')
        ds = expt.load_dataset(domain=domain, split=split)
        return ds.configure(shuffle_seed=seed, n=n)

    def _load_tabmwp(self, split: str, n: int | None, seed: int) -> Dataset:
        expt = self._load_expt_module()
        ds = expt.load_dataset(split)
        return ds.configure(shuffle_seed=seed, n=n)

    def _load_bbh(self, split: str, n: int | None, seed: int) -> Dataset:
        json_file = self.benchmark_dir / 'data' / f'{split}.json'
        if not json_file.exists():
            raise FileNotFoundError(f'BBH data not found: {json_file}')
        ds = Dataset.model_validate_json(json_file.read_text())
        return ds.configure(shuffle_seed=seed, n=n)

    def _load_finqa(self, split: str, n: int | None, seed: int) -> Dataset:
        json_file = self.benchmark_dir / 'data' / f'{split}.json'
        if not json_file.exists():
            raise FileNotFoundError(f'FinQA data not found: {json_file}')
        ds = Dataset.model_validate_json(json_file.read_text())
        return ds.configure(shuffle_seed=seed, n=n)

    # -- Listing -------------------------------------------------------------

    @classmethod
    def list_benchmarks(cls) -> list[dict[str, Any]]:
        """Return a list of benchmark summaries from the registry."""
        registry = _load_registry()
        benchmarks = registry.get('benchmarks', {})
        result = []
        for name, spec in benchmarks.items():
            train = spec.get('train', {})
            eval_ = spec.get('eval', {})
            result.append({
                'name': name,
                'directory': spec.get('directory', ''),
                'entry_point': spec.get('entry_point', ''),
                'loader': spec.get('loader', ''),
                'train_split': train.get('split', ''),
                'train_size': train.get('size', 0),
                'eval_split': eval_.get('split', ''),
                'eval_size': eval_.get('size', 0),
            })
        return result
