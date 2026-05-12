"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

export function MessageBubble({
  role,
  content,
  isStreaming = false,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[75%] rounded-lg px-4 py-2 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white"
            : "prose prose-sm max-w-none bg-gray-100 text-gray-900"
        }`}
      >
        {isUser ? (
          content
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content || ""}
          </ReactMarkdown>
        )}
        {isStreaming && (
          <span className="inline-block w-[2px] h-4 bg-gray-500 animate-pulse ml-0.5 align-text-bottom" />
        )}
      </div>
    </div>
  );
}
