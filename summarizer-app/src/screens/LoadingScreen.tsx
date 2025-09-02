import React from "react"
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  TouchableOpacity,
} from "react-native"
import { useSummaryStore } from "../state/SummaryStore"

export const LoadingScreen = () => {
  const { stage, percentComplete, warnings, cancel } = useSummaryStore()
  return (
    <SafeAreaView style={styles.wrapper}>
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.title}>Generating summary</Text>
        <Text style={styles.stepText}>Stage: {formatStage(stage)}</Text>
        <View style={styles.progressBarOuter}>
          <View
            style={[
              styles.progressBarInner,
              { width: `${Math.max(0, Math.min(100, percentComplete || 0))}%` },
            ]}
          />
        </View>
        <Text style={styles.percentText}>
          {Math.round(percentComplete || 0)}%
        </Text>
        {warnings && warnings.length > 0 && (
          <View style={styles.warningBox}>
            {warnings.map((w, i) => (
              <Text key={i} style={styles.warningText}>
                {String(w)}
              </Text>
            ))}
          </View>
        )}
        <TouchableOpacity style={styles.stopButton} onPress={cancel}>
          <Text style={styles.stopButtonText}>Stop</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  wrapper: {
    flex: 1,
    backgroundColor: "#FFFFFF",
    justifyContent: "center",
    alignItems: "center",
  },
  container: {
    padding: 20,
    alignItems: "center",
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginTop: 20,
    marginBottom: 30,
    color: "#3C3C43",
  },
  stepText: {
    fontSize: 16,
    color: "#8A8A8E",
    marginBottom: 10,
  },
  progressBarOuter: {
    height: 10,
    width: 240,
    backgroundColor: "#EEE",
    borderRadius: 6,
    overflow: "hidden",
    marginTop: 8,
  },
  progressBarInner: {
    height: 10,
    backgroundColor: "#007AFF",
  },
  percentText: { marginTop: 8, fontSize: 14, color: "#6B7280" },
  warningBox: {
    marginTop: 12,
    padding: 10,
    backgroundColor: "#FFF8E1",
    borderWidth: 1,
    borderColor: "#F59E0B",
    borderRadius: 8,
    width: 260,
  },
  warningText: { color: "#92400E", fontSize: 12, marginBottom: 4 },
  stopButton: {
    marginTop: 16,
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    backgroundColor: "#EF4444",
  },
  stopButtonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "600" },
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
