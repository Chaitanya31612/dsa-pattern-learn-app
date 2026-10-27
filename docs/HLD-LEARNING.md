# HLD Architecture Lab

Open **System Design → HLD Architecture Lab**, or `/system-design/hld`.

## Learn and practice

- 31 modules, 177 short lesson steps, 62 overview/recap diagrams, 95 exercises, and 124 MCQs. Volume 1 keeps its 17 modules; Volume 2 adds all thirteen chapter families plus a transfer assessment. Total planned module time is 136 hours.
- Worked teaching examples show one decision at a time. Predict before comparing later decisions. The Flow step includes its architecture picture. Teaching predictions are not graded.
- Every step starts with plain words, an example, and a memory cue. Full explanations remain under **Go deeper**.
- Diagrams support zoom, expansion, and readable source. Mermaid previews are also available in design drafts.
- The workspace follows Contract → Size → Model → Flow → Stress → Operate → Explain. Drafts autosave; submission saves a separate snapshot. Timers use elapsed wall-clock time and recover after reload.
- Reference solutions unlock after submission. Viewing a reference or using practice coaching marks the current draft assisted. A submitted earlier snapshot retains its original status. Declare assistance honestly.
- Quizzes show one question at a time. Full-quiz submission calculates scores from answer keys and reveals feedback. Previous scores are preserved.
- Missed questions enter recall immediately. Other cards begin after a day. Retrieved cards advance through 1/3/7/14/30/60-day intervals; partial recall returns tomorrow; failed recall returns in ten minutes. These are learning defaults, not guaranteed optimal intervals.
- Add personal decision cards in the module’s recall tab. Write an answer before comparing and rating recall.

## AI and self-review

The floating tutor reuses `useAIChat` and the configured backend AI providers. Lesson mode teaches; practice mode asks questions and narrow hints; review mode can discuss the reference after submission. History is separated by mode and exercise.

`POST /api/ai/hld-chat` loads trusted course context on the server. `POST /api/hld/evaluate` reviews a submitted snapshot on eight dimensions, 0–3 each, with evidence. The server validates the response and derives the total/pass gate itself. Assisted attempts and critical correctness failures cannot pass. Design scores are provisional feedback, not certification. Focused repair exercises use four areas and a 12-point total, cannot award a full-design pass, and do not require unrelated scale/API sections. The server rejects a report using the wrong rubric. Missing or invalid evidence never becomes a fabricated score.

If the provider is unavailable or returns invalid structured feedback, no fabricated score is saved. Use the local evidence-based self-review or retry after fixing the provider configuration. AI provider keys remain server-side. The app must be run with its existing backend and a working configured provider for live AI features.

The shared Groq `smart` and `fast` aliases now use `openai/gpt-oss-120b` and `openai/gpt-oss-20b`, verified as available to the configured provider. The older Llama defaults returned `model_not_found`. Explicit model names still pass through unchanged; change an explicit obsolete `DEFAULT_AI_MODEL` in your local configuration if necessary.

## Data and course updates

HLD state uses its own browser key, `hld-architecture-progress-v1`. DSA/LLD state is separate. Export/restore HLD backups from the course page or Settings. Backups include notes, drafts, submitted snapshots, quiz history, and review dates. Restore validates before replacing HLD data. Corrupt stored data is not automatically overwritten.

Volume 1 uses the existing journal plus `hld_plain_language.py` and `hld_diagrams.py`. Volume 2 is authored in `backend/pipeline/hld_volume2.py`, with short lessons, deeper explanations, a separate worked teaching example, three practice types with separate references, four reasoned MCQs, and two original diagrams per module. The supplied scanned book is a chapter reference; no book text, images, or PDF are shipped in the app. Regenerate after editing either source:

```bash
python3 backend/pipeline/build_hld_course.py
```

The importer validates and writes matching `frontend/public/hld-course.json` and `backend/pipeline/data/hld-course.json`. Teaching cards and original Mermaid diagrams live in `backend/pipeline/hld_plain_language.py` and `backend/pipeline/hld_diagrams.py`. No AI regenerates or rewrites the source during import. Restart the backend after rebuilding its catalog because it caches loaded course data.

## Checks

```bash
cd frontend
npm run build
npm run test:hld
```

From the repository root:

```bash
backend/venv/bin/python -m unittest discover -s backend/tests -v
```

Use Node 20.19+ or 22.12+ for the existing Vite version. Mermaid is loaded on demand so normal DSA navigation does not eagerly load the diagram library.

## Course navigation and learning evidence

Choose Volume 1 or Volume 2 on the course map. The hero points to the next lesson, design, transfer, repair, or quiz in that volume. Deep links retain the track and activity. “How to use this course” explains saving, AI review, solution unlocks, assistance, and backup. Its backend check distinguishes configured connectivity from a real provider request.

Every module shows seven separate evidence checks: all lesson steps, a design attempt, a transfer attempt, a repair attempt, latest quiz≥75%, an unaided design meeting the provisional rubric threshold, and good self-rated design recall at least seven days after the first submission. These are practice goals, not hard locks or a certification. Older backups remain valid; old recall without a recorded rating is not inferred as successful evidence.

Four deterministic visual labs cover queue overload, a last-seat race, a lost provider reply, and map-cell borders. Learners predict first, change inputs or step through events, then save their own explanation as a recall card. The labs are small explicit models, not production simulators.

Submitting scrolls/focuses the saved-attempt review. The seven phase timeboxes scale to 45/30/20-minute exercises. References mark the current draft assisted; a later closed-book fresh attempt can be unaided if no help is used during it. Original submitted snapshots retain their original assistance flag.

The full track is about 20 weeks at 7 hours/week. Work through one module at a time and use part of the weekly budget for recall and repairs. The old one-month goal is a foundation checkpoint, not the completion promise for both volumes.
