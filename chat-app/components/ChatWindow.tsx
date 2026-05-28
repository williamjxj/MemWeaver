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
      <div className="border-b p-4 shrink-0">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything — wiki memory is injected automatically"
            disabled={isStreaming}
            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
          />
          {isStreaming ? (
            <button
              onClick={onStop}
              className="px-4 py-2 bg-destructive text-destructive-foreground rounded-lg text-sm hover:bg-red-600"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim()}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:opacity-90 disabled:opacity-50"
            >
              Send
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 p-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            Ask anything — wiki memory is injected automatically
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble
            key={m.id}
            role={m.role}
            content={m.content}
            isStreaming={isStreaming && i === messages.length - 1 && m.role === "assistant"}
          />
        ))}
        {isStreaming && !messages.some((m) => m.role === "assistant" && m.content) && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-lg px-4 py-2 text-sm text-muted-foreground">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
