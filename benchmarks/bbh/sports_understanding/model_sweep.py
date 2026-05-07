"""Experiment to compare implementations that use multiple different
models.

Sweeps through several varying-cost models and all ptools, overriding
the default LLM for exactly one ptool at a time.
"""

from secretagent.cli import expt
from secretagent import config
import ptools

MODELS = [
    'together_ai/google/gemma-3n-E4B-it',     # ultra-cheap ($0.02/$0.04 per 1M tokens)
    'together_ai/openai/gpt-oss-20b',         # very cheap ($0.05/$0.20 per 1M tokens)
    'together_ai/openai/gpt-oss-120b',        # cheap ($0.15/$0.60 per 1M tokens)
#    'together_ai/deepseek-ai/DeepSeek-V3.1',  # inexpensive strong reasoning ($0.60/$1.70 per 1M tokens)
#    'together_ai/moonshotai/Kimi-K2.5',       # getting pricy ($0.50/$2.80 per 1M tokens)
]

STEPS=[
    'analyze_sentence',
    'sport_for',
    'consistent_sports',
]

CORE_DOTLIST = [
    'ptools.are_sports_in_sentence_consistent.method=direct',
    'ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow',
    'evaluate.result_dir=model_sweep_results',
]
    

def sweep():
    for model in MODELS:
        model_stem = model.split('/')[-1]
        for step in STEPS:
            print(f' step: {step} model: {model} '.center(60, '-'))
            dotlist = (CORE_DOTLIST + 
                       [f'ptools.{step}.model={model}',
                        f'evaluate.expt_name={step}_{model_stem}'])
            with config.configuration():
                expt.run_experiment(
                    top_level_interface=ptools.are_sports_in_sentence_consistent,
                    dotlist=dotlist
                )

if __name__ == '__main__':
    sweep()
