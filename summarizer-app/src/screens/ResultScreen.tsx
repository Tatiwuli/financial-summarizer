import { useSummaryStore } from "../state/SummaryStoreTest"
import {
  SafeAreaView,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
  StyleSheet,
} from "react-native"
import {
  OverviewBlockData,
  QaBlockData,
  JudgeBlockData,
  Analyst,
  Question,
  SummaryResult,
} from "../types"

export const ResultScreen = () => {
  const { result, reset } = useSummaryStore()

  const overviewBlock = result?.blocks.find((b: any) => b.type === "overview")
    ?.data as OverviewBlockData | undefined
  const qaBlock = result?.blocks.find((b: any) => b.type.startsWith("q_a_"))
    ?.data as QaBlockData | undefined
  const title = result?.title || "Untitled"
  const judgeBlock = result?.blocks.find((b: any) => b.type === "judge")
    ?.data as JudgeBlockData | undefined

  if (!result) {
    return (
      <SafeAreaView style={styles.wrapper}>
        <Text>No result found.</Text>
        <TouchableOpacity style={styles.resetButton} onPress={reset}>
          <Text style={styles.resetButtonText}>Start Over</Text>
        </TouchableOpacity>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.wrapper}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>{result.title}</Text>

        {overviewBlock && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Overview</Text>
            <Text style={styles.bodyText}>{overviewBlock.overview}</Text>
          </View>
        )}

        {qaBlock && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Q&A Summary</Text>
            {qaBlock.analysts.map((analyst: Analyst, index: number) => (
              <View key={index} style={styles.analystContainer}>
                <Text style={styles.analystName}>
                  {analyst.name} - {analyst.firm}
                </Text>
                {analyst.questions.map((q: Question, qIndex: number) => (
                  <View key={qIndex} style={styles.questionContainer}>
                    <Text style={styles.questionText}>Q: {q.question}</Text>
                    <Text style={styles.bodyText}>A: {q.answer_summary}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        )}
        {judgeBlock && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Quality Assessment</Text>
            <Text style={styles.bodyText}>
              Overall Score: {judgeBlock.overall_assessment.passed_criteria}/
              {judgeBlock.overall_assessment.total_criteria}(
              {(judgeBlock.overall_assessment.pass_rate * 100).toFixed(1)}%)
            </Text>
            <Text style={styles.bodyText}>
              Status:{" "}
              {judgeBlock.overall_assessment.overall_passed
                ? "✅ Passed"
                : "❌ Failed"}
            </Text>
            <Text style={styles.bodyText}>
              {judgeBlock.overall_assessment.evaluation_summary}
            </Text>
          </View>
        )}
      </ScrollView>
      <View style={styles.footer}>
        <TouchableOpacity style={styles.resetButton} onPress={reset}>
          <Text style={styles.resetButtonText}>Start Over</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: "#FFFFFF" },
  container: { padding: 20, paddingBottom: 100 , backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#000000"},
  title: { fontSize: 26, fontWeight: "bold", marginBottom: 20 },
  section: { marginBottom: 25 },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "600",
    marginBottom: 10,
    color: "#000000",
  },
  bodyText: { fontSize: 16, lineHeight: 24, color: "#3C3C43" },
  analystContainer: { marginBottom: 15 },
  analystName: { fontSize: 16, fontWeight: "bold", marginBottom: 5 },
  questionContainer: { marginLeft: 10, marginBottom: 10 },
  questionText: { fontSize: 16, fontWeight: "500", fontStyle: "italic" },
  footer: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    backgroundColor: "#FFFFFF",
    borderTopWidth: 1,
    borderTopColor: "#E5E5EA",
  },
  resetButton: {
    backgroundColor: "#007AFF",
    borderRadius: 12,
    padding: 15,
    alignItems: "center",
  },
  resetButtonText: { color: "#FFFFFF", fontSize: 18, fontWeight: "600" },
})
