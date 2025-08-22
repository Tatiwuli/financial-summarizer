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
}

if (
  typeof window !== "undefined" &&
  window.location?.protocol === "https:" &&
  API_BASE.startsWith("http://")
) {
  // eslint-disable-next-line no-console
  console.warn(
    "Mixed content: API_BASE is http while the site is https. Use an https backend URL in Vercel."
  )
}
