"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession, signIn } from "next-auth/react";

import LoadingTerminal from "./loading-terminal";
import { streamSSE } from "@/lib/sse";

const DEMO_URL = "https://youtu.be/jEnxvZXzo0E";
const DEMO_VIDEO_ID = "jEnxvZXzo0E";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function UrlInput() {
  const router = useRouter();
  const { data: session, status: sessionStatus } = useSession();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("initialized");
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<"free" | "pro" | null>(null);

  const token = session?.backendToken;
  const [demoTitle, setDemoTitle] = useState<string | null>(null);

  // Public YouTube oEmbed endpoint for the video title; the thumbnail needs no fetch.
  useEffect(() => {
    fetch(`https://www.youtube.com/oembed?url=${encodeURIComponent(DEMO_URL)}&format=json`)
      .then((r) => r.json())
      .then((d) => setDemoTitle(d.title))
      .catch(() => {});
  }, []);

  // Ask the backend which plan this user is on. After a Stripe checkout
  // (?upgraded=1) the webhook may land a moment later, so poll briefly.
  useEffect(() => {
    if (!token) return;
    const justUpgraded = new URLSearchParams(window.location.search).has("upgraded");
    let cancelled = false;
    const load = async (attemptsLeft: number) => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.status === 401) {
          // Backend token expired (they last ~1h) — get a fresh one.
          if (!cancelled) signIn("google");
          return;
        }
        const me = await res.json();
        if (cancelled) return;
        setPlan(me.plan);
        if (justUpgraded && me.plan !== "pro" && attemptsLeft > 0) {
          setTimeout(() => load(attemptsLeft - 1), 2000);
        }
      } catch {
        if (!cancelled) setPlan("free");
      }
    };
    load(5);
    return () => {
      cancelled = true;
    };
  }, [token]);

  const openDemo = async () => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/demo`);
      if (!res.ok) throw new Error("Demo is unavailable right now.");
      const data = await res.json();
      sessionStorage.setItem("clipforge_latest_result", JSON.stringify(data));
      sessionStorage.setItem("clipforge_latest_url", data.youtube_url);
      sessionStorage.setItem("clipforge_latest_offset", "0");
      sessionStorage.setItem("clipforge_demo", "1");
      router.push("/result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo is unavailable right now.");
    }
  };

  const upgrade = async () => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/billing/checkout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not start checkout.");
      window.location.href = data.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start checkout.");
    }
  };

  const processUrl = async () => {
    if (!url.trim() || !token) return;

    setLoading(true);
    setError(null);
    setStatus("initialized");

    try {
      const streamUrl = `${API_BASE_URL}/api/v1/process/stream?youtube_url=${encodeURIComponent(url)}&chunk_offset=0`;

      await streamSSE(streamUrl, token, (payload) => {
        if (payload.type === "update") {
          setStatus(payload.status as string);
        } else if (payload.type === "complete") {
          sessionStorage.setItem("clipforge_latest_result", JSON.stringify(payload.data));
          sessionStorage.setItem("clipforge_latest_url", url);
          sessionStorage.setItem("clipforge_latest_offset", "0");
          sessionStorage.removeItem("clipforge_demo");
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

  const isPro = !!session && plan === "pro";
  // Pro users can flip to the visitor view to see exactly what a recruiter sees.
  const [previewDemo, setPreviewDemo] = useState(false);
  const demoView = !isPro || previewDemo;

  // Everyone gets the same paste bar. Free/signed-out visitors see the demo
  // video pre-loaded and "Find Clips" shows its cached result instantly (no
  // LLM cost). Only Pro users can edit the URL and run the real pipeline —
  // enforced server-side too (402).
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!demoView) await processUrl();
    else await openDemo();
  };

  if (sessionStatus === "loading") return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px", width: "100%" }}>
      {!loading && (
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "12px", width: "100%" }}>
          <input
            id="youtube-url-input"
            type="url"
            placeholder="Paste a YouTube URL..."
            value={demoView ? DEMO_URL : url}
            onChange={(e) => setUrl(e.target.value)}
            readOnly={demoView}
            className="custom-input"
            style={{ flex: 1 }}
            suppressHydrationWarning
          />
          <div style={{ position: "relative", display: "flex" }}>
            {demoView && (
              <div className="cta-hint">
                Click to see a real result <span>↓</span>
              </div>
            )}
          <button
              id="submit-button"
              type="submit"
              disabled={!demoView && !url.trim()}
              className={`btn btn-primary ${demoView ? "cta-pulse" : ""}`}
              style={{ whiteSpace: "nowrap", height: "auto", padding: "14px 28px" }}
              suppressHydrationWarning
            >
              Find Clips
            </button>
          </div>
        </form>
      )}

      {isPro && !loading && (
        <button type="button" onClick={() => setPreviewDemo(!previewDemo)} style={{ alignSelf: "flex-start", background: "none", border: "none", padding: 0, cursor: "pointer", color: "var(--color-forge, #FF4F1F)", font: "inherit", fontSize: 13, textDecoration: "underline" }}>
          {previewDemo ? "Back to my videos (Pro)" : "Preview demo mode"}
        </button>
      )}

      {demoView && !loading && (
        <div className="card" style={{ display: "flex", gap: 16, alignItems: "center", padding: 12, textAlign: "left" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`https://img.youtube.com/vi/${DEMO_VIDEO_ID}/hqdefault.jpg`}
            alt="Demo video thumbnail"
            width={160}
            height={90}
            style={{ borderRadius: 8, objectFit: "cover", flexShrink: 0 }}
          />
          <div style={{ minWidth: 0 }}>
            <span className="badge badge-forge">Demo video</span>
            <p style={{ margin: "8px 0 0", fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
              {demoTitle ?? "Sample YouTube video"}
            </p>
          </div>
        </div>
      )}

      {!isPro && !loading && (
        <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary, #9AA3B2)" }}>
          Demo mode: this video is pre-loaded so you can see a real result instantly.{" "}
          {session ? (
            <button type="button" onClick={upgrade} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", color: "var(--color-forge, #FF4F1F)", font: "inherit", textDecoration: "underline" }}>
              Upgrade to Pro
            </button>
          ) : (
            <button type="button" onClick={() => signIn("google")} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", color: "var(--color-forge, #FF4F1F)", font: "inherit", textDecoration: "underline" }}>
              Sign in
            </button>
          )}{" "}
          to analyze your own videos.
        </p>
      )}

      {loading && <LoadingTerminal status={status} />}

      {error && !loading && (
        <div className="card anim-fade-up" style={{ padding: "16px", borderColor: "rgba(255, 79, 110, 0.4)", background: "rgba(255, 79, 110, 0.05)" }}>
          <p style={{ color: "#FF4F6E", fontSize: "14px", margin: 0 }}>{error}</p>
        </div>
      )}
    </div>
  );
}
