# Deploy the existing Python AI backend on Cloudflare

For the full deployment guide, commands, implementation snapshots, and access-key scope, read [Cloudflare Worker Deploy](../CLOUDFLARE-WORKER-DEPLOY.md). This file remains the shorter setup guide.

The frontend stays on Netlify. Cloudflare runs the **same FastAPI routes and provider adapters** used locally. There is no TypeScript backend and no second copy of the teaching/scoring logic.

## What was added

- `backend/worker.py`: Cloudflare's ASGI entry point around the existing `app`.
- `backend/cloudflare_adapter.py`: hosted-only access checks, CORS, body limits, and best-effort throttling.
- `backend/cloudflare/`: deployment configuration and locked Python dependencies.
- `backend/cloudflare/prepare.py`: packages original source files and four runtime JSON catalogs into ignored `backend/.cloudflare/src`.
- `backend/cloudflare.sh`: prepares the source bundle and invokes Cloudflare's Python tooling.
- Settings → Hosted AI connection: a personal access key stored in this tab's session storage. Provider keys are never sent to the frontend.

The source packaging step is like creating a deployment archive. Files are copied byte-for-byte from the original backend. Do not edit generated `.cloudflare/src` files. Re-run the launcher after changing original Python files or course JSON.

`backend/.env`, virtual environments, tests, scraping tools, and private/work directories are not bundled. Dependencies use Cloudflare's Python/WebAssembly package ecosystem, including the existing Groq and Gemini SDKs. Local Uvicorn still uses its original virtual environment and requirements files.

## 1. Configure your private site origins and check locally

The tracked configuration allows localhost only. Create your ignored local configuration:

```bash
cp backend/cloudflare/wrangler.local.example.json backend/cloudflare/wrangler.local.json
```

Edit `vars.ALLOWED_ORIGINS` in that local file. Replace the example URLs with your frontend origins, with no paths or trailing slashes. Do not commit account URLs, deployment IDs, or personal machine paths.

The launcher merges the local values into ignored `backend/.cloudflare/wrangler.jsonc`. Keep provider keys and the access token in runtime secrets, not this configuration.


From the repository root:

```bash
./backend/cloudflare.sh check
```

This creates a deployment bundle without uploading it. On first use it downloads Python tooling, compatible interpreters, and packages. It selects a compatible installed Node (22.12+ or a newer major) and npm 10+. It can reuse the bundled Codex Node runtime without changing global asdf settings. If uv is absent, it installs a pinned copy into the ignored deployment tooling environment. Wrangler is pinned to 4.154.0.

For a local Worker with real AI:

```bash
cp backend/cloudflare/.dev.vars.example backend/cloudflare/.dev.vars
```

Edit that ignored file locally. Set your provider key and a random `AI_ACCESS_TOKEN` of at least 32 characters. Do not commit it or paste its contents into chat.

```bash
./backend/cloudflare.sh dev --port 8787
```

The Worker responds at `http://127.0.0.1:8787/api/health`. AI endpoints need `Authorization: Bearer YOUR_PERSONAL_ACCESS_KEY`. Health checks do not call the provider; use a chat request to verify the key and quota.

For a frontend connected to this local Worker, set `VITE_API_BASE_URL=http://127.0.0.1:8787` when starting Vite, then enter the personal key in Settings. The ordinary `./run.sh` still starts the original Python server on 8000.

## 2. Deploy using your Cloudflare account

The simplest first deployment is from your terminal:

```bash
./backend/cloudflare.sh login
./backend/cloudflare.sh deploy
```

Complete Cloudflare's browser sign-in yourself. Use Workers Free. No database, paid compute, or custom domain is needed. The name in `backend/cloudflare/wrangler.jsonc` is `patternfirst-ai`.

Until runtime secrets are added, the deployed Worker deliberately returns 503 instead of allowing public AI calls.

In Cloudflare → Workers & Pages → `patternfirst-ai` → Settings → Variables and Secrets, add **Secret** values:

- `GROQ_API_KEY`: your existing provider key.
- `AI_ACCESS_TOKEN`: a new random personal access key, at least 32 characters.
- `GEMINI_API_KEY`: optional. Gemini is used when no Groq key is configured.

Generate a personal access key locally with `openssl rand -hex 32`. Keep it in your password manager. It is a shared personal-use credential, not a multi-user login system.

Set these as runtime secrets, not just build secrets. Apply the changes using Cloudflare's dashboard. Alternatively, after sign-in:

