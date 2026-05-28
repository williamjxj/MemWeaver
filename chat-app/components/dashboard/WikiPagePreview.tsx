import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface WikiPage {
  id: string;
  title: string;
  content: string;
  tags?: string[];
  sources?: string[];
}

interface WikiPagePreviewProps {
  page: WikiPage;
  onBack: () => void;
}

export function WikiPagePreview({ page, onBack }: WikiPagePreviewProps) {
  return (
    <div className="h-full flex flex-col">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-xs text-primary hover:underline px-3 py-2 shrink-0"
      >
        ← Back to Dashboard
      </button>
      <div className="flex-1 overflow-y-auto px-3 pb-4 prose prose-xs max-w-none">
        <h2 className="text-sm font-semibold mb-2">{page.title}</h2>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {page.content}
        </ReactMarkdown>
        {page.tags && page.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {page.tags.map((t) => (
              <span
                key={t}
                className="text-xs bg-secondary text-secondary-foreground px-1.5 py-0.5 rounded"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
