"use client";

import { useState, useRef, useEffect } from "react";
import { MessageBubble } from "./MessageBubble";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
  onSend: (question: string) => void;
  onStop?: () => void;
}

export function ChatWindow({
  messages,
  isStreaming,
  onSend,
  onStop,
}: ChatWindowProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  function handleSubmit() {
    const q = input.trim();
    if (!q || isStreaming) return;
    setInput("");
    onSend(q);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-3 p-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Ask anything — wiki memory is injected automatically
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} content={m.content} />
        ))}
        {isStreaming && messages[messages.length - 1]?.role === "assistant" && (
          <MessageBubble
            role="assistant"
            content={messages[messages.length - 1].content}
            isStreaming
          />
        )}
        {isStreaming && !messages.some((m) => m.role === "assistant" && m.content) && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2 text-sm text-gray-500">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t p-4">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            disabled={isStreaming}
            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          {isStreaming ? (
            <button
              onClick={onStop}
              className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Send
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
