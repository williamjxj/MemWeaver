"use client";

import { ActiveContextWidget } from "./ActiveContextWidget";
import { GraphWidget } from "./GraphWidget";
import { HistoryWidget } from "./HistoryWidget";
import { WikiTreeWidget } from "./WikiTreeWidget";
import { WikiPagePreview } from "./WikiPagePreview";
import { SystemStatusWidget } from "./SystemStatusWidget";
import type { GraphNode, GraphEdge } from "@/lib/use-wiki-graph";

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
  activeContext: string[];
  history: HistoryItem[];
  wikiTree: TreeNode[];
  systemStatus: SystemEntry[];
  selectedPage: WikiPage | null;
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  graphLoading: boolean;
  graphError: string | null;
  onHistoryRerun: (query: string) => void;
  onWikiPageSelect: (pageId: string) => void;
  onBackToDashboard: () => void;
  onGraphRefresh: () => void;
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
        <GraphWidget
          nodes={props.graphNodes}
          edges={props.graphEdges}
          loading={props.graphLoading}
          error={props.graphError}
          onNodeClick={props.onWikiPageSelect}
          onRefresh={props.onGraphRefresh}
        />
        <SystemStatusWidget entries={props.systemStatus} />
      </div>
    </aside>
  );
}
