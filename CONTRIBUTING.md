# Contributing to DSA Pattern Lab

Thanks for contributing.

## Table of Contents

- [1. Ground Rules](#1-ground-rules)
- [2. Development Setup](#2-development-setup)
- [3. Branching and PR Process](#3-branching-and-pr-process)
- [4. Coding Standards](#4-coding-standards)
- [5. Commit Guidelines](#5-commit-guidelines)
- [6. Documentation Changes](#6-documentation-changes)

## 1. Ground Rules

- Be respectful and constructive.
- Keep pull requests focused and reasonably small.
- If you plan a large change, open an issue first to align on approach.

## 2. Development Setup

Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## 3. Branching and PR Process

- Create a feature branch from `main`.
- Do not push directly to `main`.
- Open a pull request with:
  - clear summary,
  - linked issue (if any),
  - testing notes,
  - screenshots for UI changes.

Expected branch naming:

- `feat/<short-topic>`
- `fix/<short-topic>`
- `docs/<short-topic>`
- `chore/<short-topic>`

## 4. Coding Standards

- Follow existing project style and structure.
- Avoid unrelated refactors in feature PRs.
- Prefer explicit, readable logic over clever abstractions.
- Keep dependencies minimal and justified.

## 5. Commit Guidelines

Recommended commit style:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `refactor: ...`
- `chore: ...`

Examples:

- `feat: add retries for leetcode metadata fetch`
- `docs: document pipeline file contracts`

## 6. Documentation Changes

If behavior changes, update docs in the same PR:

- Root docs: `README.md`
- Backend docs: `backend/README.md`
- Frontend docs: `frontend/README.md`

