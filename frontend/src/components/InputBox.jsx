import { useState } from "react";
import { Send } from "lucide-react";

export default function InputBox({ onSend, disabled }) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSend = text.trim().length > 0 && !disabled;

  return (
    <div className="border-t border-slate-200 bg-white px-3 sm:px-4 py-3">
      <div className="flex items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled ? "Waiting for response..." : "Ask a support question..."
          }
          disabled={disabled}
          rows={1}
          maxLength={1000}
          className="flex-1 resize-none px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed text-sm sm:text-base max-h-32"
          style={{ minHeight: "42px" }}
        />
        <button
          onClick={handleSubmit}
          disabled={!canSend}
          className="flex-shrink-0 p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
          aria-label="Send message"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="text-xs text-slate-400 mt-1.5 px-1">
        Press Enter to send • Shift+Enter for new line
      </p>
    </div>
  );
}
