import { create } from "zustand"
import { healthCheck, validatePdf } from "../services/api"
import axios from "axios"

interface SummaryState {
  status: "idle" | "validating" | "validated" | "loading" | "success" | "error"
  error: string | null
  result: any | null
  validation: {
    isValidated: boolean
    filename?: string
    validatedAt?: string
  } | null
  summarize: (
    file: any,
    callType: string,
    summaryLength: string
  ) => Promise<void>
  reset: () => void
}

// Web-only persistence using localStorage
const STORAGE_KEY = "kapitalo_summary_state_v2"

type PersistedState = Pick<SummaryState, "status" | "validation">

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

//create is from zustand para criar uma "caixinha" de estado
// THIS IS A HOOK
//set => ({...}) syntax para atualizar o estado da caixinha
export const useSummaryStore = create<SummaryState>((set) => {
  const persisted = loadPersistedState()

  const initialStatus: SummaryState["status"] = persisted?.status || "idle"
  const initialValidation = persisted?.validation || null

  return {
    status: initialStatus, // may restore to 'validated' from previous session
    error: null,
    result: null,
    validation: initialValidation,
    summarize: async (file, callType, summaryLength) => {
      // Start validation flow
      set({ status: "validating", error: null })
      // it's async
      console.log("[Zustand] Starting to summarize with : ", {
        fileName: file.name,
        callType,
        summaryLength,
      })

      try {
        // 1) Health check obrigatório (timeout curto)
        try {
          await healthCheck(2000)
        } catch (_e) {
          set({
            status: "error",
            error: "Backend indisponível (health check)",
            result: null,
          })
          clearPersistedState()
          return
        }

        // 2) Validate file
        console.log("[Zustand]  await validatePdf")
        const validation = await validatePdf(file, callType, summaryLength)
        console.log("[Zustand] validation response:", validation)

        const filename =
          validation?.filename ||
          validation?.input?.filename ||
          validation?.transcript_name ||
          file.name
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
        // Keep validation-only state; do not set summary result
        set({
          status: "validated",
          error: null,
          validation: {
            isValidated: true,
            filename,
            validatedAt: validation?.validated_at,
          },
        })
        savePersistedState({
          status: "validated",
          validation: {
            isValidated: true,
            filename,
            validatedAt: validation?.validated_at,
          },
        })
      } catch (err: any) {
        console.log("[Zustand]  Caught error:", err)
        let msg = "An unknown error occurred"

        if (axios.isAxiosError(err)) {
          // Prefer server structured error
          const data: any = err.response?.data
          msg = data?.error?.message || data?.message || err.message || msg
        } else if (err instanceof Error) {
          msg = err.message
        }

        console.log("[Zustand]  Setting error state:", msg)
        set({ status: "error", error: msg, result: null }) // agora é string mesmo
        // Do not persist error state; clear any stale persisted success
        clearPersistedState()
      }
    },

    reset: () => {
      set({ status: "idle", error: null, result: null, validation: null })
      clearPersistedState()
      console.log("[Zustand] Go back. Resetting state")
    },
  }
})
