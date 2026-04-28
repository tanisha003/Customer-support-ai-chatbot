import { Bot, User } from "lucide-react";
import SourcePill from "./SourcePill.jsx";
import SuggestedQuestions from "./SuggestedQuestions.jsx";

export default function Message({ message, onSuggestionSelect, suggestionsDisabled }) {
  const isUser = message.role === "user";
  const showSuggestions = message.showSuggestions === true;

  return (
    <div
      className={`flex gap-3 animate-slide-up ${
        isUser ? "flex-row-reverse" : "flex-row"
      }`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-indigo-100 text-indigo-700"
            : "bg-slate-200 text-slate-700"
        }`}
        aria-hidden
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Bubble + extras */}
      <div
        className={`max-w-[85%] sm:max-w-[75%] ${
          isUser ? "items-end" : "items-start"
        } flex flex-col gap-1.5`}
      >
        <div
          className={`px-4 py-2.5 rounded-2xl shadow-sm whitespace-pre-wrap break-words ${
            isUser
              ? "bg-indigo-600 text-white rounded-br-md"
              : "bg-white text-slate-900 rounded-bl-md border border-slate-200"
          }`}
        >
          {message.pending && !message.content ? (
            <TypingDots />
          ) : (
            message.content
          )}
        </div>

        {/* Suggested questions — only on the welcome message, before first user send */}
        {!isUser && showSuggestions && onSuggestionSelect && (
          <SuggestedQuestions
            onSelect={onSuggestionSelect}
            disabled={suggestionsDisabled}
          />
        )}

        {/* Source pills (assistant only, after streaming completes) */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            <span className="text-xs text-slate-500 self-center mr-1">Sources:</span>
            {message.sources.map((s) => (
              <SourcePill key={s} name={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1" aria-label="thinking">
      <span
        className="w-2 h-2 bg-slate-400 rounded-full animate-bounce-dot"
        style={{ animationDelay: "0ms" }}
      />
      <span
        className="w-2 h-2 bg-slate-400 rounded-full animate-bounce-dot"
        style={{ animationDelay: "150ms" }}
      />
      <span
        className="w-2 h-2 bg-slate-400 rounded-full animate-bounce-dot"
        style={{ animationDelay: "300ms" }}
      />
    </div>
  );
}
