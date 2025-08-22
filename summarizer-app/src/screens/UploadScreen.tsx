import React, { useState } from "react"
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Alert,
} from "react-native"
import * as DocumentPicker from "expo-document-picker"

import { ToggleButton } from "../components/common/ToggleButton"
// ⚠️ Garanta que o caminho/case batem com o arquivo real:
// se o arquivo é summaryStore.ts, use "summaryStore" (não "SummaryStore")
import { useSummaryStore } from "../state/SummaryStoreTest"

type CallType = "earnings" | "conference"
type SummaryLength = "long" | "short"

export const UploadScreen: React.FC = () => {
  const [callType, setCallType] = useState<CallType>("earnings")
  const [summaryLength, setSummaryLength] = useState<SummaryLength>("long")
  const [selectedFile, setSelectedFile] =
    useState<DocumentPicker.DocumentPickerAsset | null>(null)

  // Zustand
  const { summarize, status, error, result } = useSummaryStore()

  console.log("[UploadScreen] useSummaryStore mounted")
  console.log("[UploadScreen] using store", useSummaryStore.getState().status)

  const handleSelectFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "application/pdf",
        multiple: false,
        copyToCacheDirectory: true,
      })

      console.log("[DocPicker] result:", result)

      if (result.canceled) return

      const file = result.assets?.[0]
      if (!file) {
        Alert.alert("Erro", "Não foi possível ler o arquivo selecionado.")
        return
      }

      const maxSizeBytes = 10 * 1024 * 1024 // 10MB
      if (typeof file.size === "number" && file.size > maxSizeBytes) {
        Alert.alert(
          "Erro",
          "Arquivo maior que 10MB. Por favor selecione um PDF menor."
        )
        return
      }

      console.log("[DocPicker] asset:", file)
      setSelectedFile(file)
    } catch (e) {
      console.error("Erro ao selecionar arquivo:", e)
      Alert.alert("Erro", "Falha ao selecionar o arquivo. Tente novamente.")
    }
  }

  // ✅ FECHA a função aqui (antes do return do componente)
  const handleSubmit = async () => {
    try {
      if (!selectedFile) {
        Alert.alert("Selecione um arquivo", "Você precisa escolher um PDF.")
        return
      }
      await summarize(selectedFile, callType, summaryLength)
      console.log("[UploadScreen] summarize() done")
    } catch (e) {
      console.error("[UploadScreen] handleSubmit error:", e)
    }
  } // ← FECHOU A FUNÇÃO AQUI

  // ✅ A partir daqui é o return do COMPONENTE (renderização)
  return (
    <SafeAreaView style={styles.wrapper}>
      <View style={styles.container}>
        <Text style={styles.title}>New Summary</Text>

        <Text style={styles.label}>Select the call type</Text>
        <View style={styles.toggleGroup}>
          <ToggleButton
            label="Earnings Call"
            isActive={callType === "earnings"}
            onPress={() => setCallType("earnings")}
          />
          {/** Temporarily hidden for deploy
          <ToggleButton
            label="Conference Call"
            isActive={callType === "conference"}
            onPress={() => setCallType("conference")}
          />
          */}
        </View>

        <Text style={styles.label}>Select the summary length</Text>
        <View style={styles.toggleGroup}>
          <ToggleButton
            label="Long Summary"
            isActive={summaryLength === "long"}
            onPress={() => setSummaryLength("long")}
          />
          <ToggleButton
            label="Short Summary"
            isActive={summaryLength === "short"}
            onPress={() => setSummaryLength("short")}
            disabled={callType === "conference"}
            style={callType === "conference" ? { opacity: 0.6 } : undefined}
          />
        </View>

        <TouchableOpacity style={styles.uploadBox} onPress={handleSelectFile}>
          {selectedFile ? (
            <Text style={styles.uploadBoxText}>{selectedFile.name}</Text>
          ) : (
            <View style={{ alignItems: "center" }}>
              <Text style={styles.uploadBoxText}>
                Upload or Drop the transcript in PDF
              </Text>
              <Text style={styles.uploadBoxSubtext}>*.pdf (10MB)</Text>
            </View>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.submitButton} onPress={handleSubmit}>
          <Text style={styles.submitButtonText}>Generate Summary</Text>
        </TouchableOpacity>

        {/* ✅ Renderize o resultado/erro AQUI, não dentro do handleSubmit */}
        {status === "success" && result && (
          <Text selectable style={{ marginTop: 12 }}>
            {JSON.stringify(result, null, 2)}
          </Text>
        )}

        {status === "loading" && (
          <Text style={{ marginTop: 12 }}>Summarizing...</Text>
        )}

        {error && <Text style={styles.errorText}>{error}</Text>}
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: "#FFFFFF" },
  container: { flex: 1, padding: 20 },
  title: { fontSize: 28, fontWeight: "bold", marginBottom: 30 },
  label: { fontSize: 16, color: "rgb(0, 0, 0)", marginBottom: 10 },
  toggleGroup: {
    flexDirection: "row",
    alignItems: "flex-start",
    columnGap: 12,
    marginBottom: 20,
  },
  toggleButton: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 10,
    minHeight: "30%",
  },
  uploadBox: {
    borderWidth: 2,
    borderColor: "#C7C7CC",
    borderStyle: "dashed",
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#F9F9F9",
    minHeight: 150,
    marginTop: 20,
  },
  uploadBoxText: { fontSize: 16, color: "#666", fontWeight: "500" },
  uploadBoxSubtext: { fontSize: 14, color: "#8A8A8E", marginTop: 5 },
  submitButton: {
    backgroundColor: "#007AFF",
    borderRadius: 12,
    padding: 15,
    alignItems: "center",
    justifyContent: "center",
    marginTop: "auto",
    marginBottom: 20,
  },
  submitButtonText: { color: "#FFFFFF", fontSize: 18, fontWeight: "600" },
  errorText: { color: "red", textAlign: "center", marginTop: 10 },
})
