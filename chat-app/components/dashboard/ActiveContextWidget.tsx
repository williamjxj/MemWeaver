import { Widget } from "./Widget";

interface ActiveContextWidgetProps {
  pages: Array<{
    id: string;
    label: string;
    detail?: string;
  }>;
}

export function ActiveContextWidget({ pages }: ActiveContextWidgetProps) {
  return (
    <Widget title="Active Context" icon="📋">
      {pages.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No active wiki page yet. Ask a question to load context.
        </p>
      ) : (
        pages.map((p) => (
          <div key={p.id} className="space-y-0.5">
            <div className="flex items-center gap-2 text-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
              <span className="truncate font-medium">{p.label}</span>
            </div>
            {p.detail && (
              <div className="pl-3.5 text-xs text-muted-foreground truncate">
                {p.detail}
              </div>
            )}
          </div>
        ))
      )}
    </Widget>
  );
}
