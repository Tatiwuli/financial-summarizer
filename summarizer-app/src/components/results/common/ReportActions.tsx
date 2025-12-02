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
            color={reportCopied ? "#22C55E" : "#FF6B54"}
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
            color={Platform.OS === "web" ? "#FF6B54" : "#9CA3AF"}
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
    gap: 10,
  },
  actionButton: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },
  actionButtonCopied: {
    backgroundColor: "rgba(34, 197, 94, 0.1)",
    borderColor: "#22C55E",
  },
  actionButtonText: {
    marginLeft: 6,
    fontSize: 14,
    color: "#FF6B54",
    fontWeight: "600",
  },
  actionButtonTextCopied: {
    color: "#22C55E",
  },
  actionButtonTextDisabled: {
    color: "#9CA3AF",
  },
  pdfMessage: {
    textAlign: "center",
    fontSize: 13,
    color: "#6B7280",
    marginTop: 6,
  },
})
