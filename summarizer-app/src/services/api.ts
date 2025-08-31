import axios from "axios"
import { DocumentPickerAsset } from "expo-document-picker"
import { API_BASE } from "../env" // keep as-is for relative path stability

// !! IMPORTANTE !!

// Substitua 'YOUR_COMPUTER_IP' pelo endereço IP da sua máquina na sua rede Wi-Fi.
// Emuladores/dispositivos não conseguem acessar 'localhost' ou '127.0.0.1'.
// Windows: `ipconfig` | macOS/Linux: `ifconfig`

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
    return response.data as {
      is_validated: boolean
      validated_at?: string
      input?: { call_type?: string; summary_length?: string; filename?: string }
      transcript_name?: string
      filename?: string
      job_id: string
    }
  } catch (error) {
    throw error
  }
}

export const getSummary = async (jobId: string) => {
  // GET request with a job id
  const response = await apiClient.get("/summary", {
    params: { job_id: jobId },
  })

  return response.data as {
    job_id: string
    transcript_name: string
    current_stage:
      | "q_a_summary"
      | "overview_summary"
      | "summary_evaluation"
      | "completed"
      | "failed"
    //each stage has these status: pending, running, completed, failed
    stages: Record<string, "pending" | "running" | "completed" | "failed">
    // for progress bar
    percent_complete: number
    updated_at: string
    input?: { call_type?: string; summary_length?: string; filename?: string }
    outputs?: {
      q_a_summary?: any
      overview_summary?: any
      summary_evaluation?: any
    }
    error?: { code?: string; message?: string }
  }
}

export const cancelJob = async (jobId: string) => {
  const response = await apiClient.post("/cancel", null, {
    params: { job_id: jobId },
  })
  return response.data as { ok: boolean; job_id: string; status: string }
}
