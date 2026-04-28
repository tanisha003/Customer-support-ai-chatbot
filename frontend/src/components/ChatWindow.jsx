import { useEffect, useRef } from "react";
import Message from "./Message.jsx";

export default function ChatWindow({ messages, onSuggestionSelect, suggestionsDisabled }) {
  const bottomRef = useRef(null);

  // Auto-scroll to the bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto chat-scroll px-4 sm:px-6 py-4 space-y-4 bg-slate-50">
      {messages.map((m) => (
        <Message
          key={m.id}
          message={m}
          onSuggestionSelect={onSuggestionSelect}
          suggestionsDisabled={suggestionsDisabled}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
