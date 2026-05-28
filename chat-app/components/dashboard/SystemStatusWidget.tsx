import { Widget } from "./Widget";

interface SystemEntry {
  label: string;
  status: "connected" | "disconnected" | "warning";
  detail?: string;
}

interface SystemStatusWidgetProps {
  entries: SystemEntry[];
}

const dotColors: Record<SystemEntry["status"], string> = {
  connected: "bg-green-500",
  disconnected: "bg-red-500",
  warning: "bg-amber-500",
};

export function SystemStatusWidget({ entries }: SystemStatusWidgetProps) {
  return (
    <Widget title="System" icon="⚙️">
      {entries.length === 0 ? (
        <p className="text-xs text-muted-foreground">No system info.</p>
      ) : (
        entries.map((e) => (
          <div key={e.label} className="flex items-center gap-2 text-sm">
            <span
              className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColors[e.status]}`}
            />
            <span>{e.label}</span>
            {e.detail && (
              <span className="text-xs text-muted-foreground ml-auto">
                {e.detail}
              </span>
            )}
          </div>
        ))
      )}
    </Widget>
  );
}
