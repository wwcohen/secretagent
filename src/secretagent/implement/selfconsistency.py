"""Self-consistency factory: majority vote over multiple samples.

A factory that wraps another factory's implementation, runs it N times,
and returns the most common answer. This is a test-time scaling method
that improves accuracy at the cost of more LLM calls.

Reference: "Self-Consistency Improves Chain of Thought Reasoning in
Language Models" (Wang et al., 2022)

Usage via config::

    ptools:
      answer_question:
        method: self_consistency
        inner_method: simulate
        n_samples: 5

Or programmatically::

    interface.implement_via('self_consistency',
                            inner_method='simulate',
                            n_samples=5)

The inner_method can be any registered factory (simulate, prompt_llm,
ptp, etc). All extra kwargs (except n_samples and inner_method) are
passed through to the inner factory.
"""

from collections import Counter
from typing import Any

from secretagent.core import (
    Implementation, register_factory, _FACTORIES,
)
from secretagent import config, record


class SelfConsistencyFactory(Implementation.Factory):
    """Run an implementation multiple times and return the majority vote.

    Config keys:
        inner_method: the factory method to wrap (e.g. 'simulate')
        n_samples: number of times to run (default 3)

    All other kwargs are passed to the inner factory's setup.
    """
    inner_fn: Any = None
    n_samples: int = 3

    def setup(self, inner_method='simulate', n_samples=3, **inner_kwargs):
        self.n_samples = n_samples
        inner_factory = _FACTORIES[inner_method]
        inner_impl = inner_factory.build_implementation(
            self.bound_interface, model=self.model, **inner_kwargs)
        self.inner_fn = inner_impl.implementing_fn

    def __call__(self, *args, **kw):
        interface = self.bound_interface
        outputs = []

        for i in range(self.n_samples):
            try:
                # Temporarily disable caching so we get diverse samples
                with config.configuration(cachier={'enable_caching': False}):
                    output = self.inner_fn(*args, **kw)
                outputs.append(output)
            except Exception:
                # Skip failed samples
                pass

        if not outputs:
            raise ValueError(
                f'self_consistency: all {self.n_samples} samples failed')

        # Majority vote
        # Convert unhashable types to strings for counting
        try:
            counter = Counter(outputs)
        except TypeError:
            counter = Counter(str(o) for o in outputs)
            # Map back to original
            str_to_orig = {str(o): o for o in outputs}
            winner_str = counter.most_common(1)[0][0]
            winner = str_to_orig[winner_str]
        else:
            winner = counter.most_common(1)[0][0]

        # Record the majority vote result
        vote_info = {
            'n_samples': self.n_samples,
            'n_succeeded': len(outputs),
            'vote_counts': dict(Counter(str(o) for o in outputs)),
            'agreement': counter.most_common(1)[0][1] / len(outputs),
        }
        record.record(
            func=interface.name,
            args=args, kw=kw,
            output=winner,
            stats={},
            step_info={'self_consistency': vote_info},
        )

        return winner


register_factory('self_consistency', SelfConsistencyFactory())
