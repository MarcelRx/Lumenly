import { useState } from "react";
// 1. Install react-router-dom: `npm install react-router-dom`
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import Chat from "./Chat";
import Login from "./Login";
// 2. Import the component created in Step 3 Task A
import KnowledgeBase from "./pages/KnowledgeBase";

// 3. Centralized layout component with navigation for protected routes
const ProtectedLayout: React.FC<{
  token: string;
  onLogout: () => void;
  children: React.ReactNode;
}> = ({ onLogout, children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <nav className="container mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🧠</span>
            <span className="text-xl font-bold text-gray-900">Lumenly</span>
          </div>

          <div className="flex items-center gap-6 text-sm font-medium">
            <Link to="/" className="text-gray-600 hover:text-blue-600 transition">
              💬 Chat workspace
            </Link>
            {/* Task E: Navigation Link */}
            <Link to="/kb" className="text-gray-600 hover:text-blue-600 transition">
              🗂️ Knowledge Base Dashboard
            </Link>
          </div>

          <button
            onClick={onLogout}
            className="text-sm text-red-600 hover:text-red-700 bg-red-50 px-3 py-1.5 rounded-md transition"
          >
            Logout
          </button>
        </nav>
      </header>
      <main className="flex-grow">{children}</main>
    </div>
  );
};

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

  // 4. Implement Routing Orchestration
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Route */}
        <Route
          path="/login"
          element={token ? <Navigate to="/" /> : <Login onLoginSuccess={handleLoginSuccess} />}
        />

        {/* Protected Routes Wrapper */}
        <Route
          path="/*"
          element={
            token ? (
              <ProtectedLayout token={token} onLogout={handleLogout}>
                <Routes>
                  {/* Default chat routing */}
                  <Route path="/" element={<Chat token={token} onLogout={handleLogout} />} />

                  {/* Task E Routing: Dashboard page */}
                  <Route path="/kb" element={<KnowledgeBase />} />

                  {/* Default catch-all redirect */}
                  <Route path="*" element={<Navigate to="/" />} />
                </Routes>
              </ProtectedLayout>
            ) : (
              // Not logged in? Redirect all paths to login
              <Navigate to="/login" />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
