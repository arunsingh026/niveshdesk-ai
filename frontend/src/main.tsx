import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Dashboard } from "./Dashboard";
import { StockPlanner } from "./StockPlanner";
import { PinAuth } from "./PinAuth";
import { NotificationSettings } from "./NotificationSettings";
import { MonthlyExpenses } from "./MonthlyExpenses";
import { LoadingScreen } from "./LoadingScreen";
import "./styles.css";
import "./dashboard.css";
import "./pin-auth.css";
import "./notification-settings.css";
import "./monthly-expenses.css";
import "./loading-screen.css";
import "./expenses-workspace.css";
import "./suite-theme.css";

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [lastActivity, setLastActivity] = useState(Date.now());
  const INACTIVITY_TIMEOUT = 15 * 60 * 1000; // 15 minutes

  useEffect(() => {
    if (!isAuthenticated) return;

    const checkInactivity = () => {
      const elapsed = Date.now() - lastActivity;
      if (elapsed >= INACTIVITY_TIMEOUT) {
        handleLogout();
      }
    };

    const interval = setInterval(checkInactivity, 60000); // Check every minute

    const resetActivity = () => {
      setLastActivity(Date.now());
    };

    // Track user activity
    window.addEventListener("mousedown", resetActivity);
    window.addEventListener("keydown", resetActivity);
    window.addEventListener("scroll", resetActivity);
    window.addEventListener("touchstart", resetActivity);

    return () => {
      clearInterval(interval);
      window.removeEventListener("mousedown", resetActivity);
      window.removeEventListener("keydown", resetActivity);
      window.removeEventListener("scroll", resetActivity);
      window.removeEventListener("touchstart", resetActivity);
    };
  }, [isAuthenticated, lastActivity]);

  const handleLogout = () => {
    localStorage.removeItem("authTime");
    setIsAuthenticated(false);
  };

  if (isLoading) {
    return <LoadingScreen onComplete={() => setIsLoading(false)} />;
  }

  if (!isAuthenticated) {
    return <PinAuth onAuthenticated={() => setIsAuthenticated(true)} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard onLogout={handleLogout} />} />
        <Route path="/stock-planner" element={<StockPlanner onLogout={handleLogout} />} />
        <Route path="/notifications" element={<NotificationSettings onLogout={handleLogout} />} />
        <Route path="/expenses" element={<MonthlyExpenses onLogout={handleLogout} />} />
        <Route path="/budget" element={<ComingSoon name="Budget Tracker" />} />
        <Route path="/portfolio" element={<ComingSoon name="Investment Portfolio" />} />
      </Routes>
    </BrowserRouter>
  );
}

function ComingSoon({ name }: { name: string }) {
  return (
    <div style={{ padding: "40px", textAlign: "center" }}>
      <h1>🚧 {name}</h1>
      <p>Coming Soon!</p>
      <a href="/">← Back to Dashboard</a>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
