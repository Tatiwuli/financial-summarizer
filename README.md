## Financial Summarizer (Full Stack)

**Note: this repository is a demo of the financial summarizer web app built for my internship at Kapitalo Investimentos**

Generates structured earnings/conference call summaries from uploaded PDFs. Frontend (React Native + TypeScript) collects inputs and renders results. Backend (FastAPI + Python) validates PDFs, runs LLM workflows, persists job state to a local cache, and exposes REST APIs.

### Monorepo Layout

```
financial-summarizer/
├── summarizer-app/                # Frontend (React Native + Expo)
└── backend/                       # Backend (FastAPI)
```

---

## 1) Tech Stack

- Frontend: React Native (Expo), TypeScript, Zustand, Axios, pdfmake
- Backend: FastAPI, Python 3.12, PyMuPDF, OpenAI, Gemini 
- Infra: Local file cache, background threads, Render (deployment)

---

## 2) Architecture & Data Flow (High-level)

1. Frontend `UploadScreen` captures: call_type, summary_length, answer_format, and a PDF file.
2. Frontend calls `POST /validate_file` to validate/extract transcripts and create or reuse a job.
3. Backend stores transcripts and job state under `backend/local_cache/` (dedup enabled).
4. Frontend polls `GET /summary?job_id=...` until sufficient outputs are ready.
5. Results are shown on `ResultScreen`, with copy/PDF export options.
6. User can cancel via `POST /cancel?job_id=...` (immediate stop + cleanup of partial outputs).

---

## 3) Frontend

### Key Files

- `summarizer-app/App.tsx`: Status-driven routing (Upload → Loading → Results).
- `summarizer-app/src/screens/UploadScreen.tsx`: User inputs, file picker, submit.
- `summarizer-app/src/screens/LoadingScreen.tsx`: Progress and cancel control.
- `summarizer-app/src/screens/ResultScreen.tsx`: Render results (earnings/conference), export.
- `summarizer-app/src/services/api.ts`: `validatePdf`, `getSummary`, `cancelJob`, `healthCheck`.
- `summarizer-app/src/state/SummaryStore.ts`: Zustand store (status, progress, results, actions).

### State Model (Zustand)

- Global: `status`, `validation`, `result`, `currentCallType`, `jobId`, `stage`, `percentComplete`, `stages`, `warnings`.
- Persisted (localStorage): `status`, `validation`, `result`, `currentCallType`.
- Local component state: `callType`, `summaryLength`, `answerFormat`, `selectedFile` (not persisted).

### Frontend Flow

1. Upload → `summarize(file, callType, summaryLength, { q_a: answerFormat })`.
2. On validation success: set `status=validated` (10% progress), then `status=loading` and start polling.
3. Poll every 5s (after 10s initial delay) up to 4 minutes. When Q&A is ready and Overview is ready or failed, set `status=success` and show results.
4. Cancel stops polling and resets state to `idle`.

---

## 4) Backend

### Directory Layout

```
backend/
├── src/
│   ├── api/
│   │   ├── app.py                    # FastAPI app (includes routers)
│   │   └── routes/
│   │       ├── file_validation.py    # POST /validate_file
│   │       └── summary.py            # GET /summary, POST /cancel
│   ├── services/
│   │   ├── precheck.py               # run_validate_file (PDF → transcripts)
│   │   └── summary_workflow.py       # run_summary_workflow_from_saved_transcripts
│   ├── utils/
│   │   ├── pdf_processor.py          # low-level PDF text extraction
│   │   ├── job_creation.py           # dedup, job create, background thread
│   │   ├── job_state.py              # JobStatusManager (status, cancel events)
│   │   ├── job_utils.py              # atomic writes, read helpers, job state helpers
│   │   └── cache_cleanup.py          # TTL cleanup thread (retention/force)
│   ├── llm/
│   │   ├── llm_client.py             # model clients
│   │   └── llm_utils.py              # prompts + LLM calls (Q&A, overview, judge)
│   └── config/
│       ├── constants.py              # CACHE_DIR, TTL constants, etc.
│       └── runtime.py                # prompt versions used in signatures
└── local_cache/                      # transcripts, jobs, job_index.json
```

### REST API

- `GET /health`: Liveness check.
- `POST /validate_file` (multipart form): `file`, `call_type`, `summary_length`, `answer_format` → returns `{ is_validated, transcript_name, job_id?, error? }`.
- `GET /summary?job_id=...`: Returns `status.json` plus any available outputs.
- `POST /cancel?job_id=...`: Signals cancel event, marks job cancelled, removes partial outputs.

### Workflow (Backend)

1. `precheck.run_validate_file`: Validate PDF, extract transcripts, compute `content_hash`, persist `transcript_name.json`.
2. `file_validation.validate_file_endpoint`: If validated, try `_handle_deduplication`; else `_create_new_job`.
3. `job_creation._create_new_job`: Create `job_id/`, write `status.json`, start background thread.
4. `summary_workflow.run_summary_workflow_from_saved_transcripts`: Q&A → Overview+Judge (parallel), update `status.json`, write outputs.
5. `summary.get_summary`: Serve current `status` and outputs for polling.

### Deduplication

- Signature = `content_hash + call_type + summary_length + prompt_versions + answer_format` via `job_creation._compute_signature`.
- Map signature → `job_id` in `local_cache/job_index.json`.
- `_handle_deduplication` returns existing `job_id` if all outputs are reusable.

### Local Cache

- Transcripts: `local_cache/<original>.pdf.json` (extracted text + content_hash).
- Jobs: `local_cache/<job_id>/status.json`, `q_a_summary.json`, `overview_summary.json`, `summary_evaluation.json`.
- Atomic writes and safe reads via `utils/job_utils.py`.

#### Cleanup (TTL)

- Background thread (`utils/cache_cleanup.py::_start_cleanup_thread`) runs a cycle every `CLEANUP_INTERVAL_SECONDS`.
- Deletes finished jobs older than `RETENTION_DAYS` and any jobs older than `FORCE_CLEANUP_DAYS` (stuck) with job-level locks; prunes `job_index.json`.
- Note: On Render free tier (autosleeps), cleanup only runs while the service is awake.

### Cancellation

- Frontend calls `POST /cancel?job_id=...`.
- `JobStatusManager.signal_cancel(job_id)` flips a `threading.Event`; workflow checks the flag at key points and stops quickly; partial outputs are removed; `status.json` marked as cancelled.

---

## 5) Setup & Run Locally

### Prerequisites

- Node 18+, pnpm/npm, Expo CLI (optional for web), Python 3.12+, pip
- API keys (set as env vars): `OPENAI_API_KEY`, `GOOGLE_API_KEY` (Gemini)

### Backend

```
cd backend
pip install -r requirements.txt
python -m uvicorn src.api.app:app --reload --host 0.0.0.0 #Start server
```

### Frontend

```
cd summarizer-app
npm install
npm start #Clicks on  localhost://
```

---
