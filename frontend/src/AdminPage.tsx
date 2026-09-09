import React, { useEffect, useMemo, useState } from "react";
import { apiJson } from "./auth-client";
import { WorkspaceHeader } from "./WorkspaceHeader";

type AdminUser = {
  id: number; full_name: string; email?: string; phone?: string; role: "user" | "admin";
  active: boolean; email_verified: boolean; must_change_password: boolean;
  created_at: string; last_login_at?: string; active_sessions: number;
  record_counts: Record<string, number>;
};
type Overview = { current_admin: AdminUser; users: AdminUser[]; legacy_record_counts: Record<string, number> };

const formatDate = (value?: string) => value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "Never";
const dataCount = (counts: Record<string, number>) => Object.values(counts).reduce((sum, value) => sum + value, 0);

export function AdminPage({ onLogout, currentUserId }: { onLogout: () => void; currentUserId: number }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [busy, setBusy] = useState<number | string | null>(null);
  const [message, setMessage] = useState("");
  const [profileName, setProfileName] = useState("");
  const [profilePhone, setProfilePhone] = useState("");

  const load = async () => {
    try {
      const result = await apiJson("/api/admin/overview");
      setOverview(result);
      setProfileName(result.current_admin.full_name || "");
      setProfilePhone(result.current_admin.phone || "+91");
    }
    catch (error) { setMessage(error instanceof Error ? error.message : "Admin details are unavailable"); }
  };
  useEffect(() => { load(); }, []);

  const legacyTotal = useMemo(() => dataCount(overview?.legacy_record_counts || {}), [overview]);
  const activeUsers = overview?.users.filter(user => user.active).length || 0;
  const sessions = overview?.users.reduce((sum, user) => sum + user.active_sessions, 0) || 0;

  const updateUser = async (user: AdminUser, values: { active?: boolean; role?: "user" | "admin" }) => {
    setBusy(user.id); setMessage("");
    try {
      await apiJson(`/api/admin/users/${user.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "User could not be updated"); }
    finally { setBusy(null); }
  };

  const revokeSessions = async (user: AdminUser) => {
    setBusy(`sessions-${user.id}`); setMessage("");
    try {
      const result = await apiJson(`/api/admin/users/${user.id}/revoke-sessions`, { method: "POST" });
      setMessage(`${result.revoked_sessions} session${result.revoked_sessions === 1 ? "" : "s"} revoked for ${user.full_name}.`);
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Sessions could not be revoked"); }
    finally { setBusy(null); }
  };

  const claimLegacy = async () => {
    setBusy("legacy"); setMessage("");
    try {
      const result = await apiJson("/api/admin/claim-legacy-data", { method: "POST" });
      setMessage(`${result.records_transferred} protected records moved into your account.`);
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Data could not be transferred"); }
    finally { setBusy(null); }
  };

  const saveProfile = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy("profile"); setMessage("");
    try {
      await apiJson("/api/auth/profile", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: profileName, phone: profilePhone }) });
      setMessage("Your owner profile has been updated. Your mobile number can now be used for password sign-in.");
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Profile could not be updated"); }
    finally { setBusy(null); }
  };

  return <div className="admin-page">
    <WorkspaceHeader section="Admin" onLogout={onLogout} />
    <main className="admin-shell">
      <header className="admin-hero">
        <div><span className="admin-eyebrow">OWNER CONTROL CENTRE</span><h1>People, access and data—clearly managed.</h1><p>Review accounts, protect active sessions and keep every person’s financial workspace separate.</p></div>
        <div className="admin-security"><i className="fas fa-lock" /><span><strong>Passwords stay private</strong>Only salted password hashes are stored. Passwords are never shown here.</span></div>
      </header>

      <section className="admin-stats" aria-label="Account overview">
        <article><span>Total users</span><strong>{overview?.users.length ?? "—"}</strong><small>registered accounts</small></article>
        <article><span>Active users</span><strong>{overview ? activeUsers : "—"}</strong><small>allowed to sign in</small></article>
        <article><span>Live sessions</span><strong>{overview ? sessions : "—"}</strong><small>across all devices</small></article>
        <article className={legacyTotal ? "attention" : ""}><span>Protected legacy data</span><strong>{overview ? legacyTotal : "—"}</strong><small>{legacyTotal ? "ready to move to you" : "transfer complete"}</small></article>
      </section>

      {legacyTotal > 0 && <section className="admin-legacy">
        <div><i className="fas fa-box-archive" /><span><strong>Your earlier financial records are protected</strong><small>Move them into this administrator account so they appear in Budget, Expenses, Portfolio and Notifications.</small></span></div>
        <button onClick={claimLegacy} disabled={busy === "legacy"}>{busy === "legacy" ? "Moving data…" : "Move my data"}</button>
      </section>}

      {message && <div className="admin-message" role="status">{message}</div>}

      <section className="admin-profile">
        <div><span className="admin-eyebrow">YOUR OWNER PROFILE</span><h2>Personal sign-in details</h2><p>Your verified email stays protected. Add your Indian mobile number to sign in with phone and password.</p></div>
        <form onSubmit={saveProfile}>
          <label>Full name<input value={profileName} onChange={e => setProfileName(e.target.value)} autoComplete="name" required /></label>
          <label>Mobile number<input value={profilePhone} onChange={e => setProfilePhone(e.target.value)} type="tel" autoComplete="tel" placeholder="+91 98765 43210" /></label>
          <label>Verified email<input value={overview?.current_admin.email || ""} disabled /></label>
          <button disabled={busy === "profile"}>{busy === "profile" ? "Saving…" : "Save my details"}</button>
        </form>
      </section>

      <section className="admin-users">
        <div className="admin-section-title"><div><span className="admin-eyebrow">USER DIRECTORY</span><h2>Accounts and access</h2></div><button onClick={load}><i className="fas fa-rotate" /> Refresh</button></div>
        {!overview ? <div className="admin-loading"><i className="fas fa-circle-notch fa-spin" /> Loading secure account details…</div> : <div className="admin-user-grid">
          {overview.users.map(user => {
            const ownAccount = user.id === currentUserId;
            return <article className="admin-user-card" key={user.id}>
              <div className="admin-user-head"><div className="admin-avatar">{user.full_name.slice(0, 1).toUpperCase()}</div><div><h3>{user.full_name}{ownAccount && <small>You</small>}</h3><p>{user.email || "No email"}</p></div><span className={`admin-state ${user.active ? "active" : "inactive"}`}>{user.active ? "Active" : "Paused"}</span></div>
              <div className="admin-user-meta"><span><i className="fas fa-mobile-screen" /> {user.phone || "No mobile number"}</span><span><i className="fas fa-shield-halved" /> {user.role === "admin" ? "Administrator" : "Standard user"}</span><span><i className="fas fa-clock" /> Last sign-in: {formatDate(user.last_login_at)}</span><span><i className="fas fa-database" /> {dataCount(user.record_counts)} private records</span><span><i className="fas fa-laptop" /> {user.active_sessions} active sessions</span></div>
              {user.must_change_password && <div className="admin-temp-badge"><i className="fas fa-key" /> Temporary password must be changed</div>}
              <div className="admin-user-actions">
                <button disabled={ownAccount || busy === user.id} onClick={() => updateUser(user, { role: user.role === "admin" ? "user" : "admin" })}>{user.role === "admin" ? "Make standard" : "Make admin"}</button>
                <button disabled={ownAccount || busy === user.id} onClick={() => updateUser(user, { active: !user.active })}>{user.active ? "Pause access" : "Restore access"}</button>
                <button disabled={ownAccount || busy === `sessions-${user.id}`} onClick={() => revokeSessions(user)}>Sign out devices</button>
              </div>
            </article>;
          })}
        </div>}
      </section>
    </main>
  </div>;
}
