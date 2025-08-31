import React from "react"
import { View, Text, StyleSheet } from "react-native"
import { OverviewBlockData } from "../../../types"

interface ExecutivesListProps {
  executives?: OverviewBlockData["executives_list"]
}

export const ExecutivesList: React.FC<ExecutivesListProps> = ({
  executives,
}) => {
  if (!executives || executives.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.sectionTitle}>Executives</Text>
        <Text style={styles.noDataText}>Not provided</Text>
      </View>
    )
  }

  return (
    <View style={styles.container}>
      <Text style={styles.sectionTitle}>Executives</Text>
      {executives.map((executive, index) => (
        <View key={index} style={styles.executiveItem}>
          <Text style={styles.executiveName}>
            {executive.executive_name || "Not provided"}
          </Text>
          <Text style={styles.executiveRole}>
            {executive.role || "Not provided"}
          </Text>
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
  executiveItem: {
    marginBottom: 4,
  },
  executiveName: {
    fontSize: 14,
    fontWeight: "600",
  },
  executiveRole: {
    fontSize: 12,
    color: "#666",
    marginLeft: 8,
  },
  noDataText: {
    fontSize: 14,
    color: "#666",
    fontStyle: "italic",
  },
})
