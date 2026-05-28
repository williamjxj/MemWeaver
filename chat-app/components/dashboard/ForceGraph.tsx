"use client";

import { useRef, useEffect } from "react";
import * as d3 from "d3";

interface RawNode {
  id: string;
  title: string | null;
  category: string | null;
  inbound_links: number;
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  category: string | null;
  radius: number;
}

interface RawEdge {
  source: string;
  target: string;
}

interface ForceGraphProps {
  nodes: RawNode[];
  edges: RawEdge[];
  compact: boolean;
  onNodeClick: (pageId: string) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
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

function getCategoryColor(category: string | null): string {
  if (category && CATEGORY_COLORS[category]) return CATEGORY_COLORS[category];
  return "#9ca3af";
}

export function ForceGraph({
  nodes: rawNodes,
  edges: rawEdges,
  compact,
  onNodeClick,
}: ForceGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const el = svgRef.current;
    if (!el || rawNodes.length === 0) return;

    const width = el.clientWidth || 240;
    const height = el.clientHeight || (compact ? 120 : 340);

    // Build simulation nodes
    const maxLinks = Math.max(1, ...rawNodes.map((n) => n.inbound_links));
    const radiusScale = d3
      .scaleSqrt()
      .domain([0, maxLinks])
      .range(compact ? [3, 8] : [4, 16]);

    const simNodes: SimNode[] = rawNodes.map((n) => ({
      id: n.id,
      category: n.category,
      radius: radiusScale(n.inbound_links || 1),
    }));

    // Build simulation edges (convert string IDs to object refs)
    const nodeIds = new Set(simNodes.map((n) => n.id));
    const simEdges: d3.SimulationLinkDatum<SimNode>[] = rawEdges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e) => ({ source: e.source, target: e.target }));

    // Clear and setup SVG
    d3.select(el).selectAll("*").remove();

    const svg = d3.select(el).attr("viewBox", `0 0 ${width} ${height}`);

    const g = svg.append("g");

    // Zoom
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
    svg.call(zoom);

    // Double-click to reset zoom
    svg.on("dblclick.zoom", () => {
      svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
    });

    // Simulation
    const simulation = d3
      .forceSimulation<SimNode>(simNodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, d3.SimulationLinkDatum<SimNode>>(simEdges)
          .id((d) => d.id)
          .distance(compact ? 50 : 80)
          .strength(0.5),
      )
      .force("charge", d3.forceManyBody().strength(compact ? -80 : -150))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collide",
        d3.forceCollide<SimNode>().radius((d) => d.radius + (compact ? 3 : 5)),
      )
      .alphaDecay(0.03);

    // Edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(simEdges)
      .join("line")
      .attr("stroke", "#e8e6e1")
      .attr("stroke-width", 1);

    // Nodes
    const nodeGroup = g
      .append("g")
      .selectAll<SVGCircleElement, SimNode>("circle")
      .data(simNodes)
      .join("circle")
      .attr("r", (d) => d.radius)
      .attr("fill", (d) => getCategoryColor(d.category))
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer")
      .on("click", (_event, d) => onNodeClick(d.id))
      .on("mouseenter", function () {
        d3.select(this).attr("stroke-width", 3).attr("stroke", "#7c9082");
      })
      .on("mouseleave", function () {
        d3.select(this).attr("stroke-width", 1.5).attr("stroke", "#fff");
      })
      .call(
        d3
          .drag<SVGCircleElement, SimNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            // Keep pinned where dropped
          }),
      );

    // Tooltips / labels for expanded mode
    if (!compact) {
      nodeGroup.append("title").text((d) => d.id);
    }

    // Tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (typeof d.source === "object" ? (d.source.x ?? 0) : 0))
        .attr("y1", (d) => (typeof d.source === "object" ? (d.source.y ?? 0) : 0))
        .attr("x2", (d) => (typeof d.target === "object" ? (d.target.x ?? 0) : 0))
        .attr("y2", (d) => (typeof d.target === "object" ? (d.target.y ?? 0) : 0));
      nodeGroup.attr("cx", (d) => d.x!).attr("cy", (d) => d.y!);
    });

    return () => {
      simulation.stop();
    };
  }, [rawNodes, rawEdges, compact, onNodeClick]);

  if (rawNodes.length === 0) return null;

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      style={{ minHeight: compact ? 100 : 200 }}
    />
  );
}
