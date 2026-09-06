import { WorkspaceHeader } from "./WorkspaceHeader";
import React, { useEffect, useState } from "react";
import { StockChartModal } from "./StockChartModal";
import { SIPConfigModal, SIPConfirmModal } from "./SIPModals";
import { MutualFundModal } from "./MutualFundModal";
import "./chart-modal.css";

type R = {
  symbol: string;
  name: string;
  instrument_type: string;
  market_cap: string;
  current_price: number | null;
  day_change: number | null;
  day_change_percent: number | null;
  target_amount: number;
  suggested_price: number | null;
  quantity: number;
  deploy_amount: number;
  status: string;
  reason: string;
};

// Use the same host as the frontend, but port 8000 for API
const getApiUrl = () => {
  return window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : window.location.origin;
};

const API = getApiUrl();

const companyDomains: Record<string, string> = {
  // Stocks
  ICICIBANK: "icicibank.com",
  BHARTIARTL: "airtel.in",
  LT: "larsentoubro.com",
  RELIANCE: "ril.com",
  HDFCBANK: "hdfcbank.com",
  MAXHEALTH: "maxhealthcare.in",
  KFINTECH: "kfintech.com",
  INDHOTEL: "tajhotels.com",
  TDPOWERSYS: "tdpowersystems.com",
  // Mutual Funds (Fund House Logos)
  PPFAS: "ppfas.com",
  AXISBLU: "axismf.com",
  MIRAELC: "miraeassetmf.co.in",
  AXISMID: "axismf.com",
  QUANTSC: "quantmutual.com",
  ICICIN50: "icicipruamc.com"
};

const mutualFundLogos: Record<string, string> = {
  PPFAS: "https://assets-netstorage.groww.in/mf-assets/logos/ppfas_groww.png",
  AXISBLU: "https://assets-netstorage.groww.in/mf-assets/logos/axis_groww.png",
  MIRAELC: "https://assets-netstorage.groww.in/mf-assets/logos/mirae_groww.png",
  AXISMID: "https://assets-netstorage.groww.in/mf-assets/logos/axis_groww.png",
  QUANTSC: "https://assets-netstorage.groww.in/mf-assets/logos/quant_groww.png",
  ICICIN50: "https://assets-netstorage.groww.in/mf-assets/logos/icici_groww.png"
};

