import React from "react"
import {
  View,
  TouchableOpacity,
  Text,
  StyleSheet,
  Platform,
} from "react-native"
import { Ionicons } from "@expo/vector-icons"

interface ReportActionsProps {
  onCopyReport: () => void
  onSavePdf: () => void
  reportCopied: boolean
  pdfMessage: string | null
}

export const ReportActions: React.FC<ReportActionsProps> = ({
  onCopyReport,
  onSavePdf,
  reportCopied,
  pdfMessage,
}) => {
  return (
    <View style={styles.container}>
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={[
            styles.actionButton,
            reportCopied && styles.actionButtonCopied,
          ]}
          onPress={onCopyReport}
        >
          <Ionicons
            name={reportCopied ? "checkmark" : "copy-outline"}
            size={16}
            color={reportCopied ? "#4CAF50" : "#007AFF"}
          />
          <Text
            style={[
              styles.actionButtonText,
              reportCopied && styles.actionButtonTextCopied,
            ]}
          >
            {reportCopied ? "Copied!" : "Copy"}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={onSavePdf}
          disabled={Platform.OS !== "web"}
        >
          <Ionicons
            name="document-outline"
            size={16}
            color={Platform.OS === "web" ? "#007AFF" : "#999"}
          />
          <Text
            style={[
              styles.actionButtonText,
              Platform.OS !== "web" && styles.actionButtonTextDisabled,
            ]}
          >
            PDF
          </Text>
        </TouchableOpacity>
      </View>

      {pdfMessage && <Text style={styles.pdfMessage}>{pdfMessage}</Text>}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    marginTop: 0,
    paddingTop: 0,
    borderTopWidth: 0,
  },
  actionRow: {
    flexDirection: "row",
    gap: 8,
  },
  actionButton: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 6,
    backgroundColor: "#f8f9fa",
    borderWidth: 1,
    borderColor: "#e0e0e0",
  },
  actionButtonCopied: {
    backgroundColor: "#e8f5e8",
    borderColor: "#4CAF50",
  },
  actionButtonText: {
    marginLeft: 4,
    fontSize: 12,
    color: "#007AFF",
    fontWeight: "500",
  },
  actionButtonTextCopied: {
    color: "#4CAF50",
  },
  actionButtonTextDisabled: {
    color: "#999",
  },
  pdfMessage: {
    textAlign: "center",
    fontSize: 12,
    color: "#666",
    marginTop: 4,
  },
})
