"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE } from "./api";

export interface GraphNode {
  id: string;
  title: string | null;
  category: string | null;
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
      const res = await fetch(`${API_BASE}/wiki/graph`);
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

  useEffect(() => {
    const id = setTimeout(() => {
      void fetchGraph();
    }, 0);
    return () => clearTimeout(id);
  }, [fetchGraph]);

  return { nodes, edges, loading, error, refresh: fetchGraph };
}
