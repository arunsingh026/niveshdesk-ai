import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

interface AppStatus {
  name: string;
  description: string;
  icon: string;
  route: string;
  apiUrl: string;
  color: string;
  status: "active" | "inactive" | "checking";
}

interface DashboardProps {
  onLogout?: () => void;
}

export function Dashboard({ onLogout }: DashboardProps) {
  const navigate = useNavigate();
  const [serverRunning, setServerRunning] = useState<"checking" | "running" | "stopped">("checking");
  const [isStarting, setIsStarting] = useState(false);
  const [isBlurred, setIsBlurred] = useState(false);

  // Use the same host as the frontend, but port 8000 for API
  const API_BASE = window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : `http://${window.location.hostname}:8000`;

  const [apps, setApps] = useState<AppStatus[]>([
    {
      name: "Stock Planner",
      description: "Monthly Indian equity investment planner",
      icon: "fa-chart-line",
      route: "/stock-planner",
      apiUrl: `${API_BASE}/health`,
      color: "#10b981",
      status: "checking"
    },
    {
      name: "Monthly Expenses",
      description: "Track and manage monthly expenses",
      icon: "fa-wallet",
      route: "/expenses",
      apiUrl: `${API_BASE}/api/expenses`,
      color: "#3b82f6",
      status: "checking"
    },
    {
      name: "Budget Tracker",
      description: "Personal budget planning tool",
      icon: "fa-calculator",
      route: "/budget",
      apiUrl: "",
      color: "#8b5cf6",
      status: "inactive"
    },
    {
      name: "Investment Portfolio",
      description: "Track all your investments",
      icon: "fa-briefcase",
      route: "/portfolio",
      apiUrl: "",
      color: "#f59e0b",
      status: "inactive"
    },
    {
      name: "Notifications",
      description: "Email & WhatsApp alerts for stocks",
      icon: "fa-bell",
      route: "/notifications",
      apiUrl: `${API_BASE}/api/notifications/status`,
      color: "#8b5cf6",
      status: "checking"
    }
  ]);

  useEffect(() => {
    checkServerStatus();
    checkAppsStatus();
    const serverInterval = setInterval(checkServerStatus, 5000);
    const appsInterval = setInterval(checkAppsStatus, 5000);
    return () => {
      clearInterval(serverInterval);
      clearInterval(appsInterval);
    };
  }, []);

  const checkServerStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/health`, {
        method: "GET",
        signal: AbortSignal.timeout(3000)
      });
      if (response.ok) {
        setServerRunning("running");
      } else {
        setServerRunning("stopped");
      }
    } catch (error) {
      setServerRunning("stopped");
    }
  };

  const handleStartServer = () => {
    setIsStarting(true);
    alert("To start the server:\n\n1. Open File Explorer\n2. Navigate to your project folder\n3. Double-click START.bat\n\nThe server will start automatically!");
    setTimeout(() => {
      setIsStarting(false);
      checkServerStatus();
    }, 2000);
  };

  const checkAppsStatus = async () => {
    try {
      const updatedApps = await Promise.all(
        apps.map(async (app) => {
          if (!app.apiUrl) {
            return { ...app, status: "inactive" as const };
          }
          try {
            const response = await fetch(app.apiUrl, {
              method: "GET",
              signal: AbortSignal.timeout(3000)
            });
            return { ...app, status: response.ok ? "active" as const : "inactive" as const };
          } catch (error) {
            return { ...app, status: "inactive" as const };
          }
        })
      );
      setApps(updatedApps);
    } catch (error) {
      console.error("Failed to check apps status:", error);
    }
  };

  const handleAppClick = (app: AppStatus) => {
    if (app.status === "active") {
      navigate(app.route);
    } else {
      alert(`${app.name} is not available yet. Coming soon!`);
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <div className="logo-section">
            <i className="fas fa-home dashboard-icon"></i>
            <h1>Arun's Personal Dashboard</h1>
          </div>
          <div className="header-controls">
            <div className="server-controls">
              <div className={`status-indicator ${serverRunning}`}>
                <span className="status-dot"></span>
                <span className="status-text">
                  {serverRunning === "checking" && <><i className="fas fa-spinner fa-spin"></i> Checking Server...</>}
                  {serverRunning === "running" && <><i className="fas fa-check-circle"></i> Server Running</>}
                  {serverRunning === "stopped" && <><i className="fas fa-times-circle"></i> Server Stopped</>}
                </span>
              </div>
              {serverRunning === "stopped" && (
                <button onClick={handleStartServer} className="start-server-btn" disabled={isStarting}>
                  <i className="fas fa-play-circle"></i> {isStarting ? "Starting..." : "Start Server"}
                </button>
              )}
              {serverRunning === "running" && (
                <button onClick={checkServerStatus} className="refresh-btn">
                  <i className="fas fa-sync-alt"></i>
                </button>
              )}
            </div>
            <button
              onClick={() => setIsBlurred(!isBlurred)}
              className="privacy-btn"
              title={isBlurred ? "Show content" : "Hide content (Privacy mode)"}
            >
              <i className={`fas ${isBlurred ? "fa-eye" : "fa-eye-slash"}`}></i>
              {isBlurred ? " Show" : " Hide"}
            </button>
            {onLogout && (
              <button onClick={onLogout} className="logout-btn">
                <i className="fas fa-sign-out-alt"></i> Logout
              </button>
            )}
          </div>
        </div>
      </header>

      <div className={`dashboard-container ${isBlurred ? "blurred" : ""}`}>
        <div className="welcome-section">
          <h2>Welcome Back, Arun! 👋</h2>
          <p>Choose an application to get started</p>
        </div>

        <div className="apps-grid">
          {apps.map((app, index) => (
            <div
              key={index}
              className={`app-card ${app.status}`}
              onClick={() => handleAppClick(app)}
              style={{ borderColor: app.color }}
            >
              <div className="app-card-header">
                <div className="app-icon" style={{ background: app.color }}>
                  <i className={`fas ${app.icon}`}></i>
                </div>
                <div className={`app-status-badge ${app.status}`}>
                  {app.status === "checking" && <i className="fas fa-spinner fa-spin"></i>}
                  {app.status === "active" && <i className="fas fa-check-circle"></i>}
                  {app.status === "inactive" && <i className="fas fa-times-circle"></i>}
                  <span>
                    {app.status === "checking" && "Checking"}
                    {app.status === "active" && "Active"}
                    {app.status === "inactive" && "Coming Soon"}
                  </span>
                </div>
              </div>
              <div className="app-card-body">
                <h3>{app.name}</h3>
                <p>{app.description}</p>
              </div>
              <div className="app-card-footer">
                {app.status === "active" ? (
                  <button className="app-launch-btn">
                    <i className="fas fa-arrow-right"></i> Launch
                  </button>
                ) : (
                  <button className="app-launch-btn disabled">
                    <i className="fas fa-lock"></i> Coming Soon
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        <footer className="dashboard-footer">
          <p><i className="fas fa-copyright"></i> {new Date().getFullYear()} Arun Kumar. All rights reserved.</p>
          <p><i className="fas fa-heart" style={{color: '#ef4444'}}></i> Built with passion for productivity</p>
        </footer>
      </div>
    </div>
  );
}
