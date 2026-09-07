import React, { useEffect, useState } from "react";
import "./loading-screen.css";

export function LoadingScreen({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(8);
  useEffect(() => {
    const started = Date.now();
    const timer = window.setInterval(() => {
      const next = Math.min(100, Math.round((Date.now() - started) / 18));
      setProgress(next);
      if (next >= 100) { window.clearInterval(timer); window.setTimeout(onComplete, 220); }
    }, 30);
    return () => window.clearInterval(timer);
  }, [onComplete]);
  return <div className="loading-screen">
    <div className="loader-glow loader-glow-one" /><div className="loader-glow loader-glow-two" />
    <div className="loading-content">
      <div className="nivesh-mark" aria-label="NiveshDesk">
        <svg viewBox="0 0 120 120" role="img" aria-hidden="true">
          <path className="mark-arch" d="M22 92V34c0-7 5-12 12-12h52c7 0 12 5 12 12v58" />
          <path className="mark-n" d="M38 82V45l44 37V43" />
          <path className="mark-growth" d="M57 35c9-13 22-17 35-14-3 13-12 21-27 20" />
          <circle cx="38" cy="92" r="5" /><circle cx="82" cy="92" r="5" />
        </svg>
      </div>
      <span className="loader-eyebrow">PERSONAL MONEY, BEAUTIFULLY ORGANISED</span>
      <h1>NiveshDesk</h1><p>Plan today. Build tomorrow.</p>
      <div className="loader-progress" aria-label={`Loading ${progress}%`}><span style={{ width: `${progress}%` }} /></div>
      <div className="loader-status"><span>{progress < 35 ? "Securing your workspace" : progress < 75 ? "Bringing your money into focus" : "Almost ready"}</span><strong>{progress}%</strong></div>
    </div>
  </div>;
}
