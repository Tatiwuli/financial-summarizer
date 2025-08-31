
# 1. Health Check
Frontend uses a /health check endpoint to check the server status. If the server is down it will immediately raise an error.

# File Validation Process 
source : app.py

1. Process the uploaded  file anyways
2. Check  the uploaded file  name if equal to existing one, check content hash ( q a and presentation text).If equal, don't save the new uploaded, use the existing one. If parsing error of the existing one, just overwrite with the uploaded one. If not matched, save the uplaoded one 
Still had to process duplicated files to get the content hash as a unique and reliable key for distinguishing uploaded files. because we can have diff transcripts but with same name from diff users. 


### Fail Cases:



- Backend returns early (no job, no thread, no job_id) when validation fails:
```166:169:financial-summarizer/backend/src/api/app.py
    # If validation failed, return early without creating a job
    if not bool(payload.get("is_validated")):
        return payload
```

- Frontend stays on Upload Screen and shows an error when validation fails. The store sets status="error" and a message, and returns before any polling setup:
```131:140:financial-summarizer/summarizer-app/src/state/SummaryStoreTest.ts
        const isValidated = Boolean(validation?.is_validated)
        if (!isValidated) {
          set({
            status: "error",
            error: "Validation failed",
            result: null,
            validation: null,
          })
          clearPersistedState()
          return
        }
```
And Upload screen renders the error text on that page:
```180:181:financial-summarizer/summarizer-app/src/screens/UploadScreen.tsx
        {error && <Text style={styles.errorText}>{error}</Text>}
```

- Frontend never calls GET /summary after failed validation, because polling only starts when a job_id exists:
```166:175:financial-summarizer/summarizer-app/src/state/SummaryStoreTest.ts
        // 3) Start polling after 10 seconds
        if (jobId) {
          set({ status: "loading" })
          ...
          const poll = async () => {
            const res = await getSummary(jobId)
            ...
```
**ClearPersistedState()**

- It clears the  state we persist in the browser’s localStorage (web). Specifically, it removes the `STORAGE_KEY` entry so a later app load won’t restore a stale status/validation.
So clearPersistedState removes that saved object to avoid resuming into a bad state after an error.

Evidence:
```69:82:financial-summarizer/summarizer-app/src/state/SummaryStoreTest.ts
const clearPersistedState = () => {
  if (!canUseLocalStorage()) return
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}
```

- We only persist `status` and `validation`:
```31:63:financial-summarizer/summarizer-app/src/state/SummaryStoreTest.ts
type PersistedState = Pick<SummaryState, "status" | "validation">
...
const savePersistedState = (state: PersistedState) => {
  ...
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}
```

# Creating JOb process
# When status of a job is failed 

**When user clicks cancel button**
if cancel_event is not None and cancel_event.is_set():
        if job_dir:
            _update_status(job_dir, {
                "current_stage": "failed",
                "updated_at": _now(),
                "error": {"code": "cancelled", "message": "Cancelled before start"},
            })
        return {
            "title": "Untitled",
            "call_type": call_type,
            "blocks": [],
        }

     - Early cancel check before judge/overview
    if cancel_event is not None and cancel_event.is_set():
        if job_dir:
            _update_status(job_dir, {
                "current_stage": "failed",
                "stages": {"overview_summary": "failed", "summary_evaluation": "failed"},
                "updated_at": _now(),
                "error": {"code": "cancelled", "message": "Cancelled by user"},
            })
        return {
            "title": "Untitled",
            "call_type": call_type,
            "blocks": blocks,
        }
**In Q_A Summary Stage**
- If fails to save the summary output to the project folder
```if not ok:
                _update_status(job_dir, {
                    "stages": {"q_a_summary": "failed"},
                    "current_stage": "failed",
                    "updated_at": _now(),
                    "error": {"code": "persist_error", "message": "Failed to write q_a_summary.json. Check the error logs on Render and retrieve the summary from the project folder"},
                })
             ```

 - If fails to parse the output in JSON format
## Cancel process
Here’s the full cancel flow end-to-end and what each variable does.

