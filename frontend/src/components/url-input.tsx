"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession, signIn } from "next-auth/react";

import LoadingTerminal from "./loading-terminal";
import { streamSSE } from "@/lib/sse";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const statusToStepMessage: Record<string, string> = {
  initialized: "Initializing pipeline...",
  transcript_downloaded: "Fetching YouTube transcript...",
  transcript_processed: "Cleaning and removing filler words...",
  clips_discovered: "AI scanning for viral hooks...",
  clips_validated: "Evaluating retention dynamics...",
  editing_plans_generated: "Generating frame-perfect blueprints...",
  completed: "Finalizing clip extraction...",
  failed: "Pipeline failed."
};

export default function UrlInput() {
  const router = useRouter();
  const { data: session, status: sessionStatus } = useSession();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("initialized");
  const [error, setError] = useState<string | null>(null);

  const processUrl = async () => {
    if (!url.trim() || !session?.backendToken) return;

    setLoading(true);
    setError(null);
    setStatus("initialized");

    try {
      const streamUrl = `${API_BASE_URL}/api/v1/process/stream?youtube_url=${encodeURIComponent(url)}&chunk_offset=0`;

      await streamSSE(streamUrl, session.backendToken, (payload) => {
        if (payload.type === "update") {
          setStatus(payload.status as string);
        } else if (payload.type === "complete") {
          sessionStorage.setItem("clipforge_latest_result", JSON.stringify(payload.data));
          sessionStorage.setItem("clipforge_latest_url", url);
          sessionStorage.setItem("clipforge_latest_offset", "0");
          router.push("/result");
        } else if (payload.type === "error") {
          const data = payload.data as { errors?: string[] } | undefined;
          setError(data?.errors?.[0] || "Pipeline execution failed.");
          setLoading(false);
        }
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Network connection to the pipeline dropped."
      );
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await processUrl();
  };

  // Signed-out state: gate the whole flow behind Google sign-in, since every
  // /process call now requires an authenticated user (see AUDIT.md — the
  // pipeline triggers real, billed LLM calls, so this can't be left open).
  if (sessionStatus !== "loading" && !session) {
    return (
      <div className="card anim-fade-up" style={{ padding: "28px", textAlign: "center", display: "flex", flexDirection: "column", gap: "16px", alignItems: "center" }}>
        <p style={{ margin: 0, color: "var(--text-secondary, #9AA3B2)", fontSize: 14 }}>
          Sign in to find clips from a YouTube video.
        </p>
        <button
          type="button"
          onClick={() => signIn("google")}
          className="btn btn-primary"
          style={{ padding: "12px 28px" }}
        >
          Sign in with Google
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%" }}>
      {/* URL Input Form - Hide while loading to focus on terminal */}
      {!loading && (
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "12px", width: "100%" }}>
          <input
            id="youtube-url-input"
            type="url"
            placeholder="Paste a YouTube URL..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="custom-input"
            style={{ flex: 1 }}
            disabled={loading}
            suppressHydrationWarning
          />
          <button
            id="submit-button"
            type="submit"
            disabled={!url.trim()}
            className="btn btn-primary"
            style={{ whiteSpace: "nowrap", height: "auto", padding: "14px 28px" }}
            suppressHydrationWarning
          >
            Find Clips
          </button>
        </form>
      )}

      {/* Loading State Container */}
      {loading && (
        <LoadingTerminal status={status} />
      )}

      {/* Error Display */}
      {error && !loading && (
        <div className="card anim-fade-up" style={{ padding: "16px", borderColor: "rgba(255, 79, 110, 0.4)", background: "rgba(255, 79, 110, 0.05)" }}>
          <p style={{ color: "#FF4F6E", fontSize: "14px", margin: 0 }}>{error}</p>
        </div>
      )}
    </div>
  );
}
