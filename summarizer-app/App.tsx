// app/index.tsx

import React from "react"
import { useSummaryStore } from "./src/state/SummaryStoreTest"
import { UploadScreen } from "./src/screens/UploadScreen"
import { LoadingScreen } from "./src/screens/LoadingScreen"
import { ResultScreen } from "./src/screens/ResultScreen"

const AppNavigator = () => {
  // O maestro que lê o estado global
  const status = useSummaryStore((state) => state.status)
  console.log("[AppNavigator] Status:", status)

  // Renderização condicional baseada no status
  if (status === "loading") {
    return <LoadingScreen />
  }

  if (status === "success") {
    return <ResultScreen />
  }

  // Os estados 'idle' e 'error' mostram a tela de upload.
  // A própria UploadScreen já mostra a mensagem de erro.
  return <UploadScreen />
}

export default AppNavigator
