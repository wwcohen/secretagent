# TL;DR:

- Prompt elaborateness alone didn't drive the gain alone. The same elaborate prompt content used in single-shot baselines doesn’t improve brief baselines (and sometimes slightly hurts performance). The workflow's win comes from forcing the LLM to externalize its reasoning in a parseable format and then running deterministic Python on it.

- Structured-output tools need a custom prompt template, not a generic-simulate-style wrapper. Simulate is fine for "produce some plausible output of this function" but too permissive for "produce strictly-formatted output that downstream code will parse."

- A principled mixture of direct (Python) and LLM-backed implementations is better. Direct for arithmetic, parsing, and formatting since these are precise, cheap, deterministic. LLM for reading the table, picking values, interpreting questions since this requires understanding.

- What the workflow handles well: scale errors, yes-no questions, deterministic formatting of computed results.

- What the workflow doesn't fix: wrong row/column selection, wrong formula structure, ambiguous question interpretation. These remain because no amount of post-processing logic rescues them.

- I aligned POT and React to share the same toolset. On the test split POT and React perform poorly. The pot issues are because it has no scaffolding to enforce code-block format and pot has no scaffolding to enforce the FinQA decimal-vs-percent convention, but I deliberately left them un-engineered since the ablation contract is "delete the workflow, keep the same primitives," so adding format-enforcement to pot or output cleanup to react would just rebuild workflow scaffolding under a different name and erase the evidence the ablation exists to surface. The structured baseline (61.7%) already isolates raw LLM reasoning with no tools, so the gap from there down to pot/react (17.7% / 32.0%) measures the cost of tool-call complexity without compensating glue, which is the case for some of workflow's helpers.

# What I did:
- I started with a workflow that asked the LLM to produce a reasoning plan, then used Python to evaluate the formula. The LLM mostly produced bare answers, so the workflow fell through to LLM-based final-number extraction. The deterministic Python compute step almost never ran.

- I enforced the plan structure with a custom prompt template (asking explicitly for <plan>...</plan> output with named fields). Format compliance jumped from ~10% to ~98% and accuracy improved several percentage points, but most of that gain came from the LLM's answer being cleaner to extract, not from Python doing the math. The compute step was still almost never being used because the formulas contained variable names (e.g., rev_2017) that Python couldn't evaluate.

- I made the workflow actually use the structured plan by parsing out the variable names + their numeric values, substituting values into the formula before passing it to compute(), then formatting by the declared scale (percent / integer / decimal / yes-no). This was the biggest single accuracy jump.

- I tried moving the structured-output prompt into a docstring + the framework's generic simulate factory (instead of a custom prompt-llm template). Format compliance collapsed back to ~18% and accuracy dropped sharply. I found that simulate's framing ("propose a possible output of the function") competes with strict format demands, and the LLM resolves the conflict by ignoring the format spec.

- I cleaned up the architecture by promoting internal Python helpers (parse-plan-fields, substitute-values, format-for-scale) from hidden helpers to proper ptool interfaces (bound to direct by default). No change in accuracy, but every workflow step is now ablatable and the strategy is fully serializable from config.

- I built baselines that use the same prompt machinery and similarly elaborate prompt content as the workflow, but ask the LLM for the final answer directly with no decomposition. These topped out around 59-65% on valid, around their original values and below the workflow's 75.7%.

- Then, I aligned POT and React to share the same toolset (parse_table, lookup_cell, compute, extract_reasoning_plan) so the ablations cleanly isolate the orchestration mechanism (program-of-thought vs ReAct loop) from tool capability.

- I tested whether the workflow itself should switch its value extraction to those same primitives (lookup_cell + compute); it lost by ~2.7pp on a 300-case validation run (73.0% vs 75.7%) with 0 wins and 8 losses across the diverging cases.
The LLM's dominant failure on FinQA isn't misreading values. It's citing the wrong row/column, often attributing a number from prose to a table cell. A deterministic lookup faithfully follows the wrong citation and produces the wrong value, whereas the LLM's own eyeballed value usually comes from the correct cell even when its citation is off. So a "more rigorous" lookup primitive amplifies citation errors rather than correcting them. Therefore, I kept the workflow on its existing value extraction and documented the variant as a negative result for reproducibility.


# Notes on POT / React:

POT and React perform pretty poorly on the test split: POT: 17.7%, React: 32.0%

## POT

162/300 exceptions: pot has no scaffolding to enforce code-block format and pot has no scaffolding to enforce the FinQA decimal-vs-percent convention (~40/300).
These two failure modes are the kind of glue the workflow provides via format_for_scale, extract_final_number, the strict <plan>...</plan> template, and the parse_plan_fields regex.

Note that format_for_scale isn't a usable standalone tool. It needs a scale argument that the workflow gets from parse_plan_fields over the structured plan, which pot doesn't have, so handing it to pot would force me to also reproduce the workflow's plan-parsing scaffolding. The shared toolset for pot/react covers reasoning primitives any agent could use, while format_for_scale is workflow-internal output glue. Even ignoring the principle, it wouldn't rescue pot in practice since only ~40/300 wrong cases are percent-format errors, while 162/300 are structural exceptions where no Python is emitted at all, so best-case it lifts pot from 17.7% to ~30% (still a distant fourth).

Thus, I deliberately leave pot and react un-engineered since the ablation contract is "delete the workflow, keep the same primitives." Adding format-enforcement to pot's prompt or extra cleanup logic to react would just re-introduce pieces of the workflow under different names. The failure modes I see are evidence for the scaffolding the workflow provides via its strict plan template, `format_for_scale`, and `extract_final_number`. The structured baseline (61.7%) already isolates "raw LLM reasoning, no tools," so the gap from there down to pot/react measures the cost of tool-call complexity without compensating glue.

## React

Only 10/199 non-exception off-by-100 failures (5%). Its 32% on test isn't an artifact I could prompt-engineer away. There doesn’t appear to be a small fix here unless I redesign the agent strategy, and at that point it would no longer be the same React ablation.
