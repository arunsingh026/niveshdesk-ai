import React, { useEffect, useMemo, useState } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";

const API = window.location.hostname === "localhost" ? "http://localhost:8000" : window.location.origin;
const kinds = {
  stock_buy: { label: "Stock buy", icon: "fa-chart-line", tone: "gold" },
  sip: { label: "SIP", icon: "fa-seedling", tone: "green" },
  credit_card: { label: "Card / bill", icon: "fa-credit-card", tone: "coral" },
  custom: { label: "Custom", icon: "fa-bell", tone: "blue" },
} as const;

type ReminderKind = keyof typeof kinds;
type Preferences = {
  email_address: string; email_enabled: boolean; push_enabled: boolean; expense_due_enabled: boolean;
  budget_alert_enabled: boolean; monthly_report_enabled: boolean; failure_alerts_enabled: boolean;
  budget_threshold: number; default_lead_minutes: number; quiet_start: number; quiet_end: number; timezone: string;
};
type Reminder = {
  id: number; kind: ReminderKind; title: string; details: string; symbol: string; amount: number | null;
  due_at: string; recurrence: "once" | "weekly" | "monthly"; remind_before_minutes: number; channels: string[]; enabled: boolean;
};
type Delivery = { id: number; kind: string; channel: string; title: string; status: string; error: string; sent_at: string };
type Overview = {
  status: { push: { enabled: boolean; configured: boolean; devices: number }; email: { enabled: boolean; configured: boolean; address: string }; scheduler: { configured: boolean; frequency: string }; free_tier: boolean };
  preferences: Preferences; reminders: Reminder[]; deliveries: Delivery[];
};

const toLocalInput = (value?: string) => {
  const date = value ? new Date(value) : new Date(Date.now() + 86400000);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
};

