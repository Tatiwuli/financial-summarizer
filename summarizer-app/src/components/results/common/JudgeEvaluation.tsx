import React from "react"
import { View, Text, StyleSheet } from "react-native"
import { JudgeBlockData } from "../../../types"

interface JudgeEvaluationProps {
  judgeBlocks: { data: JudgeBlockData; metadata: any }[]
}

export const JudgeEvaluation: React.FC<JudgeEvaluationProps> = ({
  judgeBlocks,
}) => {
  if (!judgeBlocks || judgeBlocks.length === 0) {
    return null
  }

  return (
    <View style={styles.container}>
      <Text style={styles.sectionTitle}>Judge Evaluation</Text>
      {judgeBlocks.map((block, index) => (
        <View key={index} style={styles.judgeBlock}>
          <Text style={styles.judgeTitle}>Evaluation {index + 1}</Text>

          {/* Overall Assessment */}
          <View style={styles.overallSection}>
            <Text style={styles.overallTitle}>Overall Assessment</Text>
            <Text style={styles.overallStatus}>
              Status:{" "}
              {block.data.overall_assessment.overall_passed
                ? "✅ Passed"
                : "❌ Failed"}
            </Text>
            <Text style={styles.overallScore}>
              Score: {block.data.overall_assessment.passed_criteria}/
              {block.data.overall_assessment.total_criteria}
            </Text>
            <Text style={styles.overallSummary}>
              {block.data.overall_assessment.evaluation_summary ||
                "No content available"}
            </Text>
          </View>

          {/* Evaluation Results Table */}
          <View style={styles.resultsSection}>
            <Text style={styles.resultsTitle}>Evaluation Results</Text>
            <View style={styles.tableHeader}>
              <Text style={styles.tableHeaderCell}>Metric</Text>
              <Text style={styles.tableHeaderCell}>Status</Text>
              <Text style={styles.tableHeaderCell}>Details</Text>
            </View>
            {block.data.evaluation_results.map((result, resultIndex) => (
              <View key={resultIndex} style={styles.tableRow}>
                <Text style={styles.tableCell}>{result.metric_name}</Text>
                <Text
                  style={[
                    styles.tableCell,
                    styles.statusCell,
                    result.passed ? styles.passedStatus : styles.failedStatus,
                  ]}
                >
                  {result.passed ? "✅ Pass" : "❌ Fail"}
                </Text>
                <View style={styles.detailsCell}>
                  {result.errors && result.errors.length > 0 ? (
                    result.errors.map((error, errorIndex) => (
                      <View key={errorIndex} style={styles.errorItem}>
                        <Text style={styles.errorText}>{error.error}</Text>
                        <Text style={styles.errorSource}>
                          <Text style={styles.errorLabel}>Transcript:</Text>{" "}
                          {error.transcript_text}
                        </Text>
                        <Text style={styles.errorSource}>
                          <Text style={styles.errorLabel}>Summary:</Text>{" "}
                          {error.summary_text}
                        </Text>
                      </View>
                    ))
                  ) : (
                    <Text style={styles.noErrors}>No issues found</Text>
                  )}
                </View>
              </View>
            ))}
          </View>
        </View>
      ))}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "bold",
    marginBottom: 8,
  },
  judgeBlock: {
    backgroundColor: "#f8f9fa",
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  judgeTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
  },
  overallSection: {
    marginBottom: 16,
    padding: 8,
    backgroundColor: "#ffffff",
    borderRadius: 4,
  },
  overallTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
    color: "#333",
  },
  overallStatus: {
    fontSize: 14,
    fontWeight: "500",
    marginBottom: 4,
  },
  overallScore: {
    fontSize: 14,
    fontWeight: "500",
    marginBottom: 8,
    color: "#666",
  },
  overallSummary: {
    fontSize: 14,
    lineHeight: 20,
    color: "#333",
  },
  resultsSection: {
    marginTop: 8,
  },
  resultsTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
    color: "#333",
  },
  tableHeader: {
    flexDirection: "row",
    backgroundColor: "#f2f2f7",
    padding: 8,
    borderRadius: 4,
    marginBottom: 4,
  },
  tableHeaderCell: {
    flex: 1,
    fontSize: 14,
    fontWeight: "700",
    color: "#333",
  },
  tableRow: {
    flexDirection: "row",
    padding: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e5ea",
    minHeight: 40,
  },
  tableCell: {
    flex: 1,
    fontSize: 14,
    color: "#333",
    paddingRight: 8,
  },
  statusCell: {
    fontWeight: "600",
  },
  passedStatus: {
    color: "#34C759",
  },
  failedStatus: {
    color: "#FF3B30",
  },
  detailsCell: {
    flex: 2,
  },
  errorItem: {
    marginBottom: 8,
  },
  errorText: {
    fontSize: 13,
    color: "#FF3B30",
    fontWeight: "500",
    marginBottom: 4,
  },
  errorSource: {
    fontSize: 12,
    color: "#666",
    marginBottom: 2,
    lineHeight: 16,
  },
  errorLabel: {
    fontWeight: "600",
    color: "#333",
  },
  noErrors: {
    fontSize: 13,
    color: "#34C759",
    fontStyle: "italic",
  },
})
