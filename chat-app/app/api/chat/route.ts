import { NextRequest } from "next/server";

const API_BASE = process.env.API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  let question: string;
  try {
    const body = await request.json();
    question = body.question;
  } catch {
    return new Response(JSON.stringify({ error: "invalid JSON body" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }

  if (!question || typeof question !== "string" || !question.trim()) {
    return new Response(JSON.stringify({ error: "question is required" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }

  const upstream = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question: question.trim() }),
  });

  if (!upstream.ok) {
    const text = await upstream.text().catch(() => "upstream error");
    return new Response(
      JSON.stringify({ error: `backend error: ${upstream.status}`, detail: text }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }

  const upstreamReader = upstream.body?.getReader();
  if (!upstreamReader) {
    return new Response(JSON.stringify({ error: "backend stream unavailable" }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  }

  const stream = new ReadableStream({
    async start(controller) {
      const decoder = new TextDecoder();
      try {
        while (true) {
          const { done, value } = await upstreamReader.read();
          if (done) break;
          const text = decoder.decode(value, { stream: true });
          controller.enqueue(new TextEncoder().encode(text));
        }
        controller.close();
      } catch (err) {
        controller.enqueue(
          new TextEncoder().encode(
            `event: error\ndata: ${JSON.stringify({ message: "stream interrupted" })}\n\n`,
          ),
        );
        controller.close();
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache",
      connection: "keep-alive",
    },
  });
}
