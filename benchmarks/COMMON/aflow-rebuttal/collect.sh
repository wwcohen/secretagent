#!/usr/bin/env bash
# Collect AFlow rebuttal artifacts from the local AFlow clone into this
# directory. Rerunnable; run from the secretagent repo root:
#   bash benchmarks/COMMON/aflow-rebuttal/collect.sh
set -u
AFLOW="${AFLOW_DIR:-/c/Users/STUDENT/aflow}"
DEST="benchmarks/COMMON/aflow-rebuttal"

mkdir -p "$DEST/upstream" "$DEST/results/sports" "$DEST/results/finqa"

# Exact upstream commit + our full modification set as a git patch
(cd "$AFLOW" && git log -1 --format='%H %cs %s') > "$DEST/upstream/aflow_commit.txt"
(cd "$AFLOW" && git diff) > "$DEST/upstream/aflow_changes.patch"

# New files we added to the AFlow clone (untracked there)
cp "$AFLOW/benchmarks/finqa.py" "$DEST/upstream/benchmarks_finqa.py"
cp "$AFLOW/test_pass.py" "$AFLOW/sanity_check.py" "$AFLOW/smoke_test.py" "$DEST/upstream/"
cp "$AFLOW/RUNBOOK.md" "$DEST/"

# LLM config with the API key redacted
sed 's/api_key:.*/api_key: "<GEMINI_API_KEY>"/' "$AFLOW/config/config2.yaml" > "$DEST/upstream/config2.yaml.redacted"

# Datasets are regenerated bit-identically by scripts/export_aflow_datasets.py;
# record checksums so a regeneration can be verified.
(cd "$AFLOW/data/datasets" && sha256sum *.jsonl) > "$DEST/upstream/dataset_checksums.txt"

# Full search workspaces: seed + every generated round + experience + results.json
rm -rf "$DEST/results/sports/workspace" "$DEST/results/finqa/workspace"
cp -r "$AFLOW/workspace/SportsUnderstanding" "$DEST/results/sports/workspace"
cp -r "$AFLOW/workspace/FinQA" "$DEST/results/finqa/workspace"

# Held-out test pass CSVs
if [ -d "$AFLOW/test_logs" ]; then
  rm -rf "$DEST/results/test_logs"
  cp -r "$AFLOW/test_logs" "$DEST/results/test_logs"
fi

# Search logs (every LLM call incl. token/cost lines), gzipped
gzip -c "$AFLOW/sports_search.log" > "$DEST/results/sports/sports_search.log.gz"
for f in "$AFLOW"/finqa_search*.log; do
  [ -f "$f" ] && gzip -c "$f" > "$DEST/results/finqa/$(basename "$f").gz"
done

echo "collected into $DEST:"
find "$DEST" -type f | wc -l
du -sh "$DEST"
