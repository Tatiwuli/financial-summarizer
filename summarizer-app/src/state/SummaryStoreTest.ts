import { create } from "zustand"
import { summarizePdf } from "../services/api"
import axios from "axios"

interface SummaryState {
  status: "idle" | "loading" | "success" | "error"
  error: string | null
  result: any | null
  summarize: (
    file: any,
    callType: string,
    summaryLength: string
  ) => Promise<void>
  reset: () => void
}

// Web-only persistence using localStorage
const STORAGE_KEY = "kapitalo_summary_state_v1"

type PersistedState = Pick<SummaryState, "status" | "result">

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

  const initialStatus: SummaryState["status"] =
    persisted?.status === "success" && persisted.result ? "success" : "idle"
  const initialResult =
    persisted?.status === "success" && persisted.result
      ? persisted.result
      : null

  return {
    status: initialStatus, // not doing anything yet unless we have a persisted success
    error: null,
    result: initialResult,
    summarize: async (file, callType, summaryLength) => {
      // Once the user clicks the summarize button, the state is set to loading
      set({ status: "loading" })
      // it's async
      console.log("[Zustand] Starting to summarize with : ", {
        fileName: file.name,
        callType,
        summaryLength,
      })

      try {
        //call API SERVICE
        console.log("[Zustand] before await summarizePdf")
        const responseData = await summarizePdf(file, callType, summaryLength)
        console.log("[Zustand] AFTER await (should always print)")
        set({ status: "success", error: null, result: responseData })
        // Persist success state for reload resilience on web
        savePersistedState({ status: "success", result: responseData })
        console.log("[Zustand] AFTER set success (same tick)")
        setTimeout(() => console.log("[Zustand] tick after set success"), 0)
      } catch (err: any) {
        console.log("[Zustand]  Caught error:", err)
        let msg = "An unknown error occurred"

        if (axios.isAxiosError(err)) {
          msg =
            (err.response?.data as any)?.error?.message ||
            err.message || // ex.: "Request failed with status code 422"
            msg
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
      set({ status: "idle", error: null, result: null })
      clearPersistedState()
      console.log("[Zustand] Go back. Resetting state")
    },
  }
})
