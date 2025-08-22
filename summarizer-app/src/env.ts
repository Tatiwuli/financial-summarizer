import Constants from "expo-constants"

// Trata string vazia como ausente
const pick = (v?: string) =>
  typeof v === "string" && v.trim() ? v.trim() : undefined

// 1) Valor “assado” no build (web via app.config.js) ou manifest (native)
const apiFromConfig = pick(
  (Constants.expoConfig?.extra as any)?.API_URL ??
    (Constants.manifest as any)?.extra?.API_URL
)

// // 2) Valor via process.env em dev (Expo só expõe EXPO_PUBLIC_*)
// const apiFromEnv = pick(
//   typeof process !== "undefined"
//     ? (process.env as Record<string, string | undefined>).EXPO_PUBLIC_API_URL
//     : undefined
// )

const apiFromEnv = undefined

// 3) Fallback automático para localhost quando rodando em localhost no navegador
const isLocalWeb =
  typeof window !== "undefined" &&
  /^(localhost|127\.0\.0\.1|0\.0\.0\.0)$/i.test(window.location.hostname)
const localDefault = isLocalWeb ? "http://localhost:8000" : undefined

// 4) Resolver e sanitizar
const raw = apiFromConfig ?? apiFromEnv ?? localDefault
export const API_BASE = (raw ?? "").replace(/\/+$/, "")

if (!API_BASE && !isLocalWeb) {
  throw new Error("EXPO_PUBLIC_API_URL is required for API base URL")
}

// Aviso de mixed content
if (
  typeof window !== "undefined" &&
  window.location.protocol === "https:" &&
  API_BASE.startsWith("http://")
) {
  // eslint-disable-next-line no-console
  console.warn(
    "Mixed content: API_BASE é http enquanto o site é https. Use uma URL https no Vercel."
  )
}
