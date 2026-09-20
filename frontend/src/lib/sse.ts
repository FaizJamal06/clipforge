/**
 * Reads a Server-Sent Events stream via fetch() instead of the browser's
 * native EventSource. EventSource cannot send custom headers, so it has no
 * way to carry an Authorization bearer token — this is the tradeoff of
 * requiring auth on a streaming endpoint (see backend/app/api/routes.py's
 * /process/stream, and AUDIT.md's guardrails section).
 */
export interface SSEEvent {
  type?: string;
  [key: string]: unknown;
}

export async function streamSSE(
  url: string,
  token: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    signal,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("Streaming is not supported in this environment.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const dataLines = rawEvent
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim());

      if (dataLines.length === 0) continue;

      try {
        onEvent(JSON.parse(dataLines.join("\n")));
      } catch (err) {
        console.error("Failed to parse SSE payload", err);
      }
    }
  }
}
