import { create } from "zustand"
import {
  healthCheck,
  validatePdf,
  getSummary,
  cancelJob,
} from "../services/api"
import axios from "axios"
import {
  SummaryState,
  SummaryStatus,
  ValidationState,
  SummaryResult,
} from "../types"

// Remove duplicate interface - using imported SummaryState from types

// ------- CODES FOR PERSISTING FRONTEND STATE WHEN USER REFRESHES THE PAGE -------
// Web-only persistence using localStorage
const STORAGE_KEY = "kapitalo_summary_state_v2"

type PersistedState = Pick<
  SummaryState,
  "status" | "validation" | "result" | "currentCallType"
>

const canUseLocalStorage = (): boolean => {
  try {
    return (
      typeof window !== "undefined" &&
      typeof window.localStorage !== "undefined"
    )
  } catch {
    return false
  }
}

const loadPersistedState = (): PersistedState | null => {
  if (!canUseLocalStorage()) return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === "object") {
      return parsed as PersistedState
    }
    return null
  } catch {
    return null
  }
}

const savePersistedState = (state: PersistedState) => {
  if (!canUseLocalStorage()) return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // ignore
  }
}

const clearPersistedState = () => {
  if (!canUseLocalStorage()) return
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

export const useSummaryStore = create<SummaryState>((set) => {
  const persisted = loadPersistedState() // Always load the last state from the browser

  const initialStatus: SummaryStatus = persisted?.status || "idle" // Restore status from previous session
  const initialValidation: ValidationState | null =
    persisted?.validation || null // Restore validation from previous session
  const initialResult: SummaryResult | null = persisted?.result || null // Restore result from previous session
  const initialCallType = persisted?.currentCallType || undefined // Restore call type from previous session

  return {
    status: initialStatus, // may restore to 'validated' or 'success' from previous session
    error: null,
    result: initialResult, // may restore completed result from previous session
    validation: initialValidation,
    currentCallType: initialCallType,
    jobId: null,
    transcriptName: null,
    stage: null,
    percentComplete: null,
    warnings: [],
    cancel: async () => {
      const { jobId } = useSummaryStore.getState()
      if (!jobId) return
      try {
        await cancelJob(jobId)
      } catch (e) {
        console.warn("[SummaryStore] cancel error:", e)
      }
      // Also clear client-side polling and state back to idle/upload
      if (intervalId !== undefined) {
        clearInterval(intervalId)
        intervalId = undefined
      }
      if (timeoutId !== undefined) {
        clearTimeout(timeoutId)
        timeoutId = undefined
      }
      set({
        status: "idle",
        error: null,
        result: null,
        stage: null,
        percentComplete: null,
        jobId: null,
        stages: null,
      })
      clearPersistedState()
    },
    summarize: async (file: any, callType: string, summaryLength: string) => {
      // Start validation flow
      set({
        status: "validating",
        error: null,
        currentCallType: callType as any,
      })

      // Persist the call type
      savePersistedState({
        status: "validating",
        validation: null,
        result: null,
        currentCallType: callType as "earnings" | "conference",
      })
      // it's async
      console.log("[SummaryStore] Starting to summarize with : ", {
        fileName: file.name,
        callType,
        summaryLength,
      })

      console.log("[SummaryStore] currentCallType: ", callType)

      try {
        // Mandatory health check . Returns error if backend is not available
        try {
          await healthCheck(2000)
        } catch (_e) {
          set({
            status: "error",
            error:
              "[Health Check] Backend is not available. Refresh the page and try again. If the problem persists, check the backend logs on Render.",
            result: null,
          })
          clearPersistedState()
          return
        }

        // Validate file
        console.log("[SummaryStore]  await validatePdf")
        const validation = await validatePdf(file, callType, summaryLength)
        console.log("[SummaryStore] validation response:", validation)

        const filename =
          validation?.filename ||
          validation?.input?.filename ||
          validation?.transcript_name ||
          file.name
        const isValidated = Boolean(validation?.is_validated)
        if (!isValidated) {
          const backendMsg = (validation as any)?.error?.message
          set({
            status: "error",
            error: backendMsg || "Validation failed",
            result: null,
            validation: null,
          })
          clearPersistedState()
          return
        }
        //If validation is successful: Keep validation-only state; do not set summary result
        const jobId = validation?.job_id
        const transcriptName = validation?.transcript_name || filename
        set({
          status: "validated",
          error: null,
          validation: {
            isValidated: true,
            filename,
            validatedAt: validation?.validated_at,
          },
          jobId,
          transcriptName,
          stage: "File Validated! Starting summary",
          percentComplete: 10, // update the progress bar
        }) // save the progress in the browser
        savePersistedState({
          status: "validated",
          validation: {
            isValidated: true,
            filename,
            validatedAt: validation?.validated_at,
          },
          result: null,
          currentCallType: undefined,
        })

        // Frontend start polling the result
        if (jobId) {
          set({ status: "loading" })
          const startTime = Date.now()
          const maxDurationMs = 4 * 60 * 1000 // 4 minutes
          const pollIntervalMs = 5000

          const poll = async () => {
            try {
              const res = await getSummary(jobId) // GET request to get summary outputs from backend
              // Update stage/progress
              set({
                stage: res.current_stage,
                percentComplete: res.percent_complete,
                stages: res.stages,
                warnings: (res as any)?.warnings || [],
              })

              // Build partial result from available outputs
              const outputs = res.outputs || {}
              const blocks: any[] = []

              // If Q&A summary is available, add it to the blocks
              if (outputs.q_a_summary) {
                const qMeta = outputs.q_a_summary.metadata || {}
                const qData = outputs.q_a_summary.data || {}
                const isShort =
                  (res.input?.summary_length || "long") === "short"
                blocks.push({
                  type: isShort ? "q_a_short" : "q_a_long",
                  metadata: qMeta,
                  data: qData,
                })
              }

              // If overview summary is available, add it to the blocks
              if (outputs.overview_summary) {
                const ovMeta = outputs.overview_summary.metadata || {}
                const ovData = outputs.overview_summary.data || {}
                blocks.push({
                  type: "overview",
                  metadata: ovMeta,
                  data: ovData,
                })
              }

              // If summary evaluation is available, add it to the blocks
              if (outputs.summary_evaluation) {
                const jMeta = outputs.summary_evaluation.metadata || {}
                const jData = outputs.summary_evaluation.data || {}
                blocks.push({ type: "judge", metadata: jMeta, data: jData })
              }

              // Get Overview and Q&A Outputs
              const hasOverview = blocks.some((b) => b.type === "overview")
              const hasQA = blocks.some(
                (b) => String(b.type).startsWith("q_a_") // q_a_long or q_a_short
              )
              const overviewFailed =
                (res.stages && res.stages["overview_summary"]) === "failed"
              // Get title from Overview or Q&A
              const title =
                outputs.q_a_summary?.data?.title ||
                outputs.overview_summary?.data?.title ||
                "Untitled"

              // Get call type from user input
              const callTypeForResult =
                res.input?.call_type || "conference call"

              // If both overview and q_a are done, or overview failed and q_a is done, set success and show result
              if ((hasOverview && hasQA) || (overviewFailed && hasQA)) {
                const resultData = {
                  title,
                  call_type: callTypeForResult,
                  blocks,
                }
                set({
                  status: "success",
                  result: resultData,
                })

                // Persist the successful result
                savePersistedState({
                  status: "success",
                  validation: {
                    isValidated: true,
                    filename: useSummaryStore.getState().validation?.filename,
                    validatedAt:
                      useSummaryStore.getState().validation?.validatedAt,
                  },
                  result: resultData,
                  currentCallType: callTypeForResult as
                    | "earnings"
                    | "conference",
                })
              } else {
                // keep loading while waiting for both
                set({ status: "loading" })
              }

              // Stop conditions
              // Note these stages are defined by the summary workflow in the backend
              if (res.current_stage === "completed") {
                if (intervalId !== undefined) {
                  clearInterval(intervalId)
                  intervalId = undefined
                }
                return
              }
              // If any stage is set to failed
              if (res.current_stage === "failed") {
                if (intervalId !== undefined) {
                  clearInterval(intervalId)
                  intervalId = undefined
                }
                const errMsg = (res as any)?.error?.message || "Job failed"
                set({ status: "error", error: errMsg })
                return // stop polling
              }
              // If timeout: do one final fetch before stopping
              if (Date.now() - startTime > maxDurationMs) {
                try {
                  console.log("[SummaryStore] Final fetch before stopping")
                  const res2 = await getSummary(jobId)
                  // Update stage/progress
                  set({
                    stage: res2.current_stage,
                    percentComplete: res2.percent_complete,
                    stages: res2.stages,
                    warnings: (res2 as any)?.warnings || [],
                  })

                  const outputs2 = res2.outputs || {}
                  const blocks2: any[] = []

                  if (outputs2.q_a_summary) {
                    const qMeta2 = outputs2.q_a_summary.metadata || {}
                    const qData2 = outputs2.q_a_summary.data || {}
                    const isShort2 =
                      (res2.input?.summary_length || "long") === "short"
                    blocks2.push({
                      type: isShort2 ? "q_a_short" : "q_a_long",
                      metadata: qMeta2,
                      data: qData2,
                    })
                  }

                  if (outputs2.overview_summary) {
                    const ovMeta2 = outputs2.overview_summary.metadata || {}
                    const ovData2 = outputs2.overview_summary.data || {}
                    blocks2.push({
                      type: "overview",
                      metadata: ovMeta2,
                      data: ovData2,
                    })
                  }

                  if (outputs2.summary_evaluation) {
                    const jMeta2 = outputs2.summary_evaluation.metadata || {}
                    const jData2 = outputs2.summary_evaluation.data || {}
                    blocks2.push({
                      type: "judge",
                      metadata: jMeta2,
                      data: jData2,
                    })
                  }

                  const hasOverview2 = blocks2.some(
                    (b) => b.type === "overview"
                  )
                  const hasQA2 = blocks2.some((b) =>
                    String(b.type).startsWith("q_a_")
                  )
                  const overviewFailed2 =
                    (res2.stages && res2.stages["overview_summary"]) ===
                    "failed"
                  const title2 =
                    outputs2.overview_summary?.data?.title ||
                    outputs2.q_a_summary?.data?.title ||
                    "Untitled"
                  const callTypeForResult2 =
                    res2.input?.call_type || "conference call"

                  if (res2.current_stage === "completed") {
                    set({
                      status: "success",
                      result: {
                        title: title2,
                        call_type: callTypeForResult2,
                        blocks: blocks2,
                      },
                    })
                  } else if (
                    (hasOverview2 && hasQA2) ||
                    (overviewFailed2 && hasQA2)
                  ) {
                    set({
                      status: "success",
                      result: {
                        title: title2,
                        call_type: callTypeForResult2,
                        blocks: blocks2,
                      },
                    })
                  }
                } catch (e) {
                  console.warn("[SummaryStore] final timeout fetch failed:", e)
                }

                if (intervalId !== undefined) {
                  clearInterval(intervalId)
                  intervalId = undefined
                }
                return
              }
            } catch (e) {
              // transient errors: keep polling until timeout
              console.warn("[SummaryStore] polling error:", e)
            }
          }

          // Initial delay 10s then poll every 5s
          if (timeoutId !== undefined) {
            clearTimeout(timeoutId)
            timeoutId = undefined
          }
          timeoutId = setTimeout(() => {
            poll()
            // Clear any existing interval before setting a new one
            if (intervalId !== undefined) {
              clearInterval(intervalId)
              intervalId = undefined
            }
            intervalId = setInterval(poll, pollIntervalMs)
          }, 10000)
        }
      } catch (err: any) {
        console.log("[SummaryStore]  Caught error:", err)
        let msg = "An unknown error occurred"

        if (axios.isAxiosError(err)) {
          // Prefer server structured error
          const data: any = err.response?.data
          msg = data?.error?.message || data?.message || err.message || msg
        } else if (err instanceof Error) {
          msg = err.message
        }

        console.log("[SummaryStore]  Setting error state:", msg)
        set({ status: "error", error: msg, result: null }) // agora é string mesmo
        // Do not persist error state; clear any stale persisted success
        clearPersistedState()
      }
    },

    reset: () => {
      // clear polling interval if present
      if (intervalId !== undefined) {
        clearInterval(intervalId)
        intervalId = undefined
      }
      if (timeoutId !== undefined) {
        clearTimeout(timeoutId)
        timeoutId = undefined
      }
      set({
        status: "idle",
        error: null,
        result: null,
        validation: null,
        currentCallType: undefined,
        jobId: null,
        transcriptName: null,
        stage: null,
        percentComplete: null,
        stages: null,
        warnings: [],
      })
      clearPersistedState()
      console.log("[SummaryStore] Go back. Resetting state")
    },
  }
})

// interval handle lives at module scope to avoid duplicates
// Use NodeJS.Timer | number for cross-platform TypeScript compatibility
let intervalId: ReturnType<typeof setInterval> | undefined = undefined
let timeoutId: ReturnType<typeof setTimeout> | undefined = undefined
