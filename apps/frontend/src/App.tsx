import { useState } from "react";
import Chat from "./Chat";
import Login from "./Login";

export default function App() {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem("access_token");
    } catch {
      return null;
    }
  });

  const handleLoginSuccess = (accessToken: string) => {
    localStorage.setItem("access_token", accessToken);
    setToken(accessToken);
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
  };

  if (!token) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return <Chat token={token} onLogout={handleLogout} />;
}

