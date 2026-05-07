#!/bin/bash
# Re-run only the state-aware variant evals after fixing the dir naming.
set -e
for OC in 0 1; do
  for MP in 3 5 8; do
    TAG="state-oc$OC-mp$MP"
    echo "===== EVAL $TAG ====="
    uv run python expt.py run \
      --config-file conf/react_state_eval.yaml \
      llm.model=gemini/gemini-3.1-flash-lite-preview \
      learn.train_dir=learned/$TAG \
      ptools.react_calculate.method=simulate_pydantic \
      ptools.react_calculate.tool_module=__learned__ \
      ptools.react_calculate.learner=ptool_inducer \
      ptools.react_calculate.tools=__all__ \
      evaluate.expt_name=induced_${TAG}_eval \
      evaluate.max_workers=4
  done
done
