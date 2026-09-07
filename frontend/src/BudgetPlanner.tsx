import React, { useEffect, useMemo, useState } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";

type Bucket = "needs" | "wants" | "future";
interface Category { id?: number | null; name: string; bucket: Bucket; planned_amount: number; actual_amount: number; icon: string; }
const API = window.location.hostname === "localhost" ? "http://localhost:8000" : window.location.origin;
const money = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value || 0);
const monthLabel = (date: Date) => date.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
const bucketInfo: Record<Bucket, { label: string; guide: number; copy: string }> = {
  needs: { label: "Needs", guide: 50, copy: "Home, bills and essentials" },
  wants: { label: "Wants", guide: 30, copy: "Lifestyle and flexible spends" },
  future: { label: "Future", guide: 20, copy: "Savings, SIPs and debt payoff" },
};

export function BudgetPlanner({ onLogout }: { onLogout?: () => void }) {
  const [date, setDate] = useState(new Date());
  const [income, setIncome] = useState(0);
  const [notes, setNotes] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [newCategory, setNewCategory] = useState<Category>({ name: "", bucket: "needs", planned_amount: 0, actual_amount: 0, icon: "fa-receipt" });
  const year = date.getFullYear(), month = date.getMonth() + 1;

  const loadBudget = async () => {
    setLoading(true); setMessage("");
    try {
      const response = await fetch(`${API}/api/budget/${year}/${month}`);
      if (!response.ok) throw new Error();
      const data = await response.json();
      setIncome(Number(data.income || 0)); setNotes(data.notes || ""); setCategories(data.categories || []);
    } catch { setMessage("Could not load this budget. Please check the connection."); }
    finally { setLoading(false); }
  };
  useEffect(() => { loadBudget(); }, [year, month]);

  const totals = useMemo(() => {
    const planned = categories.reduce((sum, item) => sum + Number(item.planned_amount || 0), 0);
    const spent = categories.reduce((sum, item) => sum + Number(item.actual_amount || 0), 0);
    const future = categories.filter(item => item.bucket === "future").reduce((sum, item) => sum + Number(item.actual_amount || 0), 0);
    return { planned, spent, remaining: income - spent, unallocated: income - planned, savingsRate: income ? future / income * 100 : 0 };
  }, [categories, income]);

  const updateCategory = (index: number, field: "planned_amount" | "actual_amount", value: number) =>
    setCategories(items => items.map((item, i) => i === index ? { ...item, [field]: Math.max(0, value || 0) } : item));
  const saveBudget = async () => {
    setSaving(true); setMessage("");
    try {
      const response = await fetch(`${API}/api/budget/${year}/${month}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ income, notes, categories }) });
      if (!response.ok) throw new Error();
      const data = await response.json(); setCategories(data.categories); setMessage("Budget saved securely.");
    } catch { setMessage("Budget could not be saved. Please try again."); }
    finally { setSaving(false); }
  };
  const moveMonth = (offset: number) => setDate(new Date(year, month - 1 + offset, 1));
  const addCategory = () => {
    if (!newCategory.name.trim()) return;
    setCategories(items => [...items, { ...newCategory, name: newCategory.name.trim() }]);
    setNewCategory({ name: "", bucket: "needs", planned_amount: 0, actual_amount: 0, icon: "fa-receipt" }); setShowAdd(false);
  };

  return <div className="money-workspace">
    <WorkspaceHeader section="Budget" onLogout={onLogout} />
    <main className="money-content">
      <section className="money-heading">
        <div><span className="suite-eyebrow">MONTHLY MONEY PLAN</span><h1>Give every rupee a purpose.</h1><p>Plan essentials, enjoy life, and build your future—all in one clear monthly view.</p></div>
        <div className="month-switcher"><button onClick={() => moveMonth(-1)} aria-label="Previous month"><i className="fas fa-chevron-left" /></button><strong>{monthLabel(date)}</strong><button onClick={() => moveMonth(1)} aria-label="Next month"><i className="fas fa-chevron-right" /></button></div>
      </section>
      {message && <div className={`money-notice ${message.includes("saved") ? "success" : ""}`}>{message}</div>}
      {loading ? <div className="money-loading"><span className="money-spinner" />Preparing your month…</div> : <>
        <section className="budget-hero">
          <div><label htmlFor="monthly-income">Monthly take-home income</label><div className="income-input"><span>₹</span><input id="monthly-income" type="number" min="0" value={income || ""} placeholder="0" onChange={e => setIncome(Number(e.target.value))} /></div><small>Use the amount available after deductions.</small></div>
          <div className="budget-ring" style={{ background: `conic-gradient(#176f57 0 ${Math.min(100, income ? totals.spent / income * 100 : 0)}%, #dce8df 0)` }}><div><strong>{income ? Math.round(totals.spent / income * 100) : 0}%</strong><span>used</span></div></div>
          <div className="budget-hero-summary"><span>Available now</span><strong className={totals.remaining < 0 ? "negative" : ""}>{money(totals.remaining)}</strong><small>{totals.unallocated >= 0 ? `${money(totals.unallocated)} not yet assigned` : `${money(Math.abs(totals.unallocated))} over-planned`}</small></div>
        </section>
        <section className="money-stats">
          <article><span>Planned</span><strong>{money(totals.planned)}</strong><small>{income ? Math.round(totals.planned / income * 100) : 0}% of income</small></article>
          <article><span>Actual</span><strong>{money(totals.spent)}</strong><small>Across {categories.length} categories</small></article>
          <article><span>Remaining</span><strong className={totals.remaining < 0 ? "negative" : "positive"}>{money(totals.remaining)}</strong><small>Income less actual</small></article>
          <article><span>Savings rate</span><strong>{totals.savingsRate.toFixed(0)}%</strong><small>Future bucket actuals</small></article>
        </section>
        <div className="budget-layout">
          <section className="money-panel category-panel"><div className="panel-title"><div><h2>Monthly categories</h2><p>Planned versus actual spending</p></div><button className="text-action" onClick={() => setShowAdd(true)}><i className="fas fa-plus" /> Add category</button></div>
            <div className="category-labels"><span>Category</span><span>Plan</span><span>Actual</span><span></span></div>
            {categories.map((item, index) => { const percent = item.planned_amount ? item.actual_amount / item.planned_amount * 100 : 0; return <div className="budget-row" key={`${item.name}-${index}`}>
              <div className="budget-category"><span className={`category-icon ${item.bucket}`}><i className={`fas ${item.icon}`} /></span><div><strong>{item.name}</strong><small>{bucketInfo[item.bucket].label}</small><div className="row-progress"><span className={percent > 100 ? "over" : ""} style={{ width: `${Math.min(100, percent)}%` }} /></div></div></div>
              <div className="money-field"><span>₹</span><input aria-label={`${item.name} planned`} type="number" min="0" value={item.planned_amount || ""} placeholder="0" onChange={e => updateCategory(index, "planned_amount", Number(e.target.value))} /></div>
              <div className="money-field"><span>₹</span><input aria-label={`${item.name} actual`} type="number" min="0" value={item.actual_amount || ""} placeholder="0" onChange={e => updateCategory(index, "actual_amount", Number(e.target.value))} /></div>
              <button className="row-delete" aria-label={`Remove ${item.name}`} onClick={() => setCategories(items => items.filter((_, i) => i !== index))}><i className="fas fa-trash" /></button>
            </div>; })}
          </section>
          <aside className="budget-aside">
            <section className="money-panel guide-panel"><span className="panel-kicker">50 / 30 / 20 GUIDE</span><h2>A balanced starting point</h2>{(Object.keys(bucketInfo) as Bucket[]).map(bucket => { const amount = categories.filter(i => i.bucket === bucket).reduce((s, i) => s + Number(i.planned_amount), 0); const share = income ? amount / income * 100 : 0; return <div className="guide-row" key={bucket}><div><strong>{bucketInfo[bucket].label}</strong><small>{bucketInfo[bucket].copy}</small></div><span>{share.toFixed(0)}% <em>/ {bucketInfo[bucket].guide}%</em></span></div>; })}<p className="guide-note">A guide, not a rule. Adjust it to suit your city, family and goals.</p></section>
            <section className="money-panel note-panel"><label htmlFor="budget-notes">Notes for {monthLabel(date)}</label><textarea id="budget-notes" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Salary change, annual premium, travel plans…" /><button className="primary-action" onClick={saveBudget} disabled={saving}><i className={`fas ${saving ? "fa-spinner fa-spin" : "fa-check"}`} /> {saving ? "Saving…" : "Save this budget"}</button></section>
          </aside>
        </div>
      </>}
    </main>
    {showAdd && <div className="money-modal" role="dialog" aria-modal="true" aria-labelledby="add-category-title"><div className="money-modal-card"><div className="modal-heading"><div><span>NEW BUDGET LINE</span><h2 id="add-category-title">Add a category</h2></div><button onClick={() => setShowAdd(false)} aria-label="Close"><i className="fas fa-times" /></button></div><label>Category name<input autoFocus value={newCategory.name} onChange={e => setNewCategory({ ...newCategory, name: e.target.value })} placeholder="e.g. Childcare" /></label><label>Money bucket<select value={newCategory.bucket} onChange={e => setNewCategory({ ...newCategory, bucket: e.target.value as Bucket })}><option value="needs">Needs</option><option value="wants">Wants</option><option value="future">Future</option></select></label><div className="modal-actions"><button className="secondary-action" onClick={() => setShowAdd(false)}>Cancel</button><button className="primary-action" onClick={addCategory}>Add category</button></div></div></div>}
  </div>;
}
