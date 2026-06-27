import axios from "axios";
import { ChevronDown, ChevronUp, Loader2, LogOut, Send } from "lucide-react";
import { useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  context?: string[];
}

interface ChatProps {
  token: string;
  onLogout: () => void;
}

export default function Chat({ token, onLogout }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedContext, setExpandedContext] = useState<number | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await axios.post(
        "http://localhost:8000/api/v1/chat/ask",
        {
          query: userMessage,
          collection_name: "documents",
          use_rag: true,
        },
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        },
      );

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.data.answer,
          context: response.data.context,
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
          content: "Sorry, there was an error processing your request.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleContext = (index: number) => {
    setExpandedContext(expandedContext === index ? null : index);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100">
      {/* Premium Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-gray-800/50 backdrop-blur-md border-b border-gray-850 sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
            L
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
            Lumenly
          </span>
        </div>
        <button
          onClick={onLogout}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white border border-gray-700 hover:border-gray-600 transition-all font-medium text-sm shadow-sm"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </header>

      <div className="flex-1 overflow-y-auto w-full">
        <div className="max-w-3xl mx-auto py-6 px-4 space-y-6">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 mt-20">
              <h2 className="text-2xl font-semibold mb-2">Welcome to Lumenly</h2>
              <p>Ask me anything about your documents.</p>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl p-4 ${
                  message.role === "user"
                    ? "bg-gray-700 text-gray-100"
                    : "bg-gray-800 text-gray-100"
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

                {message.role === "assistant" && message.context && message.context.length > 0 && (
                  <div className="mt-3">
                    <button
                      onClick={() => toggleContext(index)}
                      className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 font-medium"
                    >
                      {expandedContext === index ? (
                        <>
                          <ChevronUp size={16} />
                          Hide Context
                        </>
                      ) : (
                        <>
                          <ChevronDown size={16} />
                          View Context
                        </>
                      )}
                    </button>
                    {expandedContext === index && (
                      <div className="mt-2 p-3 bg-gray-700 rounded-md">
                        <p className="text-xs font-semibold text-gray-300 mb-2">Context Sources:</p>
                        <ul className="text-sm text-gray-400 space-y-1">
                          {message.context.map((ctx, ctxIndex) => (
                            <li key={ctxIndex} className="text-xs">
                              • {ctx}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 text-gray-100 rounded-2xl p-4">
                <div className="flex items-center gap-2">
                  <Loader2 className="animate-spin" size={20} />
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="p-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto w-full">
          <div className="relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Lumenly..."
              className="w-full px-4 py-4 pr-14 bg-gray-800 border border-gray-700 rounded-xl text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
            >
              <Send size={20} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
