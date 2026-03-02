# Repository Guidelines

## Project Structure & Module Organization
- `frontend/`: Vue 3 + TypeScript app (Vite). Main code is under `frontend/src/`:
  - `views/` route pages, `components/` reusable UI, `composables/` state/data hooks, `router/` route config, `types/` shared types.
  - Runtime dataset lives at `frontend/public/db.json`.
- `backend/`: Python data pipeline plus optional FastAPI runtime API.
  - `pipeline/` scripts build and enrich DSA data into `pipeline/data/db.json`.
  - `ai/` contains provider abstractions/adapters (Gemini, Groq, Ollama).
  - `app.py` exposes mock interview endpoints.
- `project-markdowns/`: planning/internal docs. Root docs (`README.md`, `CONTRIBUTING.md`, `SECURITY.md`) define contributor expectations.

## Build, Test, and Development Commands
- Frontend:
  - `cd frontend && npm install`
  - `npm run dev` (local dev server)
  - `npm run build` (type-check + production build)
  - `npm run preview` (preview built output)
- Backend setup:
  - `cd backend && python -m venv venv && source venv/bin/activate`
  - `pip install -r requirements.txt`
- Backend pipeline (run in order):
  - `python pipeline/parse_neetcode.py`
  - `python pipeline/parse_striver.py`
  - `python pipeline/merge_and_curate.py`
  - `python pipeline/fetch_leetcode.py`
  - `python pipeline/generate_patterns.py`
  - `python pipeline/generate_problem_insights.py`
  - `python pipeline/build_final_db.py`
  - `cp pipeline/data/db.json ../frontend/public/db.json`
- Optional API: `uvicorn app:app --reload --port 8000`

## Coding Style & Naming Conventions
- Python: 4-space indentation, snake_case for functions/variables, module-level constants in UPPER_SNAKE_CASE.
- Vue/TypeScript: `<script setup lang="ts">`, composables named `useX.ts`, view components in PascalCase (for example `ProblemView.vue`).
- Prefer explicit, readable logic over clever abstractions; keep PRs focused and avoid unrelated refactors.

## Testing Guidelines
- No dedicated automated test suite is committed yet.
- Minimum validation before PR:
  - Frontend: `npm run build` succeeds.
  - Backend: run affected pipeline scripts and confirm regenerated `frontend/public/db.json` loads in the app.
  - For API changes: run `uvicorn app:app --reload --port 8000` and verify `GET /api/health`.

## Commit & Pull Request Guidelines
- Branch from `main`; do not push directly to `main`.
- Branch naming: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`.
- Follow Conventional Commit style used in repo docs: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`, `chore: ...`.
- PRs should include: clear summary, linked issue (if any), testing notes, and screenshots/logs for UI or behavior changes.

## Security & Configuration Tips
- Copy `backend/.env.example` to `.env`; never commit secrets.
- Keep API keys local (`GEMINI_API_KEY`, `GROQ_API_KEY`, etc.) and ensure no credentials appear in logs, screenshots, or PR text.
