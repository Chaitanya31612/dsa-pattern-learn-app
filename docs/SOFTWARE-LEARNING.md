# Software Learnings

Open `/software`. Start with frontend and UX for current work, or choose one primary track. Filter Beginner/Intermediate and search for a chapter. The top navigation, Review page, and Settings backup area link to it.

The library has 132 chapters across eight tracks: Spring Boot, Ruby/Rails, Git, frontend, UX, AWS, production tools, and event-driven systems. There are 57 Beginner and 75 Intermediate chapters, 264 practice tasks, and 413 quiz questions. Each chapter has four lesson steps, overview/recap diagrams, two separate practice tasks and answers, a quiz, references, and optional AI coaching. Kafka, AWS, and toolkit capstones add cumulative checks. Long quizzes show one question at a time. Some chapters include interactive mechanism models or a multi-file Code lab. The models illustrate behavior; they do not run submitted code.

## Learner flow

1. Read one step and follow its example. Mark it read when you can explain it.
2. Predict the result before checking the explanation. Manipulate the model when available.
3. Write a repair in Predict / Change / Verify / Explain. Use a separate local training sandbox for execution. Say explicitly if you did not run it.
4. Submit. This preserves a snapshot and unlocks that exercise’s reference and AI review.
5. Compare reasoning, add one missing check to the bug diary, then try the changed-condition exercise without the answer.
6. Take the quiz. Wrong concepts become recall cards. Return for recall when due.

The first recall is due after one day. Good advances through 3/7/14/30/60-day gaps; Hard returns in one day and Again in ten minutes. The course checks reading, both practice submissions, latest quiz ≥75%, and a successful non-quiz recall at least seven days after the first practice submission. These are participation/retention indicators, not verified mastery or a hiring assessment. There are no background notifications.

Drafts, attempts, quiz choices/results, notes, and recall cards use the separate browser key `software-learnings-progress-v1`. They do not change DSA, LLD, or HLD progress. Export in Settings or the course Backup tab. File and pasted-JSON imports validate the full structure before replacement. Corrupt saved data blocks automatic overwriting; export the stored copy before restoring a valid backup. Reference hiding is a learning aid, not access control: the static course download contains reference content.

## Source and rebuild

The sibling journal is the editable source. `software-learnings/course-index.json` lists module directories. Each directory has separate lesson, practice, answer, quiz, and metadata files. Existing Git/frontend notes are bundled as deeper reading without copying answer files into lesson context.

```sh
python3 backend/pipeline/build_software_course.py
```

The builder writes identical `frontend/public/software-course.json` and `backend/pipeline/data/software-course.json`. It reads only the journal. Restart the AI backend after a rebuild because its catalog is cached. The frontend loads its bundled catalog once per page session; reload it after rebuilding.

## AI behavior

`POST /api/ai/software-chat` uses the existing configured provider. Learn mode receives one selected step, or the selected approved lab file plus its version and guide. Practice mode receives only the task and student notes, with a rule to clarify or nudge rather than solve. Review mode includes the selected reference. References and notes are treated as data, not instructions. Hint/reference use marks the active draft assisted.

`POST /api/software/evaluate` compares a saved snapshot with that task’s reference. It requests provider JSON mode when supported and validates exactly four dimensions, each integer 0–3 with evidence and feedback: predict, change, verify, explain. It does not execute code. Proposed tests without observed results are instructed to score at most 1 for verification. A provider error or invalid response produces an honest error without a fabricated score. AI feedback marks the current draft assisted, while preserving the pre-feedback snapshot. Reference gating is enforced by the UI learning flow, not a server-side submission database.

The frontend dev proxy targets `127.0.0.1:8000`. For a different deployment, configure `VITE_API_BASE_URL` and run the provider backend as usual. Lessons and self-review work without AI. Code submitted for review stays text; there is no arbitrary-code execution endpoint.

## Versions and privacy

Ruby/Rails lessons target the supplied work context: Ruby 2.7.8, Rails 4.2.11.3, Sidekiq 5.2, Vue 2.6. Newer Rails/Ruby/Vue behavior is labelled separately. Private project inspection was read-only and limited to versions and broad structure/patterns. No production application code, records, or secrets are bundled or sent to the provider. All teaching examples use synthetic task-tracker data. The application never reads the work repository.

The books informed concept order and reading maps. Original explanations replace copied prose. The Spring sandbox pins Java 21 and Boot 4.0.3. Its H2 tests do not establish PostgreSQL behavior. The journal now includes a complete isolated Rails 7.2 / Ruby 3.3 / Kafka 4.1 training app. Its modern dependencies are deliberately separate from the legacy work baseline. The browser displays its files but does not execute commands.

## Validation commands

```sh
cd frontend
npm run build
npm run test:learning
```

Use a supported Node version (the bundled Node 24 runtime was used for verification).

```sh
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/test_software.py tests/test_hld.py -q
```

Journal labs: run `ruby ruby_lab.rb`, `node frontend_lab.mjs`, and `python3 git_lab.py` in `software-learnings/labs`. Run `./mvnw test` in `spring-boot/labs/task-service`. The Spring project includes the official Maven 3.9.9 wrapper. It downloads its own tool runtime; it does not change the work environment.

## Expanded labs and scope

`software-learnings/labs.json` lists approved lab files. The builder checks resolved paths and bundles four lab views: Rails/Kafka, AWS adapters/setup, Redis, and Vue 3. The AWS view shares adapter files with the Rails lab. Nothing reads the work repository. The course is about 292 hours with practice; the guide provides a focused four-week frontend/UX block rather than claiming the full library fits one month.

Local checks completed on 2026-10-21:

- Frontend type check and production build; 28 learning/HLD tests.
- Backend: 17 tests covering catalogs, cumulative coverage, separate answers, approved lab paths, versioned AI context, JSON scoring, and honest provider failures.
- All 268 bundled diagrams parse. Browser checks cover search, levels, file navigation, single-question cumulative quiz, the Kafka crash/replay model, and no page overflow at 390px.
- Isolated Rails/PostgreSQL lab: 10 tests, 28 assertions, including AWS SDK stubs. Test startup requires a separate database ending in `_test`.
- Real local Kafka smoke: repeated command, repeated delivery, consumer stop/restart catch-up.
- Redis: typed data, concurrent increments, lost GET/SET update, expiry, token-checked release, Lua counter/TTL, stream acknowledgment.
- Separate Vue lab: three DOM/component tests and its production build.

AWS services, Kubernetes clusters, managed Kafka, SaaS integrations, and multi-node broker/Redis failover were not deployed or integration-tested. Their lessons use labelled configuration examples and setup/debugging workbooks. Local SDK stubs do not prove cloud permissions or networking. The lab is a teaching mechanism, not a production deployment template.

Live AI smoke returned HTTP 200 for selected-file tutoring and new-module scoring. Proposed, unrun checks received verification 1/3. Provider output remains provisional and is validated before saving.
