// Shared API configuration for all backend calls.
//
// VITE_API_BASE_URL is a public, non-secret value. Do NOT put secrets
// (API keys, JWT secrets, database credentials) in Vite environment
// variables - anything prefixed VITE_ is bundled into the client build.
//
// Local development falls back to the documented local backend address.
// Configure per environment with a .env file or CI build variable, e.g.:
//   VITE_API_BASE_URL=http://localhost:8000          (development)
//   VITE_API_BASE_URL=https://api.yourdomain.com      (deployment)
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Shared request timeout (ms). AI/RAG responses can legitimately take
// several seconds; 30s balances slow-generation tolerance against
// hung-request UX. Failures surface as user-facing error messages.
export const API_TIMEOUT_MS = 30_000;
