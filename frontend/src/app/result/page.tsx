"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Types ─── */
interface EditingSegment {
  timestamp: string;
  visual_type: string;
  broll_idea: string;
  caption_text: string;
  editing_note: string;
}
interface EditingPlan {
  title_suggestion: string;
  hook_strategy: string;
  segments: EditingSegment[];
  caption_style: string;
  pacing_notes: string;
  call_to_action: string;
}
interface ClipResult {
  clip_text: string;
  start_time: number;
  end_time: number;
  duration: number;
  virality_score: number;
  virality_reasoning: string;
  hook: string;
  payoff: string;
  editing_plan: EditingPlan | string;
}
interface ProcessResponse {
  status: string;
  youtube_url: string;
  video_id: string;
  clips: ClipResult[];
  errors: string[];
}

/* ─── Helpers ─── */
function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60);
  return `${m}:${ss < 10 ? "0" : ""}${ss}`;
}
function getPlan(ep: EditingPlan | string): EditingPlan | null {
  if (!ep || typeof ep === "string") return null;
  return ep;
}

const VTYPE_MAP: Record<string, { icon: string; label: string; color: string }> = {
  talking_head: { icon: "🎙️", label: "Talking Head", color: "#FF4F1F" },
  broll:        { icon: "🎬", label: "B-Roll",       color: "#00C4A7" },
  text_overlay: { icon: "💬", label: "Text Overlay", color: "#FFD60A" },
  mixed:        { icon: "🔀", label: "Mixed",         color: "#9AA3B8" },
};
function getVtype(raw: string) {
  const key = (raw || "").toLowerCase().replace(/[\s-]/g, "_");
  return VTYPE_MAP[key] || { icon: "🎥", label: raw || "Visual", color: "#9AA3B8" };
}

/* ─── Score Ring ─── */
function ScoreRing({ score, size = 68 }: { score: number; size?: number }) {
  const ref = useRef<SVGCircleElement>(null);
  const r = (size / 2) - 5;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(score / 10, 1);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.strokeDasharray = `0 ${circ}`;
    const raf = requestAnimationFrame(() => {
      setTimeout(() => {
        if (ref.current) ref.current.style.strokeDasharray = `${circ * pct} ${circ}`;
      }, 120);
    });
    return () => cancelAnimationFrame(raf);
  }, [circ, pct]);

  const color = score >= 8 ? "#FFD60A" : score >= 6 ? "#FF7A50" : "#9AA3B8";

  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)", flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1E2230" strokeWidth="4"/>
      <circle ref={ref} cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="4"
        strokeLinecap="round" style={{ transition: "stroke-dasharray 1.1s cubic-bezier(0.16,1,0.3,1)" }}/>
      <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central"
        fill={color} fontSize={size * 0.28} fontWeight="800"
        style={{ transform: `rotate(90deg)`, transformOrigin: `${size/2}px ${size/2}px`, fontFamily: "var(--font-display)" }}>
        {score}
      </text>
    </svg>
  );
}

/* ─── Blueprint Section ─── */
function BPSection({ icon, label, accent, children }: {
  icon: string; label: string; accent: string; children: React.ReactNode;
}) {
  return (
    <div style={{ borderRadius: 14, overflow: "hidden", border: `1px solid ${accent}28` }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 10, padding: "12px 18px",
        background: `${accent}0D`, borderBottom: `1px solid ${accent}18`,
      }}>
        <span style={{ fontSize: 15 }}>{icon}</span>
        <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", fontWeight: 700,
          letterSpacing: "0.1em", textTransform: "uppercase", color: accent }}>
          {label}
        </span>
      </div>
      <div style={{ padding: "16px 18px", background: "rgba(13,15,20,0.6)" }}>{children}</div>
    </div>
  );
}

