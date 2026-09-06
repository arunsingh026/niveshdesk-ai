import React from "react";
import { useNavigate } from "react-router-dom";

export function WorkspaceHeader({ section, onLogout }: { section: string; onLogout?: () => void }) {
  const navigate = useNavigate();
  return <nav className="suite-topbar" aria-label="Main navigation">
    <button className="suite-back" onClick={() => navigate("/")}><i className="fas fa-arrow-left" /> Dashboard</button>
    <div className="suite-brand"><span>S</span><strong>Stock Planner</strong><b>/</b><small>{section}</small></div>
    <div className="suite-links">
      <button aria-current={section === "Stocks & funds" ? "page" : undefined} onClick={() => navigate("/stock-planner")}>Investments</button>
      <button aria-current={section === "Expenses" ? "page" : undefined} onClick={() => navigate("/expenses")}>Expenses</button>
      <button aria-current={section === "Notifications" ? "page" : undefined} onClick={() => navigate("/notifications")}>Notifications</button>
    </div>
    {onLogout && <button className="suite-logout" onClick={onLogout}><i className="fas fa-sign-out-alt" /> Logout</button>}
  </nav>;
}
