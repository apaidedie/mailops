#!/bin/sh
set -eu

: "${GUNICORN_WORKERS:=1}"
: "${GUNICORN_THREADS:=4}"
: "${GUNICORN_TIMEOUT:=120}"
: "${GUNICORN_BIND:=0.0.0.0:5000}"
: "${GUNICORN_ACCESS_LOGFILE:=-}"
: "${GUNICORN_MAX_REQUESTS:=0}"
: "${GUNICORN_MAX_REQUESTS_JITTER:=0}"

require_positive_int() {
  name="$1"
  value="$2"
  case "$value" in
    ''|*[!0-9]*)
      echo "$name must be a positive integer, got: $value" >&2
      exit 1
      ;;
  esac
  if [ "$value" -lt 1 ]; then
    echo "$name must be a positive integer, got: $value" >&2
    exit 1
  fi
}

require_positive_int GUNICORN_WORKERS "$GUNICORN_WORKERS"
require_positive_int GUNICORN_THREADS "$GUNICORN_THREADS"
require_positive_int GUNICORN_TIMEOUT "$GUNICORN_TIMEOUT"
# GUNICORN_MAX_REQUESTS / JITTER 允许 0（= 关闭 worker 回收），不做正整数校验

# Keep the default to one worker so the in-process scheduler is not duplicated.
# Threads let sync endpoints such as wait-message share the worker instead of
# blocking the entire site while waiting on upstream mail providers.
#
# GUNICORN_MAX_REQUESTS > 0 enables worker recycling to prevent memory leaks
# on long-running instances (recommended for <=2GB RAM servers).
MAX_REQUESTS_ARGS=""
if [ "$GUNICORN_MAX_REQUESTS" -gt 0 ]; then
  MAX_REQUESTS_ARGS="--max-requests $GUNICORN_MAX_REQUESTS --max-requests-jitter $GUNICORN_MAX_REQUESTS_JITTER"
fi

exec gunicorn \
  -w "$GUNICORN_WORKERS" \
  --threads "$GUNICORN_THREADS" \
  -b "$GUNICORN_BIND" \
  --timeout "$GUNICORN_TIMEOUT" \
  --access-logfile "$GUNICORN_ACCESS_LOGFILE" \
  $MAX_REQUESTS_ARGS \
  web_mailops_app:app
