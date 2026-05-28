"use client";

import { useState, useEffect } from "react";
import { ChatWindow } from "@/components/ChatWindow";
import { Dashboard, type DashboardView, type HistoryItem, type TreeNode, type SystemEntry, type WikiPage } from "@/components/dashboard/Dashboard";
import { streamChat, fetchWikiContent } from "@/lib/api";
import type { ChatDoneData } from "@/lib/api";
import { useWikiGraph } from "@/lib/use-wiki-graph";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

let nextId = 1;

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dashboardView, setDashboardView] = useState<DashboardView>("dashboard");
  const [selectedPage, setSelectedPage] = useState<WikiPage | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [wikiTree, setWikiTree] = useState<TreeNode[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemEntry[]>([
    { label: "Ollama", status: "connected" },
    { label: "SQLite", status: "connected", detail: "247 pages" },
    { label: "Embedder", status: "connected", detail: "nomic-embed-text" },
  ]);

  const {
    nodes: graphNodes,
    edges: graphEdges,
    loading: graphLoading,
    error: graphError,
    refresh: onGraphRefresh,
  } = useWikiGraph();

  // Load history from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("memweaver-history");
    if (saved) {
      try {
        const parsed: HistoryItem[] = JSON.parse(saved);
        setHistory(parsed.map((h) => ({ ...h, timestamp: new Date(h.timestamp) })));
      } catch { /* ignore corrupt data */ }
    }
  }, []);

  // Persist history to localStorage
  useEffect(() => {
    if (history.length > 0) {
      localStorage.setItem("memweaver-history", JSON.stringify(history));
    }
  }, [history]);

  async function handleSend(question: string) {
    setError(null);
    const userMsg: Message = { id: String(nextId++), role: "user", content: question };
    const assistantMsg: Message = { id: String(nextId++), role: "assistant", content: "" };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    // Add to history
    setHistory((prev) => {
      const item: HistoryItem = {
        id: String(nextId++),
        query: question,
        timestamp: new Date(),
      };
      return [item, ...prev].slice(0, 50); // keep last 50
    });

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

  function handleHistoryRerun(query: string) {
    handleSend(query);
  }

  async function handleWikiPageSelect(pageId: string) {
    try {
      const content = await fetchWikiContent(pageId);
      setSelectedPage({
        id: pageId,
        title: pageId,
        content,
      });
      setDashboardView("preview");
    } catch {
      setSelectedPage({
        id: pageId,
        title: pageId,
        content: "Error loading page content.",
      });
      setDashboardView("preview");
    }
  }

  function handleBackToDashboard() {
    setDashboardView("dashboard");
    setSelectedPage(null);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="h-12 shrink-0 border-b bg-card flex items-center gap-3 px-4">
        <img src="/logo.svg" alt="MemWeaver" className="w-6 h-6" />
        <span className="text-sm font-semibold text-primary">MemWeaver</span>
        <div className="flex-1" />
        <span className="text-xs bg-secondary text-secondary-foreground px-2 py-0.5 rounded hidden sm:inline">
          🧠 qwen2.5:7b
        </span>
        {/* Mobile hamburger */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="lg:hidden text-muted-foreground hover:text-foreground"
          aria-label="Toggle sidebar"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      </header>

      {/* Main content */}
      <div className="flex flex-1 min-h-0">
        <main className="flex-1 flex flex-col min-w-0">
          {error && (
            <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-2 text-sm text-destructive">
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

        {/* Desktop sidebar */}
        <div className="hidden lg:block">
          <Dashboard
            view={dashboardView}
            activeContext={activeSlug ? [activeSlug] : []}
            history={history}
            wikiTree={wikiTree}
            systemStatus={systemStatus}
            selectedPage={selectedPage}
            graphNodes={graphNodes}
            graphEdges={graphEdges}
            graphLoading={graphLoading}
            graphError={graphError}
            onHistoryRerun={handleHistoryRerun}
            onWikiPageSelect={handleWikiPageSelect}
            onBackToDashboard={handleBackToDashboard}
            onGraphRefresh={onGraphRefresh}
          />
        </div>

        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="absolute inset-0 bg-black/30"
              onClick={() => setSidebarOpen(false)}
            />
            <div className="absolute right-0 top-0 h-full">
              <Dashboard
                view={dashboardView}
                activeContext={activeSlug ? [activeSlug] : []}
                history={history}
                wikiTree={wikiTree}
                systemStatus={systemStatus}
                selectedPage={selectedPage}
                graphNodes={graphNodes}
                graphEdges={graphEdges}
                graphLoading={graphLoading}
                graphError={graphError}
                onHistoryRerun={handleHistoryRerun}
                onWikiPageSelect={handleWikiPageSelect}
                onBackToDashboard={handleBackToDashboard}
                onGraphRefresh={onGraphRefresh}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