What triggers cancel
- Frontend Stop button (Loading screen).
When user clicks cancel, frontend sends POST /cancel?job_id=... and immediately clears polling locally (while setting state back to idle to go back to UploadScreen.
The backend removes all the outputs accumulated from the job directory.

Backend: cancel endpoint
- Route: POST /cancel
- Input: job_id (query param)
- Variables:
  - job_dir: transcripts/<job_id> directory where status.json lives.
  - status_path: path to status.json inside job_dir.
  - _CANCEL_EVENTS: dict[job_id → threading.Event] shared in-process.
  - evt: the threading.Event for this job (if present).
- Actions:
  - evt.set() signals the running background thread to stop ASAP.
  - status.json is updated immediately:
    - current_stage: "cancelled"
    - any running stages in stages map are flipped to "failed"
    - error: { code: "cancelled", message: "Cancelled by user" }
  - Returns { ok: true, status: "cancelled" }.

Backend: background workflow (summary_workflow)
- Entry: run_summary_workflow_from_saved_transcripts(transcript_name, call_type, summary_length, job_dir, cancel_event)
- Variables:
  - cancel_event: the same threading.Event stored in _CANCEL_EVENTS[job_id]
  - job_dir: enables persistence; if None, everything would be in-memory (not your case).
  - status.json fields:
    - current_stage: "q_a_summary" | "overview_summary" | "summary_evaluation" | "completed" | "failed" (and briefly "cancelled" only when /cancel sets it)
    - stages: { validating, q_a_summary, overview_summary, summary_evaluation: "pending"|"running"|"completed"|"failed" }
- Where cancel is honored:
  1) Before starting Q&A:
     - If cancel_event.is_set(): mark job failed with error cancelled and return immediately.
  2) Between Q&A and the parallel steps:
     - If cancel_event.is_set(): mark both overview_summary and summary_evaluation as failed, mark current_stage "failed", and return with whatever Q&A block exists.
  3) During the parallel judge/overview run:
     - The loop checks cancel_event while waiting. If set, it cancels any pending futures, marks their stages failed, and breaks.
- Finalization:
  - If status.json happens to be in a "cancelled" state, it is converted to "failed" so the frontend stop condition is consistent.
  - If Q&A completed and both overview and judge are terminal ("completed" or "failed"), current_stage becomes "completed" (this allows partial success: Q&A done, overview or judge failed).

Frontend polling and UI behavior
- While loading, the store polls GET /summary every 5s and updates:
  - stage (current_stage)
  - percentComplete
  - stages map
  - warnings (if any)
  - partial outputs (q_a_summary.json, overview_summary.json, summary_evaluation.json) as they appear
- Stop conditions:
  - If current_stage === "failed": clear polling and show the error banner (from status.json.error.message).
  - If current_stage === "completed": stop polling and show results.
  - Note: Immediately after POST /cancel the backend sets current_stage to "cancelled"; the workflow quickly converts that to "failed". If you want to stop instantly on "cancelled", add that extra check in polling (optional).

What each key variable/field means
- job_id: unique identifier for the run; used by frontend for polling and cancel.
- job_dir: transcripts/<job_id>; directory for persisted status and outputs.
- status.json fields:
  - current_stage:
    - "q_a_summary": generating Q&A
    - "overview_summary": generating overview
    - "summary_evaluation": running judge
    - "completed": all terminal and Q&A completed
    - "failed": unrecoverable failure or cancelled
    - "cancelled": transient marker (set by /cancel), later converted to "failed"
  - stages: per-stage lifecycle: "pending" | "running" | "completed" | "failed"
  - percent_complete: coarse progress indicator
  - warnings: array of strings (e.g., timeouts or persist issues)
  - error: { code, message } present on failure/cancel
- _CANCEL_EVENTS[job_id]: threading.Event used to cooperatively interrupt the background thread.
- cancel_event: the Event passed into the workflow, checked often to stop work and update status correctly.

Net effect you see
- Press Stop: POST /cancel sets "cancelled" immediately; the thread sees the event, stops, marks stages failed, and current_stage becomes "failed". Frontend polling then stops and shows the user-friendly message. Partial outputs already written (e.g., Q&A) remain available for the UI.