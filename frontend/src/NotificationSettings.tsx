import { WorkspaceHeader } from "./WorkspaceHeader";
import React, { useState, useEffect } from "react";

interface NotificationStatus {
  email_enabled: boolean;
  email_configured: boolean;
  whatsapp_enabled: boolean;
  whatsapp_configured: boolean;
  telegram_enabled: boolean;
  telegram_configured: boolean;
}

interface NotificationSettingsProps {
  onLogout?: () => void;
}

// Use the same host as the frontend, but port 8000 for API
const getApiUrl = () => {
  return window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : `http://${window.location.hostname}:8000`;
};

const API = getApiUrl();

export function NotificationSettings({ onLogout }: NotificationSettingsProps) {
  const [status, setStatus] = useState<NotificationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const response = await fetch(`${API}/api/notifications/status`);
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      setMessage("Failed to load notification status");
    } finally {
      setLoading(false);
    }
  };

  const sendTestNotification = async () => {
    setSending(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/api/notifications/send`, {
        method: "POST"
      });
      const data = await response.json();

      if (data.result.email || data.result.whatsapp) {
        setMessage(`✅ Notifications sent successfully! (${data.result.buy_count} stocks)`);
      } else {
        setMessage("⚠️ No notifications sent. Please configure email/WhatsApp settings.");
      }
    } catch (error) {
      setMessage("❌ Failed to send notifications");
    } finally {
      setSending(false);
    }
  };

  const getStatusBadge = (enabled: boolean, configured: boolean) => {
    if (!enabled) {
      return <span className="status-badge disabled">Disabled</span>;
    }
    if (!configured) {
      return <span className="status-badge not-configured">Not Configured</span>;
    }
    return <span className="status-badge active">Active</span>;
  };

  return (
    <main className="app-workspace notification-workspace">
      <WorkspaceHeader section="Notifications" onLogout={onLogout} />
      <div className="suite-content">

      <div className="notification-settings">
        <div className="suite-page-heading"><span className="suite-eyebrow">STAY IN THE KNOW</span><h1>Notification Settings</h1><p>Your investment updates, delivered where you need them.</p></div>

        {loading ? (
          <div className="loading-state">
            <i className="fas fa-spinner fa-spin"></i> Loading...
          </div>
        ) : (
          <>
            <div className="settings-cards">
              <div className="settings-card">
                <div className="card-icon email">
                  <i className="fas fa-envelope"></i>
                </div>
                <div className="card-content">
                  <h3>Email Notifications</h3>
                  <p>A detailed summary of your stock recommendations, delivered to your inbox.</p>
                  {getStatusBadge(status?.email_enabled || false, status?.email_configured || false)}
                </div>
              </div>

              <div className="settings-card">
                <div className="card-icon telegram">
                  <i className="fab fa-telegram"></i>
                </div>
                <div className="card-content">
                  <h3>Telegram Notifications</h3>
                  <p>Receive stock updates in your Telegram bot conversation.</p>
                  {getStatusBadge(status?.telegram_enabled || false, status?.telegram_configured || false)}
                </div>
              </div>

              <div className="settings-card">
                <div className="card-icon whatsapp">
                  <i className="fab fa-whatsapp"></i>
                </div>
                <div className="card-content">
                  <h3>WhatsApp Notifications</h3>
                  <p>Receive stock alerts through your configured WhatsApp channel.</p>
                  {getStatusBadge(status?.whatsapp_enabled || false, status?.whatsapp_configured || false)}
                </div>
              </div>
            </div>

            <div className="action-section"><div className="delivery-copy"><h2>Check your delivery</h2><p>Send the current stock recommendations to your enabled channels.</p><small>Disabled channels will not receive messages.</small></div>
              <button onClick={sendTestNotification} disabled={sending} className="send-notification-btn">
                {sending ? (
                  <>
                    <i className="fas fa-spinner fa-spin"></i> Sending...
                  </>
                ) : (
                  <>
                    <i className="fas fa-paper-plane"></i> Send Test Notification
                  </>
                )}
              </button>

              {message && (
                <div className={`notification-message ${message.startsWith("✅") ? "success" : message.startsWith("⚠️") ? "warning" : "error"}`}>
                  {message}
                </div>
              )}
            </div>

            <details className="configuration-info">
              <summary><span><i className="fas fa-sliders-h" /> Channel setup guide</span><span className="guide-hint">View instructions <i className="fas fa-chevron-down" /></span></summary>

              <div className="info-section">
                <h4>📧 Email Setup (Gmail)</h4>
                <ol>
                  <li>Create/edit <code>backend/.env</code> file</li>
                  <li>Add the following variables:</li>
                </ol>
                <pre className="code-block">
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=your-email@gmail.com
ENABLE_EMAIL_NOTIFICATIONS=true
                </pre>
                <p className="note">
                  <i className="fas fa-info-circle"></i> For Gmail, use an <strong>App Password</strong> instead of your regular password.
                  Generate one at: <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer">Google App Passwords</a>
                </p>
              </div>

              <div className="info-section">
                <h4>💬 Telegram Setup (FREE - RECOMMENDED)</h4>
                <ol>
                  <li>Open Telegram and search for <strong>@BotFather</strong></li>
                  <li>Send <code>/newbot</code> and follow instructions to create your bot</li>
                  <li>Copy the <strong>Bot Token</strong></li>
                  <li>Start a chat with your bot and send any message</li>
                  <li>Visit: <code>https://api.telegram.org/botYOUR_TOKEN/getUpdates</code></li>
                  <li>Find your <strong>Chat ID</strong> in the response</li>
                  <li>Add to <code>backend/.env</code>:</li>
                </ol>
                <pre className="code-block">
ENABLE_TELEGRAM_NOTIFICATIONS=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
                </pre>
                <p className="note">
                  <i className="fas fa-info-circle"></i> <strong>FREE</strong> and takes only 5 minutes to set up!
                  See <code>TELEGRAM_SETUP.md</code> for detailed instructions.
                </p>
              </div>

              <div className="info-section">
                <h4>📱 WhatsApp Setup (Twilio - Paid)</h4>
                <ol>
                  <li>Sign up for <a href="https://www.twilio.com" target="_blank" rel="noopener noreferrer">Twilio account</a></li>
                  <li>Get your Account SID and Auth Token</li>
                  <li>Add to <code>backend/.env</code>:</li>
                </ol>
                <pre className="code-block">
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+919876543210
ENABLE_WHATSAPP_NOTIFICATIONS=true
                </pre>
                <p className="note">
                  <i className="fas fa-info-circle"></i> Replace the "TO" number with your WhatsApp number (include country code with +)
                </p>
              </div>

              <div className="info-section">
                <h4>🔄 After Configuration</h4>
                <ol>
                  <li>Restart the backend container:</li>
                </ol>
                <pre className="code-block">
docker compose restart api
                </pre>
                <p className="note">
                  <i className="fas fa-info-circle"></i> The configuration will be loaded automatically on restart
                </p>
              </div>
            </details>
          </>
        )}
      </div>

      <footer className="footer">
        <i className="fas fa-copyright"></i> {new Date().getFullYear()} Arun Kumar. All rights reserved.
      </footer>
      </div>
    </main>
  );
}
