# Plan: MemWeaver UI Redesign

**Spec**: `docs/superpowers/specs/2026-05-28-memweaver-ui-redesign.md`
**Branch**: `ui-redesign-sage-garden`
**Estimate**: 2-3 days

---

## Overview

Replace the current 2-column layout (ChatWindow bottom-input + sparse WikiSidebar) with:
- Input bar at **top** of chat area
- Right panel becomes a **widget-based dashboard** (ActiveContext, History, WikiTree → preview, SystemStatus)
- **Sage Garden** theme colors throughout
- **SVG logo + favicon**

---

## Files Changed / Created

| Action | File | Why |
|--------|------|-----|
| Modify | `chat-app/app/globals.css` | Sage Garden CSS variables |
| Create | `chat-app/public/logo.svg` | SVG logo |
| Create | `chat-app/public/favicon.svg` | SVG favicon |
| Modify | `chat-app/app/layout.tsx` | Favicon metadata, title |
| Modify | `chat-app/components/ChatWindow.tsx` | Input bar → top |
| Modify | `chat-app/components/MessageBubble.tsx` | Theme colors (sage) |
| Create | `chat-app/components/dashboard/Widget.tsx` | Generic card wrapper |
| Create | `chat-app/components/dashboard/Dashboard.tsx` | Container w/ view switching |
| Create | `chat-app/components/dashboard/ActiveContextWidget.tsx` | Active wiki pages |
| Create | `chat-app/components/dashboard/HistoryWidget.tsx` | Recent queries |
| Create | `chat-app/components/dashboard/WikiTreeWidget.tsx` | Wiki tree navigation |
| Create | `chat-app/components/dashboard/WikiPagePreview.tsx` | Wiki page preview |
| Create | `chat-app/components/dashboard/SystemStatusWidget.tsx` | Live service status |
| Delete | `chat-app/components/WikiSidebar.tsx` | Replaced by Dashboard |
| Modify | `chat-app/app/page.tsx` | Wire Dashboard, new state, remove WikiSidebar import |

---

## Step-by-step

### Step 1: Theme — Sage Garden CSS variables

**File**: `chat-app/app/globals.css`

Replace the `:root` block oklch values with Sage Garden HSL values. Add `.dark` block.

**Current**:
```css
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  /* ... more oklch values */
}
```

**After**:
```css
:root {
  --background: 45 20% 97%;
  --foreground: 222 25% 14%;
  --card: 45 20% 97%;
  --card-foreground: 222 25% 14%;
  --primary: 155 12% 48%;
  --primary-foreground: 0 0% 100%;
  --secondary: 113 15% 79%;
  --secondary-foreground: 222 25% 14%;
  --muted: 45 15% 89%;
  --muted-foreground: 215 10% 56%;
  --accent: 113 15% 76%;
  --accent-foreground: 222 25% 14%;
  --destructive: 0 72% 51%;
  --border: 45 10% 85%;
  --input: 45 10% 85%;
  --ring: 155 12% 48%;
  --radius: 0.75rem;
}

.dark {
  --background: 0 0% 4%;
  --foreground: 0 0% 95%;
  --card: 0 0% 6%;
  --popover: 0 0% 6%;
  --primary: 155 12% 55%;
  --primary-foreground: 0 0% 5%;
  --secondary: 113 10% 30%;
  --secondary-foreground: 0 0% 95%;
  --muted: 0 0% 9%;
  --muted-foreground: 0 0% 50%;
  --accent: 155 8% 20%;
  --accent-foreground: 0 0% 95%;
  --border: 0 0% 12%;
  --ring: 155 12% 48%;
}
```

**Verify**: `lsp_diagnostics` on globals.css — clean.

---

### Step 2: SVG assets — logo + favicon

**Create**: `chat-app/public/logo.svg`
**Create**: `chat-app/public/favicon.svg`

