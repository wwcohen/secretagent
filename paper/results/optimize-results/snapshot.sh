#!/usr/bin/env bash
# snapshot.sh — Phase 2 snapshot + commit + push automation
#
# Usage:
#   bash benchmarks/COMMON/optimize-results/snapshot.sh <BENCH> <CWD> <COVERAGE> [--push]
#
# COVERAGE values:
#   "RQ1+RQ2+RQ4"   - sweep added react_learned AND wf_orch
#   "RQ2+RQ4"       - sweep added wf_orch only (no induction artifacts)
#
# Examples:
#   bash benchmarks/COMMON/optimize-results/snapshot.sh sports_understanding benchmarks/bbh/sports_understanding RQ1+RQ2+RQ4
#   bash benchmarks/COMMON/optimize-results/snapshot.sh finqa benchmarks/finqa RQ2+RQ4
#   bash benchmarks/COMMON/optimize-results/snapshot.sh musr_murder benchmarks/musr RQ1+RQ2+RQ4 --push
#
# Without --push, the script stops after `git commit`. Add --push to also
# `git push upstream main`. Designed to be idempotent: the snapshot dir is
# refreshed in place, so re-running over a benchmark is safe.
#
# Refuses to run if the three sweep artifacts are missing. Never adds the
# Co-Authored-By: Claude trailer.

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <BENCH> <CWD> <COVERAGE> [--push]" >&2
  echo "  BENCH    = snapshot folder name under benchmarks/COMMON/optimize-results/" >&2
  echo "  CWD      = the benchmark's cwd (used by --cwd in the optimizer)" >&2
  echo "  COVERAGE = e.g. 'RQ1+RQ2+RQ4' or 'RQ2+RQ4'" >&2
  exit 2
fi

BENCH="$1"
CWD="$2"
COVERAGE="$3"
PUSH=0
if [[ ${4:-} == "--push" ]]; then PUSH=1; fi

case "$COVERAGE" in
  "RQ1+RQ2+RQ4") METHODS_DESC="react_learned + wf_orch" ;;
  "RQ2+RQ4")     METHODS_DESC="wf_orch" ;;
  *)             METHODS_DESC="$COVERAGE" ;;
esac

DEST="benchmarks/COMMON/optimize-results/$BENCH"

# Step 1: verify artifacts exist
SUMMARY="$CWD/results/nsga2_summary.csv"
GENS="$CWD/results/nsga2_generations.csv"
PNG="$CWD/results/nsga2.png"

for f in "$SUMMARY" "$GENS" "$PNG"; do
  if [[ ! -f "$f" ]]; then
    echo "MISSING artifact: $f" >&2
    echo "Did the sweep finish? Check $CWD/results/" >&2
    exit 1
  fi
done

echo "[snapshot] artifacts found:"
ls -la "$SUMMARY" "$GENS" "$PNG"

# Step 2: snapshot the three top-level files
mkdir -p "$DEST/nsga_runs"
cp "$SUMMARY" "$DEST/"
cp "$GENS" "$DEST/"
cp "$PNG" "$DEST/"

# Step 3: copy per-config nsga_NNN dirs from today's date prefix
TODAY=$(date +%Y%m%d)
echo "[snapshot] copying per-config dirs matching $TODAY.*.nsga_*..."
COUNT=0
for d in "$CWD/results/$TODAY".*.nsga_*; do
  if [[ -d "$d" ]]; then
    cp -r "$d" "$DEST/nsga_runs/"
    COUNT=$((COUNT + 1))
  fi
done
echo "[snapshot] copied $COUNT per-config dirs"

# Step 4: write REPRODUCE.md
COMMIT=$(git rev-parse --short HEAD)
DATE=$(date -u +%Y-%m-%d)
cat > "$DEST/REPRODUCE.md" <<EOF
# $BENCH NSGA-II sweep snapshot

Frozen on $DATE from commit $COMMIT.

## Command

\`\`\`
uv run -m secretagent.cli.optimize nsga2 \\
  --space-file $CWD/nsga2.yaml \\
  --cwd $CWD \\
  --pop-size 12 --n-gen 5 --timeout 1200 \\
  <dataset overrides — see EXPERIMENT_CMDS.md Phase 1 for the exact split>
\`\`\`

## Methods searched

\`structured_baseline\`, \`workflow\`, \`pot\`, \`react\`, \`react_learned\`
(RQ1; if applicable), \`wf_orch\` (RQ2). See \`$CWD/nsga2.yaml\` for the exact
dotlist expansions per method.

## Files

- \`nsga2_summary.csv\` — one row per evaluated config
- \`nsga2_generations.csv\` — per-generation convergence stats
- \`nsga2.png\` — Pareto plot (cost vs correctness)
- \`nsga_runs/<TS>.nsga_NNN/\` — per-config rollout dirs ($COUNT total)
EOF
echo "[snapshot] wrote $DEST/REPRODUCE.md"

# Step 5: stage cache + snapshot + yaml
NSGA_YAML=""
for candidate in "$CWD/nsga2.yaml" "$CWD/nsga2_murder.yaml" "$CWD/nsga2_object.yaml" "$CWD/nsga2_team.yaml" "$CWD/nsga2_meeting.yaml" "$CWD/nsga2_trip.yaml"; do
  if [[ -f "$candidate" ]]; then NSGA_YAML="$candidate"; break; fi
done

git add "$CWD/llm_cache/" "$DEST/" ${NSGA_YAML:+"$NSGA_YAML"}
echo "[snapshot] staged: $CWD/llm_cache/, $DEST/, $NSGA_YAML"

# Step 6: commit (no Co-Authored-By trailer)
MSG="$BENCH: NSGA-II sweep with $METHODS_DESC ($COVERAGE)"
git commit -m "$MSG"
echo "[snapshot] committed: $MSG"

# Step 7: push to upstream (only if --push)
if [[ $PUSH -eq 1 ]]; then
  echo "[snapshot] pushing to upstream main..."
  git push upstream main
  echo "[snapshot] pushed to upstream/main."
else
  echo "[snapshot] commit complete. Run with --push to push, or:"
  echo "           git push upstream main"
fi
