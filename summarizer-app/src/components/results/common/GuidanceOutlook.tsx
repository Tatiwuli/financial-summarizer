import React from "react"
import { View, Text, StyleSheet } from "react-native"
import { OverviewBlockData } from "../../../types"

interface GuidanceOutlookProps {
  guidanceOutlook?: OverviewBlockData["guidance_outlook"]
}

export const GuidanceOutlook: React.FC<GuidanceOutlookProps> = ({
  guidanceOutlook,
}) => {
  if (!guidanceOutlook || guidanceOutlook.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.sectionTitle}>Guidance & Outlook</Text>
        <Text style={styles.noDataText}>Not provided</Text>
      </View>
    )
  }

  // Group by period_label
  const grouped: Record<
    string,
    { metric_name: string; metric_description: string }[]
  > = {}
  guidanceOutlook.forEach((item) => {
    const key = item.period_label || "Not provided"
    if (!grouped[key]) grouped[key] = []
    grouped[key].push({
      metric_name: item.metric_name || "Not provided",
      metric_description: item.metric_description || "Not provided",
    })
  })

  return (
    <View style={styles.container}>
      <Text style={styles.sectionTitle}>Guidance & Outlook</Text>
      {Object.entries(grouped).map(([period, metrics]) => (
        <View key={period} style={styles.periodContainer}>
          <Text style={styles.periodLabel}>{period}</Text>
          {metrics.map((metric, index) => (
            <View key={index} style={styles.metricItem}>
              <Text style={styles.metricName}>{metric.metric_name}</Text>
              <Text style={styles.metricDescription}>
                {metric.metric_description}
              </Text>
            </View>
          ))}
        </View>
      ))}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 14,
    color: "#1A1A1A",
  },
  periodContainer: {
    marginBottom: 16,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 14,
  },
  periodLabel: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 10,
    color: "#FF6B54",
  },
  metricItem: {
    marginLeft: 10,
    marginBottom: 8,
    paddingLeft: 10,
    borderLeftWidth: 2,
    borderLeftColor: "#E5E7EB",
  },
  metricName: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1A1A1A",
  },
  metricDescription: {
    fontSize: 14,
    color: "#4B5563",
    marginTop: 4,
    lineHeight: 22,
  },
  noDataText: {
    fontSize: 14,
    color: "#6B7280",
    fontStyle: "italic",
  },
})
