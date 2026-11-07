#!/bin/sh
set -eu
# Scope privilege to creating a fresh network namespace; Node runs as the caller.
if [ "${GITHUB_ACTIONS:-}" = true ] && [ "${RUNNER_OS:-}" = Linux ]; then
    exec sudo unshare -n -- setpriv --reuid="$(id -u)" --regid="$(id -g)" --clear-groups "$(command -v node)" "$@"
fi
exec unshare -Urn node "$@"
