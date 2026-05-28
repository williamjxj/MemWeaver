import { Widget } from "./Widget";

interface ActiveContextWidgetProps {
  pages: string[];
}

export function ActiveContextWidget({ pages }: ActiveContextWidgetProps) {
  return (
    <Widget title="Active Context" icon="📋">
      {pages.length === 0 ? (
        <p className="text-xs text-muted-foreground">No context loaded.</p>
      ) : (
        pages.map((p) => (
          <div key={p} className="flex items-center gap-2 text-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
            <span className="truncate">{p}</span>
          </div>
        ))
      )}
    </Widget>
  );
}
