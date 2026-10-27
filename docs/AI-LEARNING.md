# AI Learnings · implementation and operation

Open http://127.0.0.1:5173/ai. The top navigation has AI Learnings beside Software Learnings. Start with chapter 1 or open the four-week starting plan. The full course has 56 chapters, 8 ordered stages, 112 separate practice tasks, chapter quizzes and cumulative checks, a 58-question final check, and about 115 hours of estimated work. It progresses from beginner through advanced application engineering.

## Learning flow

Learn → Predict → Practice → Quiz → delayed recall. Short lesson steps use diagrams and memory cues. Five deterministic sandboxes illustrate context budgets, scoped vector ranking, typed evidence checks, approval freshness and evaluation thresholds. Practice submission saves a snapshot. Separate references and AI scoring become available afterward. Teacher chat uses the selected lesson/lab file; practice coaching excludes the reference. The download contains answer keys, so this is a learning aid rather than a secrecy mechanism.

AI feedback compares submitted work with the course reference. It never executes a submission. Four provisional scores cover prediction, change, verification and explanation. Proposed-but-unrun verification is capped at 1/3 in the evaluator rubric. A valid report requires four distinct integer-scored dimensions with evidence and feedback. Provider failure or malformed feedback is reported honestly; no fallback score is invented.

AI progress uses ai-learnings-progress-v1. Existing Software progress keeps software-learnings-progress-v1. Backups have a learningArea envelope; imports reject the other area. Older unwrapped Software backups remain supported. Corrupt stored data is preserved until a valid successful replacement. HLD/DSA state and the existing Software catalog are unchanged.

## Source and rebuild

Editable course: ../swe-mastery-journal/ai-learnings. Each chapter separates lesson Markdown, practice prompts, reference answers and quiz keys. The versions/source guide maps the public ai-mastery-journal into this developer path. It corrects token/word simplifications and treats vectorless-retrieval claims as evaluation hypotheses. No work-project files are bundled.

From this repository:

```bash
python3 backend/pipeline/build_ai_course.py
backend/venv/bin/python -m pytest backend/tests -q
cd frontend
npm run test:learning
npm run build
```

The builder confines content/lab paths to the journal, rejects unsupported levels/duplicate IDs/invalid keys, and emits matching frontend/public/ai-course.json and backend/pipeline/data/ai-course.json. The existing Software builder remains the default. Drafting scripts in the journal's authoring folder are not the normal publication path; they may overwrite manual source edits.

## Servers

Frontend: npm run dev -- --host 127.0.0.1 --port 5173. Backend: from backend, venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000. Vite proxies /api to the backend. GET /api/health reports the configured provider. Restart the backend after changing a bundled catalog because it caches that data.

New endpoints: POST /api/ai/ai-course-chat and POST /api/ai-course/evaluate. Both use the configured existing analyzer. AI and Software catalogs cannot be mixed through module IDs. Requests do not read arbitrary local files or execute submitted code.

## Runnable worked example

The journal's ai-learnings/labs/dispatch-desk folder contains complete Rails, MCP and pgvector files. The Code lab browser includes its file map, tests and setup. It is fictional warehouse operations: allowlisted filters, verified reasons, comparison, briefing, owned asynchronous explanations and fallback. The optional provider adapter uses the official Ruby SDK; default routes use scripted fixtures and make no paid model calls.

Ruby 3.3.6 / Rails 7.2.2.2 / MCP SDK 1.8.2 / OpenAI SDK 0.113.0 / pgvector 0.8.1 on PostgreSQL 16 are tested course versions. This is an isolated training stack. Its caller-selected identity header is not production authentication. It binds only to localhost. Its in-process async queue is not durable and has no abandoned-run recovery lease. Generated prose remains a labelled draft. Typed checks and citation membership do not prove every sentence is supported.

Start with the lab README. Its separate test database is enforced by a guard. Smoke checks use live HTTP, official MCP initialization/discovery/tool execution, and denied foreign-actor access. The evaluation workbook can run with Python alone. Its saved teaching outputs intentionally score 10/12 with a critical access decision failure, demonstrating why an average can hide a release blocker. It is not a live-model benchmark.

## Validation recorded · 2026-10-27

- TypeScript check and Vite production build passed. Vite reports its existing large-diagram bundle-size advisory.
- 36 frontend checks passed, including independent progress, old backup compatibility, cross-area rejection, corrupt-data preservation and the interactive mechanism calculations.
- 23 backend checks passed, including all earlier HLD/Software checks, reproducible catalogs, separate practice/review context, route isolation and strict AI report validation. FastAPI's test client emits an httpx deprecation advisory.
- 31 Rails checks / 74 assertions passed against the separate test database. Scope, revoked stale actor objects, invalid proposals, fallback, source freshness, job ownership, MCP errors, optional SDK refusal/timeouts and bounded tool behavior are covered.
- Live HTTP lab smoke passed, including a denied foreign record returned as an intentional MCP tool error rather than a generic internal exception.
- All 27 unique primary chapter reference URLs responded successfully when checked.
- Browser checks covered AI/Software navigation, advanced filtering, lesson/sequence diagrams, mobile practice and lab-file selection, snapshot submission, gated reference, quiz grading, one-at-a-time final questions, backup restore, and mobile page overflow. Test practice progress was restored.
- The configured live AI reviewer returned a valid report for synthetic submitted work and correctly treated unrun verification as proposed. A synthetic lesson chat also returned successfully. This is a connectivity/flow check, not a model-quality evaluation.

No training, live production provider benchmark, real OAuth deployment, durable worker infrastructure or cloud rollout is certified by these checks. Those are explicit course design/evaluation activities.

## Git baseline

Existing app dev work was integrated through PR #5 before this feature. main and dev were synchronized at 095c89d. Existing journal sources were preserved at ce98385 and its dev branch synchronized. The new difference on dev is the AI course and the app support required for it. New AI changes have not been merged into main.
