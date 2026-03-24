"use client";

import { useEffect, useState, useRef } from "react";
import UrlInput from "@/components/url-input";

export default function Home() {
  const [navScrolled, setNavScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const scoreRef = useRef<HTMLSpanElement>(null);
  const [scoreAnimated, setScoreAnimated] = useState(false);

  useEffect(() => {
    // Nav scroll effect
    const handleScroll = () => {
      setNavScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", handleScroll);
    handleScroll();

    // Scroll reveal
    const reveals = document.querySelectorAll(".reveal");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("visible");
            observer.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    reveals.forEach((el) => observer.observe(el));

    // Waveform hover animation on player
    const waveBars = document.querySelectorAll(".wave-bar");
    const waveInterval = setInterval(() => {
      waveBars.forEach((bar) => {
        const r = Math.random();
        if (r > 0.85) {
          bar.classList.add("highlight");
          bar.classList.remove("active");
        } else if (r > 0.5) {
          bar.classList.add("active");
          bar.classList.remove("highlight");
        } else {
          bar.classList.remove("highlight", "active");
        }
      });
    }, 900);

    // Viral score counter animation
    const scoreObs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !scoreAnimated) {
        setScoreAnimated(true);
        let val = 60;
        const target = 94;
        const inc = setInterval(() => {
          if (scoreRef.current) {
            scoreRef.current.textContent = val.toString();
          }
          if (val >= target) clearInterval(inc);
          val = Math.min(val + 2, target);
        }, 40);
      }
    });

    if (scoreRef.current) scoreObs.observe(scoreRef.current);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      observer.disconnect();
      clearInterval(waveInterval);
      scoreObs.disconnect();
    };
  }, [scoreAnimated]);

  const toggleMenu = () => {
    setMenuOpen(!menuOpen);
    document.body.style.overflow = !menuOpen ? "hidden" : "";
  };

  const closeMobileNav = () => {
    setMenuOpen(false);
    document.body.style.overflow = "";
  };

  return (
    <>
      {/* ─── NAVIGATION ─── */}
      <nav className={`nav ${navScrolled ? "scrolled" : ""}`} id="navbar">
        <div className="container">
          <div className="nav-inner">
            <a href="#" className="nav-logo anim-fade-up">
              <span className="nav-logo-mark">⚡</span>
              ClipForge
            </a>
            <ul className="nav-links anim-fade-in anim-delay-1">
              <li>
                <a href="#features">Features</a>
              </li>
              <li>
                <a href="#how">How it works</a>
              </li>
              <li>
                <a href="#pricing">Pricing</a>
              </li>
              <li>
                <a href="#docs">Docs</a>
              </li>
            </ul>
            <div className="nav-actions anim-fade-in anim-delay-2">
              <a href="#" className="btn btn-ghost">
                Log in
              </a>
              <a href="#cta" className="btn btn-primary">
                Get early access
              </a>
            </div>
            <button
              className="hamburger"
              id="menuBtn"
              aria-label="Open menu"
              onClick={toggleMenu}
            >
              <span></span>
              <span></span>
              <span></span>
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Nav */}
      <div className={`mobile-nav ${menuOpen ? "open" : ""}`} id="mobileNav">
        <a href="#features" onClick={closeMobileNav}>
          Features
        </a>
        <a href="#how" onClick={closeMobileNav}>
          How it works
        </a>
        <a href="#pricing" onClick={closeMobileNav}>
          Pricing
        </a>
        <a
          href="#cta"
          onClick={closeMobileNav}
          style={{ color: "var(--color-forge)" }}
        >
          Get early access →
        </a>
      </div>

      {/* ─── HERO ─── */}
      <section className="hero">
        <div className="container">
          <div className="hero-inner">
            {/* Left: Copy */}
            <div className="hero-copy">
              <div className="hero-eyebrow anim-fade-up">
                <span className="badge badge-forge badge-dot">Now in beta</span>
                <span className="badge badge-spark">🏆 #1 on Product Hunt</span>
              </div>

              <h1 className="hero-title anim-fade-up anim-delay-1">
                Your podcast.<br />
                <em>Engineered</em><br />
                to go viral.
              </h1>

              <p className="hero-sub anim-fade-up anim-delay-2">
                ClipForge uses AI to scan every minute of your podcast, extract
                the 40–60 second moments that hook audiences, and generate
                frame-perfect editing blueprints — in seconds.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "28px", marginTop: "40px" }} className="anim-fade-up anim-delay-3 w-full max-w-lg">
                <div className="hero-actions" style={{ marginBottom: 0 }}>
                  <a href="#cta" className="btn btn-primary btn-lg">
                    Start clipping free
                    <span>→</span>
                  </a>
                  <a href="#how" className="btn btn-secondary btn-lg">
                    See how it works
                  </a>
                </div>

                <div className="w-full anim-fade-up anim-delay-4">
                  <UrlInput />
                </div>
              </div>

              <div className="hero-note anim-fade-in anim-delay-5" style={{ marginTop: "32px", marginBottom: "32px" }}>
                No credit card. Free 5 clips per month. Cancel anytime.
              </div>
            </div>

            {/* Right: Visual */}
            <div className="hero-visual anim-fade-up anim-delay-2">
              {/* Floating stat cards */}
              <div className="hero-float-card card-a">
                <div className="float-label">Viral Score</div>
                <div className="float-value spark">94 / 100</div>
              </div>
              <div className="hero-float-card card-b">
                <div className="float-label">Processing time</div>
                <div className="float-value forge">4.2s ⚡</div>
              </div>

              {/* Main player card */}
              <div className="clip-player">
                <div className="clip-player-header">
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ color: "var(--color-forge)", fontSize: "18px" }}>
                      ▶
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "12px",
                        color: "var(--text-secondary)",
                      }}
                    >
                      ep_247_huberman_sleep.mp3
                    </span>
                  </div>
                  <span className="badge badge-forge" style={{ fontSize: "10px" }}>
                    AI Scanning
                  </span>
                </div>

                {/* Waveform */}
                <div className="clip-waveform">
                  <div className="clip-highlight-region"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar active"></div>
                  <div className="wave-bar active"></div>
                  <div className="wave-bar highlight"></div>
                  <div className="wave-bar highlight"></div>
                  <div className="wave-bar highlight"></div>
                  <div className="wave-bar highlight"></div>
                  <div className="wave-bar highlight"></div>
                  <div className="wave-bar highlight"></div>
                  <div className="wave-bar highlight"></div>
                  <div className="wave-bar highlight"></div>
                  <div className="wave-bar active"></div>
                  <div className="wave-bar active"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                </div>

                {/* Clip meta */}
                <div className="clip-meta">
                  <div className="clip-score">
                    <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                      VIRAL SCORE
                    </span>
                    <span className="clip-score-value" ref={scoreRef}>
                      94
                    </span>
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--text-muted)",
                    }}
                  >
                    12:34 → 13:19 ·{" "}
                    <span style={{ color: "var(--color-forge)" }}>45s</span>
                  </div>
                </div>

                {/* Hook chips */}
                <div className="clip-chips">
                  <span className="chip hot">🔥 Strong hook</span>
                  <span className="chip warm">💡 Counterintuitive take</span>
                  <span className="chip">High energy</span>
                  <span className="chip warm">⚡ Cliffhanger</span>
                  <span className="chip">Clear CTA</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── SOCIAL PROOF BAR ─── */}
      <div className="proof-bar">
        <div className="proof-track-wrap">
          <div className="proof-track" id="proofTrack">
            {/* Set 1 */}
            <div className="proof-stat">
              <span className="proof-stat-number">2.4M+</span>
              <span className="proof-stat-label">Clips Generated</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">18K</span>
              <span className="proof-stat-label">Creators</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">94%</span>
              <span className="proof-stat-label">Avg. Viral Score</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">4.2s</span>
              <span className="proof-stat-label">Avg. Process Time</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">340%</span>
              <span className="proof-stat-label">Reach Increase</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">12+</span>
              <span className="proof-stat-label">Platforms Supported</span>
            </div>
            <div className="proof-divider"></div>
            {/* Set 2 (duplicate for seamless loop) */}
            <div className="proof-stat">
              <span className="proof-stat-number">2.4M+</span>
              <span className="proof-stat-label">Clips Generated</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">18K</span>
              <span className="proof-stat-label">Creators</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">94%</span>
              <span className="proof-stat-label">Avg. Viral Score</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">4.2s</span>
              <span className="proof-stat-label">Avg. Process Time</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">340%</span>
              <span className="proof-stat-label">Reach Increase</span>
            </div>
            <div className="proof-divider"></div>
            <div className="proof-stat">
              <span className="proof-stat-number">12+</span>
              <span className="proof-stat-label">Platforms Supported</span>
            </div>
          </div>
        </div>
      </div>

      {/* ─── FEATURES ─── */}
      <section className="section" id="features">
        <div className="container">
          <div className="section-header reveal">
            <span className="badge badge-wave">Features</span>
            <h2>
              Everything a clip<br />
              needs to dominate.
            </h2>
            <p>
              From raw audio to ready-to-post clip blueprint — ClipForge
              handles the intelligence. You just hit export.
            </p>
          </div>

          <div className="features-grid">
            {/* Wide card */}
            <div
              className="feature-card wide reveal reveal-delay-1"
              style={{ "--accent": "var(--color-forge)" } as React.CSSProperties}
            >
              <div className="feature-inner">
                <div>
                  <div
                    className="feature-icon"
                    style={
                      {
                        "--icon-bg": "rgba(255,79,31,0.1)",
                        "--icon-border": "rgba(255,79,31,0.25)",
                      } as React.CSSProperties
                    }
                  >
                    🎯
                  </div>
                  <h4>AI Viral Detection</h4>
                  <p>
                    Our model scans transcripts, audio energy, pacing, and
                    semantic meaning to pinpoint the exact 40–60 seconds most
                    likely to stop a thumb mid-scroll.
                  </p>
                </div>
                <div className="feature-visual">
                  <div className="blueprint-line active medium"></div>
                  <div className="blueprint-line short"></div>
                  <div className="blueprint-line active"></div>
                  <div className="blueprint-line spark"></div>
                  <div className="blueprint-line medium"></div>
                  <div className="blueprint-line active short"></div>
                  <div
                    style={{
                      position: "absolute",
                      bottom: "12px",
                      right: "12px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      color: "var(--color-forge)",
                    }}
                  >
                    Viral Score: 94 ↑
                  </div>
                </div>
              </div>
            </div>

            {/* Regular cards */}
            <div
              className="feature-card reveal reveal-delay-2"
              style={{ "--accent": "var(--color-spark)" } as React.CSSProperties}
            >
              <div
                className="feature-icon"
                style={
                  {
                    "--icon-bg": "rgba(255,214,10,0.08)",
                    "--icon-border": "rgba(255,214,10,0.2)",
                  } as React.CSSProperties
                }
              >
                📋
              </div>
              <h4>Editing Blueprints</h4>
              <p>
                Receive precise cut-lists, caption suggestions, B-roll cues, and
                music fade points — formatted for Premiere, DaVinci, or CapCut.
              </p>
            </div>

            <div
              className="feature-card reveal"
              style={{ "--accent": "var(--color-wave)" } as React.CSSProperties}
            >
              <div
                className="feature-icon"
                style={
                  {
                    "--icon-bg": "rgba(0,196,167,0.08)",
                    "--icon-border": "rgba(0,196,167,0.2)",
                  } as React.CSSProperties
                }
              >
                📊
              </div>
              <h4>Hook Scoring</h4>
              <p>
                Every identified clip gets a breakdown: hook strength, retention
                prediction, emotional arc, and platform fit score for TikTok,
                Reels, and YouTube Shorts.
              </p>
            </div>

            <div
              className="feature-card reveal reveal-delay-1"
              style={{ "--accent": "var(--color-forge)" } as React.CSSProperties}
            >
              <div
                className="feature-icon"
                style={
                  {
                    "--icon-bg": "rgba(255,79,31,0.1)",
                    "--icon-border": "rgba(255,79,31,0.25)",
                  } as React.CSSProperties
                }
              >
                ⚡
              </div>
              <h4>Lightning Processing</h4>
              <p>
                A 60-minute episode is fully analyzed in under 5 seconds. No
                queue. No waiting. Batch up to 10 episodes simultaneously.
              </p>
            </div>

            <div
              className="feature-card reveal reveal-delay-2"
              style={{ "--accent": "var(--color-spark)" } as React.CSSProperties}
            >
              <div
                className="feature-icon"
                style={
                  {
                    "--icon-bg": "rgba(255,214,10,0.08)",
                    "--icon-border": "rgba(255,214,10,0.2)",
                  } as React.CSSProperties
                }
              >
                🔌
              </div>
              <h4>One-Click Integrations</h4>
              <p>
                Connect your RSS feed, Riverside, Descript, or Buzzsprout.
                ClipForge pulls new episodes automatically the moment they drop.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* DIVIDER */}
      <div className="divider"></div>

      {/* ─── HOW IT WORKS ─── */}
      <section className="section" id="how">
        <div className="container">
          <div className="section-header center reveal">
            <span className="badge badge-forge">Process</span>
            <h2>
              From upload to blueprint<br />
              in 3 steps.
            </h2>
            <p>
              No editing skills needed. No watching through hours of footage.
              Just results.
            </p>
          </div>

          <div className="how-grid">
            <div className="how-connector"></div>

            <div className="how-step reveal">
              <div className="how-step-num">01</div>
              <h4>Upload your episode</h4>
              <p>
                Drop in an MP3, M4A, or paste your RSS feed. We accept any
                podcast format.
              </p>
            </div>

            <div className="how-step reveal reveal-delay-1">
              <div
                className="how-step-num"
                style={{ color: "var(--color-spark)" }}
              >
                02
              </div>
              <h4>AI finds the moments</h4>
              <p>
                ClipForge scans for narrative peaks, high-energy exchanges, and
                scroll-stopping statements.
              </p>
            </div>

            <div className="how-step reveal reveal-delay-2">
              <div
                className="how-step-num"
                style={{ color: "var(--color-wave)" }}
              >
                03
              </div>
              <h4>Export your blueprint</h4>
              <p>
                Receive a complete editing guide: timestamps, captions, music
                cues, and viral scores. Ready to edit.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* DIVIDER GLOW */}
      <div className="divider divider-glow"></div>

      {/* ─── TESTIMONIAL ─── */}
      <section className="section">
        <div className="container">
          <div className="testimonial-wrap reveal">
            <p className="testimonial-quote">
              &quot;I went from spending <span>4 hours</span> manually finding
              clips to getting <span>8 perfect moments</span> in 30 seconds.
              ClipForge basically replaced my entire post-production workflow.&quot;
            </p>
            <div className="testimonial-author">
              <div className="testimonial-avatar">JR</div>
              <div className="testimonial-meta">
                <div className="testimonial-name">Jordan Reeves</div>
                <div className="testimonial-title">
                  Host, The Optimization Podcast · 220K subscribers
                </div>
              </div>
              <div className="badge badge-spark" style={{ marginLeft: "auto" }}>
                ★★★★★
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── CTA SECTION ─── */}
      <section className="cta-section" id="cta">
        <div className="container">
          <div className="cta-inner reveal">
            <span
              className="badge badge-forge badge-dot"
              style={{ marginBottom: "var(--space-xl)", display: "inline-flex" }}
            >
              Early access open
            </span>
            <h2>
              Ready to forge<br />
              your first viral clip?
            </h2>
            <p>
              Join 18,000 creators already using ClipForge. Free to start — no
              credit card required.
            </p>
            <div className="cta-input-row">
              <input
                className="custom-input"
                type="email"
                placeholder="you@podcast.com"
                suppressHydrationWarning
              />
              <button className="btn btn-primary btn-lg" suppressHydrationWarning>Notify me</button>
            </div>
            <p className="cta-small">
              Free plan: 5 clips/month · No card needed · Cancel anytime
            </p>
          </div>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer className="footer">
        <div className="container">
          <div className="footer-grid">
            <div className="footer-brand">
              <a href="#" className="nav-logo" style={{ fontSize: "1.125rem" }}>
                <span
                  className="nav-logo-mark"
                  style={{ width: "28px", height: "28px", fontSize: "14px" }}
                >
                  ⚡
                </span>
                ClipForge
              </a>
              <p>
                AI-powered podcast clipping that finds your viral moments and
                engineers the perfect edit — automatically.
              </p>
            </div>
            <div className="footer-col">
              <h6>Product</h6>
              <ul className="footer-links">
                <li>
                  <a href="#">Features</a>
                </li>
                <li>
                  <a href="#">Pricing</a>
                </li>
                <li>
                  <a href="#">Integrations</a>
                </li>
                <li>
                  <a href="#">Changelog</a>
                </li>
                <li>
                  <a href="#">Roadmap</a>
                </li>
              </ul>
            </div>
            <div className="footer-col">
              <h6>Resources</h6>
              <ul className="footer-links">
                <li>
                  <a href="#">Documentation</a>
                </li>
                <li>
                  <a href="#">API Reference</a>
                </li>
                <li>
                  <a href="#">Blog</a>
                </li>
                <li>
                  <a href="#">Case Studies</a>
                </li>
                <li>
                  <a href="#">Status</a>
                </li>
              </ul>
            </div>
            <div className="footer-col">
              <h6>Company</h6>
              <ul className="footer-links">
                <li>
                  <a href="#">About</a>
                </li>
                <li>
                  <a href="#">Careers</a>
                </li>
                <li>
                  <a href="#">Privacy</a>
                </li>
                <li>
                  <a href="#">Terms</a>
                </li>
                <li>
                  <a href="#">Contact</a>
                </li>
              </ul>
            </div>
          </div>

          <div className="footer-bottom">
            <span className="footer-copy">
              © 2026 ClipForge, Inc. — All rights reserved.
            </span>
            <div className="footer-socials">
              <button
                className="footer-social-btn"
                aria-label="Twitter/X"
                suppressHydrationWarning
              >
                𝕏
              </button>
              <button className="footer-social-btn" aria-label="LinkedIn" suppressHydrationWarning>
                in
              </button>
              <button className="footer-social-btn" aria-label="YouTube" suppressHydrationWarning>
                ▶
              </button>
              <button className="footer-social-btn" aria-label="GitHub" suppressHydrationWarning>
                ⌥
              </button>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
