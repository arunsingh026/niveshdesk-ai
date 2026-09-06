import React, { useState } from "react";

interface SIPConfigModalProps {
  currentStart: number;
  currentEnd: number;
  onSave: (start: number, end: number) => void;
  onClose: () => void;
}

export function SIPConfigModal({ currentStart, currentEnd, onSave, onClose }: SIPConfigModalProps) {
  const [start, setStart] = useState(currentStart);
  const [end, setEnd] = useState(currentEnd);

  const handleSave = () => {
    if (start >= 1 && start <= 28 && end >= 1 && end <= 28 && start <= end) {
      onSave(start, end);
    } else {
      alert("Invalid date range. Must be 1-28 and start <= end");
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Configure SIP Date Range</h2>
          <button onClick={onClose} className="modal-close">
            <i className="fas fa-times"></i>
          </button>
        </div>
        <div className="modal-body">
          <p className="modal-description">
            Set the date range for SIP analysis. The system will analyze market data within this range to find optimal purchase dates.
          </p>
          <div className="form-group">
            <label>Start Date (day of month)</label>
            <input
              type="number"
              min="1"
              max="28"
              value={start}
              onChange={(e) => setStart(parseInt(e.target.value))}
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label>End Date (day of month)</label>
            <input
              type="number"
              min="1"
              max="28"
              value={end}
              onChange={(e) => setEnd(parseInt(e.target.value))}
              className="form-input"
            />
          </div>
          <div className="date-range-preview">
            <i className="fas fa-calendar-alt"></i>
            <span>Analysis window: {start}th to {end}th of each month</span>
          </div>
        </div>
        <div className="modal-footer">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} className="btn-primary">Save Range</button>
        </div>
      </div>
    </div>
  );
}

interface SIPConfirmModalProps {
  changes: Array<{
    symbol: string;
    name: string;
    optimal_date: number;
    previous_date: number;
    justification: string;
  }>;
  onConfirm: (acceptAll: boolean) => void;
}

export function SIPConfirmModal({ changes, onConfirm }: SIPConfirmModalProps) {
  return (
    <div className="modal-overlay" onClick={() => onConfirm(false)}>
      <div className="modal-content sip-confirm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2><i className="fas fa-calendar-check"></i> SIP Date Changes Recommended</h2>
        </div>
        <div className="modal-body">
          <p className="modal-description">
            Analysis suggests changing SIP dates for {changes.length} mutual fund{changes.length > 1 ? 's' : ''}:
          </p>
          <div className="sip-changes-list">
            {changes.map((change) => (
              <div key={change.symbol} className="sip-change-item">
                <div className="sip-change-header">
                  <strong>{change.name}</strong>
                  <span className="symbol-badge">{change.symbol}</span>
                </div>
                <div className="sip-change-dates">
                  <div className="old-date">
                    <i className="fas fa-arrow-right"></i>
                    <span>Previous: {change.previous_date}th</span>
                  </div>
                  <i className="fas fa-long-arrow-alt-right date-arrow"></i>
                  <div className="new-date">
                    <i className="fas fa-check-circle"></i>
                    <span>Recommended: {change.optimal_date}th</span>
                  </div>
                </div>
                <div className="sip-justification">
                  <i className="fas fa-info-circle"></i>
                  <p>{change.justification}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="modal-footer">
          <button onClick={() => onConfirm(false)} className="btn-secondary">
            Keep Current Dates
          </button>
          <button onClick={() => onConfirm(true)} className="btn-primary">
            <i className="fas fa-check"></i> Apply Changes
          </button>
        </div>
      </div>
    </div>
  );
}