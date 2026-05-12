"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { TopicBadge } from "./TopicBadge";

interface WikiSidebarProps {
  slug: string | null;
  topic: string;
  wikiContent: string;
  onFetchContent: (slug: string) => Promise<string>;
}

export function WikiSidebar({
  slug,
  topic,
  wikiContent,
  onFetchContent,
}: WikiSidebarProps) {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    onFetchContent(slug).finally(() => setLoading(false));
  }, [slug, onFetchContent]);

  return (
    <aside className="w-80 border-l bg-gray-50 flex flex-col h-full">
      <div className="p-4 border-b bg-white shrink-0">
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
          Active context
        </p>
        <p className="text-sm font-mono text-blue-700 truncate">
          {slug ?? "none"}
        </p>
        {topic && (
          <div className="mt-1">
            <TopicBadge topic={topic} />
          </div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-xs text-gray-400">Loading...</div>
        ) : wikiContent ? (
          <div className="prose prose-xs max-w-none text-xs text-gray-700">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {wikiContent}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="text-xs text-gray-400">No wiki context loaded.</p>
        )}
      </div>
    </aside>
  );
}
