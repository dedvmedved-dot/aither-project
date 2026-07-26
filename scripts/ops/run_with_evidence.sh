#!/usr/bin/env bash
set -Eeuo pipefail

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 LOGFILE COMMAND [ARGS...]" >&2
    exit 64
fi

LOGFILE="$1"
shift

mkdir -p "$(dirname "$LOGFILE")"

START_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
START_EPOCH="$(date +%s)"

{
    echo "============================================================"
    echo "COMMAND START"
    echo "UTC START TIMESTAMP: $START_TS"
    echo "WORKING DIRECTORY: $(pwd)"
    printf "COMMAND:"
    printf " %q" "$@"
    echo
    echo "------------------------------------------------------------"
} | tee "$LOGFILE"

set +e
"$@" > >(tee -a "$LOGFILE") 2> >(tee -a "$LOGFILE" >&2)
RC=$?
set -e

END_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
END_EPOCH="$(date +%s)"
DURATION="$((END_EPOCH-START_EPOCH))"

{
    echo "------------------------------------------------------------"
    echo "EXIT_CODE=$RC"
    echo "UTC END TIMESTAMP: $END_TS"
    echo "DURATION_SECONDS=$DURATION"
    echo "COMMAND END"
    echo "============================================================"
} | tee -a "$LOGFILE"

exit "$RC"
