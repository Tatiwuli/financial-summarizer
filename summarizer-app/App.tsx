// app/index.tsx

import React from "react"
import { useSummaryStore } from "./src/state/SummaryStoreTest"
import { UploadScreen } from "./src/screens/UploadScreen"
import { LoadingScreen } from "./src/screens/LoadingScreen"
import { ResultScreen } from "./src/screens/ResultScreen"
import { API_BASE } from "./src/env"
import { SafeAreaProvider } from "react-native-safe-area-context"

const App = () => {
  console.log("API base:", API_BASE)
  fetch(`${API_BASE}/health`, { cache: "no-store" })
    .then((r) => console.log("API health:", r.ok ? "OK" : "DOWN"))
    .catch(() => console.log("API health: DOWN"))

  // O maestro que lê o estado global
  const status = useSummaryStore((state) => state.status)
  console.log("[AppNavigator] Status:", status)

  let content: React.ReactNode
  if (status === "loading") {
    content = <LoadingScreen />
  } else if (status === "success") {
    content = <ResultScreen />
  } else {
    // Os estados 'idle' e 'error' mostram a tela de upload.
    // A própria UploadScreen já mostra a mensagem de erro.
    content = <UploadScreen />
  }

  return <SafeAreaProvider>{content}</SafeAreaProvider>
}

export default App
