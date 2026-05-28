import type { ReactNode } from "react";

interface WidgetProps {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Widget({ title, icon, children, className = "" }: WidgetProps) {
  return (
    <div className={`rounded-lg border bg-card text-card-foreground shadow-xs ${className}`}>
      <div className="flex items-center gap-2 px-3 py-2 border-b">
        {icon && <span className="text-xs">{icon}</span>}
        <h3 className="text-xs font-semibold uppercase tracking-wider text-primary">
          {title}
        </h3>
      </div>
      <div className="px-3 py-2 space-y-1 text-sm">{children}</div>
    </div>
  );
}
