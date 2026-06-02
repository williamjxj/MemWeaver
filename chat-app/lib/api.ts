export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CHAT_API = `${API_BASE}/chat`;

export interface ChatDoneData {
  wiki_slug: string | null;
  topic: string;
  context_chars: number;
}

export interface QueryResult {
  id: string;
  title: string;
  type: string;
  path: string;
  snippet: string;
  tags: string[];
  score: number;
  updated: string | null;
  inbound_links: number;
}

export interface QueryResponse {
  query: string;
  mode: "keyword" | "semantic" | "hybrid";
  results: QueryResult[];
  total: number;
  summarized_answer: string | null;
}

export interface WikiTreeNode {
  id: string;
  label: string;
  type: "folder" | "page";
  children?: WikiTreeNode[];
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: (data: ChatDoneData) => void;
  onError: (message: string) => void;
}

export async function queryWiki(
  question: string,
  mode: "keyword" | "semantic" | "hybrid" = "hybrid",
  summarize = true,
  signal?: AbortSignal,
): Promise<QueryResponse> {
  const params = new URLSearchParams({
    q: question,
    mode,
    summarize: summarize ? "true" : "false",
  });

  const response = signal
    ? await fetch(`${API_BASE}/query?${params.toString()}`, { signal })
    : await fetch(`${API_BASE}/query?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Server error: ${response.status} ${response.statusText}`);
  }

  const data = (await response.json()) as QueryResponse;
  return {
    query: data.query ?? question,
    mode: data.mode ?? mode,
    results: Array.isArray(data.results) ? data.results : [],
    total: typeof data.total === "number" ? data.total : 0,
    summarized_answer: data.summarized_answer ?? null,
  };
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

export async function fetchWikiTree(): Promise<WikiTreeNode[]> {
  const res = await fetch(`${API_BASE}/wiki/tree`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.tree ?? [];
}

export async function saveQa(
  question: string,
  answer: string,
  note?: string,
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        answer,
        source: "chat",
        ...(note && note.trim() ? { note: note.trim() } : {}),
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}