/* ─── Timeline row ─── */
function SegRow({ seg, i }: { seg: EditingSegment; i: number }) {
  const vt = getVtype(seg.visual_type);
  return (
    <div style={{
      display: "grid", gridTemplateColumns: "76px 110px 1fr", gap: 12,
      padding: i === 0 ? "0 0 14px" : "14px 0",
      borderTop: i > 0 ? "1px solid #1E2230" : "none",
      alignItems: "start",
    }}>
      {/* timestamp */}
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700,
        color: "#FF4F1F", background: "#FF4F1F18", padding: "4px 8px",
        borderRadius: 5, textAlign: "center", lineHeight: 1.4 }}>
        {seg.timestamp || "—"}
      </div>
      {/* visual type pill */}
      <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
        <span style={{ fontSize: 13 }}>{vt.icon}</span>
        <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: vt.color, fontWeight: 600 }}>
          {vt.label}
        </span>
      </div>
      {/* details */}
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {seg.caption_text && (
          <div style={{ fontSize: 13, fontWeight: 700, color: "#FFD60A",
            fontFamily: "var(--font-display)", lineHeight: 1.3 }}>
            "{seg.caption_text}"
          </div>
        )}
        {seg.broll_idea && (
          <div style={{ fontSize: 12, color: "#9AA3B8", lineHeight: 1.5 }}>
            <span style={{ fontSize: 9, fontFamily: "var(--font-mono)", color: "#00C4A7",
              letterSpacing: "0.08em", marginRight: 6, fontWeight: 700 }}>B-ROLL</span>
            {seg.broll_idea}
          </div>
        )}
        {seg.editing_note && (
          <div style={{ fontSize: 11, color: "#4E5568", fontStyle: "italic",
            borderLeft: "2px solid #1E2230", paddingLeft: 8 }}>
            {seg.editing_note}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Clip Card ─── */
function ClipCard({ clip, index, videoId }: { clip: ClipResult; index: number; videoId: string }) {
  const [open, setOpen] = useState(index === 0);
  const plan = getPlan(clip.editing_plan);
  const score = Math.round(clip.virality_score);
  const scoreColor = score >= 8 ? "#FFD60A" : score >= 6 ? "#FF7A50" : "#9AA3B8";

  return (
    <div className="anim-fade-up" style={{
      background: "var(--color-slate-mid)", borderRadius: 20, overflow: "hidden",
      border: `1px solid ${open ? "rgba(255,79,31,0.25)" : "var(--color-slate-border)"}`,
      boxShadow: open ? "0 0 40px rgba(255,79,31,0.07)" : "none",
      transition: "border-color 300ms ease, box-shadow 300ms ease",
      animationDelay: `${index * 80}ms`,
    }}>
      {/* ── Header ── */}
      <div onClick={() => setOpen(o => !o)} style={{
        display: "flex", alignItems: "center", gap: 18, padding: "20px 24px",
        cursor: "pointer", userSelect: "none",
        borderBottom: open ? "1px solid var(--color-slate-border)" : "none",
        background: open ? "rgba(255,79,31,0.025)" : "transparent",
        transition: "background 250ms ease",
      }}>
        <ScoreRing score={score} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* clip number badge + high potential */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", fontWeight: 700,
              color: "#4E5568", letterSpacing: "0.08em" }}>
              CLIP {index + 1}
            </span>
            <span style={{ width: 1, height: 10, background: "#1E2230" }} />
            <span className="badge badge-spark" style={{ fontSize: 9, padding: "3px 10px" }}>
              HIGH POTENTIAL
            </span>
          </div>
          {/* title */}
          <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)",
            fontFamily: "var(--font-display)", lineHeight: 1.2, marginBottom: 6,
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {plan?.title_suggestion || `Clip ${index + 1}`}
          </div>
          {/* timing row */}
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#4E5568" }}>
              {formatTime(clip.start_time)} → {formatTime(clip.end_time)}
              <span style={{ color: "#FF4F1F", marginLeft: 6, fontWeight: 700 }}>
                {Math.round(clip.duration)}s
              </span>
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#4E5568" }}>
              {videoId ? `Clip_${index + 1}_${videoId}.mp4` : ""}
            </span>
          </div>
        </div>

        {/* Virality score label + chevron */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6, flexShrink: 0 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: scoreColor,
            letterSpacing: "0.06em", fontWeight: 700 }}>
            {score}/10 VIRAL
          </span>
          <span style={{ color: "#4E5568", fontSize: 18, lineHeight: 1,
            transform: open ? "rotate(180deg)" : "rotate(0)",
            transition: "transform 280ms var(--ease-out-expo)" }}>⌄</span>
        </div>
      </div>

      {/* ── Body ── */}
      {open && (
        <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: 18 }}>

          {/* Virality reasoning */}
          {clip.virality_reasoning && (
            <div style={{ fontSize: 13, color: "#9AA3B8", fontStyle: "italic",
              lineHeight: 1.7, borderLeft: "3px solid #FF4F1F", paddingLeft: 16 }}>
              {clip.virality_reasoning}
            </div>
          )}

          {/* Hook / Payoff */}
          {(clip.hook || clip.payoff) && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {clip.hook && (
                <div style={{ background: "#FF4F1F0E", border: "1px solid #FF4F1F28",
                  borderRadius: 12, padding: 16 }}>
                  <div style={{ fontSize: 9, fontFamily: "var(--font-mono)", fontWeight: 700,
                    color: "#FF4F1F", letterSpacing: "0.1em", marginBottom: 8 }}>🎣 HOOK</div>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>
                    {clip.hook}
                  </div>
                </div>
              )}
              {clip.payoff && (
                <div style={{ background: "#00C4A70E", border: "1px solid #00C4A728",
                  borderRadius: 12, padding: 16 }}>
                  <div style={{ fontSize: 9, fontFamily: "var(--font-mono)", fontWeight: 700,
                    color: "#00C4A7", letterSpacing: "0.1em", marginBottom: 8 }}>🎯 PAYOFF</div>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>
                    {clip.payoff}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Clip Script */}
          <BPSection icon="📝" label="Clip Script — Verbatim" accent="#FF4F1F">
            <p style={{ fontSize: 14, lineHeight: 1.75, color: "var(--text-primary)",
              fontStyle: "italic", margin: 0 }}>
              &ldquo;{clip.clip_text}&rdquo;
            </p>
          </BPSection>

          {plan && (
            <>
              {/* Hook Strategy */}
              {plan.hook_strategy && (
                <BPSection icon="⚡" label="Hook Strategy — First 3 Seconds" accent="#FF4F1F">
                  <p style={{ fontSize: 13, color: "#9AA3B8", lineHeight: 1.7, margin: 0 }}>
                    {plan.hook_strategy}
                  </p>
                </BPSection>
              )}

              {/* Edit Timeline */}
              {plan.segments?.length > 0 && (
                <BPSection icon="🎬" label="Edit Timeline" accent="#00C4A7">
                  {/* Column headings */}
                  <div style={{ display: "grid", gridTemplateColumns: "76px 110px 1fr",
                    gap: 12, marginBottom: 10 }}>
                    {["TIMESTAMP","VISUAL","DETAILS"].map(h => (
                      <span key={h} style={{ fontSize: 9, fontFamily: "var(--font-mono)",
                        color: "#4E5568", letterSpacing: "0.08em", fontWeight: 700 }}>{h}</span>
                    ))}
                  </div>
                  {plan.segments.map((seg, si) => (
                    <SegRow key={si} seg={seg} i={si} />
                  ))}
                </BPSection>
              )}

              {/* Caption Style */}
              {plan.caption_style && (
                <BPSection icon="💬" label="Caption Strategy" accent="#FFD60A">
                  <p style={{ fontSize: 13, color: "#9AA3B8", lineHeight: 1.7, margin: 0 }}>
                    {plan.caption_style}
                  </p>
                </BPSection>
              )}

              {/* Pacing */}
              {plan.pacing_notes && (
                <BPSection icon="🥁" label="Pacing & Rhythm" accent="#FFD60A">
                  <p style={{ fontSize: 13, color: "#9AA3B8", lineHeight: 1.7, margin: 0 }}>
                    {plan.pacing_notes}
                  </p>
                </BPSection>
              )}

              {/* CTA */}
              {plan.call_to_action && (
                <BPSection icon="📣" label="Call to Action" accent="#00C4A7">
                  <p style={{ fontSize: 14, fontWeight: 700, color: "#00C4A7",
                    lineHeight: 1.5, margin: 0 }}>
                    {plan.call_to_action}
                  </p>
                </BPSection>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Page ─── */
export default function ResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [chunkOffset, setChunkOffset] = useState(0);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("clipforge_latest_result");
    const storedUrl = sessionStorage.getItem("clipforge_latest_url");
    const storedOffset = sessionStorage.getItem("clipforge_latest_offset");
    if (!raw) { router.push("/"); return; }
    try {
      setResult(JSON.parse(raw));
      if (storedUrl) setUrl(storedUrl);
      if (storedOffset) setChunkOffset(parseInt(storedOffset, 10));
    } catch { router.push("/"); }
  }, [router]);

  const loadMore = async () => {
    if (!url) return;
    setLoading(true); setError(null);
    const nextOffset = chunkOffset + 1;
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtube_url: url, chunk_offset: nextOffset }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data: ProcessResponse = await res.json();
      if (result) {
        const merged = { ...data, clips: [...result.clips, ...data.clips] };
        setResult(merged);
        sessionStorage.setItem("clipforge_latest_result", JSON.stringify(merged));
      }
      setChunkOffset(nextOffset);
      sessionStorage.setItem("clipforge_latest_offset", String(nextOffset));
    } catch (e) {
      setError(e instanceof Error ? e.message : "An unexpected error occurred.");
    } finally { setLoading(false); }
  };

  if (!result) return null;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>

      {/* ── Nav ── */}
      <nav style={{
        position: "sticky", top: 0, zIndex: 100,
        borderBottom: "1px solid var(--color-slate-border)",
        background: "rgba(13,15,20,0.9)", backdropFilter: "blur(20px)",
        padding: "14px 0",
      }}>
        <div className="container">
          <div className="nav-inner">
            <button onClick={() => router.push("/")} style={{
              background: "transparent", border: "none", cursor: "pointer",
              display: "flex", alignItems: "center", gap: 8,
              fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 800,
              color: "var(--text-primary)", letterSpacing: "-0.03em",
            }}>
              <span style={{
                width: 30, height: 30, background: "var(--color-forge)",
                borderRadius: 6, display: "grid", placeItems: "center",
                fontSize: 16, boxShadow: "0 0 14px rgba(255,79,31,0.5)",
              }}>⚡</span>
              ClipForge
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#4E5568" }}>
                {result.clips.length} clip{result.clips.length !== 1 ? "s" : ""} ready
              </span>
              <button onClick={() => router.push("/")} className="btn btn-secondary"
                style={{ padding: "10px 20px", fontSize: 13 }}>
                ← New Video
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* ── Main ── */}
      <main style={{ flex: 1, paddingTop: 52, paddingBottom: 120 }}>
        <div className="container" style={{ maxWidth: 860 }}>

          {/* Page header */}
          <div className="anim-fade-up" style={{ marginBottom: 40 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <span className="badge badge-forge badge-dot">Editing Blueprints Ready</span>
            </div>
            <h1 style={{ fontSize: "clamp(28px,5vw,44px)", marginBottom: 10,
              letterSpacing: "-0.03em", lineHeight: 1.05 }}>
              Viral Clip<br />
              <span style={{ color: "var(--color-forge)" }}>Blueprints</span>
            </h1>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#4E5568",
              wordBreak: "break-all" }}>
              Source → {url || `Video ID: ${result.video_id}`}
            </p>
          </div>

          {/* Legend bar */}
          <div className="anim-fade-in anim-delay-1" style={{
            display: "flex", alignItems: "center", gap: 20, padding: "12px 18px",
            background: "var(--color-slate-mid)", border: "1px solid var(--color-slate-border)",
            borderRadius: 12, marginBottom: 28, flexWrap: "wrap",
          }}>
            {[
              { color: "#FFD60A", label: "Viral Score" },
              { color: "#FF4F1F", label: "Hook / Timeline" },
              { color: "#00C4A7", label: "B-Roll / CTA" },
              { color: "#FFD60A", label: "Captions / Pacing" },
            ].map(({ color, label }) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: color }} />
                <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "#4E5568" }}>
                  {label}
                </span>
              </div>
            ))}
            <span style={{ marginLeft: "auto", fontSize: 11, fontFamily: "var(--font-mono)",
              color: "#4E5568" }}>
              Click to expand each clip ↓
            </span>
          </div>

          {/* Error */}
          {error && (
            <div className="anim-fade-up" style={{
              padding: 16, marginBottom: 20, borderRadius: 12,
              border: "1px solid rgba(255,79,110,0.4)", background: "rgba(255,79,110,0.05)",
            }}>
              <p style={{ color: "#FF4F6E", fontSize: 13, margin: 0 }}>{error}</p>
            </div>
          )}

          {/* Clips */}
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {result.clips.length > 0 ? (
              result.clips.map((clip, i) => (
                <ClipCard key={i} clip={clip} index={i} videoId={result.video_id} />
              ))
            ) : (
              <div style={{ textAlign: "center", padding: "80px 0" }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>🎙️</div>
                <p style={{ fontSize: 14, color: "#4E5568" }}>
                  {result.errors.length > 0
                    ? result.errors.join(", ")
                    : "No viable viral clips found in this segment."}
                </p>
              </div>
            )}

            {/* Load more */}
            {result.status !== "failed" && result.clips.length > 0 && (
              <button onClick={loadMore} disabled={loading} className="btn btn-secondary"
                style={{ width: "100%", padding: "18px 0", fontSize: 14, marginTop: 8,
                  borderRadius: 14 }}>
                {loading ? (
                  <span style={{ display: "flex", alignItems: "center",
                    justifyContent: "center", gap: 10 }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%",
                      background: "#FF4F1F", display: "inline-block",
                      animation: "pulse-dot 1.2s ease-in-out infinite" }} />
                    Scanning deeper into episode…
                  </span>
                ) : "⚡ Get Next Best Clip"}
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
