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
import { useSummaryStore } from "../state/SummaryStore"

type CallType = "earnings" | "conference"
type SummaryLength = "long" | "short"
type AnswerFormat = "prose" | "bullet"

export const UploadScreen: React.FC = () => {
  //User Inputs
  const [callType, setCallType] = useState<CallType>("earnings")
  const [summaryLength, setSummaryLength] = useState<SummaryLength>("long")
  const [answerFormat, setAnswerFormat] = useState<AnswerFormat>("prose")
  const [selectedFile, setSelectedFile] =
    useState<DocumentPicker.DocumentPickerAsset | null>(null)

  // Initialize State
  const {
    summarize,
    status,
    error,
    messageType,
    result,
    stage,
    percentComplete,
  } = useSummaryStore()

  console.log("[UploadScreen] useSummaryStore mounted")
  console.log("[UploadScreen] using store", useSummaryStore.getState().status)

  //Get File from DocumentPicker
  const handleSelectFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "application/pdf",
        multiple: false,
        copyToCacheDirectory: true,
      })

      console.log("[DocPicker] result:", result)

      // When user clicks cancel on the file manager app
      if (result.canceled) return

      const file = result.assets?.[0]
      if (!file) {
        Alert.alert("Error", "Unable to read the selected file.")
        return
      }

      // Check if file is larger than 10MB
      const maxSizeBytes = 10 * 1024 * 1024 // 10MB
      if (typeof file.size === "number" && file.size > maxSizeBytes) {
        Alert.alert(
          "Erro",
          "File is larger than 10MB. Please select a smaller PDF."
        )
        return
      }

      console.log("[DocPicker] asset:", file)
      // Update the  uploaded file to the state
      setSelectedFile(file)
    } catch (e) {
      console.error("Error selecting file:", e)
      Alert.alert("Error", "Failed to select the file. Please try again.")
    }
  }

  //Submit file to backend
  const handleSubmitFile = async () => {
    try {
      if (!selectedFile) {
        Alert.alert("Select a PDF", "You need to select a PDF.")
        return
      }
      //Submit file to backend and trigger the workflow
      await summarize(selectedFile, callType, summaryLength, {
        q_a: answerFormat,
      })
      console.log("[UploadScreen] summarize_endpoint() done")
    } catch (e) {
      console.error("[UploadScreen] handleSubmitFile error:", e)
    }
  }

  // Render the UI
  return (
    <SafeAreaView style={styles.wrapper}>
      <View style={styles.container}>
        <Text style={styles.title}>New Summary</Text>

        {/* Display Call Type Buttons and save to state*/}
        <Text style={styles.label}>Select the call type</Text>
        <View style={styles.toggleGroup}>
          <ToggleButton
            label="Earnings Call"
            isActive={callType === "earnings"}
            onPress={() => setCallType("earnings")}
          />
          {
            <ToggleButton
              label="Conference Call"
              isActive={callType === "conference"}
              onPress={() => setCallType("conference")}
            />
          }
        </View>

        {/* Display Summary Length Buttons and save to state*/}
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

        {/* Display Answer Format Buttons and save to state*/}
        <Text style={styles.label}>Select the answer format</Text>
        <View style={styles.toggleGroup}>
          <ToggleButton
            label="Prose Format"
            isActive={answerFormat === "prose"}
            onPress={() => setAnswerFormat("prose")}
          />
          <ToggleButton
            label="Bullet Points"
            isActive={answerFormat === "bullet"}
            onPress={() => setAnswerFormat("bullet")}
          />
        </View>

        {/* Display the uploaded file */}
        <TouchableOpacity style={styles.uploadBox} onPress={handleSelectFile}>
          {selectedFile ? (
            <Text style={styles.uploadBoxText}>{selectedFile.name}</Text>
          ) : (
            <View style={{ alignItems: "center" }}>
              <Text style={styles.uploadBoxText}>
                Upload the transcript (Available sources: Bloomberg, AlphaSense, BamSec)
              </Text>
              <Text style={styles.uploadBoxSubtext}>*.pdf (10MB)</Text>
            </View>
          )}
        </TouchableOpacity>

        {/* Display the result */}
        {status === "success" && result && (
          <Text selectable style={{ marginTop: 12 }}>
            {JSON.stringify(result, null, 2)}
          </Text>
        )}

        {/* Display the validating message */}
        {status === "validating" && (
          <Text style={{ marginTop: 12, fontSize: 16 }}>Validating file</Text>
        )}

        {/* Display the validated message */}
        {status === "validated" && (
          <Text style={{ marginTop: 12, fontSize: 16 }}>PDF Validated.</Text>
        )}

        {/* Display the error message */}
        {error && (
          <Text
            style={
              messageType === "success"
                ? styles.successText
                : messageType === "info"
                  ? styles.infoText
                  : styles.errorText
            }
          >
            {error}
          </Text>
        )}

        {/* Display the submit button */}
        <TouchableOpacity
          style={styles.submitButton}
          onPress={handleSubmitFile}
        >
          <Text style={styles.submitButtonText}>Generate Summary</Text>
        </TouchableOpacity>

        {/* Loading/progress view while workflow runs (before navigating to results) */}
        {/* Display the progress bar */}
        {status === "loading" && (
          <View style={styles.progressCard}>
            <Text style={styles.progressTitle}>Processing</Text>
            <Text style={styles.progressSubtitle}>{formatStage(stage)}</Text>
            <View style={styles.progressBarOuter}>
              <View
                style={[
                  styles.progressBarInner,
                  {
                    width: `${Math.max(0, Math.min(100, percentComplete || 0))}%`,
                  },
                ]}
              />
            </View>
            <Text style={styles.progressPercent}>
              {Math.round(percentComplete || 0)}%
            </Text>
          </View>
        )}
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
  errorText: { color: "red", textAlign: "center", marginTop: 10, fontSize: 16 },
  successText: {
    color: "#007AFF",
    textAlign: "center",
    marginTop: 10,
    fontWeight: "600",
  },
  infoText: { color: "#FF9500", textAlign: "center", marginTop: 10, fontSize: 16 },
  progressCard: {
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#E5E5EA",
    backgroundColor: "#FAFAFA",
  },
  progressTitle: { fontSize: 18, fontWeight: "600", marginBottom: 4 },
  progressSubtitle: { fontSize: 14, color: "#3C3C43", marginBottom: 10 },
  progressBarOuter: {
    height: 10,
    width: "100%",
    backgroundColor: "#EEE",
    borderRadius: 6,
    overflow: "hidden",
  },
  progressBarInner: {
    height: 10,
    backgroundColor: "#007AFF",
  },
  progressPercent: { marginTop: 8, fontSize: 12, color: "#6B7280" },
})

function formatStage(s?: string | null): string {
  if (!s) return "Starting..."
  const key = String(s).toLowerCase()
  const map: Record<string, string> = {
    q_a_summary: "Q&A summary",
    overview_summary: "Overview summary",
    summary_evaluation: "Evaluation",
    validating: "Validating",
    cancelled: "Cancelled",
  }
  if (map[key]) return map[key]
  const pretty = s.replace(/_/g, " ")
  return pretty.charAt(0).toUpperCase() + pretty.slice(1)
}
