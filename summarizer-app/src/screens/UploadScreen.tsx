import React, { useState } from "react"
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ScrollView,
} from "react-native"
import * as DocumentPicker from "expo-document-picker"

import { useSummaryStore } from "../state/SummaryStore"

type CallType = "earnings" | "conference"
type SummaryLength = "long" | "short"
type AnswerFormat = "prose" | "bullet"

//  toggle component
const PillToggle: React.FC<{
  label: string
  isActive: boolean
  onPress: () => void
  disabled?: boolean
}> = ({ label, isActive, onPress, disabled }) => (
  <TouchableOpacity
    onPress={onPress}
    disabled={disabled}
    style={[
      styles.pill,
      isActive && styles.pillActive,
      disabled && styles.pillDisabled,
    ]}
    activeOpacity={0.7}
  >
    <Text style={[styles.pillText, isActive && styles.pillTextActive]}>
      {label}
    </Text>
  </TouchableOpacity>
)

export const UploadScreen: React.FC = () => {
  const [callType, setCallType] = useState<CallType>("earnings")
  const [summaryLength, setSummaryLength] = useState<SummaryLength>("long")
  const [answerFormat, setAnswerFormat] = useState<AnswerFormat>("prose")
  const [selectedFile, setSelectedFile] =
    useState<DocumentPicker.DocumentPickerAsset | null>(null)

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

      const maxSizeBytes = 10 * 1024 * 1024
      if (typeof file.size === "number" && file.size > maxSizeBytes) {
        Alert.alert(
          "Error",
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
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Summarize</Text>
          <Text style={styles.subtitle}>
            Transform transcripts into actionable insights
          </Text>
        </View>

        {/* Options Card */}
        <View style={styles.card}>
          {/* Call Type */}
          <View style={styles.optionSection}>
            <Text style={styles.optionLabel}>Call Type</Text>
            <View style={styles.pillGroup}>
              <PillToggle
                label="Earnings"
                isActive={callType === "earnings"}
                onPress={() => setCallType("earnings")}
              />
              <PillToggle
                label="Conference"
                isActive={callType === "conference"}
                onPress={() => setCallType("conference")}
              />
            </View>
          </View>

          {/* Summary Length */}
          <View style={styles.optionSection}>
            <Text style={styles.optionLabel}>Length</Text>
            <View style={styles.pillGroup}>
              <PillToggle
                label="Long"
                isActive={summaryLength === "long"}
                onPress={() => setSummaryLength("long")}
              />
              <PillToggle
                label="Short"
                isActive={summaryLength === "short"}
                onPress={() => setSummaryLength("short")}
                disabled={callType === "conference"}
              />
            </View>
          </View>

          {/* Answer Format */}
          <View style={styles.optionSection}>
            <Text style={styles.optionLabel}>Format</Text>
            <View style={styles.pillGroup}>
              <PillToggle
                label="Prose"
                isActive={answerFormat === "prose"}
                onPress={() => setAnswerFormat("prose")}
              />
              <PillToggle
                label="Bullets"
                isActive={answerFormat === "bullet"}
                onPress={() => setAnswerFormat("bullet")}
              />
            </View>
          </View>
        </View>

        {/* Upload Area */}
        <TouchableOpacity
          style={[styles.uploadArea, selectedFile && styles.uploadAreaActive]}
          onPress={handleSelectFile}
          activeOpacity={0.8}
        >
          {selectedFile ? (
            <View style={styles.uploadContent}>
              <View style={styles.fileIcon}>
                <Text style={styles.fileIconText}>PDF</Text>
              </View>
              <Text style={styles.fileName} numberOfLines={1}>
                {selectedFile.name}
              </Text>
              <Text style={styles.tapToChange}>Tap to change</Text>
            </View>
          ) : (
            <View style={styles.uploadContent}>
              <View style={styles.uploadIcon}>
                <Text style={styles.uploadIconText}>↑</Text>
              </View>
              <Text style={styles.uploadTitle}>Upload Transcript</Text>
              <Text style={styles.uploadHint}>
                Bloomberg · AlphaSense · BamSec
              </Text>
              <Text style={styles.uploadLimit}>PDF up to 10MB</Text>
            </View>
          )}
        </TouchableOpacity>

        {/* Status Messages */}
        {status === "validating" && (
          <View style={styles.statusBadge}>
            <Text style={styles.statusText}>Validating...</Text>
          </View>
        )}

        {/* Display the validated message */}
        {status === "validated" && (
          <View style={[styles.statusBadge, styles.statusSuccess]}>
            <Text style={[styles.statusText, styles.statusTextSuccess]}>
              ✓ Validated
            </Text>
          </View>
        )}

        {error && (
          <View
            style={[
              styles.statusBadge,
              messageType === "success"
                ? styles.statusSuccess
                : messageType === "info"
                  ? styles.statusInfo
                  : styles.statusError,
            ]}
          >
            <Text
              style={[
                styles.statusText,
                messageType === "success"
                  ? styles.statusTextSuccess
                  : messageType === "info"
                    ? styles.statusTextInfo
                    : styles.statusTextError,
              ]}
            >
              {error}
            </Text>
          </View>
        )}

        {/* Progress Card */}
        {status === "loading" && (
          <View style={styles.progressCard}>
            <View style={styles.progressHeader}>
              <Text style={styles.progressStage}>{formatStage(stage)}</Text>
              <Text style={styles.progressPercent}>
                {Math.round(percentComplete || 0)}%
              </Text>
            </View>
            <View style={styles.progressTrack}>
              <View
                style={[
                  styles.progressFill,
                  {
                    width: `${Math.max(0, Math.min(100, percentComplete || 0))}%`,
                  },
                ]}
              />
            </View>
          </View>
        )}

        {/* Result */}
        {status === "success" && result && (
          <View style={styles.resultCard}>
            <Text selectable style={styles.resultText}>
              {JSON.stringify(result, null, 2)}
            </Text>
          </View>
        )}
      </ScrollView>

      {/* Fixed Bottom CTA */}
      <View style={styles.bottomBar}>
        <TouchableOpacity
          style={[
            styles.submitButton,
            (!selectedFile || status === "loading") &&
              styles.submitButtonDisabled,
          ]}
          onPress={handleSubmitFile}
          activeOpacity={0.85}
          disabled={status === "loading"}
        >
          <Text style={styles.submitButtonText}>
            {status === "loading" ? "Processing..." : "Generate Summary"}
          </Text>
          {status !== "loading" && <Text style={styles.submitArrow}>→</Text>}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  wrapper: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 24,
    paddingBottom: 140,
  },

  // Header
  header: {
    marginBottom: 36,
  },
  title: {
    fontSize: 42,
    fontWeight: "700",
    color: "#1A1A1A",
    letterSpacing: -1,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 17,
    color: "#6B7280",
    fontWeight: "400",
  },

  // Card
  card: {
    backgroundColor: "#F8F9FA",
    borderRadius: 20,
    padding: 28,
    marginBottom: 24,
  },
  optionSection: {
    marginBottom: 28,
  },
  optionLabel: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1A1A1A",
    marginBottom: 14,
  },
  pillGroup: {
    flexDirection: "row",
    gap: 12,
  },

  // Pills
  pill: {
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 100,
    backgroundColor: "#E5E7EB",
  },
  pillActive: {
    backgroundColor: "#FF6B54",
  },
  pillDisabled: {
    opacity: 0.4,
  },
  pillText: {
    fontSize: 17,
    fontWeight: "600",
    color: "#374151",
  },
  pillTextActive: {
    color: "#FFFFFF",
    fontWeight: "600",
  },

  // Upload Area
  uploadArea: {
    backgroundColor: "#F8F9FA",
    borderRadius: 20,
    padding: 44,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: "#E5E7EB",
    borderStyle: "dashed",
    marginBottom: 24,
  },
  uploadAreaActive: {
    borderColor: "#FF6B54",
    borderStyle: "solid",
    backgroundColor: "#FFF5F3",
  },
  uploadContent: {
    alignItems: "center",
  },
  uploadIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#FF6B54",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 18,
  },
  uploadIconText: {
    fontSize: 28,
    color: "#FFFFFF",
    fontWeight: "600",
  },
  uploadTitle: {
    fontSize: 20,
    fontWeight: "600",
    color: "#1A1A1A",
    marginBottom: 8,
  },
  uploadHint: {
    fontSize: 15,
    color: "#6B7280",
    marginBottom: 4,
  },
  uploadLimit: {
    fontSize: 13,
    color: "#9CA3AF",
  },

  // File Selected State
  fileIcon: {
    width: 64,
    height: 64,
    borderRadius: 14,
    backgroundColor: "#FF6B54",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 18,
  },
  fileIconText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  fileName: {
    fontSize: 17,
    fontWeight: "600",
    color: "#1A1A1A",
    marginBottom: 4,
    maxWidth: 280,
  },
  tapToChange: {
    fontSize: 14,
    color: "#6B7280",
  },

  // Status Badges
  statusBadge: {
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: 14,
    backgroundColor: "#F3F4F6",
    marginBottom: 18,
  },
  statusSuccess: {
    backgroundColor: "rgba(52, 199, 89, 0.12)",
  },
  statusInfo: {
    backgroundColor: "rgba(255, 159, 10, 0.12)",
  },
  statusError: {
    backgroundColor: "rgba(255, 69, 58, 0.12)",
  },
  statusText: {
    fontSize: 15,
    fontWeight: "500",
    color: "#374151",
    textAlign: "center",
  },
  statusTextSuccess: {
    color: "#22C55E",
  },
  statusTextInfo: {
    color: "#F59E0B",
  },
  statusTextError: {
    color: "#EF4444",
  },

  // Progress Card
  progressCard: {
    backgroundColor: "#F8F9FA",
    borderRadius: 18,
    padding: 22,
    marginBottom: 18,
  },
  progressHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  progressStage: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1A1A1A",
  },
  progressPercent: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FF6B54",
  },
  progressTrack: {
    height: 8,
    backgroundColor: "#E5E7EB",
    borderRadius: 4,
    overflow: "hidden",
  },
  progressFill: {
    height: 8,
    backgroundColor: "#FF6B54",
    borderRadius: 4,
  },

  // Result Card
  resultCard: {
    backgroundColor: "#F8F9FA",
    borderRadius: 18,
    padding: 18,
  },
  resultText: {
    fontSize: 13,
    color: "#6B7280",
    fontFamily: "monospace",
  },

  // Bottom Bar
  bottomBar: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    padding: 24,
    paddingBottom: 40,
    backgroundColor: "#FFFFFF",
    borderTopWidth: 1,
    borderTopColor: "#F3F4F6",
  },
  submitButton: {
    backgroundColor: "#FF6B54",
    borderRadius: 18,
    paddingVertical: 20,
    paddingHorizontal: 28,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  submitButtonDisabled: {
    backgroundColor: "#D1D5DB",
  },
  submitButtonText: {
    fontSize: 18,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  submitArrow: {
    fontSize: 20,
    fontWeight: "600",
    color: "#FFFFFF",
  },
})

function formatStage(s?: string | null): string {
  if (!s) return "Starting..."
  const key = String(s).toLowerCase()
  const map: Record<string, string> = {
    q_a_summary: "Q&A Summary",
    overview_summary: "Overview Summary",
    summary_evaluation: "Evaluation",
    validating: "Validating",
    cancelled: "Cancelled",
  }
  if (map[key]) return map[key]
  const pretty = s.replace(/_/g, " ")
  return pretty.charAt(0).toUpperCase() + pretty.slice(1)
}
