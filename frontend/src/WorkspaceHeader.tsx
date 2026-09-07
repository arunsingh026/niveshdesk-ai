import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

const mobileDestinations = [
  { route: "/", label: "Home", icon: "fa-house" },
  { route: "/stock-planner", label: "Invest", icon: "fa-chart-line" },
  { route: "/expenses", label: "Expenses", icon: "fa-wallet" },
  { route: "/budget", label: "Budget", icon: "fa-calculator" },
  { route: "/portfolio", label: "Portfolio", icon: "fa-briefcase" },
];

export function MobileTabBar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  return <nav className="suite-mobile-tabs" aria-label="Mobile navigation">
    {mobileDestinations.map(item => <button key={item.route} aria-current={pathname === item.route ? "page" : undefined} onClick={() => navigate(item.route)}>
      <i className={`fas ${item.icon}`} aria-hidden="true" /><span>{item.label}</span>
    </button>)}
  </nav>;
}

export function WorkspaceHeader({ section, onLogout }: { section: string; onLogout?: () => void }) {
  const navigate = useNavigate();
  return <>
    <nav className="suite-topbar" aria-label="Main navigation">
      <button className="suite-back" onClick={() => navigate("/")} aria-label="Back to dashboard"><i className="fas fa-arrow-left" /><span>Dashboard</span></button>
      <div className="suite-brand"><span>N</span><strong>NiveshDesk</strong><b>/</b><small>{section}</small></div>
      <div className="suite-links">
        <button aria-current={section === "Stocks & funds" ? "page" : undefined} onClick={() => navigate("/stock-planner")}>Investments</button>
        <button aria-current={section === "Expenses" ? "page" : undefined} onClick={() => navigate("/expenses")}>Expenses</button>
        <button aria-current={section === "Budget" ? "page" : undefined} onClick={() => navigate("/budget")}>Budget</button>
        <button aria-current={section === "Portfolio" ? "page" : undefined} onClick={() => navigate("/portfolio")}>Portfolio</button>
        <button aria-current={section === "Notifications" ? "page" : undefined} onClick={() => navigate("/notifications")}>Notifications</button>
      </div>
      <button className="suite-mobile-action" aria-current={section === "Notifications" ? "page" : undefined} onClick={() => navigate("/notifications")} aria-label="Notifications"><i className="fas fa-bell" /></button>
      {onLogout && <button className="suite-logout" onClick={onLogout} aria-label="Log out"><i className="fas fa-sign-out-alt" /><span>Logout</span></button>}
    </nav>
    <MobileTabBar />
  </>;
}
