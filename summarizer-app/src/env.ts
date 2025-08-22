import Constants from "expo-constants"


// Read from Expo config first (baked at build on Vercel)
const apiFromConfig = (Constants.expoConfig?.extra as any)?.API_URL as
  | string
  | undefined

// Fallbacks: Vite/Expo dev env, then localhost in dev
const apiFromEnv =
  (typeof process !== "undefined"
    ? (process.env as Record<string, string | undefined>).EXPO_PUBLIC_API_URL
    : undefined) || undefined

// Treat empty strings as missing so we can fall back correctly
const pick = (v?: string) => (v && v.trim() !== "" ? v : undefined)

const raw =
  pick(apiFromConfig) ??
  pick(apiFromEnv) ??
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "")

// Trim any trailing slashes so requests don’t become //health
export const API_BASE = raw.replace(/\/+$/, "")



if (!API_BASE) {
  throw new Error(
    "API base URL is required. Set EXPO_PUBLIC_API_URL or extra.API_URL"
  )

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

