import { useEffect, useState } from "react";
import { Bot, AlertTriangle } from "lucide-react";
import ChatWindow from "./components/ChatWindow.jsx";
import InputBox from "./components/InputBox.jsx";
import { fetchHealth, streamChat } from "./api.js";

const WELCOME_ID = "welcome";

/**
 * Top-level app. All state lives in React (no localStorage).
 *
 * Message shape:
 *   { id, role: "user" | "assistant", content: string,
 *     sources?: string[], pending?: boolean,
 *     showSuggestions?: boolean }
 */
export default function App() {
  const [messages, setMessages] = useState([
    {
      id: WELCOME_ID,
      role: "assistant",
      content:
        "Hi! I'm your support assistant. Pick a topic below or ask anything " +
        "about our product, shipping, or returns.",
      sources: [],
      showSuggestions: true,
    },
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState({
    online: false,
    docs: 0,
    checked: false,
  });

  // Health check on mount
  useEffect(() => {
    fetchHealth()
      .then((h) =>
        setBackendStatus({
          online: h.status === "ok",
          docs: h.documents_indexed ?? 0,
          checked: true,
        }),
      )
      .catch(() => setBackendStatus({ online: false, docs: 0, checked: true }));
  }, []);

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    setError(null);

    const userMsg = { id: crypto.randomUUID(), role: "user", content: trimmed };
    const botId = crypto.randomUUID();
    const botMsg = {
      id: botId,
      role: "assistant",
      content: "",
      sources: [],
      pending: true,
    };

    // Hide suggestion chips on the welcome message after the first send
    setMessages((m) => [
      ...m.map((msg) =>
        msg.id === WELCOME_ID ? { ...msg, showSuggestions: false } : msg,
      ),
      userMsg,
      botMsg,
    ]);
    setIsStreaming(true);

    await streamChat(trimmed, {
      onToken: (token) => {
        setMessages((m) =>
          m.map((msg) =>
            msg.id === botId
              ? { ...msg, content: msg.content + token, pending: false }
              : msg,
          ),
        );
      },
      onDone: (sources) => {
        setMessages((m) =>
          m.map((msg) =>
            msg.id === botId ? { ...msg, sources, pending: false } : msg,
          ),
        );
        setIsStreaming(false);
      },
      onError: (errMsg) => {
        setMessages((m) =>
          m.map((msg) =>
            msg.id === botId
              ? {
                  ...msg,
                  content:
                    msg.content ||
                    "Sorry, I couldn't reach the backend. Please try again.",
                  pending: false,
                }
              : msg,
          ),
        );
        setError(errMsg);
        setIsStreaming(false);
      },
    });
  };

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto bg-white shadow-xl sm:my-4 sm:rounded-2xl sm:h-[calc(100vh-2rem)] overflow-hidden">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 sm:px-6 py-4 bg-gradient-to-r from-indigo-600 to-indigo-500 text-white">
        <div className="bg-white/20 p-2 rounded-lg">
          <Bot className="w-5 h-5" aria-hidden />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-base sm:text-lg font-semibold">Customer Support</h1>
          <p className="text-xs sm:text-sm text-indigo-100">
            RAG-powered assistant
            {backendStatus.checked &&
              backendStatus.online &&
              ` • ${backendStatus.docs} docs indexed`}
          </p>
        </div>
        <div
          className={`flex items-center gap-1.5 text-xs ${
            backendStatus.online ? "text-green-200" : "text-amber-200"
          }`}
          aria-label={backendStatus.online ? "online" : "offline"}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              backendStatus.online ? "bg-green-400" : "bg-amber-400"
            }`}
          />
          {backendStatus.online ? "online" : "offline"}
        </div>
      </header>

      {/* Error toast */}
      {error && (
        <div className="flex items-start gap-2 px-4 py-2 bg-red-50 border-b border-red-200 text-red-800 text-sm animate-fade-in">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden />
          <div className="flex-1">{error}</div>
          <button
            onClick={() => setError(null)}
            className="text-red-600 hover:text-red-800 text-xs font-medium"
          >
            dismiss
          </button>
        </div>
      )}

      {/* Chat area */}
      <ChatWindow
        messages={messages}
        onSuggestionSelect={sendMessage}
        suggestionsDisabled={isStreaming}
      />

      {/* Input */}
      <InputBox onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
