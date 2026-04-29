"""Abstract base class for learners that produce implementations from recorded data."""

import os
import json
import random
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from secretagent import savefile
from secretagent.dataset import Case, Dataset


class Learner(ABC):
    """Base class for learners that distill recorded interface calls into code.

    The constructor collects training data from recording directories,
    saves provenance info to a working directory, and loads the Dataset.
    Subclasses implement fit(), save_implementation(), and report().
    """

    def __init__(self, interface_name: str, train_dir: str, file_under: str,
                 only_correct: bool = False):
        self.interface_name = interface_name
        self.train_dir = train_dir
        self.file_under = file_under
        self.only_correct = only_correct
        # default files to produce
        to_produce = ['data.json', 'sources.txt', 'source_configs', 'implementation.yaml']
        savefile_names = savefile.filename_list(train_dir, to_produce, file_under)
        self.out_dir = Path(savefile_names[0]).parent
        self.created_files = {short:full for short,full in zip(to_produce, savefile_names)}


    def produce_files(self, additional_files: list[str]):
        """Register other files to produce
        """
        for filename in additional_files:
            self.created_files[filename] = Path(self.out_dir / filename)

    @abstractmethod
    def fit(self) -> "Learner":
        """Fit the learner to the collected dataset."""
        ...

    @abstractmethod
    def save_implementation(self) -> Path:
        """Write learned implementation to self.out_dir. Return path to the file."""
        ...

    @abstractmethod
    def report(self) -> str:
        """Return a brief human-readable report on the learner."""
        ...

    def predict(self, input_args, input_kw=None) -> Any:
        """Predict output for a single input.

        Override in subclasses to enable validation.
        The default raises NotImplementedError, which causes validate()
        to be skipped gracefully.
        """
        raise NotImplementedError

    def validate(self, holdout_fraction: float = 0.2, seed: int = 42) -> dict:
        """Hold out some data, fit on the rest, evaluate on holdout, then refit on all.

        Returns a dict with accuracy, holdout_size, and train_size.
        Raises NotImplementedError if predict() is not overridden.
        """
        all_cases = list(self.dataset.cases)
        rng = random.Random(seed)
        rng.shuffle(all_cases)
        split = max(1, int(len(all_cases) * holdout_fraction))
        holdout = all_cases[:split]
        train = all_cases[split:]

        # Fit on training portion
        original_cases = self.dataset.cases
        self.dataset.cases = train
        self.fit()

        # Evaluate on holdout
        correct = 0
        for case in holdout:
            predicted = self.predict(case.input_args, case.input_kw)
            if predicted == case.expected_output:
                correct += 1

        metrics = {
            'accuracy': correct / len(holdout) if holdout else 0.0,
            'holdout_size': len(holdout),
            'train_size': len(train),
        }

        # Refit on all data
        self.dataset.cases = original_cases
        self.fit()

        return metrics

    def learn(self, dirs: list[Path], latest: int = 1, check: Optional[list[str]] = None):
        """Top-level routine to load data, run learner, and save.
        """
        self.collect_distillation_data(dirs, latest, check)
        print(f'collected {len(self.dataset.cases)} examples in working directory {self.out_dir}')
        self.fit()
        try:
            metrics = self.validate()
            print(f'validation: {metrics}')
        except NotImplementedError:
            pass
        output_file = self.save_implementation()
        print(self.report())
        print(f'saved output to {output_file}')

    def collect_distillation_data(self, dirs: list[Path], latest: int = 1, check: Optional[list[str]] = None) -> "Learner":
        """Collect the data to train on.

        Arguments identify directories containing recordings to collect datafrom.

        Also store the data and its provenance in train_dir.
        """
        filtered_dirs = savefile.filter_paths(dirs, latest=latest, dotlist=check or [])
        if not filtered_dirs:
            raise ValueError(f'empty list of directories to collect data from: {dirs}')
        self.dataset = self._collect_and_store_data(filtered_dirs)
        if not self.dataset.cases:
            raise ValueError(f'no data collected for {self.interface_name}')
        return self


    def _collect_and_store_data(self, dirs: list[Path]) -> Dataset:
        """Collect input/output pairs for an interface from recording directories.
        
        Creates a dataset, and stores it and its provenance information in:
            data.json       — a JSON-serialized Dataset of input/output pairs
            sources.txt     — one source directory name per line
            source_configs/ — a copy of each source directory's config.yaml

        Returns the dataset itself.
        """
        cases = self._extract_cases_from_dirs(dirs)
        dataset = Dataset(name=self.interface_name, cases=cases)
        dataset_filename = self.created_files['data.json']
        os.makedirs(os.path.dirname(dataset_filename), exist_ok=True)
        with open(dataset_filename, 'w') as f:
            f.write(dataset.model_dump_json(indent=2))

        sources_filename = self.created_files['sources.txt']
        os.makedirs(os.path.dirname(sources_filename), exist_ok=True)
        with open(sources_filename, 'w') as f:
            for d in dirs:
                f.write(f'{d}\n')

        source_cfg_dirname = self.created_files['source_configs']
        os.makedirs(source_cfg_dirname, exist_ok=True)
        for d in dirs:
            src_cfg = Path(d) / 'config.yaml'
            if not src_cfg.exists():
                raise ValueError(f'missing config file {src_cfg}')
            shutil.copy2(src_cfg, Path(source_cfg_dirname) / f'{d.name}.yaml')

        return dataset

    def _extract_cases_from_dirs(self, dirs):
        """Extract Cases for the named interface from results.jsonl in each directory."""
        result = []
        for dx, d in enumerate(dirs):
            jsonl_path = Path(d) / 'results.jsonl'
            if not jsonl_path.exists():
                raise ValueError(f'missing jsonl file {jsonl_path}')
            with open(jsonl_path) as f:
                for lx, line in enumerate(f):
                    record = json.loads(line)
                    for case in self._extract_cases_from_record(dx, lx, record):
                        result.append(case)
        return result

    def _extract_cases_from_record(self, dx, lx, record):
        """Yield Cases for the named interface from a single JSONL record.

        Stores the rollout context in Case.metadata so learners
        can see how this interface was called within the workflow,
        plus the top-level task input/output so the learner sees the
        global problem this ptool serves (not just its local i/o).

        When self.only_correct is True, skip rollouts that produced
        an incorrect final answer (filters out training data where the
        intermediate steps led to a wrong result).
        """
        if self.only_correct and not record.get('correct'):
            return
        rollout = record.get('rollout', [])
        # Top-level interface = first rollout entry; top-level i/o = record fields.
        top_level_args = (rollout[0].get('args') if rollout else None)
        top_level_kw = (rollout[0].get('kw') if rollout else None) or None
        top_level_func = (rollout[0].get('func') if rollout else None)
        top_level_predicted = record.get('predicted_output')
        top_level_expected = record.get('expected_output')
        for sx, step in enumerate(rollout):
            if step['func'] == self.interface_name:
                yield Case(
                    name=f'{self.interface_name}_{dx}.{lx}.{sx}',
                    input_args=step.get('args'),
                    input_kw=step.get('kw') or None,
                    expected_output=step.get('output'),
                    metadata={
                        'rollout_correct': record.get('correct'),
                        'step_index': sx,
                        'prior_steps': rollout[:sx],
                        'top_level_func': top_level_func,
                        'top_level_args': top_level_args,
                        'top_level_kw': top_level_kw,
                        'top_level_predicted': top_level_predicted,
                        'top_level_expected': top_level_expected,
                    }
                )
