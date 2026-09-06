import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

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
  const navigate = useNavigate();
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
    <main>
      <div className="back-to-home">
        <button onClick={() => navigate("/")} className="back-btn">
          <i className="fas fa-home"></i> Back to Dashboard
        </button>
        {onLogout && (
          <button onClick={onLogout} className="logout-btn">
            <i className="fas fa-sign-out-alt"></i> Logout
          </button>
        )}
      </div>

      <div className="notification-settings">
        <div className="settings-header">
          <div className="settings-icon">
            <i className="fas fa-bell"></i>
          </div>
          <h1>Notification Settings</h1>
          <p>Configure email and WhatsApp notifications for stock recommendations</p>
        </div>

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
                  <p>Receive detailed stock recommendations via email with formatted HTML content</p>
                  {getStatusBadge(status?.email_enabled || false, status?.email_configured || false)}
                </div>
              </div>

              <div className="settings-card">
                <div className="card-icon telegram">
                  <i className="fab fa-telegram"></i>
                </div>
                <div className="card-content">
                  <h3>Telegram Notifications (FREE)</h3>
                  <p>Get instant stock alerts on Telegram - completely free and easy to set up</p>
                  {getStatusBadge(status?.telegram_enabled || false, status?.telegram_configured || false)}
                </div>
              </div>

              <div className="settings-card">
                <div className="card-icon whatsapp">
                  <i className="fab fa-whatsapp"></i>
                </div>
                <div className="card-content">
                  <h3>WhatsApp Notifications</h3>
                  <p>Get instant stock alerts on WhatsApp via Twilio integration (Paid)</p>
                  {getStatusBadge(status?.whatsapp_enabled || false, status?.whatsapp_configured || false)}
                </div>
              </div>
            </div>

            <div className="action-section">
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

            <div className="configuration-info">
              <h3><i className="fas fa-cog"></i> How to Configure</h3>

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
            </div>
          </>
        )}
      </div>

      <footer className="footer">
        <i className="fas fa-copyright"></i> {new Date().getFullYear()} Arun Kumar. All rights reserved.
      </footer>
    </main>
  );
}
