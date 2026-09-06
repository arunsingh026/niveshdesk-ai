import React, { useEffect, useState } from "react";
import "./loading-screen.css";

export function LoadingScreen({ onComplete }: { onComplete: () => void }) {
  const [stage, setStage] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Stage progression
    const stageTimer = setInterval(() => {
      setStage((prev) => {
        if (prev >= 3) {
          clearInterval(stageTimer);
          setTimeout(onComplete, 1500); // Changed from 800 to 1500ms to see the final stage longer
          return prev;
        }
        return prev + 1;
      });
    }, 800); // Changed from 600 to 800ms for slower progression

    // Progress bar
    const progressTimer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressTimer);
          return 100;
        }
        return prev + 2;
      });
    }, 30);

    return () => {
      clearInterval(stageTimer);
      clearInterval(progressTimer);
    };
  }, [onComplete]);

  return (
    <div className="loading-screen">
      <div className="loading-content">
        {/* Logo Animation */}
        <div className="logo-stages">
          <div className={`logo-stage ${stage >= 0 ? "active" : ""}`}>
            <div className="logo-circle">
              <svg viewBox="0 0 100 100" className="logo-a-simple">
                <path
                  d="M30 80 L45 30 L55 30 L70 80 M35 60 L65 60"
                  stroke="url(#gradient1)"
                  strokeWidth="8"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <defs>
                  <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#a855f7" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
          </div>

          <div className={`logo-stage ${stage >= 1 ? "active" : ""}`}>
            <div className="logo-circle spinning">
              <svg viewBox="0 0 100 100" className="logo-a-gradient">
                <defs>
                  <linearGradient id="gradient2" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#06b6d4" />
                    <stop offset="50%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#a855f7" />
                  </linearGradient>
                </defs>
                <path
                  d="M30 80 L45 30 L55 30 L70 80 M35 60 L65 60"
                  stroke="url(#gradient2)"
                  strokeWidth="10"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <div className="spinner-ring"></div>
            </div>
          </div>

          <div className={`logo-stage ${stage >= 2 ? "active" : ""}`}>
            <div className="logo-circle with-arrow">
              <svg viewBox="0 0 120 120" className="logo-complete">
                <defs>
                  <linearGradient id="gradient3" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#06b6d4" />
                    <stop offset="50%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#a855f7" />
                  </linearGradient>
                </defs>
                {/* Letter A */}
                <path
                  d="M35 85 L50 35 L60 35 L75 85 M40 65 L70 65"
                  stroke="url(#gradient3)"
                  strokeWidth="11"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {/* Arrow */}
                <path
                  d="M65 25 L100 55 M100 55 L75 60 M100 55 L95 30"
                  stroke="#10b981"
                  strokeWidth="5"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="arrow-path"
                />
              </svg>
            </div>
          </div>

          <div className={`logo-stage ${stage >= 3 ? "active" : ""}`}>
            <div className="logo-dashboard">
              <div className="dashboard-card">
                <svg viewBox="0 0 120 120" className="logo-main">
                  <defs>
                    <linearGradient id="gradient4" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#06b6d4" />
                      <stop offset="50%" stopColor="#3b82f6" />
                      <stop offset="100%" stopColor="#a855f7" />
                    </linearGradient>
                  </defs>
                  <path
                    d="M35 85 L50 35 L60 35 L75 85 M40 65 L70 65"
                    stroke="url(#gradient4)"
                    strokeWidth="11"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M65 25 L100 55 M100 55 L75 60 M100 55 L95 30"
                    stroke="#10b981"
                    strokeWidth="5"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <div className="dashboard-icons">
                  <div className="mini-icon chart-icon">
                    <i className="fas fa-chart-bar"></i>
                  </div>
                  <div className="mini-icon trend-icon">
                    <i className="fas fa-arrow-trend-up"></i>
                  </div>
                  <div className="mini-icon wallet-icon">
                    <i className="fas fa-wallet"></i>
                  </div>
                  <div className="mini-icon bell-icon">
                    <i className="fas fa-bell"></i>
                  </div>
                  <div className="mini-icon calendar-icon">
                    <i className="fas fa-calendar"></i>
                  </div>
                </div>
              </div>
              <h1 className="brand-title">ARUN'S</h1>
              <p className="brand-subtitle">PERSONAL DASHBOARD</p>
              <div className="brand-tagline">
                <span style={{ color: "#3b82f6" }}>PLAN</span>
                <span style={{ color: "#667085" }}> • </span>
                <span style={{ color: "#a855f7" }}>TRACK</span>
                <span style={{ color: "#667085" }}> • </span>
                <span style={{ color: "#10b981" }}>ACHIEVE</span>
              </div>
            </div>
          </div>
        </div>

        {/* Loading text */}
        <div className="loading-text">
          {stage === 0 && "Loading..."}
          {stage === 1 && "Loading..."}
          {stage === 2 && "Loading..."}
          {stage === 3 && (
            <>
              <div className="loading-status">Getting things ready...</div>
              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </>
          )}
        </div>

        {/* Progress bar */}
        <div className="progress-container">
          <div className="progress-bar" style={{ width: `${progress}%` }}></div>
        </div>
        {stage === 3 && <div className="almost-there">Almost there...</div>}
      </div>
    </div>
  );
}