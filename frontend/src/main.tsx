import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";
import { Dashboard } from "./Dashboard";
import { StockPlanner } from "./StockPlanner";
import { AuthScreen } from "./AuthScreen";
import { AccountUser, API } from "./auth-client";
import { NotificationSettings } from "./NotificationSettings";
import { MonthlyExpenses } from "./MonthlyExpenses";
import { LoadingScreen } from "./LoadingScreen";
import { BudgetPlanner } from "./BudgetPlanner";
import { InvestmentPortfolio } from "./InvestmentPortfolio";
import { AdminPage } from "./AdminPage";
import { ChangePasswordScreen } from "./ChangePasswordScreen";
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
import "./admin.css";

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

  if (user.must_change_password) {
    return <ChangePasswordScreen user={user} onChanged={setUser} onLogout={handleLogout} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard onLogout={handleLogout} userName={user.full_name} isAdmin={user.role === "admin"} />} />
        <Route path="/stock-planner" element={<StockPlanner onLogout={handleLogout} />} />
        <Route path="/notifications" element={<NotificationSettings onLogout={handleLogout} />} />
        <Route path="/expenses" element={<MonthlyExpenses onLogout={handleLogout} />} />
        <Route path="/budget" element={<BudgetPlanner onLogout={handleLogout} />} />
        <Route path="/portfolio" element={<InvestmentPortfolio onLogout={handleLogout} />} />
        <Route path="/admin" element={user.role === "admin" ? <AdminPage onLogout={handleLogout} currentUserId={user.id} /> : <Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
