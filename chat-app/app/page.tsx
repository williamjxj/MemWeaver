"use client";

import { useState } from "react";
import Image from "next/image";
import { ModeChatPanel } from "@/components/ModeChatPanel";
import { InventoryPanel } from "@/components/InventoryPanel";

type ActiveView = "compare" | "qa" | "rag" | "wiki" | "inventory";

const stageTabs: Array<{ id: ActiveView; label: string; description: string }> = [
  { id: "compare", label: "Compare", description: "All three stages side by side" },
  { id: "qa", label: "QA Chat", description: "DeepSeek streaming over raw Q/A" },
  { id: "rag", label: "RAG", description: "Hybrid BM25 + sqlite-vec retrieval" },
  { id: "wiki", label: "LLM-Wiki", description: "Distilled markdown query layer" },
  { id: "inventory", label: "Inventory", description: "Record counts across all data stores" },
];

const panelConfigs = {
  qa: {
    kind: "qa" as const,
    title: "QA Chat",
    eyebrow: "Step 1 · Raw conversation",
    description: "The current DeepSeek chat flow. This is the uncompressed entry point for original questions and answers.",
    engineLabel: "DeepSeek stream",
    accentClassName: "border-primary/15",
    placeholder: "Ask the raw QA assistant...",
    emptyState: "Start with the original QA chat. Responses stream from the current DeepSeek-backed route.",
    sendLabel: "Send",
    showSaveToMemory: true,
  },
  rag: {
    kind: "rag" as const,
    title: "RAG Chat",
    eyebrow: "Step 2 · Hybrid retrieval",
    description: "Hybrid BM25 + sqlite-vec retrieval over the compiled memory layer. This shows how search precision improves after embeddings and FTS are combined.",
    engineLabel: "Ollama + qwen",
    queryMode: "hybrid" as const,
    accentClassName: "border-secondary/20",
    placeholder: "Ask the retrieval layer...",
    emptyState: "Search the hybrid retrieval layer to see how sqlite-vec and BM25 reshape the answer.",
    sendLabel: "Search",
    showSaveToMemory: false,
  },
  wiki: {
    kind: "wiki" as const,
    title: "LLM-Wiki Query",
    eyebrow: "Step 3 · Distilled memory",
    description: "Keyword search over the distilled wiki markdown. This is the canonical memory layer after compilation, optimized for precise recall.",
    engineLabel: "LLM-Wiki index",
    queryMode: "keyword" as const,
    accentClassName: "border-accent/20",
    placeholder: "Query the distilled wiki...",
    emptyState: "Ask the distilled wiki layer. This view emphasizes the final, compact memory representation.",
    sendLabel: "Query",
    showSaveToMemory: false,
  },
};

export default function Home() {
  const [activeView, setActiveView] = useState<ActiveView>("compare");

  const compareMode = activeView === "compare";
  const singleView = compareMode ? null : (activeView as Exclude<ActiveView, "compare">);

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.12),transparent_35%),linear-gradient(180deg,rgba(248,250,252,1),rgba(241,245,249,0.75))] text-foreground">
      <div className="mx-auto flex min-h-full w-full max-w-450 flex-col gap-5 px-4 py-4 lg:px-6">
        <header className="rounded-3xl border bg-card/90 px-5 py-4 shadow-sm backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <Image src="/logo.svg" alt="MemWeaver" width={32} height={32} priority />
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.32em] text-muted-foreground">Memory pipeline dashboard</p>
                  <h1 className="text-2xl font-semibold tracking-tight">MemWeaver three-stage chat</h1>
                </div>
              </div>
              <p className="max-w-3xl text-sm text-muted-foreground">
                Compare the raw QA stream, the hybrid RAG layer, and the distilled LLM-Wiki index to see how the same question becomes more precise as it moves through the memory pipeline.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {stageTabs.map((tab) => {
                const active = activeView === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveView(tab.id)}
                    className={`rounded-full border px-4 py-2 text-left transition ${active ? "border-primary bg-primary text-primary-foreground shadow-sm" : "border-border bg-background/80 text-muted-foreground hover:text-foreground"}`}
                    aria-pressed={active}
                  >
                    <div className="text-sm font-medium">{tab.label}</div>
                    <div className="text-[11px] leading-tight opacity-80">{tab.description}</div>
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        <section className="grid gap-3 rounded-3xl border bg-card/70 p-4 shadow-sm backdrop-blur lg:grid-cols-3">
          <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">Step 1</p>
            <h2 className="mt-1 text-base font-semibold">Raw Q/A</h2>
            <p className="mt-2 text-sm text-muted-foreground">DeepSeek answers the original prompt before any distillation or retrieval shaping.</p>
          </div>
          <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">Step 2</p>
            <h2 className="mt-1 text-base font-semibold">RAG layer</h2>
            <p className="mt-2 text-sm text-muted-foreground">Hybrid BM25 + sqlite-vec pulls the strongest passages from the compiled store.</p>
          </div>
          <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">Step 3</p>
            <h2 className="mt-1 text-base font-semibold">LLM-Wiki</h2>
            <p className="mt-2 text-sm text-muted-foreground">The distilled markdown wiki becomes the canonical memory surface for precise queries.</p>
          </div>
        </section>

        <main className={compareMode ? "grid flex-1 min-h-0 gap-4 xl:grid-cols-3" : "flex flex-1 min-h-0 justify-center"}>
          {compareMode ? (
            <>
              <ModeChatPanel {...panelConfigs.qa} />
              <ModeChatPanel {...panelConfigs.rag} />
              <ModeChatPanel {...panelConfigs.wiki} />
            </>
          ) : (
            <div className="w-full max-w-6xl">
              {singleView === "inventory" ? (
                <InventoryPanel />
              ) : singleView ? (
                <ModeChatPanel {...panelConfigs[singleView as keyof typeof panelConfigs]} />
              ) : null}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
