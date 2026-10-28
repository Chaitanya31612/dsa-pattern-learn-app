#!/usr/bin/env bash
# Package and run/deploy the SAME FastAPI source in Cloudflare Python Workers.
set -Eeuo pipefail
shopt -s nullglob
BACKEND="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMMAND=${1:-help}
[[ $# == 0 ]] || shift
if [[ $COMMAND == help || $COMMAND == --help ]]; then
  printf 'Usage: ./backend/cloudflare.sh prepare|check|dev|deploy|login|secret [arguments]\n'
  printf 'check = build a deployable Worker locally, without uploading.\n'
  exit 0
fi
case "$COMMAND" in prepare|check|dev|deploy|login|secret) ;; *) printf 'Unknown command: %s\n' "$COMMAND" >&2; exit 1 ;; esac

PYTHON=''
for candidate in "$BACKEND/venv/bin/python" "$(command -v python3 || true)" /usr/bin/python3.1{4,3,2,1}; do
  if [[ -x $candidate ]] && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3,11))' 2>/dev/null; then PYTHON="$candidate"; break; fi
done
[[ -n $PYTHON ]] || { printf 'Python 3.11+ is needed for packaging. Run ./run.sh --check first.\n' >&2; exit 1; }
"$PYTHON" "$BACKEND/cloudflare/prepare.py"
[[ $COMMAND != prepare ]] || exit 0
BUILD="$BACKEND/.cloudflare"

NODE=''
for candidate in "${LEARNING_NODE:-}" "$(command -v node || true)" \
  "$HOME"/.asdf/installs/nodejs/*/bin/node /usr/local/bin/node /usr/bin/node \
  "$HOME"/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node; do
  if [[ -x $candidate ]] && "$candidate" -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(Number(!(a>22||(a===22&&b>=12))))' 2>/dev/null; then NODE="$candidate"; break; fi
done
[[ -n $NODE ]] || { printf 'Install a supported Node LTS (22.12+ or 24) for Wrangler.\n' >&2; exit 1; }
NPM_CLI=''
for candidate in "$(dirname -- "$NODE")/../lib/node_modules/npm/bin/npm-cli.js" \
  /usr/share/nodejs/npm/bin/npm-cli.js "$HOME"/.asdf/installs/nodejs/*/lib/node_modules/npm/bin/npm-cli.js; do
  if [[ -f $candidate ]] && "$NODE" -e 'const p=require("node:path");const v=require(p.resolve(p.dirname(process.argv[1]),"../package.json")).version;process.exit(Number(parseInt(v)<10))' "$candidate" 2>/dev/null; then NPM_CLI="$candidate"; break; fi
done
[[ -n $NPM_CLI ]] || { printf 'Install npm 10+ before running Cloudflare tooling.\n' >&2; exit 1; }
# The bundled Node binary may not include npm. Use the installed npm CLI with
# that Node, without changing the user's global asdf selection.
mkdir -p "$BUILD/tools" "$BUILD/npm-prefix/lib"
for tool in npm npx; do
  cli="$(dirname -- "$NPM_CLI")/${tool}-cli.js"
  if [[ $tool == npx ]]; then
    printf '#!/usr/bin/env bash\nexec %q %q --package=wrangler@4.154.0 "$@"\n' "$NODE" "$cli" > "$BUILD/tools/$tool"
  else
    printf '#!/usr/bin/env bash\nexec %q %q "$@"\n' "$NODE" "$cli" > "$BUILD/tools/$tool"
  fi
  chmod +x "$BUILD/tools/$tool"
done
export PATH="$BUILD/tools:$(dirname -- "$NODE"):$PATH"
export npm_config_prefix="$BUILD/npm-prefix"
UV=$(command -v uv || true)
if [[ -z $UV && -x "$BACKEND/venv/bin/uv" ]]; then UV="$BACKEND/venv/bin/uv"; fi
if [[ -z $UV ]]; then
  if [[ ! -x "$BUILD/tooling/bin/uv" ]]; then
    "$PYTHON" -m venv "$BUILD/tooling"
    "$BUILD/tooling/bin/python" -m pip install 'uv==0.13.6'
  fi
  UV="$BUILD/tooling/bin/uv"
fi
export PATH="$(dirname -- "$UV"):$PATH"
cd "$BUILD"
case "$COMMAND" in
  check) exec "$UV" run --locked --python 3.13 pywrangler deploy --dry-run "$@" ;;
  *) exec "$UV" run --locked --python 3.13 pywrangler "$COMMAND" "$@" ;;
esac
