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
    <div className="pin-overlay">
      <div className="pin-modal">
        <div className="pin-icon">
          <i className="fas fa-lock"></i>
        </div>
        <h2>Enter PIN</h2>
        <p>Enter your 4-digit PIN to access the dashboard</p>

        <div className="pin-display">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className={`pin-dot ${pin.length > i ? "filled" : ""}`}>
              {pin.length > i && <i className="fas fa-circle"></i>}
            </div>
          ))}
        </div>

        {error && (
          <div className="pin-error">
            <i className="fas fa-exclamation-circle"></i> {error}
          </div>
        )}

        <div className="pin-keypad">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
            <button key={num} onClick={() => handleKeyPress(num.toString())} className="pin-key">
              {num}
            </button>
          ))}
          <button onClick={() => setPin("")} className="pin-key clear">
            <i className="fas fa-redo"></i>
          </button>
          <button onClick={() => handleKeyPress("0")} className="pin-key">
            0
          </button>
          <button onClick={handleBackspace} className="pin-key backspace">
            <i className="fas fa-backspace"></i>
          </button>
        </div>
      </div>
    </div>
  );
}
