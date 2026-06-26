const apiBaseUrl = process.env.VITE_API_BASE_URL;

if (!apiBaseUrl || !apiBaseUrl.trim()) {
  console.error("VITE_API_BASE_URL is required for production builds.");
  console.error("For local builds without a deployed API, run `npm run build:local`.");
  process.exit(1);
}

if (/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\/?$/.test(apiBaseUrl.trim())) {
  console.error("VITE_API_BASE_URL must not point to localhost for production builds.");
  process.exit(1);
}
