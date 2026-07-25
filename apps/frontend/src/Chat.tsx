import axios from "axios";
import { Bot, LogOut, Send, Sparkles, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  agentUsed?: string;
  memoriesRetrieved?: number;
}

interface ChatProps {
  token: string;
  onLogout: () => void;
}

export default function Chat({ token, onLogout }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm Lumenly, your multi-agent AI workspace. How can I help you today?",
      agentUsed: "life_strategist",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Defaulting to the user_id you used in your successful curl test
  const userId = "mohsen_123";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      // Hitting your new multi-agent backend endpoint
      const response = await axios.post(
        "http://localhost:8000/api/chat",
        {
          user_id: userId,
          message: userMessage,
        },
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = response.data;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          agentUsed: data.agent_used,
          memoriesRetrieved: data.memories_retrieved,
        },
      ]);
    } catch (error) {
      console.error("Error sending message:", error);

      if (axios.isAxiosError(error) && error.response?.status === 401) {
        onLogout();
        return;
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error connecting to the Lumenly backend.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100">
      {/* Premium Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-gray-800/50 backdrop-blur-md border-b border-gray-800 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
              Lumenly OS
            </h1>
            <p className="text-xs text-gray-400">Intelligent Workspace</p>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white border border-gray-700 hover:border-gray-600 transition-all font-medium text-sm shadow-sm"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto w-full">
        <div className="max-w-4xl mx-auto py-6 px-4 space-y-6">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex items-start gap-3 ${
                message.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                  message.role === "user" ? "bg-emerald-600" : "bg-indigo-600"
                }`}
              >
                {message.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
              </div>
              <div
                className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed ${
                  message.role === "user"
                    ? "bg-emerald-600 text-white rounded-tr-sm"
                    : "bg-gray-800 text-gray-200 border border-gray-700 rounded-tl-sm"
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>

                {/* Metadata Badges for AI Responses */}
                {message.agentUsed && (
                  <div className="mt-3 pt-3 border-t border-gray-700/50 flex items-center justify-between text-[10px] text-gray-400 font-medium">
                    <span className="uppercase tracking-wider text-indigo-400">
                      Agent: {message.agentUsed.replace("_", " ")}
                    </span>
                    {message.memoriesRetrieved !== undefined && message.memoriesRetrieved > 0 && (
                      <span className="text-emerald-400 flex items-center gap-1">
                        🧠 {message.memoriesRetrieved} memory used
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center animate-pulse">
                <Bot className="w-5 h-5" />
              </div>
              <div className="bg-gray-800 border border-gray-700 rounded-2xl p-4 text-sm text-gray-400 rounded-tl-sm">
                Thinking, routing across coaches, and recalling context...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 bg-gray-900 border-t border-gray-800">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto w-full">
          <div className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask your life strategist, fitness, or habit coach anything..."
              className="w-full px-5 py-4 pr-16 bg-gray-800 border border-gray-700 rounded-xl text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent shadow-inner"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="absolute right-2 p-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed transition-colors shadow-md"
            >
              <Send size={18} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