const getLogoUrls = (symbol: string, instrumentType: string = "stock") => {
  // For mutual funds, use fund house logo
  if (instrumentType === "mutual_fund" && mutualFundLogos[symbol]) {
    return [mutualFundLogos[symbol], `/logos/${symbol}.svg`];
  }

  // For stocks, use company domain
  const domain = companyDomains[symbol];
  return domain
    ? [
        `https://logo.clearbit.com/${domain}`,
        `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
        `/logos/${symbol}.svg`
      ]
    : [`/logos/${symbol}.svg`];
};

const StockLogo = ({ symbol, instrumentType = "stock" }: { symbol: string; instrumentType?: string }) => {
  const [currentUrl, setCurrentUrl] = useState(0);
  const [error, setError] = useState(false);
  const urls = getLogoUrls(symbol, instrumentType);
  const handleError = () => {
    if (currentUrl < urls.length - 1) {
      setCurrentUrl(currentUrl + 1);
    } else {
      setError(true);
    }
  };
  return !error ? (
    <img src={urls[currentUrl]} alt={symbol} className="stock-logo-img" onError={handleError} />
  ) : (
    <img src={`/logos/${symbol}.svg`} alt={symbol} className="stock-logo-img" />
  );
};

const MarketBanner = () => {
  const [marketOpen, setMarketOpen] = useState(false);
  useEffect(() => {
    const now = new Date();
    const day = now.getDay();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const isWeekday = day >= 1 && day <= 5;
    const time = hours * 60 + minutes;
    const marketStart = 9 * 60 + 15;
    const marketEnd = 15 * 60 + 30;
    setMarketOpen(isWeekday && time >= marketStart && time < marketEnd);
  }, []);

  const indicesData = [
    { name: "SENSEX", value: "77,472.94", change: "-183.15 (-0.24%)", positive: false },
    { name: "NIFTY 50", value: "24,207.75", change: "-126.8 (-0.52%)", positive: false },
    { name: "NIFTY BANK", value: "57,783.75", change: "+269.55 (+0.47%)", positive: true },
    { name: "NIFTY MIDCAP 100", value: "64,101.20", change: "-61.7 (-0.10%)", positive: false }
  ];

  return (
    <div className="market-banner">
      <div className="market-status">
        <span className={`status-dot ${marketOpen ? "open" : "closed"}`}></span>
        <span className="status-text">{marketOpen ? "Market Open" : "Market Closed"}</span>
      </div>
      <div className="indices-scroll">
        <div className="indices-scroll-content">
          {[...indicesData, ...indicesData].map((idx, i) => (
            <div key={i} className="index-item">
              <span className="index-name">{idx.name}</span>
              <span className="index-value">{idx.value}</span>
              <span className={`index-change ${idx.positive ? "positive" : "negative"}`}>
                <i className={`fas fa-caret-${idx.positive ? "up" : "down"}`}></i> {idx.change}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

interface StockPlannerProps {
  onLogout?: () => void;
}

export function StockPlanner({ onLogout }: StockPlannerProps) {
  const [rows, setRows] = useState<R[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");
  const [activeTab, setActiveTab] = useState<"stocks" | "mutual_funds">("stocks");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [capFilter, setCapFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [stockBudget, setStockBudget] = useState(35000);
  const [mfBudget, setMfBudget] = useState(30000);
  const [editStockBudget, setEditStockBudget] = useState("35000");
  const [editMfBudget, setEditMfBudget] = useState("30000");
  const [isEditingStockBudget, setIsEditingStockBudget] = useState(false);
  const [isEditingMfBudget, setIsEditingMfBudget] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [isUpdating, setIsUpdating] = useState(false);
  const [selectedStock, setSelectedStock] = useState<{ symbol: string; name: string } | null>(null);
  const [selectedMutualFund, setSelectedMutualFund] = useState<{ symbol: string; name: string } | null>(null);
  const [sipDates, setSipDates] = useState<Record<string, any>>({});
  const [sipPreferences, setSipPreferences] = useState({ start_date: 5, end_date: 10 });
  const [showSipConfig, setShowSipConfig] = useState(false);
  const [showSipConfirm, setShowSipConfirm] = useState(false);
  const [sipChanges, setSipChanges] = useState<any[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [editingSipDate, setEditingSipDate] = useState<string | null>(null);
  const [tempSipDate, setTempSipDate] = useState<number>(5);

  const load = async (silent = false) => {
    if (!silent) setLoading(true);
    else setIsUpdating(true);

    try {
      setRows(await (await fetch(`${API}/api/recommendations?stock_budget=${stockBudget}&mf_budget=${mfBudget}`)).json());
      setLastUpdated(new Date());
    } catch (e) {
      setMsg(String(e));
    } finally {
      setLoading(false);
      setIsUpdating(false);
    }
  };

  useEffect(() => {
    load();
  }, [stockBudget, mfBudget]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      load(true); // Silent refresh
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [autoRefresh, stockBudget, mfBudget]);

  // Load SIP data when switching to mutual funds tab
  useEffect(() => {
    if (activeTab === "mutual_funds") {
      loadSipData();
    }
  }, [activeTab]);

  // Auto-dismiss notifications after 5 seconds
  useEffect(() => {
    if (msg) {
      const timer = setTimeout(() => {
        setMsg("");
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [msg]);

  const applyStockBudget = () => {
    const newBudget = parseFloat(editStockBudget);
    if (isNaN(newBudget) || newBudget <= 0) {
      setMsg("Please enter a valid budget amount");
      return;
    }
    setStockBudget(newBudget);
    setIsEditingStockBudget(false);
    setMsg(`Stock budget updated to ₹${newBudget.toLocaleString("en-IN")}`);
  };

  const cancelStockBudget = () => {
    setEditStockBudget(stockBudget.toString());
    setIsEditingStockBudget(false);
  };

  const applyMfBudget = () => {
    const newBudget = parseFloat(editMfBudget);
    if (isNaN(newBudget) || newBudget <= 0) {
      setMsg("Please enter a valid budget amount");
      return;
    }
    setMfBudget(newBudget);
    setIsEditingMfBudget(false);
    setMsg(`Mutual Fund budget updated to ₹${newBudget.toLocaleString("en-IN")}`);
  };

  const cancelMfBudget = () => {
    setEditMfBudget(mfBudget.toString());
    setIsEditingMfBudget(false);
  };

  const filtered = rows.filter(
    (r) =>
      // Filter by active tab
      ((activeTab === "stocks" && r.instrument_type === "stock") ||
       (activeTab === "mutual_funds" && r.instrument_type === "mutual_fund")) &&
      // Other filters
      (statusFilter === "ALL" || r.status === statusFilter) &&
      (capFilter === "ALL" || r.market_cap === capFilter) &&
      (search === "" || r.symbol.toLowerCase().includes(search.toLowerCase()) || r.name.toLowerCase().includes(search.toLowerCase()))
  );

  // Calculate deployment for current tab
  const stockRows = rows.filter(r => r.instrument_type === "stock");
  const mfRows = rows.filter(r => r.instrument_type === "mutual_fund");
  const stockDep = stockRows.reduce((a, r) => a + Number(r.deploy_amount), 0);
  const mfDep = mfRows.reduce((a, r) => a + Number(r.deploy_amount), 0);
  const stockRes = Math.max(stockBudget - stockDep, 0);
  const mfRes = Math.max(mfBudget - mfDep, 0);

  const loadSipData = async () => {
    try {
      const [datesRes, prefRes] = await Promise.all([
        fetch(`${API}/api/sip/optimal-dates`),
        fetch(`${API}/api/sip/preferences`)
      ]);
      const dates = await datesRes.json();
      const prefs = await prefRes.json();

      // Convert array to map
      const datesMap: Record<string, any> = {};
      dates.forEach((d: any) => {
        datesMap[d.symbol] = d;
      });

      setSipDates(datesMap);
      setSipPreferences(prefs);
    } catch (e) {
      console.error("Failed to load SIP data:", e);
    }
  };

  const analyzeSipDates = async () => {
    setIsAnalyzing(true);
    try {
      const res = await fetch(`${API}/api/sip/analyze`, { method: "POST" });
      const data = await res.json();

      // Check for changed dates
      const changes = data.results.filter((r: any) => r.date_changed);

      if (changes.length > 0) {
        setSipChanges(changes);
        setShowSipConfirm(true);
      } else {
        setMsg("SIP dates analyzed. No changes recommended.");
        await loadSipData();
      }
    } catch (e) {
      setMsg("Failed to analyze SIP dates: " + String(e));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const confirmSipChanges = async (acceptAll: boolean) => {
    if (acceptAll) {
      for (const change of sipChanges) {
        await fetch(`${API}/api/sip/confirm`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol: change.symbol,
            new_date: change.optimal_date
          })
        });
      }
      setMsg("SIP dates updated successfully.");
    } else {
      setMsg("SIP date changes cancelled.");
    }

    setShowSipConfirm(false);
    setSipChanges([]);
    await loadSipData();
  };

  const updateSipPreferences = async (start: number, end: number) => {
    try {
      await fetch(`${API}/api/sip/preferences`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start_date: start, end_date: end })
      });
      setSipPreferences({ start_date: start, end_date: end });
      setShowSipConfig(false);
      setMsg("SIP date range updated. Run analysis to optimize.");
    } catch (e) {
      setMsg("Failed to update preferences: " + String(e));
    }
  };

  const setManualSipDate = async (symbol: string, date: number | null) => {
    try {
      await fetch(`${API}/api/sip/manual-date`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, manual_date: date })
      });
      setEditingSipDate(null);
      await loadSipData();
      setMsg(date ? `SIP date set to ${date}th` : "Reverted to recommended date");
    } catch (e) {
      setMsg("Failed to update date: " + String(e));
    }
  };

  const startEditSipDate = (symbol: string, currentDate: number) => {
    setEditingSipDate(symbol);
    setTempSipDate(currentDate);
  };

  const run = async () => {
    setMsg("Running review...");
    await fetch(`${API}/api/review/run`, { method: "POST" });
    setMsg("Review completed.");
  };

  return (
    <main className="app-workspace investment-workspace">
      <WorkspaceHeader section="Stocks & funds" onLogout={onLogout} />
      <div className="suite-content">
      <MarketBanner />
      <div className="suite-page-heading"><span className="suite-eyebrow">INVEST WITH INTENTION</span><h1>Stocks &amp; funds</h1><p>Your monthly plan, from allocation to review.</p></div>

      <div className="combined-budget">
        <div className="combined-budget-main">
          <span className="combined-label">Total Monthly Budget</span>
          <h2 className="combined-amount">₹{(stockBudget + mfBudget).toLocaleString("en-IN")}</h2>
        </div>
        <div className="combined-breakdown">
          <div className="breakdown-item">
            <i className="fas fa-chart-line"></i>
            <span>Stocks: ₹{stockBudget.toLocaleString("en-IN")}</span>
          </div>
          <div className="breakdown-item">
            <i className="fas fa-briefcase"></i>
            <span>Mutual Funds: ₹{mfBudget.toLocaleString("en-IN")}</span>
          </div>
        </div>
      </div>

      <header>
        <div>
          <p className="eyebrow">PERSONAL INVESTMENT PLANNER</p>
          {activeTab === "stocks" ? (
            isEditingStockBudget ? (
              <div className="budget-editor">
                <input
                  type="number"
                  value={editStockBudget}
                  onChange={(e) => setEditStockBudget(e.target.value)}
                  className="budget-input"
                  autoFocus
                />
                <button onClick={applyStockBudget} className="budget-btn apply">
                  <i className="fas fa-check"></i> Apply
                </button>
                <button onClick={cancelStockBudget} className="budget-btn cancel">
                  <i className="fas fa-times"></i> Cancel
                </button>
              </div>
            ) : (
              <h1 onClick={() => setIsEditingStockBudget(true)} className="budget-display">
                ₹{stockBudget.toLocaleString("en-IN")} / month <i className="fas fa-edit edit-icon"></i>
              </h1>
            )
          ) : (
            isEditingMfBudget ? (
              <div className="budget-editor">
                <input
                  type="number"
                  value={editMfBudget}
                  onChange={(e) => setEditMfBudget(e.target.value)}
                  className="budget-input"
                  autoFocus
                />
                <button onClick={applyMfBudget} className="budget-btn apply">
                  <i className="fas fa-check"></i> Apply
                </button>
                <button onClick={cancelMfBudget} className="budget-btn cancel">
                  <i className="fas fa-times"></i> Cancel
                </button>
              </div>
            ) : (
              <h1 onClick={() => setIsEditingMfBudget(true)} className="budget-display">
                ₹{mfBudget.toLocaleString("en-IN")} / month <i className="fas fa-edit edit-icon"></i>
              </h1>
            )
          )}
          <p className="sub">NSE delivery • monthly review on the 5th</p>
        </div>
        <div className="header-controls">
          <div className="live-status">
            {isUpdating && <span className="updating-dot"></span>}
            <span className="live-text">
              {lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`auto-refresh-btn ${autoRefresh ? "active" : ""}`}
            title={autoRefresh ? "Auto-refresh every 30s" : "Auto-refresh paused"}
          >
            <i className={`fas fa-${autoRefresh ? "play" : "pause"}`}></i>
            {autoRefresh ? "Live" : "Paused"}
          </button>
          <button onClick={() => load(true)} aria-label="Refresh market prices" className="refresh-prices-btn" disabled={isUpdating}>
            <i className={`fas fa-sync-alt ${isUpdating ? "fa-spin" : ""}`}></i>
          </button>
          <button onClick={run} className="run-review-btn">
            Run review
          </button>
        </div>
      </header>
      <section className="stats" aria-label="Investment summary">
        <div>
          <span>Budget</span>
          <strong>₹{(activeTab === "stocks" ? stockBudget : mfBudget).toLocaleString("en-IN")}</strong>
        </div>
        <div>
          <span>Suggested deployment</span>
          <strong>₹{(activeTab === "stocks" ? stockDep : mfDep).toLocaleString("en-IN")}</strong>
        </div>
        <div>
          <span>Reserve</span>
          <strong>₹{(activeTab === "stocks" ? stockRes : mfRes).toLocaleString("en-IN")}</strong>
        </div>
        <div>
          <span>Holdings</span>
          <strong>{filtered.length}</strong>
        </div>
      </section>

      <div className="investment-tabs">
        <button
          onClick={() => setActiveTab("stocks")}
          className={`tab-btn ${activeTab === "stocks" ? "active" : ""}`}
        >
          <i className="fas fa-chart-line"></i> Stocks ({rows.filter(r => r.instrument_type === "stock").length})
        </button>
        <button
          onClick={() => setActiveTab("mutual_funds")}
          className={`tab-btn ${activeTab === "mutual_funds" ? "active" : ""}`}
        >
          <i className="fas fa-briefcase"></i> Mutual Funds ({rows.filter(r => r.instrument_type === "mutual_fund").length})
        </button>
      </div>

      <section className="panel">
        <div className="panelHead">
          <h2>{activeTab === "stocks" ? "Stock Recommendations" : "Mutual Fund SIPs"}</h2>
          <button className="secondary" onClick={load}>
            Refresh prices
          </button>
        </div>
        <div className="filters">
          <input
            type="text"
            placeholder={activeTab === "stocks" ? "Search stocks..." : "Search mutual funds..."}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input" aria-label="Search investments"
          />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="filter-select" aria-label="Filter by status">
            <option value="ALL">All Status</option>
            <option value="BUY">Buy</option>
            <option value="WAIT">Wait</option>
          </select>
          <select value={capFilter} onChange={(e) => setCapFilter(e.target.value)} className="filter-select" aria-label="Filter by market cap">
            <option value="ALL">All Cap</option>
            <option value="large">Large Cap</option>
            <option value="mid">Mid Cap</option>
            <option value="small">Small Cap</option>
            <option value="flexi">Flexi Cap</option>
          </select>
          {(statusFilter !== "ALL" || capFilter !== "ALL" || search !== "") && (
            <button
              className="clear-filters"
              onClick={() => {
                setStatusFilter("ALL");
                setCapFilter("ALL");
                setSearch("");
              }}
            >
              Clear filters
            </button>
          )}
        </div>

        {activeTab === "mutual_funds" && (
          <div className="sip-controls">
            <button
              onClick={analyzeSipDates}
              disabled={isAnalyzing}
              className="sip-btn analyze"
            >
              <i className={`fas fa-${isAnalyzing ? "spinner fa-spin" : "chart-line"}`}></i>
              {isAnalyzing ? "Analyzing..." : "Analyze SIP Dates"}
            </button>
            <button
              onClick={() => setShowSipConfig(true)}
              className="sip-btn config"
            >
              <i className="fas fa-cog"></i>
              Configure Range ({sipPreferences.start_date}-{sipPreferences.end_date})
            </button>
            <div className="sip-date-badge">
              <i className="fas fa-info-circle"></i>
              Optimal dates calculated from historical NAV data
            </div>
          </div>
        )}
        {loading ? (
          <p className="loading-text">
            <i className="fas fa-spinner fa-spin"></i> Loading market data…
          </p>
        ) : (
          <div className="tableWrap" tabIndex={0} role="region" aria-label="Investment table, scroll horizontally for all columns">
            <table>
              <thead>
                <tr>
                  <th>
                    <i className={`fas fa-${activeTab === "stocks" ? "building" : "briefcase"}`}></i> {activeTab === "stocks" ? "Stock" : "Fund"}
                  </th>
                  <th>
                    <i className="fas fa-layer-group"></i> Cap
                  </th>
                  <th>
                    <i className="fas fa-tag"></i> {activeTab === "stocks" ? "Price" : "SIP"}
                  </th>
                  <th>
                    <i className="fas fa-bullseye"></i> Target
                  </th>
                  <th>
                    <i className={`fas fa-${activeTab === "stocks" ? "boxes" : "calendar-check"}`}></i> {activeTab === "stocks" ? "Qty" : "SIP Date"}
                  </th>
                  <th>
                    <i className="fas fa-money-bill-wave"></i> Deploy
                  </th>
                  <th>
                    <i className="fas fa-traffic-light"></i> Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr
                    key={r.symbol}
                    onClick={(e) => {
                      // Don't trigger if clicking on SIP date editor
                      if ((e.target as HTMLElement).closest('.sip-date-editor, .sip-date-badge')) return;

                      if (r.instrument_type === "stock") {
                        setSelectedStock({ symbol: r.symbol, name: r.name });
                      } else {
                        setSelectedMutualFund({ symbol: r.symbol, name: r.name });
                      }
                    }}
                    title={r.instrument_type === "stock" ? "Click to view advanced chart" : "Click to view fund details"}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <div className="stock-cell">
                        <StockLogo symbol={r.symbol} instrumentType={r.instrument_type} />
                        <div>
                          <b>{r.symbol}</b>
                          <small>{r.name}</small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="cap-badge">
                        <i className="fas fa-circle"></i> {r.market_cap}
                      </span>
                    </td>
                    <td>
                      {r.instrument_type === "mutual_fund" ? (
                        <span className="mf-sip-badge">
                          <i className="fas fa-calendar-alt"></i> SIP
                        </span>
                      ) : r.current_price == null ? (
                        "—"
                      ) : (
                        <div className="price-cell">
                          <span className="live-price">
                            <span className="live-indicator"></span>₹{r.current_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                          </span>
                          {r.day_change != null && r.day_change_percent != null && (
                            <span className={`day-change ${r.day_change >= 0 ? "positive" : "negative"}`}>
                              <i className={`fas fa-caret-${r.day_change >= 0 ? "up" : "down"}`}></i> {Math.abs(r.day_change).toFixed(2)} (
                              {r.day_change_percent >= 0 ? "+" : ""}
                              {r.day_change_percent.toFixed(2)}%)
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                    <td>₹{r.target_amount.toLocaleString("en-IN")}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      {r.instrument_type === "mutual_fund" ? (
                        editingSipDate === r.symbol ? (
                          <div className="sip-date-editor">
                            <select
                              value={tempSipDate}
                              onChange={(e) => setTempSipDate(parseInt(e.target.value))}
                              className="sip-date-select"
                              autoFocus
                            >
                              {Array.from({ length: 28 }, (_, i) => i + 1).map(day => (
                                <option key={day} value={day}>{day}th</option>
                              ))}
                            </select>
                            <button
                              onClick={() => setManualSipDate(r.symbol, tempSipDate)}
                              className="sip-date-btn save"
                              title="Save date"
                            >
                              <i className="fas fa-check"></i>
                            </button>
                            {sipDates[r.symbol]?.is_manual && (
                              <button
                                onClick={() => setManualSipDate(r.symbol, null)}
                                className="sip-date-btn revert"
                                title="Revert to recommended"
                              >
                                <i className="fas fa-undo"></i>
                              </button>
                            )}
                            <button
                              onClick={() => setEditingSipDate(null)}
                              className="sip-date-btn cancel"
                              title="Cancel"
                            >
                              <i className="fas fa-times"></i>
                            </button>
                          </div>
                        ) : (
                          <span
                            className={`sip-date-badge ${sipDates[r.symbol]?.is_manual ? 'manual' : ''}`}
                            onClick={() => startEditSipDate(r.symbol, sipDates[r.symbol]?.optimal_date || 5)}
                            title={sipDates[r.symbol]?.is_manual ? "Manually set - Click to change" : "AI recommended - Click to override"}
                          >
                            <i className={`fas fa-${sipDates[r.symbol]?.is_manual ? 'user-edit' : 'robot'}`}></i>
                            {sipDates[r.symbol]?.optimal_date || "—"}th
                          </span>
                        )
                      ) : (
                        r.quantity
                      )}
                    </td>
                    <td>₹{Number(r.deploy_amount).toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td>
                    <td>
                      <span className={`pill ${r.status.toLowerCase()}`}>
                        {r.status === "BUY" ? <i className="fas fa-shopping-cart"></i> : <i className="fas fa-hourglass-half"></i>} {r.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <p className="no-results">
                <i className="fas fa-inbox"></i> No stocks match your filters.
              </p>
            )}
          </div>
        )}
        <p className="note">
          <i className="fas fa-exclamation-triangle"></i> Verify the live NSE quote before ordering. This app never executes trades.
        </p>
      </section>
      <footer className="footer">
        <i className="fas fa-copyright"></i> {new Date().getFullYear()} Arun Kumar. All rights reserved. •{" "}
        <i className="fas fa-heart"></i> Built with passion for smart investing <i className="fas fa-chart-line"></i>
      </footer>
      {msg && (
        <div className="toast">
          <i className="fas fa-info-circle"></i> {msg}
        </div>
      )}
      {selectedStock && (
        <StockChartModal
          symbol={selectedStock.symbol}
          name={selectedStock.name}
          onClose={() => setSelectedStock(null)}
          apiUrl={API}
        />
      )}

      {selectedMutualFund && (
        <MutualFundModal
          symbol={selectedMutualFund.symbol}
          name={selectedMutualFund.name}
          onClose={() => setSelectedMutualFund(null)}
        />
      )}

      {showSipConfig && (
        <SIPConfigModal
          currentStart={sipPreferences.start_date}
          currentEnd={sipPreferences.end_date}
          onSave={(start, end) => updateSipPreferences(start, end)}
          onClose={() => setShowSipConfig(false)}
        />
      )}

      {showSipConfirm && (
        <SIPConfirmModal
          changes={sipChanges}
          onConfirm={confirmSipChanges}
        />
      )}
      </div>
    </main>
  );
}
