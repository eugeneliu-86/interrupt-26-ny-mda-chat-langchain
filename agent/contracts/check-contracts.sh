#!/usr/bin/env bash
# Grep-level contract checks (C1, C2, C3, C7, C8, C11).
#
# These assert what a unit test cannot: that a fact is written in exactly ONE
# place, and that files which must not mention something do not. Run from
# anywhere; it locates the project itself.
#
# Written WITHOUT `eval`. The first version used it, and `\"user\"` collapsed to
# an empty pattern that matched everything — a check that always passed while
# reporting as if it had verified something. Glob patterns are quoted for the
# same reason: an unquoted --include=*.py is expanded by some shells.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2

# Scan the SOURCE tree only. `.mda/build/` holds a copy of every project file
# plus the vendored runtime, so including it reported the project's own sources
# as contract violations and matched `"user"` inside the runtime's own
# connection code — four failures that were entirely artefacts of scope.
EXCLUDE=(--exclude-dir=.mda --exclude-dir=.venv --exclude-dir=__pycache__
         --exclude-dir=.pytest_cache --exclude-dir=node_modules)

fails=0
pass () { printf '  ok    %s\n' "$1"; }
fail () { printf '  FAIL  %s\n' "$1"; fails=$((fails + 1)); }

# Files (python only) that match a pattern, minus an allowlist of paths.
offenders () {  # $1 = pattern, rest = allowed path prefixes
  local pattern="$1"; shift
  local hits
  hits=$(grep -rl "${EXCLUDE[@]}" --include='*.py' -e "$pattern" . 2>/dev/null || true)
  local out=""
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    local ok=0
    for allowed in "$@"; do
      case "$f" in "$allowed"*) ok=1; break;; esac
    done
    [ "$ok" -eq 0 ] && out="$out$f "
  done <<< "$hits"
  printf '%s' "$out"
}

echo "contracts:"

# --- C1: the role vocabulary is written once -------------------------------
o=$(offenders '"engineer"' ./contracts/ ./tests/)
o="$o$(offenders '"employee"' ./contracts/ ./tests/)"
[ -z "$o" ] && pass "role literals only in contracts/ and tests/" \
            || fail "role literals also in: $o"

# --- C2: corpus prefixes and repo handles are written once ----------------
o=$(offenders 'productDocs' ./contracts/ ./tools/ ./middleware/ ./tests/)
[ -z "$o" ] && pass "corpus prefixes only in contracts/, tools/, middleware/, tests/" \
            || fail "corpus prefixes also in: $o"

o=$(offenders 'product-docs' ./contracts/grants.py ./tests/)
o="$o$(offenders 'engineering-runbooks' ./contracts/grants.py ./tests/)"
[ -z "$o" ] && pass "repo handles only in contracts/grants.py" \
            || fail "repo handles also in: $o"

# --- C7/C8: managed context names no role, tool or corpus -----------------
if grep -qiE 'engineer|employee|productDocs|engineeringDocs' instructions.md; then
  fail "instructions.md names a role or corpus"
else
  pass "instructions.md names no role/tool/corpus"
fi

if grep -rqiE "${EXCLUDE[@]}" 'engineer|employee|productDocs|engineeringDocs' skills/; then
  fail "skills/ name a role or corpus"
else
  pass "skills/ name no role/tool/corpus"
fi

if find skills -type d | grep -qiE 'engineer|employee'; then
  fail "a skills/ directory is named after a role"
else
  pass "no role name in any skills/ directory"
fi

# --- C11: every connection is agent-owned ---------------------------------
if grep -rn "${EXCLUDE[@]}" --include='*.py' -e 'connections.get' . | grep -q '"user"'; then
  fail "a connections.get asks for a user-owned credential"
else
  pass "connections.get is always agent-owned"
fi

# --- C3: no tool takes a role or identity parameter -----------------------
if grep -rnE 'def (search_docs|fetch_doc)\(.*(role|identity|corpus)' tools/ | grep -q .; then
  fail "a tool exposes a role/identity/corpus parameter"
else
  pass "no tool parameter named role/identity/corpus"
fi

# --- secrets --------------------------------------------------------------
# REPO-WIDE, not just agent/. The UI arrived after this script was written and
# holds its own .env; a secret check scoped to one directory is a secret check
# with a blind spot exactly where the newest code is.
#
# Asks GIT what would actually be committed rather than walking the tree, so
# a real `.env.local` sitting in ui/ is correctly ignored while an accidental
# `git add -f` of one is caught.
#
# RUN FROM THE REPO ROOT IN A SUBSHELL. `git -C .. ls-files` prints paths
# relative to the repo root while grep would resolve them against agent/, so
# every path missed and the check passed on a seeded leak — the exact
# always-passes failure this script was rewritten to eliminate once before.
if ( cd .. && git ls-files -co --exclude-standard 2>/dev/null \
       | xargs grep -lE 'lsv2_(pt|sk)_[0-9a-f]{16}' 2>/dev/null ) | grep -q .; then
  fail "key material is committed"
else
  pass "no key material committed"
fi

git check-ignore -q .env && pass ".env is ignored" || fail ".env is NOT ignored"

# --- generated artifacts in sync ------------------------------------------
# READ-ONLY. The first version of this check regenerated grants.json IN PLACE
# and diffed against a copy. It detected staleness correctly — and then left
# the regenerated file behind, so the very next run passed. A check that
# repairs what it is checking reports a false green on retry and hands CI a
# dirty working tree. Observed for real: the v4 -> v5 bump left grants.json
# stale, this check failed once, and the re-run went green with the file
# silently rewritten.
#
# So: regenerate, diff, and always put the original back.
_grants_backup=$(mktemp)
cp contracts/grants.json "$_grants_backup"
if uv run python -m contracts.emit_grants_json >/dev/null 2>&1 \
   && diff -q "$_grants_backup" contracts/grants.json >/dev/null; then
  pass "grants.json is in sync with contracts/grants.py"
else
  fail "grants.json is stale — run: uv run python -m contracts.emit_grants_json"
fi
cp "$_grants_backup" contracts/grants.json
rm -f "$_grants_backup"

echo
if [ "$fails" -eq 0 ]; then
  echo "all contract checks passed"
else
  echo "$fails contract check(s) FAILED"
fi
exit "$fails"
