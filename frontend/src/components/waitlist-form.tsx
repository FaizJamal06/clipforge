"use client";

import { useState, useRef } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type State = "idle" | "loading" | "success" | "already" | "error";

interface WaitlistFormProps {
  source?: string;
  /** Override button text */
  cta?: string;
  /** Compact single-row layout (default) vs. stacked */
  layout?: "row" | "stack";
}

export default function WaitlistForm({
  source = "landing_page",
  cta = "Join Waitlist →",
  layout = "row",
}: WaitlistFormProps) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<State>("idle");
  const [message, setMessage] = useState("");
  const honeypotRef = useRef<HTMLInputElement>(null);

  const validate = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim());

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Client-side honeypot check
    if (honeypotRef.current?.value) return;

    const trimmed = email.trim();
    if (!validate(trimmed)) {
      setState("error");
      setMessage("Please enter a valid email address.");
      return;
    }

    setState("loading");

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: trimmed,
          source,
          website: "",   // honeypot — always empty from real users
        }),
      });

      // Handle non-2xx gracefully
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (res.status === 422) {
          setState("error");
          setMessage("Please enter a valid email address.");
        } else if (res.status === 429) {
          setState("error");
          setMessage("Too many requests — please try again in a moment.");
        } else {
          setState("error");
          setMessage(err?.detail || "Something went wrong. Please try again.");
        }
        return;
      }

      const data = await res.json();
      if (data.already_joined) {
        setState("already");
        setMessage(data.message);
      } else {
        setState("success");
        setMessage(data.message);
        setEmail("");
      }
    } catch {
      setState("error");
      setMessage("Network error — please check your connection and try again.");
    }
  };

  const isRow = layout === "row";
  const inputDisabled = state === "loading" || state === "success";

  return (
    <form onSubmit={handleSubmit} noValidate style={{ width: "100%" }}>
      {/* Honeypot — hidden from real users via CSS, bots fill it */}
      <input
        ref={honeypotRef}
        type="text"
        name="website"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        style={{ position: "absolute", opacity: 0, pointerEvents: "none", width: 0, height: 0 }}
      />

      {/* Input row */}
      <div style={{
        display: "flex",
        flexDirection: isRow ? "row" : "column",
        gap: isRow ? "var(--space-md)" : "var(--space-sm)",
        maxWidth: isRow ? 480 : "100%",
        margin: "0 auto",
      }}>
        <div style={{ flex: 1, position: "relative" }}>
          <input
            id="waitlist-email"
            type="email"
            className={`custom-input${state === "error" ? " error" : ""}`}
            value={email}
            onChange={e => { setEmail(e.target.value); if (state === "error") setState("idle"); }}
            placeholder="your@email.com"
            disabled={inputDisabled}
            autoComplete="email"
            maxLength={254}
            aria-label="Email address"
            aria-describedby="waitlist-feedback"
            suppressHydrationWarning
          />
          {/* Success tick overlay */}
          {state === "success" && (
            <span style={{
              position: "absolute", right: 14, top: "50%",
              transform: "translateY(-50%)",
              color: "#00C4A7", fontSize: 18,
            }}>✓</span>
          )}
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-lg"
          disabled={inputDisabled}
          style={{ whiteSpace: "nowrap", minWidth: 160 }}
          suppressHydrationWarning
        >
          {state === "loading" ? (
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{
                width: 14, height: 14, border: "2px solid rgba(255,255,255,0.3)",
                borderTopColor: "white", borderRadius: "50%",
                display: "inline-block",
                animation: "spin 0.8s linear infinite",
              }} />
              Joining…
            </span>
          ) : state === "success" ? "✓ You're in!" : cta}
        </button>
      </div>

      {/* Feedback message */}
      {message && (
        <p
          id="waitlist-feedback"
          role="status"
          aria-live="polite"
          style={{
            fontSize: 13,
            marginTop: "var(--space-md)",
            textAlign: "center",
            color: state === "error"
              ? "#FF4F6E"
              : state === "success"
              ? "#00C4A7"
              : "#9AA3B8",
            fontFamily: "var(--font-mono)",
            transition: "color 200ms ease",
          }}
        >
          {state === "error" && "⚠ "}
          {state === "success" && "🎉 "}
          {state === "already" && "👋 "}
          {message}
        </p>
      )}

      {/* Spin keyframe */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </form>
  );
}
