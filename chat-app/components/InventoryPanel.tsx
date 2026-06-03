"use client";

import { useEffect, useState } from "react";
import { fetchInventory, type InventoryData } from "@/lib/api";
import { WikiGraphView } from "@/components/WikiGraphView";

type SectionKey = "raw_qa" | "concepts" | "db" | "index" | "log" | "graph";

interface SectionMeta {
  label: string;
  icon: string;
  summary: (data: InventoryData) => string;
}

const SECTIONS: Record<SectionKey, SectionMeta> = {
  raw_qa: {
    label: "Raw QA",
    icon: "📄",
    summary: (d) => `${d.raw_qa.total} file(s)`,
  },
  concepts: {
    label: "Wiki Concepts",
    icon: "📝",
    summary: (d) => `${d.concepts.total} page(s)`,
  },
  db: {
    label: "Database",
    icon: "🗄️",
    summary: (d) => {
      const pages = d.db.pages ?? "?";
      return `${pages} page(s) in DB`;
    },
  },
  index: {
    label: "Index",
    icon: "📑",
    summary: (d) => `${d.index.total} entry(ies)`,
  },
  log: {
    label: "Log",
    icon: "📋",
    summary: (d) => `${d.log.total} entry(ies)`,
  },
  graph: {
    label: "Wiki Graph",
    icon: "🔗",
    summary: () => "View graph",
  },
};

function SectionCard({
  section,
  data,
  onSelect,
  isExpanded,
}: {
  section: SectionMeta;
  data: InventoryData;
  onSelect: () => void;
  isExpanded: boolean;
}) {
  return (
    <button
      onClick={onSelect}
      className={`rounded-2xl border p-4 text-left transition ${isExpanded ? "border-primary/30 bg-primary/[0.04]" : "border-border/70 bg-background/70 hover:border-border"} w-full`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{section.icon}</span>
          <h3 className="text-sm font-semibold">{section.label}</h3>
        </div>
        <span className="text-sm font-medium tabular-nums text-muted-foreground">
          {section.summary(data)}
        </span>
      </div>
    </button>
  );
}

function RawQaDetail({ data }: { data: InventoryData["raw_qa"] }) {
  const dates = Object.entries(data.by_date);
  return (
    <div className="space-y-2 rounded-xl border border-border/50 bg-background/50 p-4 text-sm">
      <p className="font-medium">Total files: <span className="tabular-nums">{data.total}</span></p>
      {dates.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">By date</p>
          <div className="space-y-1">
            {dates.map(([date, count]) => (
              <div key={date} className="flex justify-between text-muted-foreground">
                <span>{date}</span>
                <span className="tabular-nums">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConceptsDetail({ data }: { data: InventoryData["concepts"] }) {
  return (
    <div className="space-y-2 rounded-xl border border-border/50 bg-background/50 p-4 text-sm">
      <p className="font-medium">Total pages: <span className="tabular-nums">{data.total}</span></p>
      {data.files.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Files</p>
          <div className="space-y-1">
            {data.files.map((f) => (
              <div key={f.name} className="flex justify-between text-muted-foreground">
                <span className="truncate">{f.name}</span>
                <span className="shrink-0 tabular-nums">{f.size}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DbDetail({ data }: { data: InventoryData["db"] }) {
  const mainTables = [
    { key: "pages", label: "Pages" },
    { key: "qa_pairs", label: "QA Pairs" },
    { key: "wiki_links", label: "Wiki Links" },
  ] as const;
  const allEntries = Object.entries(data.all_tables ?? {}).filter(
    ([k]) => !["pages", "qa_pairs", "wiki_links"].includes(k),
  );
  return (
    <div className="space-y-3 rounded-xl border border-border/50 bg-background/50 p-4 text-sm">
      <div className="space-y-1">
        {mainTables.map(({ key, label }) => (
          <div key={key} className="flex justify-between text-muted-foreground">
            <span>{label}</span>
            <span className="tabular-nums">{data[key]}</span>
          </div>
        ))}
      </div>
      {allEntries.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-muted-foreground group-open:text-foreground">
            All tables ({allEntries.length} more)
          </summary>
          <div className="mt-2 space-y-1">
            {allEntries.map(([table, count]) => (
              <div key={table} className="flex justify-between text-xs text-muted-foreground">
                <span className="truncate">{table}</span>
                <span className="shrink-0 tabular-nums">{count}</span>
              </div>
            ))}
          </div>
        </details>
      )}
      {data.db_size && (
        <p className="pt-1 text-xs text-muted-foreground">DB file size: {data.db_size}</p>
      )}
    </div>
  );
}

function IndexLogDetail({
  data,
  label,
}: {
  data: InventoryData["index"] | InventoryData["log"];
  label: string;
}) {
  return (
    <div className="space-y-2 rounded-xl border border-border/50 bg-background/50 p-4 text-sm">
      <p className="font-medium">
        {label} entries: <span className="tabular-nums">{data.total}</span>
      </p>
      <p className="text-xs text-muted-foreground">
        File lines: <span className="tabular-nums">{data.file_lines}</span>
        {data.size && <> &middot; Size: {data.size}</>}
      </p>
    </div>
  );
}

export function InventoryPanel() {
  const [data, setData] = useState<InventoryData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSection, setExpandedSection] = useState<SectionKey | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchInventory()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function toggleSection(key: SectionKey) {
    setExpandedSection((prev) => (prev === key ? null : key));
  }

  return (
    <section className="flex min-h-136 flex-col overflow-hidden rounded-3xl border bg-card/90 shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b px-4 py-3">
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-muted-foreground">
            Resource usage
          </p>
          <h2 className="text-lg font-semibold leading-none">Inventory</h2>
          <p className="max-w-prose text-sm text-muted-foreground">
            Record counts across all data stores — raw QA files, wiki concepts, database, index, and log.
          </p>
        </div>
        {data && (
          <div className="shrink-0 rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
            {data.raw_qa.total + data.concepts.total + data.log.total} total records
          </div>
        )}
      </header>

      {error && (
        <div className="border-b border-destructive/20 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="min-h-0 flex-1 p-4">
        {loading && (
          <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
            Loading inventory...
          </div>
        )}

        {data && (
          <div className="mx-auto max-w-3xl space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(Object.keys(SECTIONS) as SectionKey[]).map((key) => (
                <SectionCard
                  key={key}
                  section={SECTIONS[key]}
                  data={data}
                  onSelect={() => toggleSection(key)}
                  isExpanded={expandedSection === key}
                />
              ))}
            </div>

            {expandedSection && (
              <div className="animate-in fade-in slide-in-from-top-2 duration-200">
                {expandedSection === "raw_qa" && <RawQaDetail data={data.raw_qa} />}
                {expandedSection === "concepts" && <ConceptsDetail data={data.concepts} />}
                {expandedSection === "db" && <DbDetail data={data.db} />}
                {expandedSection === "index" && <IndexLogDetail data={data.index} label="Index" />}
                {expandedSection === "log" && <IndexLogDetail data={data.log} label="Log" />}
                {expandedSection === "graph" && <WikiGraphView />}
              </div>
            )}

            {!expandedSection && (
              <p className="text-center text-xs text-muted-foreground">
                Click a card above for details
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
