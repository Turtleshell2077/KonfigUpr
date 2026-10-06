#!/bin/sh
for candidate in python3 python; do
    if "$candidate" -c "" >/dev/null 2>&1; then
        exec "$candidate" "$(dirname "$0")/src/emulator.py" "$@"
    fi
done
echo "Python 3 not found" >&2
exit 1
