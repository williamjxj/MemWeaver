# Wiki Graph View / 图谱视图

> Add an Obsidian-style force-directed graph view of wiki pages to the MemWeaver dashboard. Nodes represent wiki pages, edges represent `[[wikilinks]]` between them.
>
> 在 MemWeaver 仪表盘中添加 Obsidian 风格的力导向图谱视图。节点表示 wiki 页面，边表示页面之间的 `[[wikilinks]]` 链接。

**Status**: Approved | **Priority**: Medium | **Estimate**: 1-2 days

---

## 1. Motivation / 动机

The Wiki Tree widget shows a hierarchical view of pages, but it doesn't reveal the **relationship structure** — which pages are most connected, which clusters of knowledge exist, and how concepts relate. A force-directed graph gives an intuitive, explorable overview of the wiki's knowledge topology.

## 2. Approach / 方案

**D3 Force Graph (Approach A)** — `d3-force` for layout simulation, SVG for rendering. Renders as a 5th collapsible section in the dashboard sidebar.

## 3. Data Flow / 数据流

### Backend: `GET /api/wiki/graph`

**New file**: `server/services/wiki_graph.py`

Scans the wiki directory, parses `[[...]]` wikilinks from each markdown file, returns:

```json
{
  "nodes": [
    {
      "id": "rag",
      "label": "RAG",
      "category": "concepts",
      "inbound_links": 5,
      "outbound_links": 3
    }
  ],
  "edges": [
    { "source": "rag", "target": "embeddings", "weight": 1 }
  ]
}
```

**Endpoint**: Add to `server/main.py` as a new route.

**Edge weight**: Number of `[[...]]` references from source to target (can be >1 if mentioned multiple times).

**Caching**: Graph data is cheap to compute — cache in memory for 5 minutes, invalidate on ingest.

### Frontend Data Flow

```
page.tsx
  └── useWikiGraph() hook           ← fetches /api/wiki/graph, returns { nodes, edges, loading }
        └── Dashboard
              └── GraphWidget        ← container, compact/expanded states
                    └── ForceGraph   ← pure D3 SVG rendering
```

`useWikiGraph` fetches on mount. No polling — user can click a "Refresh" button in the widget header.

### Fallback (if backend endpoint isn't ready)

A lightweight client-side fallback: fetch wiki index, scan for `[[...]]` patterns in page content via `GET /api/wiki/{slug}`, build graph in-browser. This handles the MVP case.

## 4. File Structure / 文件结构

```
chat-app/
├── components/
│   └── dashboard/
│       ├── GraphWidget.tsx          ← Widget wrapper (new)
│       └── ForceGraph.tsx           ← D3 SVG rendering (new)
├── lib/
│   └── use-wiki-graph.ts           ← Fetch hook (new)
server/
├── main.py                          ← Add /api/wiki/graph route
└── services/
    └── wiki_graph.py               ← Graph data builder (new)
```

## 5. Component Specifications / 组件规格

### 5.1 `ForceGraph.tsx` — Core Rendering

Pure D3 component — no React state, fully controlled via props + ref.

```typescript
interface ForceGraphProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  compact: boolean          // compact = ~200px widget, expanded = fills panel
  onNodeClick: (pageId: string) => void
  selectedNodeId?: string  // highlight a specific node
}
```

**Rendering pipeline**:

1. On mount — create SVG container with `<g>` for zoom/pan
2. On data change — join data to D3 selection, run force simulation
3. Force tick → update node `cx`/`cy` and edge `x1`/`y1`/`x2`/`y2`
4. On simulation end (alpha=0) — free positions, keep rendering

**Node rendering**:
- SVG `<circle>` with fill = category color
- SVG `<text>` label (positioned below circle)
- Radius = proportional to `inbound_links` (clamped: 4–12px normal, 3–8px compact)

**Edge rendering**:
- SVG `<line>` with stroke `#e8e6e1`, `stroke-width=1`
- On hover neighbor: highlight connected nodes + edges

**Interactions**:
- `d3-zoom` on the SVG root — zoom range 0.1x–4x
- Click node → `onNodeClick(id)`
- Drag node (via `force.drag`) — node stays where dropped, pins it
- Double-click background → reset zoom

**Empty state**: Single centered message "Ask a question to build your wiki graph" in muted text.

### 5.2 `GraphWidget.tsx` — Dashboard Widget

```typescript
interface GraphWidgetProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  loading: boolean
  error: string | null
  onNodeClick: (pageId: string) => void
  onRefresh: () => void
}
```

**Layout**:
```
┌────────────────────────────────┐
│ 🌐 Graph View          🔄 [⛶] │  ← title, refresh button, expand toggle
│                                │
│    [ForceGraph compact]        │  ← compact: ~200px height
│                                │
└────────────────────────────────┘
```

**Compact mode** (default): Shows a miniature force graph. Clicking expand toggles the dashboard to a graph-focused view (panel scrolls to show full-height graph).

**Loading state**: Skeleton placeholder — grey pulsing circles in a rough graph shape.

**Error state**: "Could not load graph" with a retry button.

**Empty state**: "Your wiki graph will appear here as pages are created."

### 5.3 `use-wiki-graph.ts` — Data Hook

```typescript
function useWikiGraph() {
  return {
    nodes: GraphNode[]
    edges: GraphEdge[]
    loading: boolean
    error: string | null
    refresh: () => void
  }
}
```

- Fetches `GET /api/wiki/graph` on mount
- Sets `loading = true` during fetch
- Catches errors → sets `error` string
- `refresh()` re-fetches

