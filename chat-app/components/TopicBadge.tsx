"use client";

const TOPIC_COLORS: Record<string, string> = {
  coding: "bg-blue-100 text-blue-700",
  design: "bg-green-100 text-green-700",
  ml: "bg-purple-100 text-purple-700",
  business: "bg-orange-100 text-orange-700",
  general: "bg-gray-100 text-gray-600",
};

interface TopicBadgeProps {
  topic: string;
}

export function TopicBadge({ topic }: TopicBadgeProps) {
  const colorClass = TOPIC_COLORS[topic] ?? TOPIC_COLORS.general;
  return (
    <span
      className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${colorClass}`}
    >
      {topic}
    </span>
  );
}
