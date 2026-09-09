import React, { useState } from "react";
import { AccountUser, apiJson } from "./auth-client";

type Props = {
  user: AccountUser;
  onChanged: (user: AccountUser) => void;
  onLogout: () => void;
};

export function ChangePasswordScreen({ user, onChanged, onLogout }: Props) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (newPassword !== confirmPassword) return setMessage("New passwords do not match");
    setBusy(true); setMessage("");
    try {
      const result = await apiJson("/api/auth/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      onChanged(result.user);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Password could not be changed");
    } finally { setBusy(false); }
  };

  return <main className="password-setup-page">
    <section className="password-setup-card">
      <div className="password-setup-brand"><span>N</span><strong>NiveshDesk</strong></div>
      <span className="admin-eyebrow">SECURE YOUR OWNER ACCOUNT</span>
      <h1>Choose your private password</h1>
      <p>Welcome, {user.full_name}. Your temporary password can only open this setup screen. Replace it before entering your financial workspace.</p>
      <form onSubmit={submit} className="password-setup-form">
        <label>Temporary password<input type="password" autoComplete="current-password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} required /></label>
        <label>New password<input type="password" autoComplete="new-password" value={newPassword} onChange={e => setNewPassword(e.target.value)} minLength={8} required /><small>Use uppercase, lowercase and a number.</small></label>
        <label>Confirm new password<input type="password" autoComplete="new-password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} minLength={8} required /></label>
        {message && <div className="auth-message" role="alert">{message}</div>}
        <button className="auth-primary" disabled={busy}>{busy ? "Securing account…" : "Save password and continue"}</button>
      </form>
      <button className="password-setup-logout" onClick={onLogout}>Sign out</button>
      <div className="password-security-note"><i className="fas fa-shield-halved" /><span>Your password is salted and hashed. Administrators can never view it.</span></div>
    </section>
  </main>;
}
