# Plan: Wiki Graph View

**Spec**: `docs/superpowers/specs/2026-05-28-wiki-graph-view-design.md`
**Estimate**: 1-2 days

---

## Overview

Add an Obsidian-style force-directed graph view as a 5th widget in the dashboard sidebar. Uses D3 for force layout + SVG rendering. Reads graph data from existing SQLite `wiki_links` + `pages` tables via a new `GET /api/wiki/graph` endpoint.

Note: `server/pipeline/wiki_graph.py` already exists with `extract_wikilink_targets()`, `sync_outbound_links()`, and `recompute_inbound_counts()` — the backend only needs a new read endpoint.

---

## Files Changed / Created

| Action | File | Why |
|--------|------|-----|
| Modify | `server/main.py` | Add `GET /api/wiki/graph` route |
| Create | `server/services/wiki_graph_api.py` | Query SQLite for graph data |
| Modify | `chat-app/package.json` | Add `d3` + `@types/d3` |
| Create | `chat-app/lib/use-wiki-graph.ts` | Fetch hook |
| Create | `chat-app/components/dashboard/ForceGraph.tsx` | D3 SVG rendering |
| Create | `chat-app/components/dashboard/GraphWidget.tsx` | Widget container |
| Modify | `chat-app/components/dashboard/Dashboard.tsx` | Add graph props + 5th widget |
| Modify | `chat-app/app/page.tsx` | Wire graph data |

---

## Step-by-step

### Step 1: Backend — `GET /api/wiki/graph` endpoint

**New file**: `server/services/wiki_graph_api.py`

```python
from server.config.settings import Settings

async def get_wiki_graph(cfg: Settings) -> dict:
    """Query SQLite for nodes + edges from pages + wiki_links tables."""
    db_cfg = cfg.model_copy(update={"db_path": cfg.db_path})
    async with aiosqlite.connect(db_cfg.db_path) as db:
        db.row_factory = aiosqlite.Row

        # Nodes
        cur = await db.execute("""
            SELECT id, title, category, inbound_links
            FROM pages
            WHERE id IS NOT NULL
        """)
        nodes = [dict(r) for r in await cur.fetchall()]

        # Edges
        cur = await db.execute("""
            SELECT from_page AS source, to_page AS target
            FROM wiki_links
        """)
        edges = [dict(r) for r in await cur.fetchall()]

    return {"nodes": nodes, "edges": edges}
```

**Modify**: `server/main.py` — add route:

```python
@app.get("/wiki/graph")
async def get_wiki_graph():
    """Return nodes + edges for the wiki graph view."""
    data = await wiki_graph_api.get_wiki_graph(cfg)
    return data
```

**Verify**: `curl http://localhost:8000/wiki/graph` returns valid JSON with `nodes` and `edges` arrays.

---

### Step 2: Frontend — install D3

```bash
cd chat-app && npm install d3 && npm install -D @types/d3
```

**Verify**: `package.json` shows `d3` in dependencies.

---

### Step 3: Frontend — `use-wiki-graph` hook

**Create**: `chat-app/lib/use-wiki-graph.ts`

```typescript
"use client";

import { useState, useEffect, useCallback } from "react";

export interface GraphNode {
  id: string;
  title: string;
  category: string;
  inbound_links: number;
}

export interface GraphEdge {
  source: string;
  target: string;
}

interface UseWikiGraphReturn {
  nodes: GraphNode[];
  edges: GraphEdge[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useWikiGraph(): UseWikiGraphReturn {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/wiki/graph");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setNodes(data.nodes ?? []);
      setEdges(data.edges ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  return { nodes, edges, loading, error, refresh: fetchGraph };
}
```

**Verify**: Clean TypeScript compilation.

---

### Step 4: Frontend — `ForceGraph.tsx` (core D3 rendering)

**Create**: `chat-app/components/dashboard/ForceGraph.tsx`

This is the most complex piece. Key structure:

