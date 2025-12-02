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
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 12,
    color: "#1A1A1A",
  },
  executiveItem: {
    marginBottom: 8,
    paddingLeft: 12,
    borderLeftWidth: 3,
    borderLeftColor: "#FF6B54",
  },
  executiveName: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1A1A1A",
  },
  executiveRole: {
    fontSize: 14,
    color: "#6B7280",
    marginTop: 2,
  },
  noDataText: {
    fontSize: 14,
    color: "#6B7280",
    fontStyle: "italic",
  },
})
