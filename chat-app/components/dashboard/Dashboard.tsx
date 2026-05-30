"use client";

import { ActiveContextWidget } from "./ActiveContextWidget";
import { HistoryWidget } from "./HistoryWidget";
import { WikiTreeWidget } from "./WikiTreeWidget";
import { WikiPagePreview } from "./WikiPagePreview";
import { SystemStatusWidget } from "./SystemStatusWidget";

export interface ActiveContextItem {
  id: string;
  label: string;
  detail?: string;
}

export interface HistoryItem {
  id: string;
  query: string;
  timestamp: Date;
}

export interface TreeNode {
  id: string;
  label: string;
  type: "folder" | "page";
  children?: TreeNode[];
}

export interface SystemEntry {
  label: string;
  status: "connected" | "disconnected" | "warning";
  detail?: string;
}

export interface WikiPage {
  id: string;
  title: string;
  content: string;
  tags?: string[];
  sources?: string[];
}

export type DashboardView = "dashboard" | "preview";

interface DashboardProps {
  view: DashboardView;
  activeContext: ActiveContextItem[];
  history: HistoryItem[];
  wikiTree: TreeNode[];
  systemStatus: SystemEntry[];
  selectedPage: WikiPage | null;
  onHistoryRerun: (query: string) => void;
  onWikiPageSelect: (pageId: string) => void;
  onBackToDashboard: () => void;
}

export function Dashboard(props: DashboardProps) {
  if (props.view === "preview" && props.selectedPage) {
    return (
      <aside className="w-72 border-l bg-card flex flex-col h-full">
        <WikiPagePreview page={props.selectedPage} onBack={props.onBackToDashboard} />
      </aside>
    );
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
  );
}
