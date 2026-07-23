#!/usr/bin/env bash
# Merge a quiz-results export from ~/Downloads into seed-results.json
# additively (never replaces existing attempts), then commits + pushes.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILE="$REPO_DIR/seed-results.json"
BACKUP_FILE="$REPO_DIR/seed-results.json.bak"
SYNC_PY="$REPO_DIR/sync_results.py"
DOWNLOADS_DIR="$HOME/Downloads"

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

# 1. Find the most recently modified matching export file.
shopt -s nullglob nocaseglob
candidates=("$DOWNLOADS_DIR"/all-results-*.json "$DOWNLOADS_DIR"/results-*.json)
shopt -u nullglob nocaseglob

if [[ ${#candidates[@]} -eq 0 ]]; then
  echo "No export file found in $DOWNLOADS_DIR matching 'all-results-*.json' or 'results-*.json'." >&2
  exit 1
fi

EXPORT_FILE=""
latest_mtime=-1
for f in "${candidates[@]}"; do
  mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f")
  if (( mtime > latest_mtime )); then
    latest_mtime=$mtime
    EXPORT_FILE="$f"
  fi
done

echo "Using export: $EXPORT_FILE"

# 2. Back up the current seed-results.json (skip in dry-run: nothing is
# being overwritten, so there's nothing to protect).
if [[ $DRY_RUN -eq 0 ]]; then
  cp "$SEED_FILE" "$BACKUP_FILE"
  echo "Backed up $SEED_FILE -> $BACKUP_FILE"
fi

# 3-6. Merge via Python.
py_args=(--seed "$SEED_FILE" --export "$EXPORT_FILE")
if [[ $DRY_RUN -eq 1 ]]; then
  py_args+=(--dry-run)
fi

summary="$(python3 "$SYNC_PY" "${py_args[@]}")"
echo "$summary"

added="$(sed -n 's/.*SUMMARY added=\([0-9]*\).*/\1/p' <<<"$summary")"

# 7. Commit and push only for a real (non-dry-run) run that added records.
if [[ $DRY_RUN -eq 0 ]]; then
  if [[ "${added:-0}" -gt 0 ]]; then
    git -C "$REPO_DIR" add seed-results.json
    git -C "$REPO_DIR" commit -m "sync results"
    git -C "$REPO_DIR" push
    echo "Committed and pushed."
  else
    echo "No new records added — nothing to commit."
  fi
fi
