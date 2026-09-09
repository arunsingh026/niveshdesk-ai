import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Dashboard } from "./Dashboard";
import { StockPlanner } from "./StockPlanner";
import { AuthScreen } from "./AuthScreen";
import { AccountUser, API } from "./auth-client";
import { NotificationSettings } from "./NotificationSettings";
import { MonthlyExpenses } from "./MonthlyExpenses";
import { LoadingScreen } from "./LoadingScreen";
import { BudgetPlanner } from "./BudgetPlanner";
import { InvestmentPortfolio } from "./InvestmentPortfolio";
import "./styles.css";
import "./dashboard.css";
import "./auth.css";
import "./notification-settings.css";
import "./monthly-expenses.css";
import "./loading-screen.css";
import "./expenses-workspace.css";
import "./suite-theme.css";
import "./money-workspaces.css";
import "./mobile-responsive.css";

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);
  const [user, setUser] = useState<AccountUser | null>(null);

  useEffect(() => {
    fetch(`${API}/api/auth/me`)
      .then(async response => response.ok ? response.json() : null)
      .then(result => setUser(result?.user || null))
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true));
  }, []);

  const handleLogout = async () => {
    await fetch(`${API}/api/auth/logout`, { method: "POST" }).catch(() => undefined);
    localStorage.removeItem("niveshdesk_push_token");
    setUser(null);
  };

  if (isLoading || !authChecked) {
    return <LoadingScreen onComplete={() => setIsLoading(false)} />;
  }

  if (!user) {
    return <AuthScreen onAuthenticated={setUser} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard onLogout={handleLogout} userName={user.full_name} />} />
        <Route path="/stock-planner" element={<StockPlanner onLogout={handleLogout} />} />
        <Route path="/notifications" element={<NotificationSettings onLogout={handleLogout} />} />
        <Route path="/expenses" element={<MonthlyExpenses onLogout={handleLogout} />} />
        <Route path="/budget" element={<BudgetPlanner onLogout={handleLogout} />} />
        <Route path="/portfolio" element={<InvestmentPortfolio onLogout={handleLogout} />} />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
