export default ({ config }) => ({
  ...config,
  extra: {
    API_URL: process.env.EXPO_PUBLIC_API_URL || "",
  },
})
