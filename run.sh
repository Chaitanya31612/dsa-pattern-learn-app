#!/usr/bin/env bash
# Start the learning app and AI API without relying on activated shell runtimes.
set -Eeuo pipefail
shopt -s nullglob

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }
if [[ ${1:-} == --help ]]; then
  printf 'Usage: ./run.sh [--check]\nStarts frontend :5173 and AI API :8000. Ctrl+C stops both.\n'
  printf 'Optional overrides: LEARNING_NODE=/path/to/node LEARNING_PYTHON=/path/to/python\n'
  exit 0
fi
[[ $# == 0 || ( $# == 1 && $1 == --check ) ]] || fail 'Use ./run.sh or ./run.sh --check.'

valid_python() {
  [[ -x $1 ]] && "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null
}
valid_node() {
  [[ -x $1 ]] && "$1" -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(Number(!((a===20&&b>=19)||(a===22&&b>=12)||a>22)))' 2>/dev/null
}

PYTHON=''
if [[ -n ${LEARNING_PYTHON:-} ]]; then
  valid_python "$LEARNING_PYTHON" || fail 'LEARNING_PYTHON must point to Python 3.11 or newer.'
fi
if valid_python "$ROOT/backend/venv/bin/python"; then
  PYTHON="$ROOT/backend/venv/bin/python"
else
  for candidate in "${LEARNING_PYTHON:-}" "$(command -v python3 || true)" \
    /usr/bin/python3.1{4,3,2,1} "$HOME"/.asdf/installs/python/*/bin/python3; do
    if valid_python "$candidate"; then PYTHON="$candidate"; break; fi
  done
  [[ -n $PYTHON ]] || fail 'Install Python 3.11+ (recommended: 3.12). Your global Python 3.9 cannot run this API.'
  [[ ! -e "$ROOT/backend/venv" ]] || fail 'backend/venv exists but is incompatible. Rename it, then run this script again to create a Python 3.11+ environment.'
  "$PYTHON" -m venv "$ROOT/backend/venv"
  PYTHON="$ROOT/backend/venv/bin/python"
fi

NODE=''
if [[ -n ${LEARNING_NODE:-} ]]; then
  valid_node "$LEARNING_NODE" || fail 'LEARNING_NODE must point to Node 20.19+, 22.12+, or a newer supported major.'
  NODE="$LEARNING_NODE"
else
  for candidate in "$(command -v node || true)" /usr/local/bin/node /usr/bin/node \
    "$HOME"/.asdf/installs/nodejs/*/bin/node \
    "$HOME"/.local/share/mise/installs/node/*/bin/node \
    "$HOME"/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node; do
    if valid_node "$candidate"; then NODE="$candidate"; break; fi
  done
fi
[[ -n $NODE ]] || fail 'Install Node 22.12+ (or set LEARNING_NODE). Node 20.18 cannot run the current Vite reliably.'
export PATH="$(dirname -- "$NODE"):$PATH"
printf 'Python: %s (%s)\n' "$("$PYTHON" --version)" "$PYTHON"
printf 'Node:   %s (%s)\n' "$("$NODE" --version)" "$NODE"

if ! "$PYTHON" -c 'import fastapi, uvicorn, dotenv, groq, google.genai, ollama' >/dev/null 2>&1; then
  printf 'Installing API dependencies into backend/venv…\n'
  "$PYTHON" -m pip install -r "$ROOT/backend/requirements-runtime.txt"
fi
if [[ ! -f "$ROOT/frontend/node_modules/vite/bin/vite.js" ]]; then
  NPM=''
  for candidate in "$(dirname -- "$NODE")/../lib/node_modules/npm/bin/npm-cli.js" \
    /usr/share/nodejs/npm/bin/npm-cli.js \
    "$HOME"/.asdf/installs/nodejs/*/lib/node_modules/npm/bin/npm-cli.js; do
    if [[ -f $candidate ]]; then NPM="$candidate"; break; fi
  done
  [[ -n $NPM ]] || fail 'Install npm, run npm ci in frontend, then retry.'
  printf 'Installing frontend dependencies…\n'
  (cd "$ROOT/frontend" && "$NODE" "$NPM" ci)
fi
# Import the complete API now, so syntax/dependency errors are caught before launch.
(cd "$ROOT/backend" && "$PYTHON" -c 'import app')
[[ ${1:-} != --check ]] || { printf 'Runtime checks passed.\n'; exit 0; }
command -v setsid >/dev/null || fail 'This launcher needs setsid (Ubuntu: util-linux).'

"$PYTHON" - <<'PY'
import socket
import sys
for port in (8000, 5173):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('127.0.0.1', port))
        except OSError:
            sys.exit(f'Port {port} is busy. Stop the existing server in its terminal, then run ./run.sh again.')
PY

mkdir -p "$ROOT/.run"
BACKEND_PID=''
FRONTEND_PID=''
cleanup() {
  trap - EXIT INT TERM
  printf '\nStopping learning servers…\n'
  for pid in "$FRONTEND_PID" "$BACKEND_PID"; do
    if [[ -n $pid ]]; then kill -TERM -- "-$pid" 2>/dev/null || true; fi
  done
  for pid in "$FRONTEND_PID" "$BACKEND_PID"; do
    if [[ -n $pid ]]; then wait "$pid" 2>/dev/null || true; fi
  done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(cd "$ROOT/backend" && exec setsid "$PYTHON" -m uvicorn app:app --reload --host 127.0.0.1 --port 8000) >"$ROOT/.run/backend.log" 2>&1 &
BACKEND_PID=$!
(cd "$ROOT/frontend" && exec setsid "$NODE" node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort) >"$ROOT/.run/frontend.log" 2>&1 &
FRONTEND_PID=$!
printf 'Starting servers. Logs: %s/.run/{backend,frontend}.log\n' "$ROOT"
if ! "$PYTHON" - <<'PY'
import time
import urllib.request
pending = {'AI API': 'http://127.0.0.1:8000/api/health', 'Frontend': 'http://127.0.0.1:5173/'}
deadline = time.monotonic() + 45
while pending and time.monotonic() < deadline:
    for name, url in list(pending.items()):
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    print(f'{name} ready: {url}', flush=True)
                    del pending[name]
        except (OSError, ValueError):
            pass
    if pending:
        time.sleep(0.5)
if pending:
    raise SystemExit('Startup timed out: ' + ', '.join(pending))
PY
then
  tail -n 20 "$ROOT/.run/backend.log" "$ROOT/.run/frontend.log"
  fail 'Server startup failed. See the logs above.'
fi
printf '\nOpen http://127.0.0.1:5173 — AI backend is connected.\n'
printf 'Provider configuration is ready; live AI calls still depend on your key and quota.\n'
printf 'Keep this terminal open. Press Ctrl+C to stop both servers.\n'
set +e
wait -n "$BACKEND_PID" "$FRONTEND_PID"
STATUS=$?
set -e
printf 'A server stopped (exit %s). See .run logs.\n' "$STATUS" >&2
exit "$STATUS"
