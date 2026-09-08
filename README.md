# superjoindata — Fact Knowledge Layer

> **Evidence-First Fact Knowledge Layer with Local Parsing, Grounding, Normalization & Cross-Document Relationship Reasoning.**
> **100% Free-Tier Compatible • Zero External LLMs • Strict Evidence Grounding**

---

## 1. Overview & Architecture

**superjoindata** is an evidence-first document intelligence platform that parses complex PDF documents, extracts numerical and semantic facts, normalizes measurements, resolves entity aliases, and reasons across documents to discover relationships (**Corroboration**, **Contradiction**, **Contextual Reconciliation**, **Temporal Changes**, and **Audit Uncertainties**).

### Free-Tier Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                   Vercel (Free Tier)                     │
│               React + TypeScript + Vite                  │
│            (Lightweight Document Intelligence UI)        │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTPS / JSON
                             ▼
┌──────────────────────────────────────────────────────────┐
│                   Render (Free Tier)                     │
│                  FastAPI Web Service                     │
│   • PyMuPDF (Page-by-page streaming parser)              │
│   • spaCy (en_core_web_sm / lightweight statistical NLP) │
│   • RapidFuzz & Deterministic Entity Normalization       │
│   • Pint & Decimal (Unit / Currency Normalizer)          │
│   • Multi-tier Relationship & Candidate Matching Engine  │
└────────────────────────────┬─────────────────────────────┘
                             │ SQLAlchemy
                             ▼
┌──────────────────────────────────────────────────────────┐
│             PostgreSQL Database (Free Tier)              │
│       (Neon / Supabase / Render Free PostgreSQL)         │
│   • Documents & Extracted Page Blocks                    │
│   • Facts, Evidence Quotes, Bounding Boxes               │
│   • Cross-Document Inferred Relationships                │
│   • Processing Runs & Real Progress Metrics              │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Key Capabilities & Design Principles

### 100% Local & Free-Tier First
* **Zero External LLMs:** No OpenAI, Claude, Gemini, OpenRouter, or external paid APIs.
* **Lightweight NLP:** Powered by PyMuPDF, spaCy (`en_core_web_sm`), RapidFuzz, Pint, and rule-based deterministic parsing.
* **Low Memory Footprint:** Processes PDFs page-by-page, releases page objects immediately, and runs in a single web process without Redis or Celery.
* **Ephemeral Filesystem Resilient:** Uploaded PDFs are parsed and persisted in PostgreSQL immediately; server restarts never lose knowledge.
* **Upload Safety:** Configurable `MAX_PDF_SIZE_MB` limit (default 20MB) with graceful rejection.

### Structured Fact Model
Every fact contains:
* **Subject:** Resolved canonical entity
* **Predicate:** Measured metric or relationship
* **Value / Raw Value:** Verbatim extracted value
* **Fact Type:** `CURRENCY`, `PERCENTAGE`, `NUMERICAL`, `DATE`, `STATUS`
* **Normalized Value:** Standardized float/decimal representation
* **Unit & Currency:** Normalized identifiers (e.g. `USD`, `%`, `EUR`)
* **Temporal Period:** Fiscal year, quarter, or anchored exact date
* **Scope Qualifiers:** Accounting or operational boundaries (e.g. `GAAP`, `Non-GAAP`, `Consolidated`)
* **Evidence Grounding:** Document ID, page number, verbatim quote, and bounding box coordinates.

---

## 3. Demonstration of the Four Required Cases

| Case | Scenario | Documents Analyzed | Relationship | System Local Reasoning |
| :--- | :--- | :--- | :--- | :--- |
| **1. Corroboration** | Identical revenue disclosed across two independent filings | `Q4_2023_Earnings_Release.pdf` & `FY2023_Shareholder_Letter.pdf` | **`CORROBORATES`** | Both filings independently confirm identical revenue (`$4.2 billion` and `$4.2B`) for `Q4 2023` without variance. |
| **2. Contradiction** | Numerical headcount conflict for the exact same reporting date | `Global_Workforce_Report_2023.pdf` & `Annual_ESG_Disclosure_2023.pdf` | **`CONTRADICTS`** | Direct numerical conflict for `December 31, 2023`: Workforce Report states `14,200` while ESG Disclosure reports `15,800` employees without reconciliation. |
| **3. Apparent Contradiction (Contextual)** | Operating margins appear different (`21.4%` vs `28.6%`) | `Form_10K_Annual_Report.pdf` & `Q4_Investor_Presentation.pdf` | **`CONTEXTUALIZES`** | Reconciled by accounting scope qualifiers: Form 10-K reports **GAAP Operating Margin** (reflecting one-time restructuring charges), whereas Investor Presentation reports **Adjusted Non-GAAP Operating Margin**. |
| **4. Uncertainty / Audit Flag** | Underspecified entity & unanchored relative timeline | `Executive_Strategy_Memo.pdf` | **`UNCERTAIN`** | Flags: (1) Underspecified entity (*"the newly formed regional subsidiary"*), (2) Relative timeline (*"coming cycle"*), (3) Growth percentage lacking baseline denominator. Provides actionable diagnostic fix. |

---

## 4. Local Quickstart

### Prerequisites
* Python 3.9+ 
* Node.js 18+ and npm

### 1. Backend Setup

```bash
# Navigate to project root
cd superjoindata

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install lightweight dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Run the backend test suite (12 tests)
pytest -v

# Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
# In a new terminal, navigate to frontend
cd frontend

# Install dependencies and build
npm install
npm run build

# Start Vite dev server
npm run dev
```

