# MemWeaver UI Redesign / UI 重新设计

> Redesign the MemWeaver chat UI: move input to top, replace right sidebar with a widget-based dashboard panel, and apply the Sage Garden theme. Widget architecture for extensibility.
>
> 将 MemWeaver 聊天界面输入框移至顶部，用可扩展的微件化仪表板替换右侧边栏，并采用 Sage Garden 主题。

**Status**: Approved | **Priority**: High | **Estimate**: 2-3 days

---

## 1. Motivation / 动机

The current layout has the input fixed at the bottom (unusual for AI chat apps) and a sparse right sidebar showing bare wiki content. The goal is a more professional, dashboard-driven interface that surfaces system status, history, wiki navigation, and active context — all in one place.

## 2. Approach / 方案

**Widget Architecture (Approach B)** — each dashboard section is a standalone widget component. A parent `Dashboard` container manages view state (dashboard grid vs. wiki page preview). Widgets are pure presentational components receiving data via props.

## 3. File Structure / 文件结构

```
chat-app/
├── app/
│   ├── page.tsx                   ← 2-column layout (chat | dashboard)
│   ├── globals.css                ← Sage Garden CSS variables
│   └── layout.tsx                 ← SVG favicon
├── components/
│   ├── ChatWindow.tsx             ← Input bar (top) + message list (below)
│   ├── MessageBubble.tsx          ← unchanged
│   └── dashboard/
│       ├── Dashboard.tsx          ← container; manages activeView state
│       ├── Widget.tsx             ← generic wrapper card
│       ├── ActiveContextWidget.tsx
│       ├── HistoryWidget.tsx
│       ├── WikiTreeWidget.tsx     ← click → preview mode
│       ├── WikiPagePreview.tsx    ← replaces widget grid on preview
│       └── SystemStatusWidget.tsx
├── public/
│   ├── logo.svg                   ← mountain/stack SVG
│   └── favicon.svg                ← scaled version
└── lib/
    └── use-wiki-tree.ts           ← custom hook: fetch wiki tree
```

## 4. Component Specifications / 组件规格

### 4.1 `page.tsx` — Top-Level Layout

```
┌──────────────────────────────────────────────────────┐
│ Header: 48px (logo | "MemWeaver" | model badge)      │
├──────────────────────────────┬────────────────────────┤
│                              │  Dashboard (280px)     │
│  Chat Area                   │  ┌──────────────────┐  │
│  ┌─ Input bar (top) ───────┐ │  │ Widget grid or   │  │
│  │ ""                [Ask] │ │  │ page preview      │  │
│  └─────────────────────────┘ │  └──────────────────┘  │
│  ┌─ Messages ──────────────┐ │  (scrollable)         │
│  │ msg user                 │ │                       │
│  │ msg assistant            │ │                       │
│  └─────────────────────────┘ │                       │
│  (scrollable, auto-scroll)  │                       │
└──────────────────────────────┴────────────────────────┘
```

**State owned here:**
- `messages: Message[]` — chat history for current session
- `activeContext: string[]` — wiki pages injected into context
- `history: HistoryItem[]` — persisted + session query history
- `wikiTree: TreeNode[]` — hierarchical page structure
- `systemStatus: SystemEntry[]` — live service statuses
- `dashboardView: 'dashboard' | 'preview'` — current dashboard mode
- `selectedPage: WikiPage | null` — page content when in preview

### 4.2 `ChatWindow.tsx` — Chat Area

| Property | Value |
|---|---|
| Input position | **Top** of the chat area (was: bottom) |
| Input features | Text input + Send button, Enter to send |
| Messages | Scrollable container below input |
| Auto-scroll | Scroll to bottom on new messages |
| System message | Optional first message showing loaded context |

**Layout change from current:**
```
// Before: flex-col with input at bottom
<div class="flex flex-col h-full">
  <MessageList />       ← fills remaining space
  <InputBar />          ← fixed at bottom
</div>

// After: flex-col with input at top
<div class="flex flex-col h-full">
  <InputBar />          ← fixed at top
  <MessageList />       ← fills remaining space, scrollable
</div>
```

### 4.3 `Dashboard.tsx` — Container

**Responsibility**: Renders either the widget grid or `WikiPagePreview` based on `dashboardView`.

```typescript
type DashboardView = 'dashboard' | 'preview'

interface DashboardProps {
  activeContext: string[]
  history: HistoryItem[]
  wikiTree: TreeNode[]
  systemStatus: SystemEntry[]
  onHistoryRerun: (query: string) => void
  onWikiPageSelect: (pageId: string) => void
  selectedPage: WikiPage | null
  dashboardView: DashboardView
  onBackToDashboard: () => void
}
```

