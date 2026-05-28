import { Widget } from "./Widget";

interface HistoryItem {
  id: string;
  query: string;
  timestamp: Date;
}

interface HistoryWidgetProps {
  items: HistoryItem[];
  onRerun: (query: string) => void;
}

export function HistoryWidget({ items, onRerun }: HistoryWidgetProps) {
  return (
    <Widget title="History" icon="🕐">
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">No history yet.</p>
      ) : (
        items.map((item) => (
          <button
            key={item.id}
            onClick={() => onRerun(item.query)}
            className="w-full text-left text-sm truncate hover:text-primary transition-colors cursor-pointer"
          >
            {item.query}
          </button>
        ))
      )}
    </Widget>
  );
}
