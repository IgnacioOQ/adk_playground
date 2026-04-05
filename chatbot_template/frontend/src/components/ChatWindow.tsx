"use client";

import { useEffect, useRef, useState } from "react";
import { useChat } from "@/hooks/useChat";
import MessageBubble from "./MessageBubble";

export default function ChatWindow() {
  const [input, setInput] = useState("");
  // Toggle between single-turn (/chat) and streaming (/stream)
  const [streamMode, setStreamMode] = useState(false);
  const { messages, loading, sendMessage, sendMessageStream } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    if (streamMode) {
      await sendMessageStream(text);
    } else {
      await sendMessage(text);
    }
  };

  // A2UI button actions re-send the action string as a new message
  const handleAction = (action: string) => {
    sendMessage(action);
  };

  return (
    <div className="chat-window">
      {/* Header */}
      <div
        style={{
          padding: "0.75rem 1rem",
          borderBottom: "1px solid #e5e5e5",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <strong>Template Chatbot</strong>
        <label style={{ fontSize: "0.85rem", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={streamMode}
            onChange={(e) => setStreamMode(e.target.checked)}
            style={{ marginRight: "0.4rem" }}
          />
          Streaming
        </label>
      </div>

      {/* Message list */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <p style={{ color: "#999", textAlign: "center", marginTop: "2rem" }}>
            Send a message to get started.
          </p>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onAction={handleAction} />
        ))}
        {loading && (
          <div className="message assistant" style={{ opacity: 0.5 }}>
            Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