Three-layer mountain/stack icon in sage green:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <path d="M16 4L4 14l12 10L28 14 16 4z" stroke="#7c9082" stroke-width="2"/>
  <path d="M16 10l-8 6 8 6 8-6-8-6z" stroke="#7c9082" stroke-width="2"/>
  <path d="M16 16l-4 3 4 3 4-3-4-3z" stroke="#7c9082" stroke-width="2"/>
</svg>
```

Favicon is same SVG with `viewBox="0 0 32 32"` but scaled down.

**Verify**: Files exist at correct paths.

---

### Step 3: Metadata — layout.tsx

**File**: `chat-app/app/layout.tsx`

Changes:
- Update `title` to `"MemWeaver"`
- Add `icons` metadata with favicon reference
- Add `themeColor` for browser chrome

```typescript
export const metadata: Metadata = {
  title: "MemWeaver",
  description: "Chat with wiki-memory augmented LLM",
  icons: [{ rel: "icon", url: "/favicon.svg" }],
};
```

**Verify**: `lsp_diagnostics` on layout.tsx — clean.

---

### Step 4: ChatWindow — move input to top

**File**: `chat-app/components/ChatWindow.tsx`

Restructure the flex layout:

```tsx
// Current: messages fill space, input is at bottom
<div className="flex flex-col h-full">
  <div className="flex-1 overflow-y-auto ...">  {/* messages */}
  <div className="border-t p-4">                 {/* input bar */}

// After: input at top, messages below
<div className="flex flex-col h-full">
  <div className="border-b p-4 shrink-0">          {/* input bar */}
  <div className="flex-1 overflow-y-auto ...">      {/* messages */}
```

The input bar rendering stays identical — only its container position changes. The flex layout naturally handles the rest.

**Verify**:
- Input renders at top of the chat column
- Messages render below with scroll
- Auto-scroll still works (bottomRef at bottom of messages)

---

### Step 5: MessageBubble — sage theme colors

**File**: `chat-app/components/MessageBubble.tsx`

| Before | After |
|---|---|
| User: `bg-blue-600 text-white` | User: `bg-primary text-primary-foreground` |
| Assistant: `bg-gray-100 text-gray-900` | Assistant: `bg-muted text-foreground` |

```diff
- "bg-blue-600 text-white"
+ "bg-primary text-primary-foreground"

- "bg-gray-100 text-gray-900"
+ "bg-muted text-foreground"
```

**Verify**: `lsp_diagnostics` on MessageBubble.tsx — clean.

---

### Step 6: Widget card wrapper

**Create**: `chat-app/components/dashboard/Widget.tsx`

```tsx
interface WidgetProps {
  title: string
  icon?: React.ReactNode
  children: React.ReactNode
  className?: string
}

export function Widget({ title, icon, children, className = "" }: WidgetProps) {
  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-xs">
      <div className="flex items-center gap-2 px-3 py-2 border-b">
        {icon && <span className="text-xs">{icon}</span>}
        <h3 className="text-xs font-semibold uppercase tracking-wider text-primary">
          {title}
        </h3>
      </div>
      <div className="px-3 py-2 space-y-1 text-sm">
        {children}
      </div>
    </div>
  )
}
```

**Verify**: `lsp_diagnostics` clean, no type errors.

---

### Step 7: ActiveContextWidget

**Create**: `chat-app/components/dashboard/ActiveContextWidget.tsx`

```tsx
interface ActiveContextWidgetProps {
  pages: string[]
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
  )
}
```

**Verify**: Clean compilation.

---

### Step 8: SystemStatusWidget

**Create**: `chat-app/components/dashboard/SystemStatusWidget.tsx`

```tsx
interface SystemEntry {
  label: string
  status: "connected" | "disconnected" | "warning"
  detail?: string
}

interface SystemStatusWidgetProps {
  entries: SystemEntry[]
}

const dotColors: Record<SystemEntry["status"], string> = {
  connected: "bg-green-500",
  disconnected: "bg-red-500",
  warning: "bg-amber-500",
}