```bash
./backend/cloudflare.sh secret put GROQ_API_KEY
./backend/cloudflare.sh secret put AI_ACCESS_TOKEN
```

Each command prompts for the value. Do not place secrets in source files, command arguments, `wrangler.jsonc`, or `VITE_*` variables. The ignored `.dev.vars` file is for local development only; its values are not deployed as production secrets.

The Worker URL should look like `https://patternfirst-ai.YOUR-SUBDOMAIN.workers.dev`. Copy the actual URL Cloudflare gives you.

## 3. Optional: connect GitHub for later deployments

Once the changes are pushed to the repository:

1. Select the Worker → Settings → Builds → Connect GitHub.
2. Grant access to only `YOUR_GITHUB_USER/YOUR_REPOSITORY`.
3. Choose the `dev` branch while testing.
4. Set the root directory to `backend`.
5. Build command: `./cloudflare.sh prepare`.
6. Deploy command: `./cloudflare.sh deploy`.
7. Keep the Worker name `patternfirst-ai`, matching its configuration.
8. Set `CLOUDFLARE_ALLOWED_ORIGINS` in the Cloudflare build environment to your comma-separated frontend origins. The ignored local file is not available in Git builds.
9. Optionally limit build watch paths to `backend/**` to avoid rebuilding for frontend-only changes.

You can also use **Connect GitHub** on the Create application screen with the same settings. The deployment scripts must already exist on the selected branch. Build secrets and runtime secrets are separate; configure runtime credentials in the Worker's Settings.

## 4. Connect Netlify

In the existing Netlify project's environment variables, set:

```text
VITE_API_BASE_URL=https://YOUR-ACTUAL-WORKER-URL
```

Apply it to the `dev` branch-deploy context and rebuild that frontend. Netlify's local-development context named `dev` is different from a Git branch named `dev`; check that the variable applies to the branch deployment.

Open the deployed app → Settings → Hosted AI connection. Enter the personal `AI_ACCESS_TOKEN`, not your Groq/Gemini key. Save it, then retry chat or assessment. It lasts for this tab session, survives refresh, and is separate from progress backups.

Allowed browser origins come from ignored `backend/cloudflare/wrangler.local.json`, or `CLOUDFLARE_ALLOWED_ORIGINS` in the build environment (which takes precedence). The tracked defaults allow localhost only. If you change domains, update your private configuration and redeploy. An origin is just `https://site.example`, with no path or trailing slash. Dashboard edits to runtime variables may be replaced by later configuration deployments.

## 5. Verify before relying on it

Stop the local Python server and test the **Netlify** URL:

1. Check `/api/health` on the Worker URL (configuration only).
2. Try a chat message without a personal access key: expect a clear access-key error.
3. Save the correct key in Settings and ask a lesson question.
4. Submit practice and request AI feedback. Saving alone does not call AI.
5. Test DSA code analysis and HLD/Software/AI course assessment.
6. Inspect Worker errors and CPU metrics while testing. Local workerd and dry runs do not prove compliance with the hosted Free plan's CPU limits.

## Limits and expected errors

- **401:** missing/wrong personal access key. Set it in app Settings.
- **403:** browser origin not allowed. Update the configured origin list.
- **413:** request exceeds 128 KB. Shorten the question/submission.
- **429:** best-effort per-instance limit reached (default 12 authenticated requests/minute). Wait and retry. This is not a global/account-wide quota; multiple Worker instances have separate counters. Provider quotas also apply.
- **503:** missing runtime secrets or provider unavailable. A failed AI request does not delete saved work.
- **501 on custom-problem routes:** fetching LeetCode and saving custom problems to server disk still requires the local Python server. This deployment hosts the AI endpoints; it adds no persistent database or scraper service.
- **Worker CPU/resource errors:** measure on the actual Free deployment. The current catalog caches are warmed during Worker initialization to avoid reparsing whole catalogs on each request. If this app still exceeds Free resource limits, this configuration must be tuned; a successful local test is not a guarantee of free hosted capacity.

The current app does not implement provider switching or fallback after every provider API error. It preserves the original provider selection behaviour: Groq is preferred when its key is present; Gemini is available when Groq is not configured. Ollama remains a local option, not a model server hosted by this Worker.

## References

- [Cloudflare FastAPI adapter](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/)
- [Python packages and pywrangler](https://developers.cloudflare.com/workers/languages/python/packages/)
- [Runtime secrets](https://developers.cloudflare.com/workers/configuration/secrets/)
- [Worker build settings](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)
- [Free-plan limits](https://developers.cloudflare.com/workers/platform/limits/)
