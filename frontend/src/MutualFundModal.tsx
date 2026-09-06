import React, { useState, useEffect } from "react";

interface MutualFundModalProps {
  symbol: string;
  name: string;
  onClose: () => void;
}

interface FundDetails {
  fund_house: string;
  category: string;
  aum: string;
  expense_ratio: string;
  exit_load: string;
  min_investment: string;
  nav: string;
  returns_1y: string;
  returns_3y: string;
  returns_5y: string;
  risk_level: string;
  objective: string;
}

const FUND_DATA: Record<string, FundDetails> = {
  PPFAS: {
    fund_house: "PPFAS Mutual Fund",
    category: "Flexi Cap Fund",
    aum: "₹23,500 Cr",
    expense_ratio: "0.64%",
    exit_load: "2% if redeemed within 1 year",
    min_investment: "₹1,000",
    nav: "₹68.50",
    returns_1y: "32.5%",
    returns_3y: "18.2%",
    returns_5y: "21.8%",
    risk_level: "Moderately High",
    objective: "To generate long-term capital appreciation by investing in equity and equity-related instruments with flexibility across market caps and includes international equity exposure (up to 35%)."
  },
  AXISBLU: {
    fund_house: "Axis Mutual Fund",
    category: "Large Cap Fund",
    aum: "₹32,800 Cr",
    expense_ratio: "0.48%",
    exit_load: "1% if redeemed within 1 year",
    min_investment: "₹5,000",
    nav: "₹52.30",
    returns_1y: "28.4%",
    returns_3y: "16.5%",
    returns_5y: "19.2%",
    risk_level: "Moderate",
    objective: "To generate long-term capital appreciation by investing predominantly in large cap equity and equity-related instruments."
  },
  MIRAELC: {
    fund_house: "Mirae Asset Mutual Fund",
    category: "Large Cap Fund",
    aum: "₹27,600 Cr",
    expense_ratio: "0.42%",
    exit_load: "1% if redeemed within 365 days",
    min_investment: "₹5,000",
    nav: "₹98.20",
    returns_1y: "30.1%",
    returns_3y: "17.8%",
    returns_5y: "20.5%",
    risk_level: "Moderate",
    objective: "To provide long-term capital appreciation by investing predominantly in large cap equity stocks with focus on quality companies."
  },
  AXISMID: {
    fund_house: "Axis Mutual Fund",
    category: "Mid Cap Fund",
    aum: "₹18,900 Cr",
    expense_ratio: "0.56%",
    exit_load: "1% if redeemed within 1 year",
    min_investment: "₹5,000",
    nav: "₹85.40",
    returns_1y: "42.8%",
    returns_3y: "28.5%",
    returns_5y: "30.2%",
    risk_level: "High",
    objective: "To generate capital appreciation by investing predominantly in mid cap equity and equity-related instruments."
  },
  QUANTSC: {
    fund_house: "Quant Mutual Fund",
    category: "Small Cap Fund",
    aum: "₹8,200 Cr",
    expense_ratio: "0.68%",
    exit_load: "2% if redeemed within 1 year",
    min_investment: "₹5,000",
    nav: "₹245.80",
    returns_1y: "58.2%",
    returns_3y: "42.5%",
    returns_5y: "38.8%",
    risk_level: "Very High",
    objective: "To generate long-term capital appreciation through active investment in small cap equity and equity-related instruments using quantitative models."
  },
  ICICIN50: {
    fund_house: "ICICI Prudential Mutual Fund",
    category: "Index Fund - Nifty 50",
    aum: "₹48,500 Cr",
    expense_ratio: "0.10%",
    exit_load: "Nil",
    min_investment: "₹5,000",
    nav: "₹288.60",
    returns_1y: "26.8%",
    returns_3y: "15.2%",
    returns_5y: "17.8%",
    risk_level: "Moderate",
    objective: "To provide returns that closely correspond to the total returns of Nifty 50 Index, subject to tracking error."
  }
};

