#!/usr/bin/env bash
set -euo pipefail

BRANCH="codex/build-sbs-nexus-compliancehub-project-70f52c"

printf "[1/6] Fetch origin...\n"
git fetch origin

printf "[2/6] Checkout branch %s...\n" "$BRANCH"
git checkout "$BRANCH"

printf "[3/6] Merge origin/main into %s...\n" "$BRANCH"
if ! git merge origin/main; then
  printf "\nMerge has conflicts (expected).\n"
fi

printf "[4/6] Files with unresolved conflicts:\n"
git diff --name-only --diff-filter=U || true

printf "\n[5/6] Next steps:\n"
printf "- Resolve conflict markers in the listed files\n"
printf "- Run: ruff check . && pytest\n"
printf "- Commit: git commit -m \"merge: resolve conflicts with main for PR #6\"\n"

printf "\n[6/6] Push after resolution:\n"
printf "git push origin %s\n" "$BRANCH"