function formatMoney(value: number | null) {
  return value == null ? "" : new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

export function NotificationSettings({ onLogout }: { onLogout?: () => void }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Reminder | null>(null);
  const [form, setForm] = useState({ kind: "sip" as ReminderKind, title: "", details: "", symbol: "", amount: "", due_at: toLocalInput(), recurrence: "monthly", remind_before_minutes: 1440, push: true, email: true });

  const loadOverview = async () => {
    try {
      const response = await fetch(`${API}/api/notifications/overview`);
      if (!response.ok) throw new Error("Unable to load notifications");
      setOverview(await response.json());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load notifications");
    } finally { setLoading(false); }
  };
  useEffect(() => { loadOverview(); }, []);

  const upcoming = useMemo(() => (overview?.reminders || []).filter(item => item.enabled).sort((a, b) => +new Date(a.due_at) - +new Date(b.due_at)), [overview]);

  const savePreferences = async (next: Preferences, notice = "Preferences saved") => {
    if (!overview) return;
    setOverview({ ...overview, preferences: next });
    try {
      const response = await fetch(`${API}/api/notifications/preferences`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(next) });
      if (!response.ok) throw new Error("Could not save preferences");
      setMessage(notice);
      await loadOverview();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not save preferences"); }
  };

  const toggle = (key: keyof Preferences) => {
    if (!overview) return;
    savePreferences({ ...overview.preferences, [key]: !overview.preferences[key] } as Preferences);
  };

  const enablePush = async () => {
    setSaving(true); setMessage("");
    try {
      const { enablePushNotifications } = await import("./push-notifications");
      const result = await enablePushNotifications(payload => setMessage(payload.notification?.title || "New notification received"));
      const reason = result.reason;
      if (result.ok) setMessage("Push notifications are active on this device");
      else if (reason === "install_required") setMessage("On iPhone: Share → Add to Home Screen, open NiveshDesk there, then enable alerts.");
      else if (reason === "not_configured") setMessage("Firebase setup is required after this release is deployed.");
      else if (reason === "denied") setMessage("Notifications are blocked in this browser. Allow them in site settings and try again.");
      else setMessage("This browser does not support web push notifications.");
      await loadOverview();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not enable push notifications"); }
    finally { setSaving(false); }
  };

  const openForm = (item?: Reminder) => {
    setEditing(item || null);
    setForm(item ? { kind: item.kind, title: item.title, details: item.details, symbol: item.symbol, amount: item.amount?.toString() || "", due_at: toLocalInput(item.due_at), recurrence: item.recurrence, remind_before_minutes: item.remind_before_minutes, push: item.channels.includes("push"), email: item.channels.includes("email") }
      : { kind: "sip", title: "", details: "", symbol: "", amount: "", due_at: toLocalInput(), recurrence: "monthly", remind_before_minutes: 1440, push: true, email: true });
    setShowForm(true);
  };

  const saveReminder = async (event: React.FormEvent) => {
    event.preventDefault(); setSaving(true);
    const { push, email, ...values } = form;
    const payload = { ...values, amount: form.amount ? Number(form.amount) : null, due_at: new Date(form.due_at).toISOString(), channels: [push && "push", email && "email"].filter(Boolean) };
    try {
      const response = await fetch(`${API}/api/notifications/reminders${editing ? `/${editing.id}` : ""}`, { method: editing ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error((await response.json()).detail || "Could not save reminder");
      setShowForm(false); setMessage(editing ? "Reminder updated" : "Reminder scheduled"); await loadOverview();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not save reminder"); }
    finally { setSaving(false); }
  };

  const removeReminder = async (id: number) => {
    if (!window.confirm("Delete this reminder?")) return;
    await fetch(`${API}/api/notifications/reminders/${id}`, { method: "DELETE" });
    setMessage("Reminder deleted"); await loadOverview();
  };

  return <main className="app-workspace notification-workspace">
    <WorkspaceHeader section="Notifications" onLogout={onLogout} />
    <div className="notification-shell">
      {loading ? <div className="notification-loading"><i className="fas fa-circle-notch fa-spin" /> Preparing your alerts…</div> : overview && <>
        <section className="notification-hero">
          <div><span className="notification-kicker">YOUR MONEY, ON TIME</span><h1>Never miss what matters.</h1><p>One calm place for SIPs, stock-buy days, card bills, budgets and portfolio reports.</p></div>
          <div className="hero-next"><span>NEXT UP</span><strong>{upcoming[0] ? upcoming[0].title : "You’re all caught up"}</strong><small>{upcoming[0] ? new Date(upcoming[0].due_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "Create your first smart reminder"}</small><button onClick={() => openForm()}><i className="fas fa-plus" /> Add reminder</button></div>
        </section>

        {message && <div className="notification-toast" role="status"><i className="fas fa-circle-info" /><span>{message}</span><button onClick={() => setMessage("")} aria-label="Dismiss"><i className="fas fa-xmark" /></button></div>}

        <section className="channel-grid" aria-label="Delivery channels">
          <article className="channel-card"><div className="channel-icon push"><i className="fas fa-mobile-screen-button" /></div><div><span className="channel-label">MOBILE & WEB</span><h2>Push alerts</h2><p>Instant reminders, even when NiveshDesk is closed.</p></div><div className="channel-footer"><span className={`live-pill ${overview.status.push.configured && overview.status.push.devices ? "active" : ""}`}><i className="fas fa-circle" /> {overview.status.push.devices ? `${overview.status.push.devices} device connected` : overview.status.push.configured ? "Ready to connect" : "Setup needed"}</span><button onClick={enablePush} disabled={saving}>{overview.status.push.devices ? "Add this device" : "Enable alerts"}</button></div></article>
          <article className="channel-card"><div className="channel-icon email"><i className="fas fa-envelope-open-text" /></div><div><span className="channel-label">MONTHLY DIGESTS</span><h2>Email by Resend</h2><p>Beautiful portfolio reports and important failure alerts.</p></div><div className="email-control"><input type="email" aria-label="Notification email" placeholder="you@example.com" value={overview.preferences.email_address} onChange={event => setOverview({ ...overview, preferences: { ...overview.preferences, email_address: event.target.value } })} /><button onClick={() => savePreferences({ ...overview.preferences, email_enabled: Boolean(overview.preferences.email_address) }, "Email preferences saved")}>Save</button></div><span className={`live-pill ${overview.status.email.configured ? "active" : ""}`}><i className="fas fa-circle" /> {overview.status.email.configured ? "Email active" : "Resend setup needed"}</span></article>
          <article className="channel-card scheduler-card"><div className="channel-icon schedule"><i className="fas fa-clock" /></div><div><span className="channel-label">AUTOMATIC CHECKS</span><h2>Hourly smart check</h2><p>GitHub Actions checks due items without a paid background worker.</p></div><div className="channel-footer"><span className={`live-pill ${overview.status.scheduler.configured ? "active" : ""}`}><i className="fas fa-circle" /> {overview.status.scheduler.configured ? "Scheduler protected" : "Secret needed"}</span><b>₹0 / month</b></div></article>
        </section>

        <div className="notification-main-grid">
          <section className="notification-panel upcoming-panel"><div className="panel-heading"><div><span>UPCOMING</span><h2>Your reminder timeline</h2></div><button onClick={() => openForm()}><i className="fas fa-plus" /><span>Add</span></button></div>
            {upcoming.length ? <div className="reminder-list">{upcoming.map(item => { const meta = kinds[item.kind]; return <article className="reminder-row" key={item.id}><div className={`reminder-date ${meta.tone}`}><b>{new Date(item.due_at).toLocaleDateString("en-IN", { day: "2-digit" })}</b><span>{new Date(item.due_at).toLocaleDateString("en-IN", { month: "short" })}</span></div><div className="timeline-line"><i className={`fas ${meta.icon}`} /></div><div className="reminder-copy"><span>{meta.label} · {item.recurrence === "once" ? "One time" : item.recurrence}</span><h3>{item.title}</h3><p>{[item.symbol, formatMoney(item.amount), item.details].filter(Boolean).join(" • ") || "We’ll remind you before it is due."}</p><small><i className="far fa-clock" /> {new Date(item.due_at).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })} · {item.remind_before_minutes >= 1440 ? `${item.remind_before_minutes / 1440} day early` : `${item.remind_before_minutes / 60} hr early`}</small></div><div className="reminder-actions"><button onClick={() => openForm(item)} aria-label={`Edit ${item.title}`}><i className="fas fa-pen" /></button><button onClick={() => removeReminder(item.id)} aria-label={`Delete ${item.title}`}><i className="fas fa-trash" /></button></div></article>; })}</div>
            : <div className="empty-reminders"><i className="fas fa-bell-slash" /><h3>No reminders yet</h3><p>Start with your next SIP, card bill or planned stock-buy date.</p><button onClick={() => openForm()}>Create a reminder</button></div>}
          </section>

          <aside className="notification-side">
            <section className="notification-panel"><div className="panel-heading"><div><span>SMART RULES</span><h2>Always watching</h2></div></div><div className="automation-list">
              <Automation icon="fa-receipt" title="Upcoming bills" detail={`${overview.preferences.default_lead_minutes / 1440} day heads-up`} active={overview.preferences.expense_due_enabled} onClick={() => toggle("expense_due_enabled")} />
              <Automation icon="fa-gauge-high" title="Budget guardrail" detail={`Alert at ${overview.preferences.budget_threshold}%`} active={overview.preferences.budget_alert_enabled} onClick={() => toggle("budget_alert_enabled")} />
              <Automation icon="fa-chart-pie" title="Portfolio report" detail="Email on the 1st monthly" active={overview.preferences.monthly_report_enabled} onClick={() => toggle("monthly_report_enabled")} />
              <Automation icon="fa-triangle-exclamation" title="Failure alerts" detail="Know when delivery fails" active={overview.preferences.failure_alerts_enabled} onClick={() => toggle("failure_alerts_enabled")} />
            </div><div className="rule-settings"><label>Budget alert<select value={overview.preferences.budget_threshold} onChange={event => savePreferences({ ...overview.preferences, budget_threshold: Number(event.target.value) })}><option value="75">At 75%</option><option value="80">At 80%</option><option value="90">At 90%</option><option value="100">At 100%</option></select></label><label>Bill heads-up<select value={overview.preferences.default_lead_minutes} onChange={event => savePreferences({ ...overview.preferences, default_lead_minutes: Number(event.target.value) })}><option value="1440">1 day</option><option value="4320">3 days</option><option value="10080">7 days</option></select></label></div><div className="quiet-hours"><i className="fas fa-moon" /><div><strong>Quiet hours</strong><span>{overview.preferences.quiet_start}:00 – {overview.preferences.quiet_end}:00 IST</span></div></div></section>

            <section className="notification-panel"><div className="panel-heading"><div><span>RECENT ACTIVITY</span><h2>Delivery history</h2></div></div>{overview.deliveries.length ? <div className="delivery-list">{overview.deliveries.slice(0, 6).map(item => <div key={item.id}><i className={`fas ${item.status === "sent" ? "fa-check" : "fa-exclamation"}`} /><p><strong>{item.title}</strong><span>{item.channel} · {new Date(item.sent_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span></p><b className={item.status}>{item.status}</b></div>)}</div> : <p className="history-empty">Your delivery receipts will appear here.</p>}</section>
          </aside>
        </div>
      </>}
    </div>

    {showForm && <div className="notification-modal" role="presentation" onMouseDown={event => event.target === event.currentTarget && setShowForm(false)}><form className="notification-form" onSubmit={saveReminder}><div className="form-head"><div><span>SMART REMINDER</span><h2>{editing ? "Edit reminder" : "What’s coming up?"}</h2></div><button type="button" onClick={() => setShowForm(false)} aria-label="Close"><i className="fas fa-xmark" /></button></div>
      <div className="kind-picker">{(Object.keys(kinds) as ReminderKind[]).map(kind => <button type="button" className={form.kind === kind ? "selected" : ""} key={kind} onClick={() => setForm({ ...form, kind })}><i className={`fas ${kinds[kind].icon}`} /><span>{kinds[kind].label}</span></button>)}</div>
      <label>Reminder title<input required maxLength={160} placeholder="e.g. HDFC credit card payment" value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} /></label>
      <div className="form-pair"><label>Due date & time<input required type="datetime-local" value={form.due_at} onChange={event => setForm({ ...form, due_at: event.target.value })} /></label><label>Repeat<select value={form.recurrence} onChange={event => setForm({ ...form, recurrence: event.target.value })}><option value="once">One time</option><option value="weekly">Every week</option><option value="monthly">Every month</option></select></label></div>
      <div className="form-pair"><label>Amount (optional)<input type="number" min="0" inputMode="decimal" placeholder="₹ 0" value={form.amount} onChange={event => setForm({ ...form, amount: event.target.value })} /></label><label>Remind me<select value={form.remind_before_minutes} onChange={event => setForm({ ...form, remind_before_minutes: Number(event.target.value) })}><option value={60}>1 hour before</option><option value={1440}>1 day before</option><option value={4320}>3 days before</option><option value={10080}>1 week before</option></select></label></div>
      {form.kind === "stock_buy" && <label>Stock symbol<input maxLength={40} placeholder="e.g. ICICIBANK" value={form.symbol} onChange={event => setForm({ ...form, symbol: event.target.value.toUpperCase() })} /></label>}
      <label>Note (optional)<textarea maxLength={500} placeholder="Anything useful when this reminder arrives" value={form.details} onChange={event => setForm({ ...form, details: event.target.value })} /></label>
      <fieldset><legend>Send through</legend><label><input type="checkbox" checked={form.push} onChange={event => setForm({ ...form, push: event.target.checked })} /> Push notification</label><label><input type="checkbox" checked={form.email} onChange={event => setForm({ ...form, email: event.target.checked })} /> Email</label></fieldset>
      <div className="form-actions"><button type="button" onClick={() => setShowForm(false)}>Cancel</button><button type="submit" disabled={saving || (!form.push && !form.email)}>{saving ? "Saving…" : editing ? "Save changes" : "Schedule reminder"}</button></div>
    </form></div>}
  </main>;
}

function Automation({ icon, title, detail, active, onClick }: { icon: string; title: string; detail: string; active: boolean; onClick: () => void }) {
  return <button className="automation-row" onClick={onClick} aria-pressed={active}><i className={`fas ${icon}`} /><span><strong>{title}</strong><small>{detail}</small></span><b className={`toggle ${active ? "on" : ""}`}><i /></b></button>;
}
