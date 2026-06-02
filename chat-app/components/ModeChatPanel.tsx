"use client";

import { useRef, useState } from "react";
import { ChatWindow } from "@/components/ChatWindow";
import { queryWiki, saveQa, streamChat, type QueryResponse } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

type PanelKind = "qa" | "rag" | "wiki";
type QueryMode = "keyword" | "semantic" | "hybrid";

interface ModeChatPanelProps {
  kind: PanelKind;
  title: string;
  eyebrow: string;
  description: string;
  engineLabel: string;
  accentClassName: string;
  queryMode?: QueryMode;
  emptyState: string;
  placeholder: string;
  sendLabel: string;
  showSaveToMemory?: boolean;
}

let nextId = 1;

function formatQueryResponse(response: QueryResponse, fallbackLabel: string): string {
  const summary = response.summarized_answer?.trim();
  const intro = summary || "No synthesized answer was returned for this query.";
  const hits = response.results.slice(0, 5);

  const sourceBlock = hits.length
    ? hits
        .map((hit, index) => {
          const snippet = hit.snippet?.trim() || "_No snippet available_";
          const tagText = hit.tags.length ? ` • ${hit.tags.slice(0, 3).join(", ")}` : "";
          return `${index + 1}. **${hit.title}**${tagText}
   ${snippet}`;
        })
        .join("\n\n")
    : "_No hits found._";

  return [`**${fallbackLabel}**`, "", intro, "", "**Top hits**", "", sourceBlock].join("\n");
}

export function ModeChatPanel({
  kind,
  title,
  eyebrow,
  description,
  engineLabel,
  accentClassName,
  queryMode = "hybrid",
  emptyState,
  placeholder,
  sendLabel,
  showSaveToMemory = false,
}: ModeChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  async function handleSend(question: string) {
    setError(null);
    const userMsg: Message = { id: String(nextId++), role: "user", content: question };
    const assistantMsg: Message = { id: String(nextId++), role: "assistant", content: "" };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    const controller = new AbortController();
    controllerRef.current = controller;

    if (kind === "qa") {
      let fullAnswer = "";

      try {
        await streamChat(
          question,
          {
            onToken(token) {
              fullAnswer += token;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") {
                  updated[updated.length - 1] = { ...last, content: fullAnswer };
                }
                return updated;
              });
            },
            onDone() {
              setIsStreaming(false);
            },
            onError(message) {
              setError(message);
              setIsStreaming(false);
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant" && !last.content) {
                  updated.pop();
                }
                return updated;
              });
            },
          },
          controller.signal,
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : "stream interrupted";
        if (message.toLowerCase().includes("abort")) {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role === "assistant" && !last.content) {
              updated.pop();
            }
            return updated;
          });
        } else {
          setError(message);
        }
        setIsStreaming(false);
      } finally {
        controllerRef.current = null;
      }

      return;
    }

    try {
      const result = await queryWiki(question, queryMode, true, controller.signal);
      const answerLabel = kind === "rag" ? "RAG synthesis" : "LLM-Wiki synthesis";
      const content = formatQueryResponse(result, answerLabel);
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === "assistant") {
          updated[updated.length - 1] = { ...last, content };
        }
        return updated;
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "query failed";
      if (!message.toLowerCase().includes("abort")) {
        setError(message);
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant" && !last.content) {
            updated.pop();
          }
          return updated;
        });
      }
    } finally {
      controllerRef.current = null;
      setIsStreaming(false);
    }
  }

  function handleStop() {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setIsStreaming(false);
  }

  async function handleSaveQa(question: string, answer: string, note: string): Promise<boolean> {
    return saveQa(question, answer, note);
  }

  return (
    <section className={`flex min-h-136 flex-col overflow-hidden rounded-3xl border bg-card/90 shadow-sm ${accentClassName}`}>
      <header className="flex items-start justify-between gap-3 border-b px-4 py-3">
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-muted-foreground">{eyebrow}</p>
          <h2 className="text-lg font-semibold leading-none">{title}</h2>
          <p className="max-w-prose text-sm text-muted-foreground">{description}</p>
        </div>
        <div className="shrink-0 rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
          {engineLabel}
        </div>
      </header>

      {error && (
        <div className="border-b border-destructive/20 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="min-h-0 flex-1">
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          onSend={handleSend}
          onStop={handleStop}
          onSaveQa={handleSaveQa}
          placeholder={placeholder}
          emptyState={emptyState}
          sendLabel={sendLabel}
          showSaveToMemory={showSaveToMemory}
        />
      </div>
    </section>
  );
}