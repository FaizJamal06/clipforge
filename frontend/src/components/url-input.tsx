"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession, signIn } from "next-auth/react";

import LoadingTerminal from "./loading-terminal";
import { streamSSE } from "@/lib/sse";

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await processUrl();
  };

  if (sessionStatus === "loading" || (session && plan === null)) return null;

  // Anyone can try the demo. Analyzing your own videos runs real, billed LLM
  // calls, so it needs sign-in AND the Pro plan (enforced server-side too).
  if (!session || plan !== "pro") {
    return (
      <div className="card anim-fade-up" style={{ padding: "28px", textAlign: "center", display: "flex", flexDirection: "column", gap: "16px", alignItems: "center" }}>
        <p style={{ margin: 0, color: "var(--text-secondary, #9AA3B2)", fontSize: 14 }}>
          {session
            ? "You're on the free plan. Explore a sample result, or upgrade to analyze your own videos."
            : "See a real sample result instantly, or sign in to unlock your own videos."}
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center" }}>
          <button type="button" onClick={openDemo} className="btn btn-primary" style={{ padding: "12px 28px" }}>
            Try demo
          </button>
          {session ? (
            <button type="button" onClick={upgrade} className="btn btn-secondary" style={{ padding: "12px 28px" }}>
              Upgrade to Pro
            </button>
          ) : (
            <button type="button" onClick={() => signIn("google")} className="btn btn-secondary" style={{ padding: "12px 28px" }}>
              Sign in with Google
            </button>
          )}
        </div>
        {error && <p style={{ color: "#FF4F6E", fontSize: 13, margin: 0 }}>{error}</p>}
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
      {loading && <LoadingTerminal status={status} />}

      {/* Error Display */}
      {error && !loading && (
        <div className="card anim-fade-up" style={{ padding: "16px", borderColor: "rgba(255, 79, 110, 0.4)", background: "rgba(255, 79, 110, 0.05)" }}>
          <p style={{ color: "#FF4F6E", fontSize: "14px", margin: 0 }}>{error}</p>
        </div>
      )}
    </div>
  );
}
