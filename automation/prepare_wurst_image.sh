#!/usr/bin/env bash
# Keep compiler identity separate from the registry used to fetch its bytes.
# stdout is only the immutable reference for docker run --pull=never.
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^frotty/wurstscript@sha256:[0-9a-f]{64}$ ]]; then
  echo "ERROR: expected the canonical frotty/wurstscript image pinned by SHA-256" >&2
  exit 2
fi

canonical_image=$1
mirror_image="mirror.gcr.io/$canonical_image"

# A local immutable reference needs no registry request (and no pull quota).
for image in "$canonical_image" "$mirror_image"; do
  if docker image inspect "$image" >/dev/null 2>&1; then
    printf '%s\n' "$image"
    exit 0
  fi
done

# The public mirror was verified against the canonical manifest's SHA-256.
# Docker verifies that same digest on pull; no tags, login or daemon changes.
# A mirror cache miss may still be served by Hub. If both fail, stop the job.
for image in "$mirror_image" "$canonical_image"; do
  if docker pull "$image" >&2; then
    docker image inspect "$image" >/dev/null
    printf '%s\n' "$image"
    exit 0
  fi
done

echo "ERROR: neither registry supplied the pinned Wurst compiler; validation has not run" >&2
exit 1
