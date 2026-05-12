"use client";

import { useState, useCallback } from "react";
import { ChatWindow } from "@/components/ChatWindow";
import { WikiSidebar } from "@/components/WikiSidebar";
import { streamChat, fetchWikiContent } from "@/lib/api";
import type { ChatDoneData } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

let nextId = 1;

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [activeTopic, setActiveTopic] = useState("");
  const [wikiContent, setWikiContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadWikiContent = useCallback(async (slug: string) => {
    const content = await fetchWikiContent(slug);
    setWikiContent(content);
    return content;
  }, []);

  async function handleSend(question: string) {
    setError(null);
    const userMsg: Message = { id: String(nextId++), role: "user", content: question };
    const assistantMsg: Message = { id: String(nextId++), role: "assistant", content: "" };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    let fullAnswer = "";

    await streamChat(question, {
      onToken(token) {
        fullAnswer += token;
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: fullAnswer };
          }
          return updated;
        });
      },
      onDone(data: ChatDoneData) {
        setActiveSlug(data.wiki_slug);
        setActiveTopic(data.topic);
        if (data.wiki_slug) {
          loadWikiContent(data.wiki_slug);
        }
        setIsStreaming(false);
      },
      onError(message: string) {
        setError(message);
        setIsStreaming(false);
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant" && !last.content) {
            updated.pop();
          }
          return updated;
        });
      },
    });
  }

  function handleStop() {
    setIsStreaming(false);
  }

  return (
    <div className="flex h-full">
      <main className="flex-1 flex flex-col">
        {error && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          onSend={handleSend}
          onStop={handleStop}
        />
      </main>
      <WikiSidebar
        slug={activeSlug}
        topic={activeTopic}
        wikiContent={wikiContent}
        onFetchContent={loadWikiContent}
      />
    </div>
  );
}
