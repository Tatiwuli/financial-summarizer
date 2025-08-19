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

//create is from zustand para criar uma "caixinha" de estado
// THIS IS A HOOK
//set => ({...}) syntax para atualizar o estado da caixinha
export const useSummaryStore = create<SummaryState>((set) => ({
  status: "idle", //not doing anything yet
  error: null,
  result: null,
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
    }
  },

  reset: () => {
    set({ status: "idle", error: null, result: null })
    console.log("[Zustand] Go back. Resetting state")
  },
}))
