// src/screens/LoadingScreen.tsx

import React from "react"
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
} from "react-native"

export const LoadingScreen = () => {
  return (
    <SafeAreaView style={styles.wrapper}>
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.title}>Generating Summary...</Text>
        <Text style={styles.stepText}>1. Summarizing Q&A</Text>
        <Text style={styles.stepText}>2. Evaluating the Q&A Summary</Text>
        <Text style={styles.stepText}>3. Summarizing Prepared Remarks</Text>
        <Text style={styles.stepText}>4. Wrapping up</Text>
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
})
