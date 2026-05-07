# Changes - April 1

## Pipeline Optimizer integration

New files for Pareto-optimal config search across rulearena domains:

- `search_spaces.py` — per-domain search space definitions. Each domain
  returns a list of `SearchDimension`s (the axes to search) and fixed
  overrides applied to every config. Current space: 2 workflows (L1,
  L0F) x 2 models (DeepSeek-V3, DeepSeek-V3.1) = 4 configs per domain.
- `run_pareto.py` — CLI runner. Calls `run_nsga2()` from the optimizer
  infra, prints the frontier with short labels (L1/L0F + DSv3/DSv3.1),
  saves a Pareto plot to `results/pareto_{domain}.png`.
- `toy_nsga2.py` — standalone DEAP verification script with a known
  27-config toy problem. Not used in production.
- `sweep_airline_test.yaml` — minimal 2-config sweep space used to
  validate the existing grid search infrastructure.

### Known limitations

- **NBA metric is accuracy, not F1 macro.** The evaluator computes
  per-instance `correct` (0/1), which averages to accuracy. For NBA's
  binary classification with class imbalance, this is misleading — a
  model predicting all-True gets high accuracy but low F1. Do not draw
  conclusions from NBA frontier until F1 is added (either in the
  evaluator or as post-hoc aggregation in the optimizer).
- **All current results are n=5** (infrastructure validation only).
  Production runs need n>=30 minimum, n=300 for the paper.
- **L3 (ReAct) and PoT not in the search space.** Both require
  different override sets than method=direct. L3 needs a wrapper
  workflow function or compound config support. Deferred.
- **n_demos not a search dimension yet.** Requires wiring a config key
  that the simulate/ptp factories read.

## Tax extraction: return type and schema overhaul

- Changed `extract_tax_params` return type from `dict` to `str` to avoid
  `ast.literal_eval` failures on JSON booleans (`true`/`false`), trailing
  commas, and `//` comments. `l1_extract_workflow` now parses the raw
  string via `json.loads` after stripping JS-style comments.
- Expanded the `extract_tax_params` docstring with the full field schema
  (~70 fields), line references, and extraction rules. The docstring is
  the LLM prompt — this makes extraction more reliable.

## Bugfixes

- `SimulateFactory.parse_output` (framework-level, `implement/core.py`):
  raised `AttributeError` for `str` return types when the LLM omitted
  `<answer>` tags. Now falls back to returning the raw text.
- `calculators/airline.py`: cast return value to native `int`. The
  underlying fee tables produce `numpy.int64`, which broke pydantic-ai
  tool-result serialization in L3 experiments.

## Pilot verification

- Ran n=5 pilots (n=3 for L3) across all 14 experiment configurations.
  All pass. See `rulearena_secretagent_execution_guide.md` in the
  project root for a full execution reference.

# Changes - March 28

## Prompt fixes

- Standardized all three CoT prompt templates (airline, NBA, tax) to use
  `<answer>` tags, matching the secretagent `prompt_llm` factory convention.
- Removed duplicate answer-format instruction in the tax domain. The
  `_TAX_PROMPT_TEMPLATE` in `ptools.py` is now the single source of truth;
  `tax_cot.txt` just passes through `$forms_text`.
- Removed rules-text truncation (`[:6000]` in NBA, `[:3000]` in L1 airline)
  so all complexity levels see the full rule set.

## Evaluator improvements

- Added `correct_tolerance` metric using `np.isclose` (tight tolerance)
  alongside the existing 1% relative tolerance `correct`.
- Added `failure_mode` field to `compare_predictions`: `none`,
  `calculation_error`, or `extraction_failure`. Correctly handles the
  `**exception raised**` string from the evaluator base class.

## Tax calculator robustness

- `_taxpayer_defaults()` auto-fills missing TaxPayer fields with
  type-appropriate zero values, preventing crashes when the LLM omits
  optional pydantic fields.

## Tests

- Added `tests/test_rulearena.py` (28 tests):
  - `TestConfig` (3) -- YAML loading, dotlist overrides, invalid domain
  - `TestCalculators` (4) -- known anchors: airline=1275, tax=4747.5
  - `TestSchema` (4) -- Case/Dataset structure, load_dataset
  - `TestMetrics` (9) -- tolerance, isclose, failure_mode classification
  - `TestIntegrationL0` (2) -- oracle baseline, no LLM
  - `TestIntegrationL0F` (3) -- CoT, 1 LLM call/example
  - `TestIntegrationL1` (3) -- extraction + calculator
  - L3 excluded from tests (no `max_steps` cap in pydantic-ai agent)