**View logic:**
```typescript
if (dashboardView === 'preview' && selectedPage) {
  return <WikiPagePreview page={selectedPage} onBack={onBackToDashboard} />
}
return (
  <div class="flex flex-col gap-1 p-3 overflow-y-auto">
    <ActiveContextWidget pages={activeContext} />
    <HistoryWidget items={history} onRerun={onHistoryRerun} />
    <WikiTreeWidget tree={wikiTree} onSelect={onWikiPageSelect} />
    <SystemStatusWidget entries={systemStatus} />
  </div>
)
```

### 4.4 `Widget.tsx` — Generic Card Wrapper

```typescript
interface WidgetProps {
  title: string
  icon?: React.ReactNode
  children: React.ReactNode
  className?: string
}
```

Renders:
```
┌──────────────────────┐
│ 📋 Active Context    │  ← title bar (sticky within widget)
│ ○ item 1             │  ← children
│ ○ item 2             │
└──────────────────────┘
```

- Background: `hsl(var(--muted))` or transparent
- Border: subtle `1px solid hsl(var(--border))`
- Title: `text-xs uppercase tracking-wider font-semibold text-primary`
- Padding: `p-3` inside

### 4.5 `ActiveContextWidget.tsx`

**Purpose**: Show which wiki pages are currently injected into the LLM context.

```typescript
interface ActiveContextWidgetProps {
  pages: string[]  // e.g. ["deployment-setup", "pgvector-rag"]
}
```

**Display**: Each page as a row with a dot indicator:
- Colored dot (primary green) for actively loaded pages
- Grey dot for referenced but not loaded pages

### 4.6 `HistoryWidget.tsx`

**Purpose**: Show recent queries — both from current session and persisted across sessions.

```typescript
interface HistoryItem {
  id: string
  query: string
  timestamp: Date
  sessionId: string  // to group by session
}

interface HistoryWidgetProps {
  items: HistoryItem[]
  onRerun: (query: string) => void
}
```

**Click behavior**: Clicking an item calls `onRerun(query)` which re-submits the query to the LLM.

**Display**: List of queries truncated to one line. Grouped visually by session (session header with date). Show last 10-20 items.

### 4.7 `WikiTreeWidget.tsx`

**Purpose**: Browse the wiki's hierarchical page structure. Clicking a page navigates to its preview.

```typescript
interface TreeNode {
  id: string
  label: string
  type: 'folder' | 'page'
  children?: TreeNode[]
}

interface WikiTreeWidgetProps {
  tree: TreeNode[]
  onSelect: (pageId: string) => void
}
```

**Display**: Indented tree with folder/page icons. Folders expandable inline. Max depth ~3 levels displayed at once (deeper levels expand on click).

### 4.8 `WikiPagePreview.tsx`

**Purpose**: Full wiki page preview rendered in the dashboard panel (replaces widget grid).

```typescript
interface WikiPagePreviewProps {
  page: WikiPage
  onBack: () => void
}
```

**Display**:
- Back button: "← Back to Dashboard" at top
- Page title (from frontmatter)
- Rendered markdown content
- Tags (from frontmatter)
- Source links
- Scrollable within panel

**Trigger**: Called when user clicks a page in `WikiTreeWidget`.

### 4.9 `SystemStatusWidget.tsx`

**Purpose**: Show live status of connected services.

```typescript
interface SystemEntry {
  label: string
  status: 'connected' | 'disconnected' | 'warning'
  detail?: string  // e.g. "247 pages", "nomic-embed-text"
}

interface SystemStatusWidgetProps {
  entries: SystemEntry[]
}
```

**Display**: Each entry as a row with:
- Status dot: green (connected), amber (warning), red (disconnected)
- Label
- Detail text (muted, smaller)

**Example entries:**
- Ollama: Connected
- SQLite: 247 pages
- pgvector: Active
- Embedder: nomic-embed-text

## 5. Theme — Sage Garden / 主题

### 5.1 CSS Variables

Override in `globals.css`:

```css
:root {
  --background: 45 20% 97%;        /* #f8f7f4 */
  --foreground: 222 25% 14%;       /* #1a1f2e */
  --card: 45 20% 97%;
  --card-foreground: 222 25% 14%;
  --popover: 45 20% 97%;
  --popover-foreground: 222 25% 14%;
  --primary: 155 12% 48%;          /* #7c9082 */
  --primary-foreground: 0 0% 100%; /* white */
  --secondary: 113 15% 79%;        /* #ced4bf */
  --secondary-foreground: 222 25% 14%;
  --muted: 45 15% 89%;             /* #e8e6e1 */
  --muted-foreground: 215 10% 56%;
  --accent: 113 15% 76%;           /* #bfc9bb */
  --accent-foreground: 222 25% 14%;
  --border: 45 10% 85%;
  --ring: 155 12% 48%;
  --radius: 0.75rem;
}

.dark {
  --background: 0 0% 4%;           /* #0a0a0a */
  --foreground: 0 0% 95%;
  --card: 0 0% 6%;
  --card-foreground: 0 0% 95%;
  --popover: 0 0% 6%;
  --popover-foreground: 0 0% 95%;
  --primary: 155 12% 55%;          /* slightly lighter sage */
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

### 5.2 Typography

- Font: system-ui stack (no external fonts needed)
- Heading sizes: same as shadcn defaults (`h1: text-2xl`, `h2: text-xl`, etc.)
- Message text: `text-sm` (14px)
- Widget titles: `text-xs` (12px) uppercase tracking-wider
- Dashboard labels: `text-xs` (12px)

## 6. Logo & Favicon / 标志与图标

### `public/logo.svg`

A layered mountain/stack icon — 3 overlapping chevrons or peaks — in sage green (`#7c9082`).

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <path d="M16 4L4 14l12 10L28 14 16 4z" stroke="#7c9082" stroke-width="2" fill="none"/>
  <path d="M16 10l-8 6 8 6 8-6-8-6z" stroke="#7c9082" stroke-width="2" fill="none"/>
  <path d="M16 16l-4 3 4 3 4-3-4-3z" stroke="#7c9082" stroke-width="2" fill="none"/>