Open `http://localhost:5173` in your browser. Click **"⚡ Seed Demo Dataset"** to run the live extraction pipeline across the sample PDFs!

---

## 5. Docker Setup (Local / Self-Hosted)

```bash
# Build and run with Docker
docker build -t superjoindata .
docker run -p 8000:8000 -e PORT=8000 superjoindata
```

---

## 6. Free-Tier Deployment Guide

### A. Free PostgreSQL Database Setup
You can use any free managed PostgreSQL provider (Neon, Supabase, ElephantSQL, or Render PostgreSQL):
1. Create a free PostgreSQL database instance.
2. Copy the connection URI:
   ```text
   postgresql://username:password@ep-host.region.neon.tech/dbname?sslmode=require
   ```

### B. Render Web Service (Backend)
1. In the [Render Dashboard](https://dashboard.render.com), click **New +** → **Web Service**.
2. Connect your GitHub repository: `https://github.com/kirancube/superjoindata`.
3. Configure the service:
   * **Environment:** `Python 3`
   * **Plan:** `Free`
   * **Build Command:**
     ```bash
     pip install -r requirements.txt && python -m spacy download en_core_web_sm
     ```
   * **Start Command:**
     ```bash
     uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
     ```
   * **Health Check Path:** `/health`
4. Set Environment Variables:
   * `DATABASE_URL` = `your-postgresql-connection-uri`
   * `FRONTEND_URL` = `https://superjoindata.vercel.app`
   * `MAX_PDF_SIZE_MB` = `20`
   * `PYTHON_VERSION` = `3.11.9`

### C. Vercel (Frontend)
1. In the [Vercel Dashboard](https://vercel.com), click **Add New** → **Project**.
2. Import `https://github.com/kirancube/superjoindata`.
3. Configure project settings:
   * **Root Directory:** `frontend`
   * **Framework Preset:** `Vite`
   * **Build Command:** `npm run build`
   * **Output Directory:** `dist`
4. Set Environment Variable:
   * `NEXT_PUBLIC_API_URL` = `https://your-render-backend.onrender.com`
   * `VITE_API_URL` = `https://your-render-backend.onrender.com`
5. Click **Deploy**.

---

## 7. API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status |
| `POST` | `/documents` | Upload PDF (enforces `MAX_PDF_SIZE_MB`) |
| `GET` | `/documents` | List uploaded documents with status and fact counts |
| `GET` | `/documents/{id}` | Get document details and extracted page blocks |
| `POST` | `/documents/{id}/process` | Trigger page-by-page fact extraction and reconciliation |
| `GET` | `/documents/{id}/facts` | List all grounded facts for a document |
| `GET` | `/facts` | List facts with optional `doc_id` and `fact_type` filters |
| `GET` | `/facts/{id}` | Get fact details with source evidence quote and bounding box |
| `GET` | `/facts/{id}/relationships` | Get cross-document relationships involving this fact |
| `GET` | `/relationships` | List all discovered relationships (`category` filter) |
| `GET` | `/relationships/{id}` | Get relationship reasoning and contextual differences |
| `POST` | `/demo/seed` | Generate and process synthetic multi-document dataset |

---

## 8. Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///fact_knowledge.db` | PostgreSQL connection string (or local SQLite fallback) |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origins for browser requests |
| `MAX_PDF_SIZE_MB` | `20` | Maximum allowed PDF upload size in MB |
| `PORT` | `8000` | Port for the Uvicorn web server |
| `NEXT_PUBLIC_API_URL` | `""` | Backend URL used by frontend client |

---

## 9. Free-Tier Limitations & Scale Considerations

* **RAM & CPU Bounds:** Designed strictly within Render's 512MB RAM free instance by using page streaming, single-process spaCy pipelines, and database-level candidate filtering instead of O(N²) all-pairs comparisons.
* **Ephemeral Disk Storage:** The server filesystem is used strictly for temporary page parsing. All extracted knowledge, bounding coordinates, and relationships persist inside PostgreSQL.
* **Scaling Path:** Object storage (AWS S3 / Cloudflare R2) can be plugged in seamlessly via `DocumentDB.file_path` without altering the knowledge extraction or relationship reasoning layer.

---

## 10. Verification & Test Results

```text
============================= test session starts =============================
platform win32 -- Python 3.9.13, pytest-8.4.2, pluggy-1.6.0
collected 12 items

backend/tests/test_pipeline.py::test_number_normalization PASSED         [  8%]
backend/tests/test_pipeline.py::test_percentage_normalization PASSED     [ 16%]
backend/tests/test_pipeline.py::test_temporal_normalization PASSED       [ 25%]
backend/tests/test_pipeline.py::test_fy2025_vs_q1_not_automatically_contradictory PASSED [ 33%]
backend/tests/test_pipeline.py::test_entity_resolution PASSED            [ 41%]
backend/tests/test_pipeline.py::test_corroboration_logic PASSED          [ 50%]
backend/tests/test_pipeline.py::test_contradiction_logic PASSED          [ 58%]
backend/tests/test_pipeline.py::test_contextual_difference_gaap_vs_nongaap PASSED [ 66%]
backend/tests/test_pipeline.py::test_failure_case_handling PASSED        [ 75%]
backend/tests/test_pipeline.py::test_non_pdf_upload_rejected PASSED      [ 83%]
backend/tests/test_pipeline.py::test_pdf_parser_missing_file PASSED      [ 91%]
backend/tests/test_pipeline.py::test_demo_seed_api PASSED                [100%]

======================= 12 passed in 2.62s ========================
```
