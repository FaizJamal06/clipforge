"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

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
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Initializing...");
  const [error, setError] = useState<string | null>(null);

  const processUrl = async () => {
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setLoadingMessage("Connecting to server...");

    try {
      const streamUrl = `${API_BASE_URL}/api/v1/process/stream?youtube_url=${encodeURIComponent(url)}&chunk_offset=0`;
      const eventSource = new EventSource(streamUrl);

      eventSource.onmessage = (e) => {
        try {
          const payload = JSON.parse(e.data);
          
          if (payload.type === "update") {
             const msg = statusToStepMessage[payload.status] || `Processing (${payload.status})...`;
             setLoadingMessage(msg);
          } 
          else if (payload.type === "complete") {
             eventSource.close();
             sessionStorage.setItem("clipforge_latest_result", JSON.stringify(payload.data));
             sessionStorage.setItem("clipforge_latest_url", url);
             sessionStorage.setItem("clipforge_latest_offset", "0");
             router.push("/result");
          }
          else if (payload.type === "error") {
             eventSource.close();
             const errData = payload.data?.errors?.[0] || "Pipeline execution failed.";
             setError(errData);
             setLoading(false);
          }
        } catch (err) {
          console.error("Failed to parse SSE payload", err);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        // Fallback or generic network error
        setError("Network connection to the pipeline dropped.");
        setLoading(false);
      };

    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await processUrl();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%" }}>
      {/* URL Input Form */}
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
          disabled={loading || !url.trim()}
          className="btn btn-primary"
          style={{ whiteSpace: "nowrap", height: "auto", padding: "14px 28px" }}
          suppressHydrationWarning
        >
          {loading ? (
            <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span className="badge badge-dot" style={{ background: "transparent", border: "none", padding: 0, minWidth: "12px", minHeight: "12px" }}></span>
              Working...
            </span>
          ) : (
            "Find Clips"
          )}
        </button>
      </form>

      {/* Loading State Container */}
      {loading && (
        <div className="card anim-fade-up" style={{ padding: "20px", background: "rgba(255, 79, 31, 0.03)", borderColor: "rgba(255, 79, 31, 0.2)", display: "flex", alignItems: "center", gap: "16px" }}>
          <div className="badge badge-forge badge-dot" style={{ width: "fit-content" }}>Processing</div>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--text-secondary)" }}>
            {loadingMessage}
          </span>
        </div>
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
