#!/bin/sh
set -eu

CONFIG_PATH="${CRUNCHY_CONFIG_PATH:-}"
if [ -z "$CONFIG_PATH" ] && [ -f /config/config.yaml ]; then
  CONFIG_PATH="/config/config.yaml"
fi
if [ -z "$CONFIG_PATH" ] && [ -f /app/config.yaml ]; then
  CONFIG_PATH="/app/config.yaml"
fi

run_cli() {
  if [ -n "$CONFIG_PATH" ]; then
    python src/main.py -c "$CONFIG_PATH" "$@"
  else
    python src/main.py "$@"
  fi
}

case "${1:-status}" in
  daemon)
    INTERVAL="${CRUNCHY_DAEMON_INTERVAL:-3600}"
    TARGET="${CRUNCHY_DAEMON_TARGET:-status}"
    echo "CrunchyExporter daemon started (target=${TARGET}, interval=${INTERVAL}s)"
    while true; do
      if [ "$TARGET" = "sync" ]; then
        if [ -n "${CRUNCHY_DAEMON_SYNC_TARGET:-}" ]; then
          run_cli sync --target "$CRUNCHY_DAEMON_SYNC_TARGET"
        else
          run_cli sync
        fi
      elif [ "$TARGET" = "export" ]; then
        if [ -n "${CRUNCHY_DAEMON_EXPORT_TARGET:-}" ]; then
          run_cli export --target "$CRUNCHY_DAEMON_EXPORT_TARGET"
        else
          run_cli export
        fi
      else
        run_cli status
      fi
      sleep "$INTERVAL"
    done
    ;;
  *)
    run_cli "$@"
    ;;
esac
