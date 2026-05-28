"use client";

import { useState } from "react";
import { Widget } from "./Widget";
import { ForceGraph } from "./ForceGraph";
import type { GraphNode, GraphEdge } from "@/lib/use-wiki-graph";

interface GraphWidgetProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  loading: boolean;
  error: string | null;
  onNodeClick: (pageId: string) => void;
  onRefresh: () => void;
}

export function GraphWidget({
  nodes,
  edges,
  loading,
  error,
  onNodeClick,
  onRefresh,
}: GraphWidgetProps) {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <Widget title="Graph View" icon="🌐">
        <div className="flex items-center justify-center h-24 text-xs text-muted-foreground animate-pulse">
          Loading graph...
        </div>
      </Widget>
    );
  }

  if (error) {
    return (
      <Widget title="Graph View" icon="🌐">
        <div className="text-xs text-destructive mb-1">Could not load graph</div>
        <button
          onClick={onRefresh}
          className="text-xs text-primary hover:underline"
        >
          Retry
        </button>
      </Widget>
    );
  }

  if (nodes.length === 0) {
    return (
      <Widget title="Graph View" icon="🌐">
        <p className="text-xs text-muted-foreground text-center py-4">
          Your wiki graph will appear here as pages are created.
        </p>
      </Widget>
    );
  }

  return (
    <Widget
      title="Graph View"
      icon="🌐"
      className={expanded ? "" : ""}
    >
      <div className="flex justify-end gap-2 pb-1">
        <button
          onClick={onRefresh}
          className="text-xs text-muted-foreground hover:text-foreground"
          title="Refresh"
        >
          ↻
        </button>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-muted-foreground hover:text-foreground"
          title={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? "⛶" : "⛶"}
        </button>
      </div>
      <div className={expanded ? "h-80" : "h-28"}>
        <ForceGraph
          nodes={nodes}
          edges={edges}
          compact={!expanded}
          onNodeClick={onNodeClick}
        />
      </div>
    </Widget>
  );
}
