import axios from "axios"
import { DocumentPickerAsset } from "expo-document-picker"
import { API_BASE } from "../env"

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
export const summarizePdf = async (
  file: DocumentPickerAsset,
  callType: string,
  summaryLength: string
) => {
  // FormData é o formato necessário para enviar arquivos via HTTP.
  const webFile = (file as any).file as File | undefined
  if (!webFile) {
    throw new Error("File not found")
  }

  // O backend espera um arquivo no campo 'file'.
  // Criamos um objeto compatível com o que o FormData espera.
  const formData = new FormData()
  formData.append("file", webFile, webFile.name || file.name || "document.pdf")
  formData.append("call_type", callType)
  formData.append("summary_length", summaryLength)

  console.log("[apiService] file:", file)

  try {
    console.log("[apiService] Enviando requisição para /v1/summarize...")
    const response = await apiClient.post("/v1/summarize", formData)
    console.log("[apiService] Resposta recebida:", response.data)

    return response.data // Retorna os dados em caso de sucesso
  } catch (error) {
    console.error("[apiService] Erro na requisição:", error)
    // Lança o erro para que o Zustand possa capturá-lo
    throw error
  }
}
