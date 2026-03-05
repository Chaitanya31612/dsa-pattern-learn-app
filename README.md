# DSA Pattern Lab

Pattern-first DSA learning app with an AI-assisted content pipeline and a static frontend runtime.

The core idea: generate high-quality learning data once, then ship a fast client-only experience.

![dsa-pattern-learn-app](https://socialify.git.ci/Chaitanya31612/dsa-pattern-learn-app/image?description=1&font=JetBrains+Mono&forks=1&name=1&owner=1&pattern=Plus&stargazers=1&theme=Auto)

## Table of Contents

- [0. Demo](#0-demo)
- [1. High-Level Overview](#1-high-level-overview)
- [2. System Architecture](#2-system-architecture)
- [3. End-to-End Workflow](#3-end-to-end-workflow)
- [4. Repository Structure](#4-repository-structure)
- [5. Backend Deep Dive](#5-backend-deep-dive)
- [6. Frontend Deep Dive](#6-frontend-deep-dive)
- [7. Quick Start](#7-quick-start)
- [8. Why This Repo Is Structured This Way](#8-why-this-repo-is-structured-this-way)
- [9. Open Source Readiness Roadmap](#9-open-source-readiness-roadmap)

## 0. Demo


https://github.com/user-attachments/assets/42d27613-cdf5-4888-9132-246e09eab491

<img width="1865" height="1011" alt="image" src="https://github.com/user-attachments/assets/447688d8-55cb-4a82-b015-c0fb3f15c885" />
<img width="1865" height="999" alt="image" src="https://github.com/user-attachments/assets/da4b728b-67d5-4477-b282-ec21373b2dc4" />

<img width="1865" height="999" alt="image" src="https://github.com/user-attachments/assets/7199f130-0d03-4560-8ce6-0641757ecb90" />
<img width="1609" height="997" alt="image" src="https://github.com/user-attachments/assets/94ec8d8c-a088-4511-a5ec-82e64cb74db5" />
<img width="1609" height="1003" alt="image" src="https://github.com/user-attachments/assets/dbe738e8-9222-4922-9a5e-ea479d6a1f6e" />
<img width="1609" height="1003" alt="image" src="https://github.com/user-attachments/assets/62cd08b5-944c-4dcf-a5d9-344ab3aad24d" />
<img width="1609" height="1003" alt="image" src="https://github.com/user-attachments/assets/562d34c2-b3bb-4cc9-9add-4b58e54cfa5c" />
<img width="1609" height="1003" alt="image" src="https://github.com/user-attachments/assets/4ea70def-d064-41a0-9ddb-6ab396e9f125" />
<img width="1609" height="1003" alt="image" src="https://github.com/user-attachments/assets/75f34647-18c0-479e-bccc-073504eb7de3" />








## 1. High-Level Overview

This repo has two major parts:

- `backend/`: a data pipeline that curates problems and generates learning metadata using AI providers.
- `frontend/`: a Vue app that consumes static `db.json` and runs entirely client-side (including user progress in localStorage).

Current generated dataset:

- 200 problems
- 17 patterns
- Difficulty mix: Easy 70, Medium 113, Hard 17

## 2. System Architecture

```mermaid
flowchart LR
  subgraph Sources
    N[NeetCode]
    S[Striver]
    L[LeetCode APIs]
    A[AI Providers<br/>Gemini / Groq / Ollama]
  end

  subgraph Backend Pipeline
    P[Parse + Merge + Enrich + Generate]
    DB[(db.json)]
  end

  subgraph Frontend Runtime
    V[Vue 3 App]
    LS[(localStorage)]
  end

  N --> P
  S --> P
  L --> P
  A --> P
  P --> DB
  DB --> V
  V <--> LS
```

## 3. End-to-End Workflow

```mermaid
sequenceDiagram
  participant Src as Problem Sources
  participant Pipe as backend/pipeline
  participant DB as pipeline/data/db.json
  participant FE as frontend/public/db.json
  participant App as Vue App

  Src->>Pipe: Raw problem sources
  Pipe->>Pipe: Deduplicate + score + curate
  Pipe->>Pipe: Enrich from LeetCode
  Pipe->>Pipe: Generate pattern/problem insights via AI factory
  Pipe->>DB: Build final DB
  DB->>FE: Copy artifact
  FE->>App: Runtime data load
```

## 4. Repository Structure

```text
DSAPatternLearnApp/
├── backend/
│   ├── ai/                  # provider abstraction + adapters + factory
│   ├── pipeline/            # end-to-end data pipeline scripts
│   │   └── data/            # intermediate and final JSON artifacts
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── src/                 # Vue views/components/composables/router
│   ├── public/db.json       # backend-produced runtime data
│   └── README.md
└── project-markdowns/       # planning and internal notes
```

## 5. Backend Deep Dive

Backend docs are intentionally separated to keep this root README readable.

- Detailed backend documentation: [backend/README.md](backend/README.md) and Mock Interview flow: [backend/MOCKINTERVIEWFLOW.md](backend/MOCKINTERVIEWFLOW.md)
- Includes:
  - pipeline step order and commands
  - input/output contract per script
  - AI factory behavior and provider fallback
  - explanation of each file in `backend/pipeline/`

## 6. Frontend Deep Dive

Frontend already has a comprehensive technical README:

- Detailed frontend documentation: [frontend/README.md](frontend/README.md) and Mock Interview flow: [frontend/MOCKINTERVIEWFLOW.md](frontend/MOCKINTERVIEWFLOW.md)
- Includes:
  - route map and screen workflows
  - composable architecture
  - Smart Random logic and persistence

## 7. Quick Start

Backend pipeline:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python pipeline/parse_neetcode.py
python pipeline/parse_striver.py
python pipeline/merge_and_curate.py
python pipeline/fetch_leetcode.py
python pipeline/generate_patterns.py
python pipeline/generate_problem_insights.py
python pipeline/build_final_db.py

cp pipeline/data/db.json ../frontend/public/db.json
```

Frontend app:

```bash
cd frontend
npm install
npm run dev
```

## 9. Open Source Readiness Roadmap

Baseline docs and templates now included:

- [LICENSE](LICENSE)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md)
- [Issue templates](.github/ISSUE_TEMPLATE)
- [PR template](.github/pull_request_template.md)
- [CODEOWNERS](.github/CODEOWNERS)
