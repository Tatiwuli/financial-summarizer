import React from "react"
import { View, Text, StyleSheet } from "react-native"
import { QABlock, OverviewBlockData, JudgeBlockData } from "../../types"
import { Header } from "../results/common/Header"
import { ExecutivesList } from "../results/common/ExecutivesList"
import { GuidanceOutlook } from "../results/common/GuidanceOutlook"
import { JudgeEvaluation } from "../results/common/JudgeEvaluation"
import { ReportActions } from "../results/common/ReportActions"

interface EarningsResultProps {
  title: string
  overview: OverviewBlockData | undefined
  qa: QABlock | undefined
  onCopyReport: () => void
  onSavePdf: () => void
  reportCopied: boolean
  pdfMessage: string | null

  summaryMeta?: any
  overviewMeta?: any
}

export const EarningsResult: React.FC<EarningsResultProps> = ({
  title,
  overview,
  qa,
  onCopyReport,
  onSavePdf,
  reportCopied,
  pdfMessage,

  summaryMeta,
  overviewMeta,
}) => {
  return (
    <View style={styles.container}>
      {/* Header with title and actions */}
      <View style={styles.headerContainer}>
        <Text style={styles.title}>{title}</Text>
        <View style={styles.actionsContainer}>
          <ReportActions
            onCopyReport={onCopyReport}
            onSavePdf={onSavePdf}
            reportCopied={reportCopied}
            pdfMessage={pdfMessage}
          />
        </View>
      </View>

      <ExecutivesList executives={overview?.executives_list} />

      {overview && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Overview</Text>
          <Text style={styles.overviewText}>{overview.overview}</Text>
        </View>
      )}

      <GuidanceOutlook guidanceOutlook={overview?.guidance_outlook} />

      {qa && qa.analysts && qa.analysts.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{qa.title || "Q&A Summary"}</Text>
          {qa.analysts.map((analyst, analystIndex) => (
            <View key={analystIndex} style={styles.analystContainer}>
              <Text style={styles.analystHeader}>
                {analyst.name} - {analyst.firm}
              </Text>
              {analyst.questions.map((question, questionIndex) => (
                <View key={questionIndex} style={styles.questionContainer}>
                  <Text style={styles.questionText}>
                    Q: {question.question}
                  </Text>
                  <Text style={styles.answerText}>
                    A: {question.answer_summary}
                  </Text>
                </View>
              ))}
            </View>
          ))}
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  headerContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },
  title: {
    fontSize: 20,
    fontWeight: "bold",
    flex: 1,
    marginRight: 16,
  },
  actionsContainer: {
    flexDirection: "row",
    alignItems: "center",
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "bold",
    marginBottom: 8,
  },
  overviewText: {
    fontSize: 14,
    lineHeight: 20,
  },
  questionContainer: {
    marginBottom: 4,
  },
  questionText: {
    fontSize: 14,
    fontWeight: "500",
    marginBottom: 4,
    color: "#000000",
  },
  answerText: {
    fontSize: 14,
    lineHeight: 20,
    marginLeft: 8,
    marginBottom: 2,
  },
  analystInfo: {
    fontSize: 12,
    color: "#666",
    fontStyle: "italic",
    marginLeft: 8,
  },
  guidanceItem: {
    marginBottom: 4,
    padding: 8,
  },
  guidancePeriod: {
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 4,
    color: "#333",
  },
  guidanceMetric: {
    fontSize: 14,
    lineHeight: 20,
    color: "#555",
  },
  analystContainer: {
    marginBottom: 10,
    padding: 5,
    borderRadius: 4,
    borderBottomWidth: 1,
    borderBottomColor: "#E5E5EA",
  },
  analystHeader: {
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 6,
    color: "#333",
  },
})