```typescript
"use client";

import { useRef, useEffect } from "react";
import * as d3 from "d3";

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  category: string;
  radius: number;
}

interface GraphEdge extends d3.SimulationLinkDatum<GraphNode> {
  weight?: number;
}

interface ForceGraphProps {
  nodes: (Omit<GraphNode, "x" | "y" | "vx" | "vy">)[];
  edges: GraphEdge[];
  compact: boolean;
  onNodeClick: (pageId: string) => void;
  selectedNodeId?: string;
}

export function ForceGraph({ nodes, edges, compact, onNodeClick, selectedNodeId }: ForceGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight || (compact ? 180 : 400);

    // Colors by category
    const colorMap: Record<string, string> = {
      concepts: "#7c9082",
      tools: "#ced4bf",
      models: "#bfc9bb",
      frameworks: "#e8e6e1",
      workflows: "#5a8a6a",
      frontend: "#d4a84b",
      python: "#5b8cc9",
      prompting: "#c95b7a",
      "image-gen": "#5bc9b8",
      "vibe-coding": "#8b6bc9",
      _meta: "#9ca3af",
    };

    // Node radius: proportional to inbound_links
    const radiusScale = d3.scaleSqrt()
      .domain([0, d3.max(nodes, n => n.inbound_links) || 1])
      .range(compact ? [3, 8] : [4, 16]);

    const simulation = d3.forceSimulation(nodes as GraphNode[])
      .force("link", d3.forceLink(edges).id(d => (d as GraphNode).id).distance(80))
      .force("charge", d3.forceManyBody().strength(-150))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(d => (d as GraphNode).radius + 5))
      .alphaDecay(0.02);

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g");

    // Zoom
    svg.call(d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => g.attr("transform", event.transform))
    );

    // Edges
    const link = g.append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", "#e8e6e1")
      .attr("stroke-width", 1);

    // Nodes
    const node = g.append("g")
      .selectAll("circle")
      .data(nodes as GraphNode[])
      .join("circle")
      .attr("r", d => radiusScale(d.inbound_links || 1))
      .attr("fill", d => colorMap[d.category] || "#9ca3af")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer")
      .on("click", (_event, d) => onNodeClick(d.id))
      .on("mouseenter", function() { d3.select(this).attr("stroke-width", 3); })
      .on("mouseleave", function() { d3.select(this).attr("stroke-width", 1.5); })
      .call(d3.drag<SVGCircleElement, GraphNode>()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          // Keep pinned where dropped
        })
      );

    // Labels (expanded mode or hover)
    if (!compact) {
      node.append("title").text(d => d.id);
      // Optional: add text labels for larger nodes
    }

    // Tick
    simulation.on("tick", () => {
      link
        .attr("x1", d => (d.source as GraphNode).x!)
        .attr("y1", d => (d.source as GraphNode).y!)
        .attr("x2", d => (d.target as GraphNode).x!)
        .attr("y2", d => (d.target as GraphNode).y!);
      node
        .attr("cx", d => d.x!)
        .attr("cy", d => d.y!);
    });

    return () => simulation.stop();
  }, [nodes, edges, compact, onNodeClick, selectedNodeId]);

  if (nodes.length === 0) return null;

  return (
    <svg ref={svgRef} className="w-full h-full" />
  );
}
```

(Approximate — full implementation will handle edge cases, labels, hover tooltips, highlight on select.)

**Verify**: Graph renders with nodes and edges, force simulation runs smoothly.

---

### Step 5: Frontend — `GraphWidget.tsx`

**Create**: `chat-app/components/dashboard/GraphWidget.tsx`

```typescript
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

export function GraphWidget({ nodes, edges, loading, error, onNodeClick, onRefresh }: GraphWidgetProps) {
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
        <div className="text-xs text-destructive">Could not load graph</div>
        <button onClick={onRefresh} className="text-xs text-primary hover:underline mt-1">Retry</button>
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
      className={expanded ? "min-h-[400px]" : ""}
    >
      <div className="flex justify-end gap-1 pb-1">
        <button onClick={onRefresh} className="text-xs text-muted-foreground hover:text-foreground" title="Refresh">🔄</button>
        <button onClick={() => setExpanded(!expanded)} className="text-xs text-muted-foreground hover:text-foreground" title={expanded ? "Collapse" : "Expand"}>
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
```

**Verify**: Widget renders in all states (loading, error, empty, populated).

---

### Step 6: Wire into Dashboard + page.tsx

**Modify**: `chat-app/components/dashboard/Dashboard.tsx`

Add:
- New props: `graphNodes`, `graphEdges`, `graphLoading`, `graphError`, `onGraphRefresh`
- Import `GraphWidget`
- Render as 5th section after `SystemStatusWidget`

**Modify**: `chat-app/app/page.tsx`

Add:
- Import `useWikiGraph` hook
- Call `const graph = useWikiGraph();`
- Pass graph data to `<Dashboard>`

---

## Verification Checklist

After all steps:

- `curl -s http://localhost:8000/wiki/graph` returns valid JSON with `nodes[]` and `edges[]`
- `cd chat-app && npm run build` exits 0
- `npm run dev` → browser:
  - [ ] Graph widget renders in dashboard as 5th section
  - [ ] Loading state shows pulsing placeholder
  - [ ] Empty state shows message when no pages exist
  - [ ] Error state shows retry button
  - [ ] Populated: nodes render as colored circles, edges as lines
  - [ ] Clicking a node opens WikiPagePreview
  - [ ] Compact mode (~112px) vs expanded mode (~320px) via toggle
  - [ ] Drag a node → pins to position
  - [ ] Zoom in/out via scroll
  - [ ] Pan via drag on empty space
  - [ ] Double-click resets zoom
  - [ ] Hover highlights node
  - [ ] No console errors
