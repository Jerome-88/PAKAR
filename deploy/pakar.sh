#!/bin/sh
set -eu

PAKAR_PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PAKAR_PROJECT_DIR"
if [ ! -f deploy/.env ]; then
    printf '%s\n' 'Create deploy/.env from deploy/vps.env.example and fill its values first.' >&2
    exit 1
fi
exec docker compose --env-file deploy/.env -f deploy/compose.vps.yaml "$@"
