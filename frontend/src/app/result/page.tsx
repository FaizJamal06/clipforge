"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ClipResult {
  clip_text: string;
  start_time: number;
  end_time: number;
  duration: number;
  virality_score: number;
  editing_plan: string;
}

interface ProcessResponse {
  status: string;
  youtube_url: string;
  video_id: string;
  clips: ClipResult[];
  errors: string[];
}

export default function ResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [chunkOffset, setChunkOffset] = useState(0);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const rawData = sessionStorage.getItem("clipforge_latest_result");
    const storedUrl = sessionStorage.getItem("clipforge_latest_url");
    const storedOffset = sessionStorage.getItem("clipforge_latest_offset");

    if (!rawData) {
      router.push("/");
      return;
    }

    try {
      const data = JSON.parse(rawData);
      setResult(data);
      if (storedUrl) setUrl(storedUrl);
      if (storedOffset) setChunkOffset(parseInt(storedOffset, 10));
    } catch (e) {
      router.push("/");
    }
  }, [router]);

  const loadMoreClips = async () => {
    if (!url) return;
    setLoading(true);
    setError(null);
    const nextOffset = chunkOffset + 1;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtube_url: url, chunk_offset: nextOffset }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data: ProcessResponse = await response.json();
      
      if (result) {
        const newData = {
          ...data,
          clips: [...result.clips, ...data.clips],
        };
        setResult(newData);
        sessionStorage.setItem("clipforge_latest_result", JSON.stringify(newData));
      }
      setChunkOffset(nextOffset);
      sessionStorage.setItem("clipforge_latest_offset", String(nextOffset));
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  if (!result) return null;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Super minimal nav to go back */}
      <nav className="nav" style={{ position: "relative", borderBottom: "1px solid var(--color-slate-border)", background: "var(--color-bg)", padding: "16px 0" }}>
        <div className="container">
          <div className="nav-inner" style={{ padding: "8px 0" }}>
            <button 
              onClick={() => router.push("/")} 
              className="nav-logo anim-fade-in" 
              style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: "24px", color: "var(--text-primary)" }}>
              <span className="nav-logo-mark">⚡</span> ClipForge
            </button>
            <div className="nav-actions">
               <button onClick={() => router.push("/")} className="btn btn-secondary">
                 Process Another Video
               </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="container" style={{ flex: 1, paddingTop: "80px", paddingBottom: "120px", maxWidth: "800px", margin: "0 auto" }}>
        <div className="anim-fade-up" style={{ marginBottom: "40px" }}>
          <h1 style={{ fontSize: "36px", marginBottom: "12px", letterSpacing: "-0.02em" }}>Viral Clip Blueprints</h1>
          <p style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)", fontSize: "14px" }}>
            Generated from {url || `Video ID: ${result.video_id}`}
          </p>
        </div>

        {error && (
          <div className="card anim-fade-up" style={{ padding: "16px", borderColor: "rgba(255, 79, 110, 0.4)", background: "rgba(255, 79, 110, 0.05)", marginBottom: "24px" }}>
            <p style={{ color: "#FF4F6E", fontSize: "14px", margin: 0 }}>{error}</p>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "40px" }}>
          {result.clips.length > 0 ? (
             result.clips.map((clip, index) => (
                <div key={index} className="clip-player anim-fade-up" style={{ animationDelay: `${(index % 3) * 100}ms` }}>
                  
                  <div className="clip-player-header">
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ color: "var(--color-forge)", fontSize: "18px" }}>▶</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "var(--text-secondary)" }}>
                        Clip_{index + 1}_{result.video_id}.mp4
                      </span>
                    </div>
                    <span className="badge badge-spark" style={{ fontSize: "10px" }}>High Potential</span>
                  </div>

                  <div className="clip-meta" style={{ borderBottom: "1px solid var(--color-slate-border)", padding: "20px 24px" }}>
                    <div className="clip-score">
                      <span style={{ color: "var(--text-muted)", fontSize: "12px", letterSpacing: "0.05em" }}>VIRAL SCORE</span>
                      <span className="clip-score-value">{clip.virality_score}</span>
                    </div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--text-muted)", background: "var(--color-bg-secondary)", padding: "6px 12px", borderRadius: "var(--radius-sm)" }}>
                      {formatTime(clip.start_time)} → {formatTime(clip.end_time)} <span style={{ color: "var(--color-forge)", marginLeft: "8px" }}>{clip.duration}s</span>
                    </div>
                  </div>

                  <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "24px" }}>
                    <p style={{ fontSize: "18px", lineHeight: "1.5", color: "var(--text-primary)", fontStyle: "italic", borderLeft: "3px solid var(--color-forge)", paddingLeft: "20px", margin: 0 }}>
                      "{clip.clip_text}"
                    </p>
                    
                    {clip.editing_plan && (
                      <div style={{ background: "rgba(13, 15, 20, 0.6)", borderRadius: "var(--radius-sm)", padding: "20px", border: "1px solid var(--color-slate-border)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                          <span style={{ fontSize: "16px" }}>📋</span>
                          <span style={{ fontSize: "12px", color: "var(--color-forge)", fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
                            Editing Blueprint
                          </span>
                        </div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "var(--text-secondary)", whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                          {clip.editing_plan}
                        </div>
                      </div>
                    )}
                  </div>
                  
                </div>
              ))
          ) : (
             <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>
               {result.errors.length > 0
                 ? result.errors.join(", ")
                 : "No viabile viral clips found in this segment."}
             </p>
          )}

          {result.status !== "failed" && result.clips.length > 0 && (
            <div style={{ paddingTop: "24px", display: "flex", justifyContent: "center" }}>
              <button 
                onClick={loadMoreClips} 
                disabled={loading} 
                className="btn btn-secondary"
                style={{ width: "100%", padding: "16px 0", fontSize: "16px" }}
              >
                {loading ? (
                  <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "12px" }}>
                    <span className="badge badge-dot" style={{ background: "transparent", border: "none", padding: 0 }}></span>
                    Scanning further into episode...
                  </span>
                ) : (
                  "Get Next Best Clip"
                )}
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
