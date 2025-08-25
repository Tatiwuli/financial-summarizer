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
  formData.append("file", webFile, webFile.name || file.name || "document.pdf")
  formData.append("call_type", callType)
  formData.append("summary_length", summaryLength)

  try {
    const response = await apiClient.post("/v2/validate_file", formData)
    return response.data as {
      is_validated: boolean
      validated_at?: string
      input?: { call_type?: string; summary_length?: string; filename?: string }
      transcript_name?: string
      filename?: string
    }
  } catch (error) {
    // Let caller parse a structured error
    throw error
  }
}
