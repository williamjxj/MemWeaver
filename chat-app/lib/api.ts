export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CHAT_API = "/api/chat";

export interface ChatDoneData {
  wiki_slug: string | null;
  topic: string;
  context_chars: number;
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: (data: ChatDoneData) => void;
  onError: (message: string) => void;
}

export async function streamChat(
  question: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(CHAT_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });

  if (!res.ok) {
    callbacks.onError(`Server error: ${res.status} ${res.statusText}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError("Response body is not readable");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("event: ")) {
        currentEvent = trimmed.slice(7).trim();
      } else if (trimmed.startsWith("data: ")) {
        const rawData = trimmed.slice(6).trim();
        try {
          const data = JSON.parse(rawData);
          if (currentEvent === "token") {
            callbacks.onToken(data.text || "");
          } else if (currentEvent === "done") {
            callbacks.onDone({
              wiki_slug: data.wiki_slug ?? null,
              topic: data.topic ?? "",
              context_chars: data.context_chars ?? 0,
            });
          } else if (currentEvent === "error") {
            callbacks.onError(data.message || "Unknown error");
          }
        } catch {
          // ignore unparseable SSE data
        }
        currentEvent = "";
      }
    }
  }
}

export async function fetchWikiContent(slug: string): Promise<string> {
  const res = await fetch(`${API_BASE}/wiki/${slug}`);
  if (!res.ok) return "";
  const data = await res.json();
  return data.content ?? "";
}
