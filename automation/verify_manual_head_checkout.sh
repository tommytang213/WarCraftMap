#!/usr/bin/env bash
# Manual validation must use the requested repository-owned branch commit.
# The normal pull_request merge checkout does not run this preflight.
set -euo pipefail

if [[ ! ${EXPECTED_HEAD_SHA:-} =~ ^[0-9a-f]{40}$ ]]; then
  echo 'Manual validation requires a frozen lowercase 40-character commit SHA.' >&2
  exit 1
fi
if [[ ${GITHUB_EVENT_NAME:-} != workflow_dispatch ||
      ${GITHUB_REPOSITORY:-} != tommytang213/WarCraftMap ||
      ${GITHUB_REF:-} != refs/heads/fix/dot-wc3-continuation-20261118 ]]; then
  echo 'Manual validation requires the repository-owned continuation branch.' >&2
  exit 1
fi
if ! checkout_head=$(git rev-parse HEAD); then
  echo 'Cannot determine manual validation checkout revision.' >&2
  exit 1
fi
if [[ ${GITHUB_SHA:-} != "$EXPECTED_HEAD_SHA" ||
      $checkout_head != "$EXPECTED_HEAD_SHA" ]]; then
  echo 'Manual validation checkout differs from the frozen branch head.' >&2
  exit 1
fi
if ! checkout_status=$(git status --porcelain --untracked-files=all); then
  echo 'Cannot inspect manual validation checkout status.' >&2
  exit 1
fi
if [[ -n $checkout_status ]]; then
  echo 'Manual validation checkout is dirty.' >&2
  exit 1
fi
printf 'Manual source revision verified: %s\n' "$EXPECTED_HEAD_SHA"