</svg>
```

### `public/favicon.svg`

Same design, scaled 24×24, referenced in `app/layout.tsx`:

```tsx
export const metadata = {
  icons: [{ rel: 'icon', url: '/favicon.svg' }],
}
```

## 7. Data Flow / 数据流

```
┌──────────────────────────────────────────────────────┐
│ page.tsx (state owner)                                │
│  messages, activeContext, history,                     │
│  wikiTree, systemStatus, dashboardView, selectedPage   │
├──────────────┬───────────────────────────────────────┤
│ ChatWindow   │ Dashboard                              │
│              │ ├── ActiveContextWidget  ← pages[]     │
│ onSend() →   │ ├── HistoryWidget       ← items[]     │
│ append msg   │ │   onRerun(query) → onSend()          │
│              │ ├── WikiTreeWidget      ← tree[]       │
│              │ │   onSelect(id) → setSelectedPage     │
│              │ │                   → setView('preview')│
│              │ ├── WikiPagePreview     ← page + onBack │
│              │ └── SystemStatusWidget  ← entries[]     │
└──────────────┴───────────────────────────────────────┘
```

All state lives in `page.tsx` (or a lifted `useAppState` hook). Widgets never fetch — they render what they receive.

## 8. Mobile Responsiveness / 移动端适配

| Breakpoint | Dashboard behavior |
|---|---|
| ≥ 1024px | Full dashboard sidebar visible |
| 768–1023px | Dashboard hidden behind hamburger icon; slides out as overlay |
| < 768px | Dashboard in bottom sheet or full-screen overlay |

Header should shrink on mobile (hide model badges, keep logo + hamburger).

## 9. Implementation Order / 实施顺序

| Step | File(s) | Description |
|---|---|---|
| 1 | `globals.css` | Add Sage Garden CSS variables (light + dark) |
| 2 | `public/logo.svg`, `public/favicon.svg` | Add SVG assets |
| 3 | `app/layout.tsx` | Add favicon metadata |
| 4 | `components/dashboard/Widget.tsx` | Create generic widget wrapper |
| 5 | `ChatWindow.tsx` | Move input bar to top, restructure layout |
| 6 | `Dashboard.tsx` | Create container (view switching logic) |
| 7 | `ActiveContextWidget.tsx` | Show active wiki pages list |
| 8 | `SystemStatusWidget.tsx` | Show live service statuses |
| 9 | `WikiTreeWidget.tsx` | Show hierarchical wiki tree |
| 10 | `WikiPagePreview.tsx` | Show full wiki page content |
| 11 | `HistoryWidget.tsx` | Show recent queries (session + persisted) |
| 12 | `app/page.tsx` | Wire everything together, manage state |
| 13 | Polish | Mobile responsiveness, transitions, edge cases |

## 10. Open Questions / 待定问题

- **Wiki tree data source**: Does the wiki tree come from an API endpoint, or is it built from a known directory structure? Assumption: API (`GET /api/wiki/tree`).
- **History persistence**: Where is cross-session history stored? Assumption: local storage for MVP, server-side later.
- **System status polling**: Does the frontend poll or receive via WebSocket? Assumption: polling every 30s via `GET /api/system/status`.
- **Wiki page content API**: How does preview fetch page content? Assumption: `GET /api/wiki/page/:id`.

## 11. Out of Scope / 不在此范围

- Dark mode toggle (recommend tackling separately)
- Resizable dashboard panel
- Drag-to-reorder widgets
- User-customizable widgets
- Real-time WebSocket updates (polling is fine for MVP)

## 12. Sources / 来源

- [GitHub Issue #1 — UI Improvement](https://github.com/williamjxj/MemWeaver/issues/1)
- [tweakcn.com — Sage Garden theme](https://tweakcn.com/editor/theme/sage-garden)
- [Current page.tsx](../chat-app/app/page.tsx)
- [Current ChatWindow.tsx](../chat-app/components/ChatWindow.tsx)
- [Current WikiSidebar.tsx](../chat-app/components/WikiSidebar.tsx)
