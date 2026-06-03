"use client";

import { useEffect, useRef, useState } from "react";
import { fetchWikiGraph, type GraphData } from "@/lib/api";

interface SimNode {
  id: string;
  label: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  links: number;
}

export function WikiGraphView() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [simNodes, setSimNodes] = useState<SimNode[]>([]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchWikiGraph()
      .then((data) => {
        if (!cancelled) {
          setGraph(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!graph || graph.nodes.length === 0) return;
    const { edges } = graph;

    const W = 600;
    const H = 400;
    const nodes: SimNode[] = graph.nodes.map((n, i) => ({
      id: n.id,
      label: n.title || n.id,
      x: W / 2 + (Math.random() - 0.5) * 200,
      y: H / 2 + (Math.random() - 0.5) * 200,
      vx: 0,
      vy: 0,
      links: n.inbound_links,
    }));

    const REP = 3000;
    const ATT = 0.005;
    const DAMP = 0.85;
    const CTR = 0.01;
    const MAX_DIST = 250;

    function step() {
      for (const n of nodes) {
        n.vx *= DAMP;
        n.vy *= DAMP;
        n.vx += (W / 2 - n.x) * CTR;
        n.vy += (H / 2 - n.y) * CTR;
      }

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist > MAX_DIST) continue;
          const f = REP / (dist + 1);
          const fx = (dx / dist) * f;
          const fy = (dy / dist) * f;
          a.vx -= fx;
          a.vy -= fy;
          b.vx += fx;
          b.vy += fy;
        }
      }

      for (const edge of edges) {
        const src = nodes.find((n) => n.id === edge.source);
        const tgt = nodes.find((n) => n.id === edge.target);
        if (!src || !tgt) continue;
        let dx = tgt.x - src.x;
        let dy = tgt.y - src.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const f = (dist - 80) * ATT;
        const fx = (dx / dist) * f;
        const fy = (dy / dist) * f;
        src.vx += fx;
        src.vy += fy;
        tgt.vx -= fx;
        tgt.vy -= fy;
      }

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(20, Math.min(W - 20, n.x));
        n.y = Math.max(20, Math.min(H - 20, n.y));
      }
    }

    let frame: number;
    let iter = 0;
    function loop() {
      step();
      iter++;
      if (iter > 120) {
        setSimNodes([...nodes]);
        return;
      }
      setSimNodes([...nodes]);
      frame = requestAnimationFrame(loop);
    }
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [graph]);

  const maxLinks = Math.max(...simNodes.map((n) => n.links), 1);

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-border/50 bg-background/50 p-8 text-sm text-muted-foreground">
        Loading graph...
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-border/50 bg-background/50 p-8 text-sm text-muted-foreground">
        No wiki pages to display.
      </div>
    );
  }

  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));

  return (
    <div className="rounded-xl border border-border/50 bg-background/50 p-2">
      <svg
        ref={svgRef}
        viewBox="0 0 600 400"
        className="h-auto w-full"
        style={{ maxHeight: 400 }}
      >
        <defs>
          {simNodes.map((n) => (
            <radialGradient key={n.id} id={`grad-${n.id}`} cx="35%" cy="35%">
              <stop offset="0%" stopColor={n.links > 0 ? "#818cf8" : "#94a3b8"} />
              <stop offset="100%" stopColor={n.links > 0 ? "#6366f1" : "#64748b"} />
            </radialGradient>
          ))}
        </defs>

        {graph.edges.map((edge, i) => {
          const src = nodeMap.get(edge.source);
          const tgt = nodeMap.get(edge.target);
          if (!src || !tgt) return null;
          return (
            <line
              key={`e-${i}`}
              x1={src.x}
              y1={src.y}
              x2={tgt.x}
              y2={tgt.y}
              stroke="#334155"
              strokeWidth={0.5}
              opacity={0.4}
            />
          );
        })}

        {simNodes.map((n) => {
          const r = 4 + (n.links / maxLinks) * 8;
          return (
            <g key={n.id}>
              <circle cx={n.x} cy={n.y} r={r} fill={`url(#grad-${n.id})`} stroke="#1e293b" strokeWidth={1} />
              <text
                x={n.x}
                y={n.y + r + 11}
                textAnchor="middle"
                fill="#cbd5e1"
                fontSize={9}
                fontFamily="ui-monospace, monospace"
              >
                {n.label.length > 18 ? n.label.slice(0, 16) + "…" : n.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
