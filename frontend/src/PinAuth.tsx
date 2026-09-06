import React, { useState, useEffect } from "react";

interface PinAuthProps {
  onAuthenticated: () => void;
}

export function PinAuth({ onAuthenticated }: PinAuthProps) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const CORRECT_PIN = import.meta.env.VITE_PIN_CODE || "1290";

  useEffect(() => {
    // Check if already authenticated
    const authTime = localStorage.getItem("authTime");
    if (authTime) {
      const elapsed = Date.now() - parseInt(authTime);
      if (elapsed < 15 * 60 * 1000) {
        onAuthenticated();
      } else {
        localStorage.removeItem("authTime");
      }
    }
  }, [onAuthenticated]);

  useEffect(() => {
    // Handle keyboard input
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key >= "0" && e.key <= "9") {
        handlePinChange(pin + e.key);
      } else if (e.key === "Backspace") {
        handleBackspace();
      } else if (e.key === "Enter" && pin.length === 4) {
        // Already handled by handlePinChange
      } else if (e.key === "Escape") {
        setPin("");
        setError("");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [pin]);

  const handlePinChange = (value: string) => {
    if (value.length <= 4 && /^\d*$/.test(value)) {
      setPin(value);
      setError("");

      if (value.length === 4) {
        if (value === CORRECT_PIN) {
          localStorage.setItem("authTime", Date.now().toString());
          onAuthenticated();
        } else {
          setError("Incorrect PIN");
          setTimeout(() => setPin(""), 500);
        }
      }
    }
  };

  const handleKeyPress = (digit: string) => {
    handlePinChange(pin + digit);
  };

  const handleBackspace = () => {
    setPin(pin.slice(0, -1));
    setError("");
  };

  return (
    <div className="pin-overlay login-workspace">
      <div className="login-brand"><span>S</span> Stock Planner</div>
      <div className="login-layout">
      <section className="login-intro">
        <span className="login-eyebrow">YOUR FINANCIAL WORKSPACE</span>
        <h1>A clearer view.<br />A calmer month.</h1>
        <p>Your expenses, investments, and monthly plans, together in one thoughtful space.</p>
        <div className="login-features"><span><i className="fas fa-wallet" /> Track every expense</span><span><i className="fas fa-chart-line" /> Plan your investments</span><span><i className="far fa-calendar-check" /> Stay on top of your month</span></div>
        <div className="login-art" aria-hidden="true"><div /><div /><div /><div /><div /><div /><div /></div>
      </section>
      <div className="pin-modal">
        <span className="login-eyebrow">WELCOME BACK</span>
        <div className="pin-icon">
          <i className="fas fa-lock"></i>
        </div>
        <h2>Enter PIN</h2>
        <p>Enter your 4-digit PIN to open your workspace.</p>

        <div className="pin-display" role="status" aria-label={`${pin.length} of 4 PIN digits entered`}>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className={`pin-dot ${pin.length > i ? "filled" : ""}`}>
              {pin.length > i && <i className="fas fa-circle"></i>}
            </div>
          ))}
        </div>

        {error && (
          <div className="pin-error" role="alert">
            <i className="fas fa-exclamation-circle"></i> {error}
          </div>
        )}

        <div className="pin-keypad">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
            <button key={num} onClick={() => handleKeyPress(num.toString())} className="pin-key">
              {num}
            </button>
          ))}
          <button onClick={() => setPin("")} className="pin-key clear" aria-label="Clear PIN">
            <i className="fas fa-redo"></i>
          </button>
          <button onClick={() => handleKeyPress("0")} className="pin-key">
            0
          </button>
          <button onClick={handleBackspace} className="pin-key backspace" aria-label="Delete last digit">
            <i className="fas fa-backspace"></i>
          </button>
        </div>
        <p className="login-help"><i className="far fa-keyboard" /> Use the keypad or type on your keyboard</p>
      </div>
      </div>
      <footer className="login-footer">Your money. Your plan. Your pace.</footer>
    </div>
  );
}
