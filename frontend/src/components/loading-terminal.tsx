"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

// The pipeline steps we expect from the backend
const PIPELINE_STEPS = [
  { id: "initialized", label: "Initializing pipeline" },
  { id: "transcript_downloaded", label: "Fetching YouTube transcript" },
  { id: "transcript_processed", label: "Cleaning and processing audio" },
  { id: "clips_discovered", label: "AI scanning for viral hooks" },
  { id: "clips_validated", label: "Evaluating retention dynamics" },
  { id: "editing_plans_generated", label: "Generating blueprints" },
  { id: "completed", label: "Finalizing" }
];

const FUN_FACTS = [
  "Did you know? Videos with strong hooks in the first 3 seconds retain 70% more viewers.",
  "AI is currently reading a transcript equivalent to a short novel. Give it a minute!",
  "A good viral clip combines a curiosity gap with a satisfying payoff.",
  "We use an adaptive rate limiter to play nice with the AI APIs while processing your video.",
  "ClipForge analyzes emotional peaks, pacing, and semantic meaning to find the best moments.",
  "Short-form video is the fastest growing format across YouTube, TikTok, and Instagram.",
];

interface LoadingTerminalProps {
  status: string;
}

export default function LoadingTerminal({ status }: LoadingTerminalProps) {
  const [factIndex, setFactIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  // Rotate facts every 6 seconds
  useEffect(() => {
    const factInterval = setInterval(() => {
      setFactIndex((prev) => (prev + 1) % FUN_FACTS.length);
    }, 6000);
    return () => clearInterval(factInterval);
  }, []);

  // Simple elapsed timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Determine current step index
  const currentStepIndex = PIPELINE_STEPS.findIndex((s) => s.id === status);
  const activeIndex = currentStepIndex === -1 ? 0 : currentStepIndex;

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="card anim-fade-up" style={{ 
      padding: "32px", 
      background: "var(--color-bg-secondary)", 
      border: "1px solid var(--color-slate-border)",
      display: "flex", 
      flexDirection: "column", 
      gap: "32px",
      width: "100%",
      position: "relative",
      overflow: "hidden"
    }}>
      {/* Animated glow background */}
      <div style={{
        position: "absolute",
        top: "-50%",
        left: "-50%",
        width: "200%",
        height: "200%",
        background: "radial-gradient(circle at 50% 50%, rgba(255, 79, 31, 0.05) 0%, transparent 60%)",
        animation: "pulse-slow 4s infinite alternate",
        pointerEvents: "none"
      }} />

      {/* Header section with scanning animation */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "48px",
            height: "48px",
            borderRadius: "50%",
            background: "rgba(255, 79, 31, 0.1)",
            border: "1px solid rgba(255, 79, 31, 0.2)"
          }}>
            <Loader2 className="animate-spin" size={24} color="var(--color-forge)" />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: "18px", letterSpacing: "-0.01em" }}>Analyzing Video</h3>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", marginTop: "4px" }}>
              Deep semantic scan in progress
            </p>
          </div>
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "14px", color: "var(--color-spark)", textAlign: "right" }}>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "2px" }}>ELAPSED</div>
          {formatTime(elapsed)}
        </div>
      </div>

      {/* Progress Stepper */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", position: "relative", zIndex: 1 }}>
        {PIPELINE_STEPS.map((step, index) => {
          const isCompleted = index < activeIndex;
          const isActive = index === activeIndex;
          const isPending = index > activeIndex;

          return (
            <div key={step.id} style={{ 
              display: "flex", 
              alignItems: "center", 
              gap: "12px",
              opacity: isPending ? 0.4 : 1,
              transform: isActive ? "scale(1.02)" : "scale(1)",
              transition: "all 0.3s ease"
            }}>
              {/* Checkmark or Spinner */}
              <div style={{ 
                width: "20px", 
                height: "20px", 
                borderRadius: "50%", 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center",
                background: isCompleted ? "rgba(0, 196, 167, 0.1)" : isActive ? "rgba(255, 79, 31, 0.1)" : "var(--color-slate-border)",
                border: `1px solid ${isCompleted ? "rgba(0, 196, 167, 0.5)" : isActive ? "var(--color-forge)" : "transparent"}`,
                fontSize: "10px",
                color: isCompleted ? "var(--color-wave)" : "var(--text-primary)"
              }}>
                {isCompleted ? "✓" : isActive ? <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--color-forge)", animation: "pulse 1.5s infinite" }} /> : null}
              </div>
              
              <span style={{ 
                fontSize: "14px", 
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                fontWeight: isActive ? 600 : 400
              }}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Rotating Facts Carousel */}
      <div style={{ 
        marginTop: "16px",
        paddingTop: "24px",
        borderTop: "1px solid var(--color-slate-border)",
        position: "relative",
        zIndex: 1
      }}>
        <div style={{ fontSize: "11px", color: "var(--color-spark)", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "8px" }}>
          Did you know?
        </div>
        <div style={{ height: "40px", position: "relative" }}>
          {FUN_FACTS.map((fact, idx) => (
            <p 
              key={idx}
              style={{ 
                margin: 0, 
                fontSize: "13px", 
                color: "var(--text-secondary)", 
                lineHeight: 1.5,
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                opacity: idx === factIndex ? 1 : 0,
                transform: idx === factIndex ? "translateY(0)" : "translateY(10px)",
                transition: "all 0.5s ease"
              }}
            >
              {fact}
            </p>
          ))}
        </div>
        <div style={{ marginTop: "12px", fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          * This process takes ~3.5 minutes for a 1-hour podcast.
        </div>
      </div>
    </div>
  );
}
