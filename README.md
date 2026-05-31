<div align="center">

# Talash

### CV Intelligence Platform

**Upload resumes → extract structured profiles → run evidence-backed analysis across education, skills, experience, research, and more.**

<br />

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)

[Features](#-features) ·
[Architecture](#-architecture) ·
[Quick Start](#-quick-start) ·
[Configuration](#-configuration) ·
[API](#-api-overview) ·
[Project Structure](#-project-structure)

<br />

<img src="logo.svg" alt="Talash logo" width="72" />

</div>

---

## Overview

**Talash** (تلاش — *effort, endeavor*) is an end-to-end system for **parsing academic and professional CVs** and **evaluating candidates** with a mix of deterministic rules and LLM-powered insights. PDFs are uploaded, text is extracted, profiles are structured into a strict JSON schema, and seven analysis modules produce facts plus AI-generated assessments grounded in CV evidence.

Designed for hiring committees, graduate admissions, and research groups who need **repeatable, auditable** CV review—not opaque black-box scoring.

---

## Features

| | Module | What you get |
|---|--------|----------------|
| 📄 | **Upload & parse** | Multi-file PDF upload, duplicate detection, Supabase file storage, LLM extraction with evidence fields |
| 🎓 | **Education** | Timeline, normalized scores, gap detection, trend charts, AI Q&A |
| 🛠️ | **Skills** | Evidence strength per skill, coverage metrics, overstated-skill flags |
| 💼 | **Experience** | Career timeline, job overlaps, education–job overlaps, professional gaps |
| 🔬 | **Research** | Publication verification, confidence scores, cache-aware rechecks |
| 👥 | **Supervision** | Student advising records and role distribution |
| 🏆 | **Awards** | Honors timeline with issuer and evidence snippets |
| 📚 | **Books & patents** | Combined IP and publication portfolio view |

### Platform highlights

- ✅ **Evidence-first extraction** — every field carries `value`, `status`, and `evidence`
- ✅ **Facts vs. AI insights** — structured computations separate from LLM narrative analysis
- ✅ **Persistent storage** — PostgreSQL (Supabase) or local SQLite
- ✅ **Modern UI** — React dashboard with module rail, candidate sidebar, and insight cards
- ✅ **Reprocess & cache control** — re-parse duplicates, regenerate cached analyses

---

## Architecture

```mermaid
flowchart LR
  subgraph Client
    UI[React + Vite UI]
  end

  subgraph API["FastAPI Backend"]
    UP[Upload / Parse]
    FACTS[Facts Engine]
    LLM[OpenRouter LLM]
  end

  subgraph Data
    DB[(PostgreSQL / SQLite)]
    SB[(Supabase Storage)]
  end

  UI -->|REST| UP
  UP --> SB
  UP --> DB
  UI -->|REST| FACTS
  FACTS --> DB
  FACTS --> LLM
  LLM --> FACTS
```

**Pipeline**

1. **Ingest** — PDF → text extraction (`PyMuPDF` / `pdfplumber`)
2. **Parse** — LLM maps text → `CandidateProfile` JSON (OpenRouter)
3. **Store** — document metadata, parsed payload, processing jobs
4. **Analyze** — per-module facts (Python) + optional LLM assessment
5. **Review** — frontend presents facts tables, charts, and insight cards

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| **Backend** | ![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![SQLAlchemy](https://img.shields.io/badge/-SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white) ![Pydantic](https://img.shields.io/badge/-Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white) ![Uvicorn](https://img.shields.io/badge/-Uvicorn-000000?style=flat-square) |
| **PDF** | ![PyMuPDF](https://img.shields.io/badge/-PyMuPDF-3776AB?style=flat-square&logo=python&logoColor=white) `pdfplumber` |
| **AI** | ![OpenRouter](https://img.shields.io/badge/-OpenRouter-000000?style=flat-square) (OpenAI-compatible API) |
| **Database** | ![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) via Supabase · SQLite for local dev |
| **Storage** | ![Supabase](https://img.shields.io/badge/-Supabase-3FCF8E?style=flat-square&logo=supabase&logoColor=white) |
| **Frontend** | ![React](https://img.shields.io/badge/-React-61DAFB?style=flat-square&logo=react&logoColor=black) ![Vite](https://img.shields.io/badge/-Vite-646CFF?style=flat-square&logo=vite&logoColor=white) `axios` |

---

## Quick start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **OpenRouter API key** ([openrouter.ai](https://openrouter.ai/))
- **Supabase project** (optional for production; required for PDF cloud storage)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/cv-analyzer.git
cd cv-analyzer
```

### 2. Environment variables

Create a `.env` file in the **project root** (the backend loads `backend/.env` or `../.env` automatically):

```env
# ── App ──────────────────────────────────────────
APP_ENV=dev

# ── Database (use Supabase Postgres in production) ─
DATABASE_URL=postgresql://USER:PASSWORD@HOST:6543/postgres

# ── OpenRouter (parsing + analysis) ──────────────
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-oss-120b:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Optional per-module analysis models (fallback to OPENROUTER_MODEL)
EDUCATION_ANALYSIS_MODEL=
SKILLS_ANALYSIS_MODEL=
EXPERIENCE_ANALYSIS_MODEL=
RESEARCH_ANALYSIS_MODEL=

# ── Supabase (PDF storage) ───────────────────────
SUPABASE_PROJECT_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
SUPABASE_BUCKET_NAME=cv-files
```

> **Local-only dev:** omit `DATABASE_URL` to use SQLite at `backend/talash.db`. You still need OpenRouter for parsing; Supabase is required for upload storage in the current pipeline.

### 3. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs: **http://127.0.0.1:8000/docs**

### 4. Frontend

```bash
cd frontend/frontend-react
npm install
npm run dev
```

Open **http://127.0.0.1:5173**

Optional — point the UI at a remote API:

```bash
# frontend/frontend-react/.env.local
VITE_API_URL=http://127.0.0.1:8000
```

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Production | SQLAlchemy URL; PostgreSQL recommended |
| `OPENROUTER_API_KEY` | Yes | API key for CV parsing and analysis |
| `OPENROUTER_MODEL` | Yes | Default model for extraction |
| `OPENROUTER_BASE_URL` | No | Defaults to OpenRouter API |
| `EDUCATION_ANALYSIS_MODEL` | No | Override for education LLM step |
| `SKILLS_ANALYSIS_MODEL` | No | Override for skills LLM step |
| `EXPERIENCE_ANALYSIS_MODEL` | No | Override for experience LLM step |
| `RESEARCH_ANALYSIS_MODEL` | No | Override for research LLM step |
| `SUPABASE_PROJECT_URL` | Upload | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Upload | Service role key for storage |
| `SUPABASE_BUCKET_NAME` | No | PDF bucket name (default: `cv-files`) |

---

## Using the app

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│  1. Upload  │ ──▶ │ 2. Candidates │ ──▶ │ 3. Analysis (7 modules)    │
│  PDF CVs    │     │  Select profile│     │  Facts → Run AI analysis   │
└─────────────┘     └──────────────┘     └─────────────────────────────┘
```

1. **Upload** — drop one or more PDF resumes; parsing runs via the API.
2. **Candidates** — browse parsed profiles; select a candidate (also available in the sidebar).
3. **Analysis** — pick a module from the rail → **Load facts** → **Run AI analysis**.

Use **Regenerate cached** to force fresh LLM output when prompts or models change.

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload and parse PDF(s) |
| `GET` | `/documents` | List parsed documents |
| `GET` | `/documents/{id}` | Document + parsed payload |
| `POST` | `/documents/{id}/reprocess` | Re-parse a document |
| `GET` | `/documents/{id}/{module}/facts` | Deterministic facts |
| `POST` | `/documents/{id}/{module}/analyze` | LLM analysis (`regenerate` form field) |

Modules: `education`, `skills`, `experience`, `research`, `books-patents`, `supervision`

Research also exposes:

- `POST /documents/{id}/research/recheck-unverified` — re-verify unverified publications

Interactive reference: **http://127.0.0.1:8000/docs**

---

## Project structure

```text
LLMproject/
├── backend/
│   ├── main.py              # FastAPI app & routes
│   ├── config.py            # Settings (.env from root or backend/)
│   ├── models.py            # SQLAlchemy models
│   ├── parsing.py           # LLM CV extraction
│   ├── education.py         # Education facts + analysis
│   ├── skills.py
│   ├── experience.py
│   ├── research.py          # Publication verification
│   ├── supervision.py
│   ├── books_patents.py
│   ├── pdf_utils.py
│   ├── storage.py           # Supabase uploads
│   └── requirements.txt
├── frontend/
│   └── frontend-react/      # React + Vite UI
│       ├── src/
│       │   ├── App.jsx
│       │   ├── api.js
│       │   ├── components/
│       │   └── styles.css
│       └── package.json
├── logo.svg
├── talash_analysis_questions.txt
├── LICENSE
└── README.md
```

---

## Development

### Run checks

```bash
# PDF text extraction smoke test
python check_pdf_extraction.py path/to/sample.pdf

# Frontend production build
cd frontend/frontend-react && npm run build
```

### CORS

Allowed origins are configured in `backend/main.py` (localhost Vite ports and production Vercel URL). Add your deployment URL when shipping a new frontend host.

---

## Design principles

- **No hallucination in extraction** — the parser prompt requires evidence snippets and explicit `missing` / `unclear` states.
- **Separation of concerns** — Python computes verifiable facts; the LLM answers structured questions on top of those facts.
- **Auditability** — raw parsed JSON, processing jobs, and per-answer evidence fields support human review.

---

## Roadmap

- [ ] Batch export (PDF / CSV report per candidate)
- [ ] Role-based access and org workspaces
- [ ] Custom rubric / question sets per institution
- [ ] Comparison view across multiple candidates

---

## License

This project is licensed under the **[MIT License](LICENSE)**.

---

## Acknowledgments

Built for rigorous academic CV review workflows. Powered by [OpenRouter](https://openrouter.ai/), [FastAPI](https://fastapi.tiangolo.com/), and [Supabase](https://supabase.com/).

<div align="center">

**Talash** — structured effort behind every hiring decision.

<br />

[![Star on GitHub](https://img.shields.io/badge/⭐_Star_on_GitHub-181717?style=for-the-badge&logo=github)](https://github.com/YOUR_USERNAME/cv-analyzer)

</div>
