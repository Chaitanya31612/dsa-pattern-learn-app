# Cloudflare Worker Deploy

Deployment README for **DSA Pattern Lab / Pattern First**.

This guide documents the implementation and deployment commands. URLs, account names, and machine paths use placeholders. Keep your actual deployment details in ignored local files or your password manager.

### Find what you need

- [Deployment overview](#1-deployment-overview)
- [Personal key: purpose and scope](#2-is-the-personal-access-key-only-for-this-project)
- [Where the key is stored](#3-where-is-the-personal-key-stored)
- [Architecture and changed files](#4-architecture-the-same-backend-a-different-server-adapter)
- [Toolchain and deployment commands](#7-toolchain-used)
- [Secret provisioning](#9-how-the-secrets-were-configured)
- [Netlify connection](#10-netlify-setup-the-remaining-connection-step)
- [Routes and protection](#11-api-routes-and-what-is-supported)
- [Tests and smoke-test commands](#13-checks-and-tests-actually-run)
- [Setup problems and fixes](#14-investigation-problems-and-how-they-were-resolved)
- [Troubleshooting](#15-common-errors)
- [Updates, rotation, and recovery](#16-updating-rotating-and-recovering)
- [Optional GitHub integration](#17-optional-github-deployment-integration)
- [Complete deployment source snapshots](#18-source-snapshots)

For an ordinary code update, the two commands are `./backend/cloudflare.sh check` and `./backend/cloudflare.sh deploy`. You do not need to recreate secrets for each code deployment.

## 1. Deployment overview

- Worker name: `patternfirst-ai` in the shared configuration. Choose your own if needed.
- Example Worker URL: `https://your-worker.your-subdomain.workers.dev`.
- Configuration check: append `/api/health` to your Worker URL.
- Example frontend URL: `https://your-app.netlify.app`.
- Runtime: Cloudflare **Python Workers**, serving the original FastAPI app.
- Runtime secret names: `GROQ_API_KEY`, `GEMINI_API_KEY`, `AI_ACCESS_TOKEN`.

Replace example URLs with your own when configuring your deployment. Do not commit account URLs, deployment IDs, personal machine paths, or credential values to this guide.

This setup does not require a persistent database, custom domain, or model-hosting service. Provider quotas and hosting limits still apply.

## 2. Is the personal access key only for this project?

**Yes, in this setup it is the shared access key for this project's `patternfirst-ai` backend.**

It is not a Cloudflare account API token. It is not your Groq or Gemini API key.

Think of the three credentials as three different doors:

```text
Cloudflare login / OAuth token
    → lets your deployment tooling manage Workers under its granted permissions

Personal AI_ACCESS_TOKEN
    → lets the learning app call this Worker's protected API endpoints

GROQ_API_KEY / GEMINI_API_KEY
    → lets the backend call the AI provider
```

The personal key covers all protected features on this Worker: DSA, mock interviews, LLD, HLD, Software Learnings, and AI Learnings. It is not a separate key for each course or question.

Sites in your configured origin list can use the same Worker and key. Command-line clients can also call the Worker with the key. `/api/health` and browser preflight requests do not require it.

It does **not** grant permission to deploy code, manage your Cloudflare account, reveal the provider secrets, or use unrelated projects automatically. It does let the holder use this backend's AI features and consume the associated provider quota.

The project scope comes from configuring this value as a secret on this Worker. The string itself is not cryptographically tied to a repository. If you deliberately reuse it in another project, that project can accept the same string too. Use a different value for each project.

This is a **shared personal-use key**, not a user account system:

- No individual user identity or roles.
- No automatic expiry.
- Anyone holding it can make authorized requests.
- Replacing the Worker secret invalidates old copies for this backend.
- Local Uvicorn does not require this key. Its hosted-only protection is applied by the Worker adapter.

## 3. Where is the personal key stored?

With this setup:

- Cloudflare: the `AI_ACCESS_TOKEN` runtime secret on `patternfirst-ai`.
- Optional local copy: `backend/.cloudflare/personal-access-key.txt`. Prefer a password manager.
- Local Worker testing: `backend/cloudflare/.dev.vars` contains its local test value.
- Browser: after you save it in Settings, it is stored under `patternfirst-hosted-ai-access` in `sessionStorage`.

The local secret files are ignored by Git. If you create a personal-key text file, give it owner-only permissions (`600`). It is a plaintext convenience copy; keep it private or move the value to a password manager.

Browser storage is for the current tab session. Refreshing preserves it. A separate tab/browser may need the key entered again; browser tab duplication/restoration can copy or restore session state. It is not included in progress exports.

Never commit the personal key, paste it into an issue/chat, or put it in a public `VITE_*` variable. Never enter a Groq/Gemini provider key in the personal-key Settings field.

## 4. Architecture: the same backend, a different server adapter

```text
Netlify-hosted Vue frontend
    │
    │ HTTPS request
    │ Authorization: Bearer <personal access key>
    ▼
Cloudflare Python Worker
    ├─ worker.py
    ├─ HostedAPI: access key, allowed origins, body size, throttling
    └─ original FastAPI app
         ├─ app.py: DSA, mock interview, LLD endpoints
         ├─ hld_api.py: HLD chat and assessment
         ├─ software_api.py: Software chat and assessment
         ├─ ai_learning_api.py: same course router using the AI catalog
         └─ existing ai/ provider adapters
               │
               ▼
          Groq / Gemini API
```

Locally, Uvicorn serves the original app. On Cloudflare, `workers.asgi` serves it. Routes, teaching prompts, context selection, reference solutions, rubric validation, and provider adapters were **not rewritten into TypeScript**.

There are two intentional hosting boundaries:

1. The Worker adds access protection around the original app.
2. Custom-problem scraping and disk-backed storage remain local-only.

## 5. Files added and changed

### Backend additions

- `backend/worker.py`: imports the existing app, warms its read-only catalog caches, and exports Cloudflare's ASGI entry point.
- `backend/cloudflare_adapter.py`: hosted-only ASGI wrapper.
- `backend/cloudflare/prepare.py`: builds an allowlisted source bundle.
- `backend/cloudflare/wrangler.jsonc`: shared runtime defaults; localhost origins only.
- `backend/cloudflare/wrangler.local.example.json`: safe example for an ignored local origin override.
- `backend/cloudflare/pyproject.toml`: Python Worker dependencies and tooling.
- `backend/cloudflare/uv.lock`: locked local/tooling dependency resolution.
- `backend/cloudflare/pylock.toml`: locked package resolution for the Python/WebAssembly runtime.
- `backend/cloudflare/.dev.vars.example`: placeholders for local testing, not real secrets.
- `backend/cloudflare.sh`: packaging, local testing, authentication, deployment, and secret-management launcher.
- `backend/tests/test_cloudflare.py`: hosting-boundary and packaging tests.

### Frontend additions and changes

- `frontend/src/lib/aiConnection.ts`: reads the personal key from session storage, builds request headers, and resolves the backend URL.
- `frontend/src/lib/aiConnection.test.ts`: tests saved/cleared keys, URL configuration, and unavailable storage.
- `frontend/src/views/SettingsView.vue`: personal access-key input, save/clear actions, and explanatory text.
- `useAIChat.ts`, `useMockInterview.ts`, `useLLDInterview.ts`: attach the personal key; handle unauthorized hosted requests.
- `HLDAssessment.vue` and `SoftwareModuleView.vue`: attach the key to assessment requests.
- `DetailedAnalysisView.vue`: attach the key and use the configured backend URL. Previously, DSA analysis used a hard-coded same-site `/api/analyze-code` URL.
- `CustomProblemsView.vue`: attaches the key to its backend requests. The Worker explicitly responds that those features remain local-only.
- `frontend/package.json`: includes the connection tests in `test:learning`.
- `.gitignore`: excludes deployment caches, vendored packages, local secret files, and generated bundles.

### What stayed unchanged

The original implementation in `app.py`, `hld_api.py`, `software_api.py`, `ai_learning_api.py`, and `ai/*.py` was reused. The local requirements files and `./run.sh` were preserved. Course data and progress IDs were not changed by this deployment.

## 6. What the generated deployment folder contains

`backend/cloudflare/prepare.py` creates:

```text
backend/.cloudflare/                    # ignored build/tooling directory
├── src/
│   ├── worker.py
│   ├── cloudflare_adapter.py
│   ├── app.py                         # copied unchanged from backend/app.py
│   ├── hld_api.py
│   ├── software_api.py
│   ├── ai_learning_api.py
│   ├── ai/*.py
│   └── pipeline/data/
│       ├── db.json
│       ├── hld-course.json
│       ├── software-course.json
│       └── ai-course.json
├── wrangler.jsonc
├── pyproject.toml
├── uv.lock
├── pylock.toml
├── .dev.vars                         # only if explicitly provided locally
├── personal-access-key.txt           # local deployment convenience copy
├── tools/                            # compatible npm/npx wrappers
├── python_modules/                   # vendored by pywrangler
└── .venv*/                           # local packaging/runtime tooling
```

Only the curated `src` files, relevant configuration, and required runtime dependencies form the Worker bundle. Files elsewhere in the local build directory are not automatically API source modules.

The bundle excludes `backend/.env`, local virtual environments, tests, scraping scripts, and private work-project files. Secret values are installed separately through Cloudflare's secret API.

This is packaging, like making a deployment archive. It is not a second implementation. Edit the original source, then rebuild. Do not edit `.cloudflare/src` directly.

The source subtree is replaced on preparation. Tooling caches outside it are retained. If you are testing a local Worker, rerun the launcher after changing original backend source or course JSON so the updated files are packaged.

## 7. Toolchain used

Tooling requirements and pins:

- Packaging: Python 3.11+.
- Worker dependency manifest: Python 3.13+.
- Node: 22.12+ or a newer major, with npm 10+.
- uv bootstrap pin: `0.13.6`.
- Wrangler launcher pin: `4.154.0`.

Different Python environments have different jobs. Your local app does not need to switch to the Worker's Python version. The launcher does not change global asdf settings.

The launcher needs Python 3.11+ for packaging, compatible Node 22.12+ or a newer major, and npm 10+. The Worker dependency manifest declares Python 3.13+. The compatibility settings and Python tooling determine the actual Worker interpreter.

## 8. Commands used: installation, checks, login, deployment

Commands below start from the repository root unless a different directory is shown.

```bash
cd /path/to/DSAPatternLearnApp
```

### Install the Python deployment tool

This was run in the existing backend virtual environment:

```bash
cd backend
venv/bin/python -m pip install uv
cd ..
```

The installed version was 0.13.6. For a repeatable new installation, you can pin it:

```bash
backend/venv/bin/python -m pip install 'uv==0.13.6'
```

The launcher can also bootstrap its pinned uv into an ignored tooling environment if no suitable uv executable is found.

### Make the launcher executable and check shell syntax

```bash
chmod +x backend/cloudflare.sh
bash -n backend/cloudflare.sh
```

### Keep your site URLs out of Git

The tracked configuration permits localhost only. Before your first hosted deployment:

```bash
cp backend/cloudflare/wrangler.local.example.json backend/cloudflare/wrangler.local.json
```

Edit `ALLOWED_ORIGINS` in the new **ignored** file. Use your frontend origins, without paths or trailing slashes. Keep actual account URLs and private deployment notes out of committed files.

The packaging script merges this local file into ignored `backend/.cloudflare/wrangler.jsonc`. It accepts only `ALLOWED_ORIGINS` and `AI_REQUESTS_PER_MINUTE` under `vars`. Provider credentials belong in runtime secrets.

For GitHub builds, set `CLOUDFLARE_ALLOWED_ORIGINS` in the Cloudflare build environment. This overrides the local/default origin list without storing your site URLs in Git. Keep runtime secrets configured separately on the Worker.

### Prepare the bundle

```bash
./backend/cloudflare.sh prepare
```

### Perform a deployment dry run

```bash
./backend/cloudflare.sh check
```

Internally, after packaging and toolchain setup, this runs from `backend/.cloudflare`:

```bash
uv run --locked --python 3.13 pywrangler deploy --dry-run
```

`pywrangler` resolves/vendors Python dependencies and invokes Wrangler. The launcher pins the npx package to `wrangler@4.154.0`.

The successful final dry run reported approximately **32,736 KiB uncompressed** and **7,452 KiB compressed**, including vendored dependencies. Those numbers describe this build, not an allowance or a permanent size guarantee.

### Run the Worker locally

```bash
./backend/cloudflare.sh dev --port 8788 --log-level error
```

Port 8787 was also used during the initial compatibility investigation. The local Worker runs through workerd, not your normal Uvicorn process.

`--log-level error` was used for `dev` to keep its module listing out of the terminal. It is not a supported flag for the pinned `deploy` command.

### Sign into Cloudflare

```bash
./backend/cloudflare.sh login
```

Complete the browser sign-in yourself. Wrangler stored its OAuth credentials in the user's local Wrangler configuration, outside this repository. Those credentials were not added to source control or bundled into the app.

Verify the sign-in through the prepared local npx wrapper:

```bash
(
  cd backend/.cloudflare
  npm_config_prefix="$PWD/npm-prefix" ./tools/npx --yes wrangler whoami
)
```

### Deploy the same Python backend

```bash
./backend/cloudflare.sh deploy
```

To capture deployment output locally:

```bash
./backend/cloudflare.sh deploy > /tmp/patternfirst-cloudflare-deploy.log 2>&1
```

Internally:

```bash
uv run --locked --python 3.13 pywrangler deploy
```

Cloudflare returns your Worker URL after deployment. Copy it into your private setup notes. Without runtime secrets, the adapter returns a configuration error rather than permitting anonymous AI use.

## 9. How the secrets were configured

### Optional local provisioning script

The following script can:

1. Read the existing provider keys from `backend/.env`.
2. Read the personal key created for local Worker testing from `backend/cloudflare/.dev.vars`.
3. Select only `GROQ_API_KEY`, `GEMINI_API_KEY`, and `AI_ACCESS_TOKEN`.
4. Send the JSON to `./backend/cloudflare.sh secret bulk` through **standard input**.
5. Redact secret values from any captured command output before displaying it.
6. Save only the personal key to `backend/.cloudflare/personal-access-key.txt`, with mode `600`.

The personal key was generated with Python's `secrets.token_hex(32)`: 32 random bytes represented as 64 hexadecimal characters. The adapter accepts a configured key of at least 32 characters.

Run this only for initial setup or an intentional credential update. It contains no credential values:

```python
import json
import secrets
import subprocess
from pathlib import Path
from dotenv import dotenv_values

root = Path.cwd()
values = dotenv_values(root / 'backend/.env')
local = dotenv_values(root / 'backend/cloudflare/.dev.vars')
token = local.get('AI_ACCESS_TOKEN') or secrets.token_hex(32)
assert len(token) >= 32

payload = {
    key: values[key]
    for key in ('GROQ_API_KEY', 'GEMINI_API_KEY')
    if values.get(key)
}
assert payload, 'No configured cloud provider keys found.'
payload['AI_ACCESS_TOKEN'] = token

result = subprocess.run(
    [str(root / 'backend/cloudflare.sh'), 'secret', 'bulk'],
    input=json.dumps(payload),
    text=True,
    capture_output=True,
    cwd=root,
)
output = result.stdout + '\n' + result.stderr
for value in payload.values():
    output = output.replace(value, '[redacted]')
print(output[-1800:])
if result.returncode:
    raise SystemExit(result.returncode)

path = root / 'backend/.cloudflare/personal-access-key.txt'
path.write_text(token + '\n')
path.chmod(0o600)
```

Successful output lists the created secret **names**, not their values.

Do not rerun bulk secret provisioning casually. It is for initial setup or deliberate credential updates. Changing `backend/.env` alone does not update Cloudflare, and changing a Cloudflare secret does not update your local files automatically.

### Normal future secret updates

Use the interactive prompt so values do not appear in command arguments:

```bash
./backend/cloudflare.sh secret put GROQ_API_KEY
./backend/cloudflare.sh secret put GEMINI_API_KEY
./backend/cloudflare.sh secret put AI_ACCESS_TOKEN
```

Alternatively, use Worker → Settings → Variables and Secrets in Cloudflare. Choose **Secret**, not plain text. Build-time variables and runtime secrets are different; the app needs runtime secrets.

Never put provider keys in `wrangler.jsonc`, a committed environment file, frontend source, or a `VITE_*` variable.

## 10. Netlify setup: the remaining connection step

In the existing Netlify project, configure this public build variable:

```text
VITE_API_BASE_URL=https://your-worker.your-subdomain.workers.dev
```

Apply it to the **Git `dev` branch deployment**, then trigger a rebuild. Netlify's local-development context named `dev` is not the same thing as a branch deployment from a Git branch named `dev`.

This variable contains a URL, not a secret. Vite embeds `VITE_*` variables into browser code, which is why provider keys and the personal access key must not go there.

After the rebuild:

1. Open <https://dev--your-app.netlify.app/settings>.
2. Find **Hosted AI connection**.
3. Copy the personal key from its local file or password manager.
4. Paste it into **Personal AI access key** and save.
5. Open a course lesson and ask a question.
6. Submit practice, then explicitly request AI feedback. Saving an attempt alone does not call AI.

You can stop the local Python backend after this hosted connection is working. Existing browser progress remains stored locally; this deployment does not add cloud progress synchronization.

## 11. API routes and what is supported

These routes still use the original backend implementations:

- `GET /api/health`: selected provider/model and configuration health; it does not perform an inference request.
- `POST /api/ai/pattern-chat`: DSA pattern/subpattern learning chat.
- `POST /api/ai/problem-chat`: DSA problem chat.
- `POST /api/analyze-code`: submitted DSA code analysis.
- `POST /api/mock-interview/respond`: DSA interview replies/debrief handling.
- `POST /api/lld-interview/respond`: LLD coaching.
- `POST /api/ai/hld-chat`: HLD coaching.
- `POST /api/hld/evaluate`: HLD assessment.
- `POST /api/ai/software-chat`: Software Learnings coaching.
- `POST /api/software/evaluate`: Software Learnings assessment.
- `POST /api/ai/ai-course-chat`: AI Learnings coaching.
- `POST /api/ai-course/evaluate`: AI Learnings assessment.

The hosted boundary returns **501** for `/api/process-leetcode` and `/api/custom-problems`. Those features depend on scraping or server-disk storage and were not migrated to a persistent hosted service.

The presence of the Ollama adapter in the packaged source does not host Ollama on Cloudflare. Local Ollama remains a local-server option.

## 12. Request protection and runtime behaviour

For each HTTP request, the hosting adapter:

1. Checks the browser Origin, if one was supplied.
2. Answers allowed preflight requests without requiring an access key.
3. Refuses to serve the configured backend if `AI_ACCESS_TOKEN` is missing or too short.
4. Requires `Authorization: Bearer <key>` for routes other than `/api/health`.
5. Compares the supplied credential using `hmac.compare_digest`.
6. Applies a best-effort request limit to authenticated requests.
7. Rejects local-only custom-problem routes.
8. Checks that a cloud provider key is configured.
9. Adapts Worker bindings to the existing provider factory's environment-variable contract and refreshes the cached analyzer when those values change.
10. Rejects request bodies above 128 KiB, including chunked bodies with no trusted length header.
11. Calls the original FastAPI app and replaces its local wildcard CORS response with the hosted origin policy.

The configured limit is **12 authenticated requests per minute per Worker instance**. It is not a shared, durable, account-wide quota. Multiple instances have separate counters, and counters can reset. Provider-side quotas still apply.

CORS limits browser access; it is not authentication. A command-line client can omit Origin. Such a client still needs the personal access key.

Allowed origins are listed in `backend/cloudflare/wrangler.jsonc`. Changing a site/domain requires updating that list and redeploying. Avoid adding paths or trailing slashes to origins.

Provider selection preserves the original behaviour: Groq is preferred when its key is present. If Groq construction fails, the existing factory resolves its fallback; Gemini is available without a configured Groq key. There is no automatic switch to Gemini after every failed Groq API call. Merely setting `DEFAULT_AI_PROVIDER` does not override the Groq-first code in `get_analyzer()`.

## 13. Checks and tests actually run

### Backend tests

```bash
cd backend
venv/bin/python -m pytest tests -q
cd ..
```

Result: **34 passed**. There was an existing Starlette/httpx TestClient deprecation warning.

Hosting-specific tests cover missing/wrong keys, missing configuration, origin checks, preflight, body size, throttling, local-only routes, and exact source packaging without `.env` or scraping scripts.

### Frontend tests

The test runner was invoked directly with the compatible Node binary:

```bash
cd frontend
node \
  node_modules/vitest/vitest.mjs run \
  src/lib/hldLearning.test.ts \
  src/lib/softwareLearning.test.ts \
  src/lib/softwareLabs.test.ts \
  src/lib/aiLearning.test.ts \
  src/lib/reading.test.ts \
  src/lib/aiConnection.test.ts
cd ..
```

Result: **43 passed**, for **77 tests total** with the backend suite. With a compatible Node selected in your terminal, the normal equivalent is `npm run test:learning` from `frontend`.

### Type checking and production build

```bash
cd frontend
node \
  node_modules/vue-tsc/bin/vue-tsc.js -b
node \
  node_modules/vite/bin/vite.js build
cd ..
```

Both passed. Vite reported the existing large-bundle warning. With a compatible terminal runtime, `npm run build` performs these checks.

### Local compatibility tests

- The original FastAPI app imported in the Python Worker runtime.
- The existing Groq SDK made a real provider call without a transport rewrite.
- Software and AI Learnings chat returned real responses.
- HLD assessment loaded its reference and returned a validated eight-part rubric.
- Missing access keys were rejected.
- The ordinary local Uvicorn backend remained healthy.
- Settings save/clear was tested with synthetic data, then cleared.
- The Settings form was checked at a phone-sized viewport with no page overflow.
- A screenshot is saved at `docs/screenshots/cloudflare-ai-settings.png`.

### Public deployment tests

Against the actual `workers.dev` URL, using Python `requests`:

- Health returned 200 and identified Groq / `openai/gpt-oss-120b`.
- An AI request without the personal key returned 401.
- Software Learnings chat returned a real provider reply.
- HLD assessment returned a valid AI rubric after loading the course reference.
- Authorized browser-origin responses carried the expected CORS header.

Other routes are present in the reused app and covered by existing tests as applicable. This is not a claim that every route received a live production inference test.

### Safe repeatable smoke test

This reads the personal key locally and sends it in a header, without printing it or putting it in the URL/command arguments. It uses a synthetic lesson question. The chat request consumes provider quota.

```bash
backend/venv/bin/python - <<'PY'
import json
from pathlib import Path
import requests

base = 'https://your-worker.your-subdomain.workers.dev'
token = Path('backend/.cloudflare/personal-access-key.txt').read_text().strip()
origin = 'https://dev--your-app.netlify.app'

r = requests.get(base + '/api/health', timeout=30)
r.raise_for_status()
print('Health:', r.json())

module = json.loads(Path('backend/pipeline/data/software-course.json').read_text())['modules'][0]
payload = {
    'module_id': module['id'],
    'section_id': module['sections'][0]['id'],
    'messages': [{'role': 'user', 'content': 'Explain the main idea in one short sentence.'}],
}
r = requests.post(
    base + '/api/ai/software-chat',
    json=payload,
    headers={'Authorization': 'Bearer ' + token, 'Origin': origin},
    timeout=90,
)
r.raise_for_status()
assert r.json()['reply'].strip()
print('Authorized chat succeeded.')
PY
```

For a health-only check with no inference:

```bash
curl -fsS https://your-worker.your-subdomain.workers.dev/api/health
```

### Source-control checks

```bash
git diff --cached --check
git commit -m 'feat: host the existing Python AI backend on Cloudflare'
git push origin dev
```

Before committing, check staged files for private deployment details and credentials. A direct CLI deployment does not require another Git commit.

## 14. Investigation problems and how they were resolved

These are historical notes, not commands you need to repeat.

### pywrangler refused the existing requirements.txt

The initial experiment ran Python tooling directly in `backend`. The tool refused to continue while `requirements.txt` existed there.

Resolution: preserve the local requirements files, place Worker manifests under `backend/cloudflare`, and prepare an isolated deployment directory with no requirements.txt. The API source is copied into that build directory unchanged.

### Broad module discovery collected virtual environments

An early temporary bundle used the project root as its source root. Module discovery included tooling files and produced an unnecessarily large module list.

Resolution: put only allowlisted application source in a dedicated `src` directory and use `src/worker.py` as the entry point. Vendored dependencies remain separate under pywrangler's management.

### A custom PythonModule rule was rejected

The attempted explicit `PythonModule` configuration rule was not accepted by Wrangler's user-facing rule validation.

Resolution: let Wrangler apply its built-in Python handling and declare only the JSON `Data` rule explicitly.

### Bundled Node had no adjacent npm installation

The compatible Node executable did not ship with npm next to it. npm's inferred global prefix also pointed to a missing library directory.

Resolution: invoke an installed modern npm CLI using the compatible Node executable. Add local wrappers and an ignored local npm prefix. Global runtime selections remain unchanged.

### Old npx resolved an unrelated deploy command

The first helper selected an obsolete npm installation. Its npx behaviour resolved an unrelated deployment package, which asked for its own authentication and failed without receiving credentials.

Resolution: require npm 10+ and explicitly pin `wrangler@4.154.0`. The corrected helper was verified with a successful Cloudflare dry run and actual deployment.

### log-level was accepted for dev, not deploy

A diagnostic attempt passed `--log-level error` to the deploy dry run and was rejected as an unknown argument.

Resolution: run `./backend/cloudflare.sh check` without that extra flag. The final plain dry run passed.

### One early public health probe returned 403

An initial urllib probe received 403. A subsequent curl request returned 200, and the complete requests-based public smoke test passed. The exact cause of the first 403 was not established. No origin policy or other protection was disabled to make the tests pass.

## 15. Common errors

- **401:** missing/wrong personal key. Set it in app Settings and retry.
- **403 with the adapter's JSON message:** the browser origin is not allowed. Check the configured origin list. Other 403 responses may come from an edge/network layer; inspect the response before changing app policy.
- **413:** request above 128 KiB. Shorten the draft, conversation, or diagram.
- **429:** per-instance throttling or provider quota. Wait and retry; inspect which service returned the error.
- **501:** custom-problem scraping/storage is a local-only feature.
- **503:** missing Worker secrets or unavailable provider. Course endpoints return a useful error; some older endpoints can instead return their existing fallback message.
- **Local connection refused on 8000:** local Python server stopped or crashed. Use `./run.sh` rather than a Python 3.9 global uvicorn.
- **Worker resource/CPU error:** inspect actual hosted metrics. The catalog caches are warmed at Worker initialization, but future content/dependency growth still needs testing against the selected plan's current limits.
- **Local edit not visible in Worker dev:** rerun the launcher to package the original source again.
- **New Netlify backend URL not used:** rebuild after setting the variable and check that it applies to the correct branch-deploy context. A Vite development proxy is not a deployed backend.

## 16. Updating, rotating, and recovering

### Deploy a code or course-data update

```bash
./backend/cloudflare.sh check
./backend/cloudflare.sh deploy
```

Use `git add`, commit, and push separately when you want the repository to record the change. A direct CLI deployment does not require a GitHub integration.

### Rotate the personal access key

1. Generate a fresh random value locally: `openssl rand -hex 32`.
2. Run `./backend/cloudflare.sh secret put AI_ACCESS_TOKEN` and enter that value at its prompt, or replace the runtime secret in Cloudflare's dashboard.
3. Update your password manager/local personal-key file. If you use local Worker testing, update its `.dev.vars` value separately.
4. Save the new value in app Settings for each tab/session that needs it.
5. Check that the old value is rejected.

The secret update does not automatically synchronize local copies or browser storage. Rotating this personal key does not require rotating Groq/Gemini provider keys unless those provider keys were themselves exposed.

### Recover access on a new computer

There is no API that reveals the stored personal key. Use your password manager/local backup, or set a new runtime value through your authorized Cloudflare account and update the browser.

### Continue using the local backend

```bash
./run.sh
```

This uses the original Python backend on 8000. For the frontend to use it, run locally without a hosted `VITE_API_BASE_URL` override. The Cloudflare personal key is not required by local Uvicorn.

## 17. Optional GitHub deployment integration

This integration was documented, not configured as part of the direct CLI deployment.

In Cloudflare, select the Worker → Settings → Builds → Connect GitHub:

1. Grant access to `YOUR_GITHUB_USER/YOUR_REPOSITORY`.
2. Select branch `dev` while testing.
3. Root directory: `backend`.
4. Build command: `./cloudflare.sh prepare`.
5. Deploy command: `./cloudflare.sh deploy`.
6. Worker name: `patternfirst-ai`, matching the configuration.
7. Set `CLOUDFLARE_ALLOWED_ORIGINS` in the build environment to your comma-separated frontend origins.
8. Optionally watch `backend/**` to avoid unrelated frontend-only builds.

Runtime secrets remain in the Worker settings. They are not Git build variables. Check the integration's first build before relying on automatic deployments.

## 18. Source snapshots

The following sections contain the deployment code as it existed when this README was written. They are documentation snapshots. The linked source files are authoritative when making future changes.

### 18.1. [backend/worker.py](backend/worker.py)

```python
"""Cloudflare entry point; routes and teaching logic stay in app.py."""
from workers import asgi
from app import app, load_db
from cloudflare_adapter import HostedAPI
from hld_api import catalog as hld_catalog
from software_api import catalog as software_catalog
from ai_learning_api import ai_catalog

# Populate the original read-only caches during Worker initialization, rather
# than parsing whole catalogs inside the free plan's per-request CPU budget.
for load in (load_db, hld_catalog, software_catalog, ai_catalog):
    load()

Default = asgi.entrypoint(HostedAPI(app))
```

### 18.2. [backend/cloudflare_adapter.py](backend/cloudflare_adapter.py)

```python
"""Hosting boundary only. FastAPI routes, context, and scoring are reused as-is."""
import hmac
import json
import os
import time
from collections import deque


def binding(env, name, default=''):
    value = env.get(name, default) if isinstance(env, dict) else getattr(env, name, default)
    return str(value) if value is not None else default


class HostedAPI:
    def __init__(self, application):
        self.application = application
        self.configuration = None
        self.requests = deque()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.application(scope, receive, send)
        env = scope.get('env', {})
        headers = dict(scope.get('headers', []))
        origin = headers.get(b'origin', b'').decode('latin-1')
        allowed = {s.strip() for s in binding(env, 'ALLOWED_ORIGINS').split(',') if s.strip()}
        cors = [(b'vary', b'Origin')]
        if origin and origin in allowed:
            cors += [(b'access-control-allow-origin', origin.encode()),
                     (b'access-control-allow-methods', b'GET, POST, OPTIONS'),
                     (b'access-control-allow-headers', b'Content-Type, Authorization')]

        async def reply(status, detail):
            await send({'type': 'http.response.start', 'status': status,
                        'headers': cors + [(b'content-type', b'application/json')]})
            await send({'type': 'http.response.body', 'body': b'' if status == 204 else json.dumps({'detail': detail}).encode()})

        if origin and origin not in allowed:
            return await reply(403, 'This website is not allowed to use this AI backend.')
        if scope['method'] == 'OPTIONS':
            return await reply(204, '')
        token = binding(env, 'AI_ACCESS_TOKEN')
        if len(token) < 32:
            return await reply(503, 'Set a Cloudflare AI_ACCESS_TOKEN secret of at least 32 characters.')
        if scope['path'] != '/api/health':
            provided = headers.get(b'authorization', b'')
            if not hmac.compare_digest(provided, ('Bearer ' + token).encode()):
                return await reply(401, 'Enter the hosted AI access key in application Settings, then retry.')
            # Best-effort per-isolate throttling, not an account-wide quota.
            now = time.monotonic()
            while self.requests and now - self.requests[0] >= 60:
                self.requests.popleft()
            try:
                limit = max(1, min(60, int(binding(env, 'AI_REQUESTS_PER_MINUTE', '12'))))
            except ValueError:
                limit = 12
            if len(self.requests) >= limit:
                return await reply(429, 'Too many AI requests. Wait a minute and retry.')
            self.requests.append(now)
        if scope['path'] in ('/api/process-leetcode', '/api/custom-problems'):
            return await reply(501, 'Custom problem fetching/storage uses the local Python server. Cloudflare hosts the AI endpoints only.')
        if not binding(env, 'GROQ_API_KEY') and not binding(env, 'GEMINI_API_KEY'):
            return await reply(503, 'Add a GROQ_API_KEY or GEMINI_API_KEY runtime secret in Cloudflare.')

        # Bindings are fixed for a deployed Worker version, never supplied by the
        # browser. Reuse the existing provider factory's environment contract.
        configuration = tuple(binding(env, key) for key in ('GROQ_API_KEY', 'GEMINI_API_KEY', 'DEFAULT_AI_MODEL'))
        if configuration != self.configuration:
            for key, value in zip(('GROQ_API_KEY', 'GEMINI_API_KEY', 'DEFAULT_AI_MODEL'), configuration):
                if value:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)
            from app import get_analyzer
            get_analyzer.cache_clear()
            self.configuration = configuration

        # Check actual bytes as well as Content-Length; chunked bodies have no
        # trustworthy length header. Existing Pydantic field limits still apply.
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            size += len(chunk)
            if size > 128 * 1024:
                return await reply(413, 'Request too large. Keep your question or submitted attempt under 128 KB.')
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()

        async def with_cors(message):
            if message['type'] == 'http.response.start':
                # Replace the local app's permissive CORS headers at this hosted
                # boundary. Local Uvicorn continues to use the original app.
                message = {**message, 'headers': [
                    (k, v) for k, v in message.get('headers', [])
                    if not k.lower().startswith(b'access-control-')
                ] + cors}
            await send(message)

        await self.application(scope, replay, with_cors)
```

### 18.3. [backend/cloudflare/prepare.py](backend/cloudflare/prepare.py)

```python
"""Package the original API, without .env, virtualenvs, tests, or scraping tools."""
from pathlib import Path
import json
import os
import shutil

BACKEND = Path(__file__).resolve().parents[1]
CONFIG = BACKEND / 'cloudflare'
BUILD = BACKEND / '.cloudflare'


def prepare():
    source = BUILD / 'src'
    # Only the generated source subtree is replaced; cached Python tooling stays.
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    for name in ('worker.py', 'cloudflare_adapter.py', 'app.py', 'hld_api.py', 'software_api.py', 'ai_learning_api.py'):
        shutil.copy2(BACKEND / name, source / name)
    (source / 'ai').mkdir()
    for path in (BACKEND / 'ai').glob('*.py'):
        shutil.copy2(path, source / 'ai' / path.name)
    data = source / 'pipeline/data'
    data.mkdir(parents=True)
    for name in ('db.json', 'hld-course.json', 'software-course.json', 'ai-course.json'):
        shutil.copy2(BACKEND / 'pipeline/data' / name, data / name)
    for name in ('pyproject.toml', 'uv.lock', 'pylock.toml'):
        shutil.copy2(CONFIG / name, BUILD / name)
    # Keep account-specific browser origins outside tracked configuration.
    config = json.loads((CONFIG / 'wrangler.jsonc').read_text())
    local_config = CONFIG / 'wrangler.local.json'
    if local_config.exists():
        overrides = json.loads(local_config.read_text())
        if set(overrides) - {'vars'} or not isinstance(overrides.get('vars', {}), dict):
            raise ValueError('Local Worker configuration supports only a vars object.')
        variables = overrides.get('vars', {})
        if set(variables) - {'ALLOWED_ORIGINS', 'AI_REQUESTS_PER_MINUTE'}:
            raise ValueError('Keep secrets out of configuration; use Cloudflare runtime secrets.')
        config['vars'].update(variables)
    # CI can supply its origins in build settings without committing site names.
    if os.environ.get('CLOUDFLARE_ALLOWED_ORIGINS'):
        config['vars']['ALLOWED_ORIGINS'] = os.environ['CLOUDFLARE_ALLOWED_ORIGINS']
    (BUILD / 'wrangler.jsonc').write_text(json.dumps(config, indent=2) + '\n')
    # Only an explicitly created local Worker secret file is used. Production
    # secrets are configured in Cloudflare, and backend/.env is never bundled.
    secret = CONFIG / '.dev.vars'
    if secret.exists():
        shutil.copy2(secret, BUILD / '.dev.vars')
        (BUILD / '.dev.vars').chmod(0o600)
    else:
        (BUILD / '.dev.vars').unlink(missing_ok=True)
    print('Packaged the original API in backend/.cloudflare/src (no .env or pipeline scripts).')
    return BUILD


if __name__ == '__main__':
    prepare()
```

### 18.4. [backend/cloudflare.sh](backend/cloudflare.sh)

```bash
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
```

### 18.5. [backend/cloudflare/wrangler.jsonc](backend/cloudflare/wrangler.jsonc)

```json
{
  "name": "patternfirst-ai",
  "main": "src/worker.py",
  "compatibility_date": "2026-10-28",
  "compatibility_flags": [
    "python_workers"
  ],
  "find_additional_modules": true,
  "rules": [
    {
      "type": "Data",
      "globs": [
        "pipeline/data/*.json"
      ],
      "fallthrough": true
    }
  ],
  "vars": {
    "ALLOWED_ORIGINS": "http://127.0.0.1:5173,http://localhost:5173",
    "AI_REQUESTS_PER_MINUTE": "12"
  }
}
```

### 18.6. [backend/cloudflare/pyproject.toml](backend/cloudflare/pyproject.toml)

```toml
[project]
name = "patternfirst-ai"
version = "0.1.0"
description = "Cloudflare deployment of the existing Pattern First FastAPI backend"
requires-python = ">=3.13"
dependencies = [
    "fastapi",
    "python-dotenv",
    "groq",
    "google-genai",
    "ollama",
]

[dependency-groups]
dev = ["workers-py", "workers-runtime-sdk"]
```

### 18.7. [backend/cloudflare/.dev.vars.example](backend/cloudflare/.dev.vars.example)

```dotenv
# Optional local Worker test credentials. Copy to .dev.vars (ignored by Git).
GROQ_API_KEY="your-groq-key"
AI_ACCESS_TOKEN="replace-with-a-random-secret-at-least-32-characters"
# GEMINI_API_KEY="your-gemini-key"
```

### 18.8. [frontend/src/lib/aiConnection.ts](frontend/src/lib/aiConnection.ts)

```typescript
// A personal hosted-backend access key, never a Groq/Gemini provider key.
const KEY = 'patternfirst-hosted-ai-access'

export function hostedAIKey(): string {
  try { return sessionStorage.getItem(KEY) ?? '' } catch { return '' }
}

export function saveHostedAIKey(value: string): void {
  if (value.trim()) sessionStorage.setItem(KEY, value.trim())
  else sessionStorage.removeItem(KEY)
}

export function aiHeaders(): Record<string, string> {
  const key = hostedAIKey()
  return { 'Content-Type': 'application/json', ...(key ? { Authorization: `Bearer ${key}` } : {}) }
}

export function aiURL(path: string): string {
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '')
  return `${base}${path}`
}
```

### 18.9. [.gitignore](.gitignore)

```gitignore
.idea/
__pycache__/
venv/
.env
development.md
/project-markdowns
/.run/
.venv/
.wrangler/
.dev.vars
.dev.vars.*
!.dev.vars.example
node_modules/
.cloudflare/
.venv-workers/
python_modules/
/backend/cloudflare/wrangler.local.json
```

### 18.10. Settings: save and clear the personal key

Source: [SettingsView.vue](frontend/src/views/SettingsView.vue). The new state/actions are:

```typescript
const accessKey = ref(hostedAIKey())
const accessStatus = ref('')
function saveAccessKey() {
  try {
    saveHostedAIKey(accessKey.value)
    accessStatus.value = accessKey.value.trim() ? 'Saved for this tab session. Retry your AI request.' : 'Hosted access key removed.'
  } catch { accessStatus.value = 'Browser storage is unavailable. Allow session storage and retry.' }
}
```

The new Settings form is:

```vue
<section class="card card-flat" style="margin-bottom: var(--space-lg)">
      <h3 class="section-heading">Hosted AI connection</h3>
      <p class="setting-desc">Using the Cloudflare backend? Enter the personal access key you configured there. Your local Python server does not require it.</p>
      <p class="setting-desc">This is not your Groq or Gemini API key. Provider keys stay on the backend. This key is saved only for this tab session.</p>
      <form @submit.prevent="saveAccessKey" class="action-row">
        <label for="hosted-ai-key">Personal AI access key</label>
        <input id="hosted-ai-key" class="hosted-key" v-model="accessKey" type="password" autocomplete="off" spellcheck="false" />
        <button class="btn btn-primary" type="submit">Save access key</button>
        <button class="btn" type="button" @click="accessKey='';saveAccessKey()">Clear</button>
      </form>
      <p role="status">{{ accessStatus }}</p>
    </section>
```

### 18.11. Assessment/chat request integration

The request body and backend response contracts remain the same. Call sites now use `headers: aiHeaders()`. DSA code analysis also resolves its backend URL through `aiURL(...)`. For example:

```typescript
const response = await fetch(aiURL('/api/analyze-code'), {
  method: 'POST',
  headers: aiHeaders(),
  body: JSON.stringify(submittedWork),
})
```

This is a shortened integration example, not the complete component. See [DetailedAnalysisView.vue](frontend/src/views/DetailedAnalysisView.vue) and the other changed files listed above. Unauthorized responses now direct the learner to Settings instead of treating them as an AI result.

Dependency lock contents are in [uv.lock](backend/cloudflare/uv.lock) and [pylock.toml](backend/cloudflare/pylock.toml). The lock files are committed; local credentials and package caches are not.


## 19. Official references

- [Python Workers and FastAPI](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/)
- [Python Worker packages and pywrangler](https://developers.cloudflare.com/workers/languages/python/packages/)
- [Worker runtime secrets](https://developers.cloudflare.com/workers/configuration/secrets/)
- [Cloudflare build settings](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)
- [Current Worker limits](https://developers.cloudflare.com/workers/platform/limits/)
- [Netlify environment variables](https://docs.netlify.com/build/environment-variables/overview/)

Product limits and dashboard labels can change. The code, observed deployment results, and historical commands above describe this project on the recorded date.
