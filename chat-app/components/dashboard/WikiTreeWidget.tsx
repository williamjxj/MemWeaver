"use client";

import { useState } from "react";
import { Widget } from "./Widget";

interface TreeNode {
  id: string;
  label: string;
  type: "folder" | "page";
  children?: TreeNode[];
}

interface WikiTreeWidgetProps {
  tree: TreeNode[];
  onSelect: (pageId: string) => void;
}

export function WikiTreeWidget({ tree, onSelect }: WikiTreeWidgetProps) {
  return (
    <Widget title="Wiki Tree" icon="🌳">
      {tree.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          The wiki tree is the catalog of compiled pages, grouped by sections from the wiki index.
        </p>
      ) : (
        <WikiTreeNodes nodes={tree} depth={0} onSelect={onSelect} />
      )}
    </Widget>
  );
}

function WikiTreeNodes({
  nodes,
  depth,
  onSelect,
}: {
  nodes: TreeNode[];
  depth: number;
  onSelect: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(depth === 0 ? nodes.filter((node) => node.type === "folder").map((node) => node.id) : []),
  );

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  return (
    <>
      {nodes.map((node) => {
        const indent = depth * 12;
        if (node.type === "folder") {
          const isOpen = expanded.has(node.id);
          return (
            <div key={node.id}>
              <button
                onClick={() => toggle(node.id)}
                className="flex items-center gap-1 text-sm w-full text-left hover:text-primary transition-colors cursor-pointer"
                style={{ paddingLeft: `${indent}px` }}
              >
                <span className="text-xs w-4 shrink-0">
                  {isOpen ? "▼" : "▶"}
                </span>
                <span className="text-xs">📁</span>
                <span className="truncate">{node.label}</span>
              </button>
              {isOpen && node.children && (
                <WikiTreeNodes
                  nodes={node.children}
                  depth={depth + 1}
                  onSelect={onSelect}
                />
              )}
            </div>
          );
        }
        return (
          <button
            key={node.id}
            onClick={() => onSelect(node.id)}
            className="flex items-center gap-1 text-sm w-full text-left hover:text-primary transition-colors cursor-pointer"
            style={{ paddingLeft: `${indent + 16}px` }}
          >
            <span className="text-xs">📄</span>
            <span className="truncate">{node.label}</span>
          </button>
        );
      })}
    </>
  );
}