### 5.4 Backend: `wiki_graph.py`

```python
def build_wiki_graph(wiki_dir: str) -> dict:
    """Walk wiki/ directory, parse [[links]] from each .md file"""
    nodes = {}      # id -> Node
    edges = []      # list of {source, target, weight}

    for md_file in wiki_dir.glob("**/*.md"):
        page_id = derive_id(md_file)
        links = extract_wikilinks(md_file.read_text())
        category = md_file.parent.name

        nodes[page_id] = {
            "id": page_id,
            "label": derive_label(md_file),
            "category": category,
            "inbound_links": 0,     # computed in second pass
            "outbound_links": len(links),
        }

        for target in links:
            edges.append({"source": page_id, "target": target, "weight": 1})

    # Second pass: count inbound links
    for edge in edges:
        if edge["target"] in nodes:
            nodes[edge["target"]]["inbound_links"] += 1

    return {"nodes": list(nodes.values()), "edges": edges}
```

**Edge dedup**: Group identical source→target pairs, sum their weight.

### 5.5 Backend Route

Add to `server/main.py`:

```python
@app.get("/wiki/graph", response_model=GraphResponse)
async def get_wiki_graph():
    return build_wiki_graph(WIKI_DIR)
```

## 6. Node Category Colors / 节点颜色

| Category | Color | CSS Variable |
|----------|-------|-------------|
| concepts | Sage green | `--primary` `#7c9082` |
| tools | Sage light | `--secondary` `#ced4bf` |
| models | Sage accent | `--accent` `#bfc9bb` |
| frameworks | Muted | `--muted` `#e8e6e1` |
| workflows | Primary green | `#5a8a6a` (derived) |
| frontend | Amber | `#d4a84b` |
| python | Blue | `#5b8cc9` |
| prompting | Rose | `#c95b7a` |
| image-gen | Teal | `#5bc9b8` |
| vibe-coding | Purple | `#8b6bc9` |
| _meta | Grey | `#9ca3af` |

Ungrouped / unknown category → muted grey.

## 7. Rendering Physics / 渲染物理

Force parameters (tunable):

| Force | Value | Effect |
|-------|-------|--------|
| `forceLink` | distance=80, strength=0.5 | Pulls connected nodes together |
| `forceManyBody` | charge=-150 | Repels all nodes (spreads out) |
| `forceCenter` | width/2, height/2 | Centers the graph |
| `forceCollide` | radius=node.r+10 | Prevents overlap |
| `forceY` | strength=0.05 | Gentle vertical stratification by category |
| Alpha decay | 0.02 → settles in ~3s at 60fps | Fast enough to feel responsive |

## 8. Interactions / 交互

| Action | Result |
|--------|--------|
| Click node | Calls `onNodeClick(pageId)` → opens WikiPagePreview in dashboard |
| Hover node | Highlights node (brighter), dims non-connected nodes, shows tooltip with page title |
| Hover edge | Highlights source + target nodes |
| Drag node | Pins node to position (removes from force simulation) |
| Scroll / pinch | Zoom in/out (native trackpad, or Ctrl+scroll) |
| Drag background | Pan the graph |
| Double-click bg | Reset zoom to 1x centered |
| Click empty area | Deselect any highlighted node |

## 9. Dashboard Integration / 仪表盘集成

In `Dashboard.tsx`, the `dashboard` view adds a 5th widget:

```tsx
// After SystemStatusWidget
<GraphWidget
  nodes={graphData.nodes}
  edges={graphData.edges}
  loading={graphData.loading}
  error={graphData.error}
  onNodeClick={onWikiPageSelect}
  onRefresh={graphData.refresh}
/>
```

`page.tsx` passes `graphData` through `Dashboard` props:

```tsx
const graph = useWikiGraph();

<Dashboard
  ...
  graphData={graph}
/>
```

## 10. Implementation Order / 实施顺序

| Step | Files | Description | Effort |
|------|-------|-------------|--------|
| 1 | `server/services/wiki_graph.py`, `server/main.py` | Backend endpoint: `GET /api/wiki/graph` | Medium |
| 2 | `chat-app/package.json` | Install `d3` + `@types/d3` | Trivial |
| 3 | `chat-app/lib/use-wiki-graph.ts` | Data fetching hook | Small |
| 4 | `chat-app/components/dashboard/ForceGraph.tsx` | D3 SVG rendering (core) | Large |
| 5 | `chat-app/components/dashboard/GraphWidget.tsx` | Widget container + states | Small |
| 6 | `chat-app/components/dashboard/Dashboard.tsx`, `chat-app/app/page.tsx` | Wire into dashboard | Small |
| 7 | — | Visual verification + polish | Medium |

## 11. Out of Scope / 不在此范围

- Graph persistence (node positions across sessions)
- Custom node coloring / filtering by user
- Search within graph (type to find a node)
- Animated transitions between graph states
- Export graph as image
- Mobile responsiveness for the graph widget

## 12. Sources / 来源

- [Current Dashboard.tsx](../chat-app/components/dashboard/Dashboard.tsx)
- [Obsidian Graph View documentation](https://help.obsidian.md/Plugins/Graph+view)
- [D3 Force-Directed Graph examples](https://d3js.org/d3-force)
- [Existing WikiSidebar architecture](file:///Users/william.jiang/my-playgrounds/mem-weaver/chat-app/components/WikiSidebar.tsx) (deleted, but pattern reference)
- [Wiki link convention — LLM_WIKI_SCHEMA.md](../wiki/LLM_WIKI_SCHEMA.md)