export function SystemStatusWidget({ entries }: SystemStatusWidgetProps) {
  return (
    <Widget title="System" icon="⚙️">
      {entries.map((e) => (
        <div key={e.label} className="flex items-center gap-2 text-sm">
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColors[e.status]}`} />
          <span>{e.label}</span>
          {e.detail && (
            <span className="text-xs text-muted-foreground ml-auto">{e.detail}</span>
          )}
        </div>
      ))}
    </Widget>
  )
}
```

**Verify**: Clean compilation.

---

### Step 9: HistoryWidget

**Create**: `chat-app/components/dashboard/HistoryWidget.tsx`

```tsx
interface HistoryItem {
  id: string
  query: string
  timestamp: Date
}

interface HistoryWidgetProps {
  items: HistoryItem[]
  onRerun: (query: string) => void
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
  )
}
```

**Verify**: Clean compilation.

---

### Step 10: WikiTreeWidget

**Create**: `chat-app/components/dashboard/WikiTreeWidget.tsx`

```tsx
interface TreeNode {
  id: string
  label: string
  type: "folder" | "page"
  children?: TreeNode[]
}

interface WikiTreeWidgetProps {
  tree: TreeNode[]
  onSelect: (pageId: string) => void
}

export function WikiTreeWidget({ tree, onSelect }: WikiTreeWidgetProps) {
  // Recursive rendering: folders indented + expandable inline,
  // pages call onSelect on click
  return (
    <Widget title="Wiki Tree" icon="🌳">
      {tree.length === 0 ? (
        <p className="text-xs text-muted-foreground">No wiki pages.</p>
      ) : (
        <WikiTreeNodes nodes={tree} depth={0} onSelect={onSelect} />
      )}
    </Widget>
  )
}

// Internal recursive component
function WikiTreeNodes({ nodes, depth, onSelect }: {
  nodes: TreeNode[]
  depth: number
  onSelect: (id: string) => void
}) {
  // Each folder: toggle open/closed, render children indented
  // Each page: clickable button calling onSelect
}
```

Internal state: expanded folder paths (Set of IDs). Clicking a folder toggles its expansion. Clicking a page calls `onSelect(pageId)` which triggers the Dashboard to swap to preview mode.

**Verify**: Clean compilation, recursion handles nesting without overflow.

---

### Step 11: WikiPagePreview

**Create**: `chat-app/components/dashboard/WikiPagePreview.tsx`

```tsx
interface WikiPage {
  id: string
  title: string
  content: string
  tags?: string[]
  sources?: string[]
}

interface WikiPagePreviewProps {
  page: WikiPage
  onBack: () => void
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
        <h2 className="text-sm font-semibold">{page.title}</h2>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {page.content}
        </ReactMarkdown>
        {page.tags && page.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {page.tags.map((t) => (
              <span key={t} className="text-xs bg-secondary px-1.5 py-0.5 rounded">{t}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

**Verify**: Renders markdown correctly via react-markdown (already a dependency).

---

### Step 12: Dashboard container

**Create**: `chat-app/components/dashboard/Dashboard.tsx`

```tsx
type DashboardView = "dashboard" | "preview"

interface DashboardProps {
  view: DashboardView
  activeContext: string[]
  history: HistoryItem[]
  wikiTree: TreeNode[]
  systemStatus: SystemEntry[]
  selectedPage: WikiPage | null
  onHistoryRerun: (query: string) => void
  onWikiPageSelect: (pageId: string) => void
  onBackToDashboard: () => void
}

export function Dashboard(props: DashboardProps) {
  if (props.view === "preview" && props.selectedPage) {
    return (
      <aside className="w-72 border-l bg-card flex flex-col h-full">
        <WikiPagePreview page={props.selectedPage} onBack={props.onBackToDashboard} />
      </aside>
    )
  }

  return (
    <aside className="w-72 border-l bg-card flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <ActiveContextWidget pages={props.activeContext} />
        <HistoryWidget items={props.history} onRerun={props.onHistoryRerun} />
        <WikiTreeWidget tree={props.wikiTree} onSelect={props.onWikiPageSelect} />
        <SystemStatusWidget entries={props.systemStatus} />
      </div>
    </aside>
  )
}
```

**Verify**: Clean compilation, correct prop types.

---

### Step 13: Wire page.tsx

**File**: `chat-app/app/page.tsx`

Changes:
1. Replace `import { WikiSidebar }` with `import { Dashboard }`
2. Add new state:
   - `dashboardView: "dashboard" | "preview"`
   - `selectedPage`
   - `history` (initialized from localStorage)
   - `wikiTree`
   - `systemStatus`
3. Add state handlers
4. Replace `<WikiSidebar>` with `<Dashboard>`

**New state block**:
```typescript
const [dashboardView, setDashboardView] = useState<"dashboard" | "preview">("dashboard");
const [selectedPage, setSelectedPage] = useState<WikiPage | null>(null);
const [history, setHistory] = useState<HistoryItem[]>(() => {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("memweaver-history");
    return saved ? JSON.parse(saved) : [];
  }
  return [];
});
const [wikiTree, setWikiTree] = useState<TreeNode[]>([]);
const [systemStatus, setSystemStatus] = useState<SystemEntry[]>([
  { label: "Ollama", status: "connected" },
  { label: "SQLite", status: "connected", detail: "247 pages" },
  { label: "Embedder", status: "connected", detail: "nomic-embed-text" },
]);
```

**New handlers**:
- `handleHistoryRerun(query)` → calls `handleSend(query)`
- `handleWikiPageSelect(pageId)` → fetches page content, sets selectedPage + dashboardView = "preview"
- `handleBackToDashboard()` → sets dashboardView = "dashboard"
- `useEffect` on `handleSend` → append to history + persist to localStorage

**JSX change**:
```tsx
return (
  <div className="flex h-full">
    <main className="flex-1 flex flex-col">
      {error && <ErrorBanner ... />}
      <ChatWindow ... />
    </main>
    <Dashboard
      view={dashboardView}
      activeContext={activeSlug ? [activeSlug] : []}
      history={history}
      wikiTree={wikiTree}
      systemStatus={systemStatus}
      selectedPage={selectedPage}
      onHistoryRerun={handleHistoryRerun}
      onWikiPageSelect={handleWikiPageSelect}
      onBackToDashboard={handleBackToDashboard}
    />
  </div>
)
```

**Verify**: `lsp_diagnostics` clean on page.tsx. Build succeeds.

---

### Step 14: Cleanup — remove WikiSidebar

- Delete `chat-app/components/WikiSidebar.tsx`
- Ensure no remaining imports of `WikiSidebar`

**Verify**: `git grep WikiSidebar` returns no results.

---

## Verification Checklist

After each step, run:
- `lsp_diagnostics` on the changed file(s) — must be clean

After all steps complete:
- `cd chat-app && npm run build` — must exit 0
- `cd chat-app && npm run dev` — open browser, verify:
  - [ ] Input bar is at top of chat
  - [ ] Messages render below input
  - [ ] Sage Garden colors are applied (sage green primary, warm off-white bg)
  - [ ] Dashboard shows 4 sections stacked vertically
  - [ ] Active Context reflects current wiki slug
  - [ ] History shows queries (persisted across reload)
  - [ ] Clicking history entry re-runs the query
  - [ ] Wiki Tree items are clickable
  - [ ] Clicking a wiki page opens preview in dashboard
  - [ ] Back button returns to dashboard view
  - [ ] System Status shows connected/disconnected statuses
  - [ ] SVG logo renders in header
  - [ ] Favicon loads
  - [ ] Old WikiSidebar is fully gone (no stale imports)
  - [ ] Mobile: dashboard collapses behind hamburger

---

## Rollback

If anything goes wrong:
```bash
git checkout -- chat-app/app/globals.css
git checkout -- chat-app/app/layout.tsx
git checkout -- chat-app/components/ChatWindow.tsx
git checkout -- chat-app/components/MessageBubble.tsx
git checkout -- chat-app/app/page.tsx
rm -rf chat-app/components/dashboard/
rm -f chat-app/components/WikiSidebar.tsx
rm -f chat-app/public/logo.svg
rm -f chat-app/public/favicon.svg
```
