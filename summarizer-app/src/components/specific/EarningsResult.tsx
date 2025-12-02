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
                    <Text style={styles.questionLabel}>Q: </Text>
                    <Text style={styles.questionContent}>
                      {question.question}
                    </Text>
                  </Text>
                  <Text style={styles.answerText}>
                    <Text style={styles.answerContent}>
                      {Array.isArray((question as any).answers) &&
                      (question as any).answers.length > 0 ? (
                        (question as any).answers.map(
                          (ans: any, idx: number) => (
                            <View key={idx} style={styles.answerContainer}>
                              <Text style={styles.answerLabel}>
                                A (
                                <Text style={styles.executiveRole}>
                                  {ans.executive}
                                </Text>
                                )
                              </Text>
                              {ans.answer_summary.map(
                                (point: string, i: number) => (
                                  <Text key={i} style={styles.bulletPoint}>
                                    • {point}
                                  </Text>
                                )
                              )}
                            </View>
                          )
                        )
                      ) : (
                        <View style={styles.answerContainer}>
                          <Text style={styles.answerLabel}>A: </Text>
                          {Array.isArray(question.answer_summary) ? (
                            question.answer_summary.map((point, index) => (
                              <Text key={index} style={styles.bulletPoint}>
                                • {point}
                              </Text>
                            ))
                          ) : (
                            <Text style={styles.answerText}>
                              {question.answer_summary || "Not provided"}
                            </Text>
                          )}
                        </View>
                      )}
                    </Text>
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
    marginBottom: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#E5E7EB",
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    flex: 1,
    marginRight: 16,
    color: "#1A1A1A",
  },
  actionsContainer: {
    flexDirection: "row",
    alignItems: "center",
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 12,
    color: "#1A1A1A",
  },
  overviewText: {
    fontSize: 15,
    lineHeight: 24,
    color: "#4B5563",
  },
  questionContainer: {
    marginBottom: 8,
    paddingLeft: 14,
    borderLeftWidth: 3,
    borderLeftColor: "#FF6B54",
  },
  questionText: {
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 6,
    color: "#1A1A1A",
  },
  answerText: {
    fontSize: 15,
    lineHeight: 24,
    marginLeft: 8,
    marginBottom: 4,
    color: "#4B5563",
  },
  analystInfo: {
    fontSize: 13,
    color: "#6B7280",
    fontStyle: "italic",
    marginLeft: 8,
  },
  guidanceItem: {
    marginBottom: 8,
    padding: 12,
    backgroundColor: "#FFFFFF",
    borderRadius: 10,
  },
  guidancePeriod: {
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 6,
    color: "#1A1A1A",
  },
  guidanceMetric: {
    fontSize: 14,
    lineHeight: 22,
    color: "#4B5563",
  },
  analystContainer: {
    marginBottom: 16,
    padding: 14,
    borderRadius: 12,
    backgroundColor: "#FFFFFF",
  },
  analystHeader: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 10,
    color: "#1A1A1A",
  },
  questionLabel: {
    fontWeight: "700",
    color: "#FF6B54",
  },
  questionContent: {
    fontWeight: "600",
    color: "#1A1A1A",
  },
  answerLabel: {
    fontWeight: "600",
    color: "#374151",
  },
  answerContent: {
    color: "#4B5563",
  },
  bulletPoint: {
    marginBottom: 10,
    color: "#4B5563",
  },
  answerContainer: {
    marginBottom: 10,
  },
  executiveRole: {
    fontWeight: "600",
    color: "#6B7280",
  },
})
