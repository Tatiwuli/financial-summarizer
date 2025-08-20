
const apiFromEnv =
  (typeof process !== "undefined"
    ? (process.env as Record<string, string | undefined>).EXPO_PUBLIC_API_URL
    : undefined) || undefined

if (!apiFromEnv) {
  throw new Error("EXPO_PUBLIC_API_URL is required for API base URL")
}

export const API_BASE = apiFromEnv.replace(/\/+$/, "")