export function MutualFundModal({ symbol, name, onClose }: MutualFundModalProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "performance" | "holdings">("overview");
  const details = FUND_DATA[symbol] || {} as FundDetails;

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  const getRiskColor = (risk: string) => {
    if (risk.includes("Very High")) return "#dc2626";
    if (risk.includes("High")) return "#f59e0b";
    if (risk.includes("Moderate")) return "#10b981";
    return "#6b7280";
  };

  return (
    <div className="chart-modal-overlay" onClick={onClose}>
      <div className="chart-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="chart-modal-header">
          <div>
            <h2 className="mf-modal-title">{symbol}</h2>
            <p className="mf-modal-subtitle">{name}</p>
          </div>
          <button onClick={onClose} className="chart-modal-close">
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="mf-tabs">
          <button
            onClick={() => setActiveTab("overview")}
            className={`mf-tab ${activeTab === "overview" ? "active" : ""}`}
          >
            <i className="fas fa-info-circle"></i> Overview
          </button>
          <button
            onClick={() => setActiveTab("performance")}
            className={`mf-tab ${activeTab === "performance" ? "active" : ""}`}
          >
            <i className="fas fa-chart-line"></i> Performance
          </button>
          <button
            onClick={() => setActiveTab("holdings")}
            className={`mf-tab ${activeTab === "holdings" ? "active" : ""}`}
          >
            <i className="fas fa-briefcase"></i> Holdings
          </button>
        </div>

        <div className="mf-modal-body">
          {activeTab === "overview" && (
            <div className="mf-overview">
              <div className="mf-info-grid">
                <div className="mf-info-card">
                  <span className="mf-info-label">Fund House</span>
                  <strong className="mf-info-value">{details.fund_house}</strong>
                </div>
                <div className="mf-info-card">
                  <span className="mf-info-label">Category</span>
                  <strong className="mf-info-value">{details.category}</strong>
                </div>
                <div className="mf-info-card">
                  <span className="mf-info-label">Current NAV</span>
                  <strong className="mf-info-value">{details.nav}</strong>
                </div>
                <div className="mf-info-card">
                  <span className="mf-info-label">AUM</span>
                  <strong className="mf-info-value">{details.aum}</strong>
                </div>
                <div className="mf-info-card">
                  <span className="mf-info-label">Expense Ratio</span>
                  <strong className="mf-info-value">{details.expense_ratio}</strong>
                </div>
                <div className="mf-info-card">
                  <span className="mf-info-label">Min Investment</span>
                  <strong className="mf-info-value">{details.min_investment}</strong>
                </div>
                <div className="mf-info-card">
                  <span className="mf-info-label">Exit Load</span>
                  <strong className="mf-info-value">{details.exit_load}</strong>
                </div>
                <div className="mf-info-card">
                  <span className="mf-info-label">Risk Level</span>
                  <strong className="mf-info-value" style={{ color: getRiskColor(details.risk_level) }}>
                    {details.risk_level}
                  </strong>
                </div>
              </div>

              <div className="mf-objective">
                <h3><i className="fas fa-bullseye"></i> Investment Objective</h3>
                <p>{details.objective}</p>
              </div>

              <div className="mf-disclaimer">
                <i className="fas fa-exclamation-triangle"></i>
                <span>Past performance does not guarantee future results. Mutual fund investments are subject to market risks. Please read the scheme information document carefully before investing.</span>
              </div>
            </div>
          )}

          {activeTab === "performance" && (
            <div className="mf-performance">
              <h3>Returns</h3>
              <div className="mf-returns-grid">
                <div className="mf-return-card">
                  <span className="mf-return-period">1 Year</span>
                  <strong className="mf-return-value positive">{details.returns_1y}</strong>
                </div>
                <div className="mf-return-card">
                  <span className="mf-return-period">3 Years (CAGR)</span>
                  <strong className="mf-return-value positive">{details.returns_3y}</strong>
                </div>
                <div className="mf-return-card">
                  <span className="mf-return-period">5 Years (CAGR)</span>
                  <strong className="mf-return-value positive">{details.returns_5y}</strong>
                </div>
              </div>

              <div className="mf-note">
                <i className="fas fa-info-circle"></i>
                <p>Returns are calculated as of the last available NAV date. Historical returns are not indicative of future performance.</p>
              </div>
            </div>
          )}

          {activeTab === "holdings" && (
            <div className="mf-holdings">
              <div className="mf-coming-soon">
                <i className="fas fa-clock"></i>
                <h3>Holdings Information</h3>
                <p>Top holdings and sector allocation data will be available soon. This information is typically updated monthly by fund houses.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}