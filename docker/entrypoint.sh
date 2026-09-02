#!/bin/sh
set -eu

APP="python src/main.py"

case "${1:-status}" in
  daemon)
    INTERVAL="${CRUNCHY_DAEMON_INTERVAL:-3600}"
    TARGET="${CRUNCHY_DAEMON_TARGET:-status}"
    echo "CrunchyExporter daemon started (target=${TARGET}, interval=${INTERVAL}s)"
    while true; do
      if [ "$TARGET" = "sync" ]; then
        if [ -n "${CRUNCHY_DAEMON_SYNC_TARGET:-}" ]; then
          $APP sync --target "$CRUNCHY_DAEMON_SYNC_TARGET"
        else
          $APP sync
        fi
      elif [ "$TARGET" = "export" ]; then
        if [ -n "${CRUNCHY_DAEMON_EXPORT_TARGET:-}" ]; then
          $APP export --target "$CRUNCHY_DAEMON_EXPORT_TARGET"
        else
          $APP export
        fi
      else
        $APP status
      fi
      sleep "$INTERVAL"
    done
    ;;
  *)
    exec $APP "$@"
    ;;
esac
