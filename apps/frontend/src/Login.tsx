import axios from "axios";
import type { FormEvent } from "react";
import { useState } from "react";
import { API_BASE_URL, API_TIMEOUT_MS } from "./api";

interface LoginProps {
  onLoginSuccess?: (token: string) => void;
}

export default function Login({ onLoginSuccess }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    setError(null);

    if (!email.trim() || !password) {
      setError("Email and password are required.");
      return;
    }

    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      // FastAPI OAuth2PasswordRequestForm expects `username` + `password`
      params.set("username", email.trim());
      params.set("password", password);

      const response = await axios.post(
        `${API_BASE_URL}/api/v1/auth/login`,
        params,
        {
          timeout: API_TIMEOUT_MS,
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        },
      );

      const accessToken = response.data?.access_token as string | undefined;
      if (!accessToken) {
        throw new Error("Login succeeded but access_token was missing.");
      }

      localStorage.setItem("access_token", accessToken);
      if (onLoginSuccess) {
        onLoginSuccess(accessToken);
      } else {
        window.location.reload();
      }
    } catch (err) {
      const axiosErr = err as {
        response?: { data?: { detail?: unknown; message?: unknown } };
        message?: unknown;
      };

      const detail =
        axiosErr.response?.data?.detail ??
        axiosErr.response?.data?.message ??
        axiosErr.message ??
        "Login failed.";

      setError(typeof detail === "string" ? detail : "Login failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 text-gray-100 px-4">
      <div className="w-full max-w-md bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h1 className="text-2xl font-semibold mb-4">Sign in</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Email
            </label>
            <input
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              disabled={isLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Password
            </label>
            <input
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              disabled={isLoading}
            />
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-900/30 border border-red-800 rounded-lg p-3">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white font-semibold transition-colors"
          >
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
