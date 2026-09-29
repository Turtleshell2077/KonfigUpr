#!/bin/sh
cd "$(dirname "$0")" || exit 1

for candidate in python3 python; do
    if "$candidate" -c "" >/dev/null 2>&1; then
        exec "$candidate" -m src.emulator "$@"
    fi
done

echo "run.sh: Python 3 not found" >&2
exit 1
