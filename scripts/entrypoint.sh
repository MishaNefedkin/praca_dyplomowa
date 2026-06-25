#!/bin/sh
set -eu

is_enabled() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

if is_enabled "${RUN_MIGRATIONS:-false}"; then
  echo "Running database migrations..."
  alembic upgrade head
fi

exec "$@"
