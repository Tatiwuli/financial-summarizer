import axios from "axios"
import { DocumentPickerAsset } from "expo-document-picker"
import { API_BASE } from "../env" // keep as-is for relative path stability

import {
  ValidationResponse,
  SummaryResponse,
  CancelJobResponse,
} from "../types/api"

const apiClient = axios.create({
  baseURL: API_BASE,
})

apiClient.defaults.timeout = 60000

// Exponential backoff retry configuration
const MAX_RETRIES = 4 // four retries
const INITIAL_BACKOFF_MS = 10000 // 10 seconds

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// Retry only on network errors (no response) and 5xx server errors; never on 4xx
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error?.config || {}
    // Axios typing doesn't include custom fields; use duck-typing
    const currentAttempt: number = (config.__retryCount as number) ?? 0

    const status: number | undefined = error?.response?.status
    const isNetworkError = !error?.response
    const isRetryableStatus =
      typeof status === "number" && status >= 500 && status < 600
    const shouldRetry = isNetworkError || isRetryableStatus

    if (shouldRetry && currentAttempt < MAX_RETRIES) {
      config.__retryCount = currentAttempt + 1
      // fire optional hook on first retry to allow UI messaging
      try {
        if (
          currentAttempt === 0 &&
          typeof (config as any).__onFirstRetry === "function"
        ) {
          ;(config as any).__onFirstRetry()
        }
      } catch {}
      const delay = INITIAL_BACKOFF_MS * Math.pow(2, currentAttempt)
      await sleep(delay)
      return apiClient.request(config)
    }

    return Promise.reject(error)
  }
)

/**
 * Envia o PDF e os parâmetros para o backend para sumarização.
 */

export const healthCheck = async (
  timeoutMs: number = 2000,
  onFirstRetry?: () => void
) => {
  const response = await apiClient.get("/health", {
    timeout: timeoutMs,
    // custom hook consumed by the interceptor
    ...(onFirstRetry ? { __onFirstRetry: onFirstRetry } : {}),
  } as any)
  return response.data
}

export const validatePdf = async (
  file: DocumentPickerAsset,
  callType: string,
  summaryLength: string,
  answerFormat: string = "prose"
) => {
  const webFile = (file as any).file as File | undefined
  if (!webFile) {
    throw new Error("File not found")
  }

  const formData = new FormData()
  // user inputs
  formData.append("file", webFile, webFile.name || file.name || "document.pdf")
  formData.append("call_type", callType)
  formData.append("summary_length", summaryLength)
  formData.append("answer_format", answerFormat)

  try {
    // Send POST API request
    const response = await apiClient.post("/validate_file", formData)
    // Parse the response
    return response.data as ValidationResponse
  } catch (error) {
    throw error
  }
}

export const getSummary = async (jobId: string): Promise<SummaryResponse> => {
  // GET request with a job id
  const response = await apiClient.get("/summary", {
    params: { job_id: jobId },
  })

  return response.data as SummaryResponse
}

export const cancelJob = async (jobId: string): Promise<CancelJobResponse> => {
  const response = await apiClient.post("/cancel", null, {
    params: { job_id: jobId },
  })
  return response.data as CancelJobResponse
}
