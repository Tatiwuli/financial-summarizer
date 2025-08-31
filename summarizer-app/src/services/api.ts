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

/**
 * Envia o PDF e os parâmetros para o backend para sumarização.
 */

export const healthCheck = async (timeoutMs: number = 2000) => {
  const response = await apiClient.get("/health", { timeout: timeoutMs })
  return response.data
}

export const validatePdf = async (
  file: DocumentPickerAsset,
  callType: string,
  summaryLength: string
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
