import React, { useEffect, useState } from "react";
import { AccountUser, apiJson } from "./auth-client";

type Props = { onAuthenticated: (user: AccountUser) => void };
type SignInMode = "password" | "email" | "phone";

export function AuthScreen({ onAuthenticated }: Props) {
  const [view, setView] = useState<"signin" | "register">("signin");
  const [mode, setMode] = useState<SignInMode>("password");
  const [fullName, setFullName] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [emailVerificationAvailable, setEmailVerificationAvailable] = useState(false);
  const [capabilitiesLoaded, setCapabilitiesLoaded] = useState(false);

  useEffect(() => {
    apiJson("/api/auth/capabilities")
      .then(result => setEmailVerificationAvailable(Boolean(result.email_verification_available)))
      .catch(() => setEmailVerificationAvailable(false))
      .finally(() => setCapabilitiesLoaded(true));
  }, []);

  const run = async (action: () => Promise<void>) => {
    setBusy(true); setMessage("");
    try { await action(); } catch (error) { setMessage(error instanceof Error ? error.message : "Please try again"); }
    finally { setBusy(false); }
  };

  const passwordLogin = (event: React.FormEvent) => {
    event.preventDefault();
    run(async () => {
      const result = await apiJson("/api/auth/login/password", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier, password }),
      });
      onAuthenticated(result.user);
    });
  };

  const register = (event: React.FormEvent) => {
    event.preventDefault();
    run(async () => {
      const result = await apiJson("/api/auth/register", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: fullName, email, phone, password, verification_code: code || null }),
      });
      onAuthenticated(result.user);
    });
  };

  const requestRegistrationCode = () => run(async () => {
    const result = await apiJson("/api/auth/register/code", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }),
    });
    setCodeSent(true); setMessage(result.message);
  });

  const requestEmailCode = () => run(async () => {
    const result = await apiJson("/api/auth/code/request", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }),
    });
    setCodeSent(true); setMessage(result.message);
  });

  const verifyEmailCode = (event: React.FormEvent) => {
    event.preventDefault();
    run(async () => {
      const result = await apiJson("/api/auth/login/code", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, code }),
      });
      onAuthenticated(result.user);
    });
  };

  const phoneLogin = (event: React.FormEvent) => {
    event.preventDefault();
    run(async () => {
      const result = await apiJson("/api/auth/login/password", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier: phone, password }),
      });
      onAuthenticated(result.user);
    });
  };

  const changeView = (next: "signin" | "register") => {
    setView(next); setMessage(""); setCodeSent(false); setCode("");
  };

  return <main className="auth-page">
    <section className="auth-story">
      <div className="auth-brand"><span>N</span><strong>NiveshDesk</strong></div>
      <div className="auth-story-copy">
        <span className="auth-eyebrow">YOUR PRIVATE MONEY DESK</span>
        <h1>One secure place for every rupee.</h1>
        <p>Plan budgets, track investments, and receive timely reminders—built for the way India manages money.</p>
        <div className="auth-trust"><span><i className="fas fa-lock" /> Private workspace</span><span><i className="fas fa-indian-rupee-sign" /> India-first planning</span><span><i className="fas fa-mobile-screen" /> Mobile ready</span></div>
      </div>
      <p className="auth-story-foot">Your data stays separate from every other account.</p>
    </section>

    <section className="auth-panel">
      <div className="auth-card">
        <div className="auth-mobile-brand"><span>N</span><strong>NiveshDesk</strong></div>
        <div className="auth-view-tabs" role="tablist">
          <button className={view === "signin" ? "active" : ""} onClick={() => changeView("signin")}>Sign in</button>
          <button className={view === "register" ? "active" : ""} onClick={() => changeView("register")}>Create account</button>
        </div>

        {view === "register" ? <form onSubmit={register} className="auth-form">
          <div><span className="auth-eyebrow">GET STARTED</span><h2>Create your money workspace</h2><p>Your budgets, portfolio and reminders belong only to you.</p></div>
          <label>Full name<input value={fullName} onChange={e => setFullName(e.target.value)} autoComplete="name" required placeholder="Arun Kumar Singh" /></label>
          <label>Email address<input value={email} onChange={e => setEmail(e.target.value)} type="email" autoComplete="email" required placeholder="you@example.com" /></label>
          <label>Mobile number<input value={phone} onChange={e => setPhone(e.target.value)} type="tel" autoComplete="tel" placeholder="+91 98765 43210" /></label>
          <label>Password<input value={password} onChange={e => setPassword(e.target.value)} type="password" autoComplete="new-password" minLength={8} required placeholder="At least 8 characters" /><small>Use uppercase, lowercase and a number.</small></label>
          {emailVerificationAvailable && codeSent && <label>Email verification code<input value={code} onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" required placeholder="000000" /></label>}
          {message && <div className="auth-message" role="alert">{message}</div>}
          {emailVerificationAvailable && !codeSent ? <button type="button" className="auth-primary" onClick={requestRegistrationCode} disabled={busy || !email || !capabilitiesLoaded}>{busy ? "Sending…" : "Verify email"}</button> : <button className="auth-primary" disabled={busy || !capabilitiesLoaded}>{!capabilitiesLoaded ? "Checking registration…" : busy ? "Creating…" : "Create secure account"}</button>}
          {!emailVerificationAvailable && <p className="auth-terms"><i className="fas fa-envelope-open" /> Email verification is unavailable right now; your password-protected account will still be created and kept separate.</p>}
          <p className="auth-terms"><i className="fas fa-shield-halved" /> Your session is protected with a secure, HttpOnly cookie.</p>
        </form> : <>
          <div className="auth-heading"><span className="auth-eyebrow">WELCOME BACK</span><h2>Open your workspace</h2><p>Choose the sign-in method that works for you.</p></div>
          <div className="auth-methods" role="tablist">
            <button className={mode === "password" ? "active" : ""} onClick={() => { setMode("password"); setCodeSent(false); setMessage(""); }}><i className="fas fa-key" /> Password</button>
            <button className={mode === "email" ? "active" : ""} onClick={() => { setMode("email"); setCodeSent(false); setMessage(""); }}><i className="fas fa-envelope" /> Email code</button>
            <button className={mode === "phone" ? "active" : ""} onClick={() => { setMode("phone"); setCodeSent(false); setMessage(""); }}><i className="fas fa-mobile-screen" /> Phone</button>
          </div>

          {mode === "password" && <form onSubmit={passwordLogin} className="auth-form compact">
            <label>Email or mobile number<input value={identifier} onChange={e => setIdentifier(e.target.value)} autoComplete="username" required placeholder="Email or +91 mobile" /></label>
            <label>Password<input value={password} onChange={e => setPassword(e.target.value)} type="password" autoComplete="current-password" required placeholder="Your password" /></label>
            {message && <div className="auth-message" role="alert">{message}</div>}
            <button className="auth-primary" disabled={busy}>{busy ? "Signing in…" : "Sign in securely"}</button>
          </form>}

          {mode === "email" && <form onSubmit={verifyEmailCode} className="auth-form compact">
            <label>Email address<input value={email} onChange={e => setEmail(e.target.value)} type="email" autoComplete="email" required placeholder="you@example.com" /></label>
            {codeSent && <label>6-digit code<input value={code} onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" required placeholder="000000" /></label>}
            {message && <div className="auth-message" role="status">{message}</div>}
            {!codeSent ? <button type="button" className="auth-primary" onClick={requestEmailCode} disabled={busy}>{busy ? "Sending…" : "Send email code"}</button> : <button className="auth-primary" disabled={busy}>{busy ? "Checking…" : "Verify and sign in"}</button>}
          </form>}

          {mode === "phone" && <form onSubmit={phoneLogin} className="auth-form compact">
            <label>Mobile number<input value={phone} onChange={e => setPhone(e.target.value)} type="tel" autoComplete="tel" required placeholder="+91 98765 43210" /></label>
            <label>Password<input value={password} onChange={e => setPassword(e.target.value)} type="password" autoComplete="current-password" required placeholder="Your password" /></label>
            {message && <div className="auth-message" role="alert">{message}</div>}
            <button className="auth-primary" disabled={busy}>{busy ? "Signing in…" : "Sign in with phone"}</button>
          </form>}
        </>}
      </div>
      <p className="auth-panel-foot">NiveshDesk uses industry-standard password hashing and isolated account data.</p>
    </section>
  </main>;
}
