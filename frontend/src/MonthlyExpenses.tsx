import React, { useState, useEffect } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";

interface Expense {
  id: number;
  name: string;
  amount: number | null;
  day_of_month: number;
  category: string;
  description: string;
  is_paid: boolean;
  paid_date: string | null;
  notes: string;
  is_recurring?: boolean;
  specific_year?: number | null;
  specific_month?: number | null;
}

interface MonthlyExpensesProps {
  onLogout?: () => void;
}

// Use the same host as the frontend, but port 8000 for API
const getApiUrl = () => {
  return window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : window.location.origin;
};

const API = getApiUrl();

interface MonthlySummary {
  year: number;
  month: number;
  total_amount: number;
  paid_amount: number;
  left_to_pay: number;
  expense_count: number;
}

interface ExpenseInsight {
  type: "warning" | "tip" | "success";
  category: string;
  title: string;
  description: string;
  potential_savings: number;
  icon: string;
}

export function MonthlyExpenses({ onLogout }: MonthlyExpensesProps) {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [search, setSearch] = useState("");
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [showAddModal, setShowAddModal] = useState(false);
  const [filter, setFilter] = useState<"all" | "paid" | "unpaid">("all");
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [monthlySummaries, setMonthlySummaries] = useState<MonthlySummary[]>([]);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [expenseToDelete, setExpenseToDelete] = useState<Expense | null>(null);
  const [aiInsights, setAiInsights] = useState<ExpenseInsight[]>([]);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1;

  const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

  const loadMonthlySummaries = async () => {
    try {
      const response = await fetch(`${API}/api/expenses/monthly-summary`);
      const data = await response.json();
      setMonthlySummaries(data);
    } catch (error) {
      console.error("Failed to load monthly summaries:", error);
    }
  };

  const generateAIInsights = () => {
    const money = (value: number) => `\u20b9${value.toLocaleString("en-IN")}`;
    const total = expenses.reduce((sum, e) => sum + Number(e.amount || 0), 0);
    const unpaid = expenses.filter(e => !e.is_paid);
    const categories: Record<string, number> = {};
    expenses.forEach(e => { const key = e.category || "Other"; categories[key] = (categories[key] || 0) + Number(e.amount || 0); });
    const largest = Object.entries(categories).sort((a, b) => b[1] - a[1])[0];
    const insights: ExpenseInsight[] = [];
    if (unpaid.length) insights.push({type: "warning", category: "Payment overview", title: `${unpaid.length} payments remaining`, description: `${money(unpaid.reduce((sum, e) => sum + Number(e.amount || 0), 0))} is still marked unpaid for ${monthNames[month - 1]}. Review the unpaid list to plan your next payments.`, potential_savings: 0, icon: "fa-clock"});
    else if (expenses.length) insights.push({type: "success", category: "Payment overview", title: "Everything is marked paid", description: `All ${expenses.length} expenses for this month are complete.`, potential_savings: 0, icon: "fa-check-circle"});
    if (largest && total > 0) insights.push({type: "tip", category: "Spending mix", title: `${largest[0]} is your largest category`, description: `${money(largest[1])} accounts for ${Math.round(largest[1] / total * 100)}% of this month's recorded expenses.`, potential_savings: 0, icon: "fa-chart-pie"});
    const previousDate = new Date(year, month - 2, 1);
    const previous = monthlySummaries.find(m => m.year === previousDate.getFullYear() && m.month === previousDate.getMonth() + 1);
    if (previous && previous.total_amount > 0 && expenses.length) {
      const change = total - previous.total_amount;
      insights.push({type: "tip", category: "Month comparison", title: `${money(Math.abs(change))} ${change >= 0 ? "more" : "less"} than last month`, description: `Recorded expenses are ${Math.abs(change / previous.total_amount * 100).toFixed(1)}% ${change >= 0 ? "higher" : "lower"}. One-time payments and changes to recurring expenses can affect this comparison.`, potential_savings: 0, icon: "fa-chart-line"});
    }
    const missing = expenses.filter(e => e.amount == null).length;
    if (missing) insights.push({type: "warning", category: "Data completeness", title: `${missing} expenses need an amount`, description: "Add their amounts for a complete monthly total. They currently contribute zero to the totals.", potential_savings: 0, icon: "fa-pen"});
    setAiInsights(insights);
  };

  const loadExpenses = async (preserveScroll = false) => {
    // Save current scroll position if requested
    const scrollPosition = preserveScroll ? window.scrollY || window.pageYOffset : 0;

    setLoading(true);
    setLoadError("");
    try {
      const response = await fetch(`${API}/api/expenses/${year}/${month}`);
      if (!response.ok) throw new Error("Unable to load expenses");
      const data = await response.json();
      setExpenses(data);

      // Restore scroll position after React re-renders
      if (preserveScroll && scrollPosition > 0) {
        // Use requestAnimationFrame to ensure DOM has updated
        requestAnimationFrame(() => {
          window.scrollTo(0, scrollPosition);
        });
      }
    } catch (error) {
      console.error("Failed to load expenses:", error);
      setLoadError("Could not load this month. Check the connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  const togglePaid = async (expenseId: number, isPaid: boolean) => {
    // Optimistically update the UI immediately
    setExpenses(prevExpenses =>
      prevExpenses.map(exp =>
        exp.id === expenseId
          ? { ...exp, is_paid: !isPaid, paid_date: !isPaid ? new Date().toISOString().split('T')[0] : null }
          : exp
      )
    );

    try {
      if (isPaid) {
        await fetch(`${API}/api/expenses/${expenseId}/pay?year=${year}&month=${month}`, {
          method: "DELETE"
        });
      } else {
        await fetch(`${API}/api/expenses/${expenseId}/pay`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ year, month })
        });
      }
      // Silently sync with server in background without re-rendering
      const response = await fetch(`${API}/api/expenses/${year}/${month}`);
      const data = await response.json();
      setExpenses(data);
      // Refresh monthly breakdown to show updated totals
      loadMonthlySummaries();
    } catch (error) {
      console.error("Failed to toggle payment:", error);
      // Revert optimistic update on error while preserving scroll position
      loadExpenses(true);
      loadMonthlySummaries();
    }
  };

  const goToPreviousMonth = () => {
    const newDate = new Date(year, month - 2, 1);
    setCurrentDate(newDate);
  };

  const goToNextMonth = () => {
    const newDate = new Date(year, month, 1);
    setCurrentDate(newDate);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const handleDeleteClick = (expense: Expense) => {
    if (expense.is_recurring) {
      // Show modal for recurring expenses
      setExpenseToDelete(expense);
      setShowDeleteModal(true);
    } else {
      // Direct delete for one-time expenses
      setExpenseToDelete(expense);
      setShowDeleteModal(true);
    }
  };

  const handleEditClick = (expense: Expense) => {
    setEditingExpense(expense);
    setShowAddModal(true);
  };

  const markAllAsPaid = async () => {
    const unpaidExpenses = expenses.filter(e => !e.is_paid);

    if (unpaidExpenses.length === 0) {
      alert("All expenses are already paid!");
      return;
    }

    const confirmMsg = `Mark all ${unpaidExpenses.length} unpaid expenses as paid for ${monthNames[month - 1]} ${year}?`;
    if (!confirm(confirmMsg)) return;

    try {
      // Optimistically update UI
      setExpenses(prevExpenses =>
        prevExpenses.map(exp => ({ ...exp, is_paid: true, paid_date: new Date().toISOString().split('T')[0] }))
      );

      // Mark all as paid in backend
      const promises = unpaidExpenses.map(expense =>
        fetch(`${API}/api/expenses/${expense.id}/pay`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ year, month })
        })
      );

      await Promise.all(promises);

      // Reload to sync with server
      loadExpenses(true);
      loadMonthlySummaries();
    } catch (error) {
      console.error("Failed to mark all as paid:", error);
      alert("Failed to mark all expenses as paid");
      loadExpenses(true); // Reload on error
    }
  };

  const deleteExpenseFinal = async (expenseId: number, deleteType: "this_month" | "all") => {
    if (deleteType === "this_month") {
      // Hide this expense for current month only
      await fetch(`${API}/api/expenses/${expenseId}/hide-month`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year, month })
      });
    } else {
      // Delete permanently (all months)
      await fetch(`${API}/api/expenses/${expenseId}`, { method: "DELETE" });
    }
  };

  const deleteExpense = async (expenseId: number, expenseName: string) => {
    // This function is now handled by modal
    return;

    try {
      await fetch(`${API}/api/expenses/${expenseId}`, {
        method: "DELETE"
      });
      loadExpenses(true); // Preserve scroll position
    } catch (error) {
      console.error("Failed to delete expense:", error);
      alert("Failed to delete expense. Please try again.");
    }
  };

  const completedCount = expenses.filter(e => e.is_paid).length;
  const totalCount = expenses.length;

  // Calculate totals
  const totalAmount = expenses.reduce((sum, e) => sum + (e.amount || 0), 0);
  const paidAmount = expenses.filter(e => e.is_paid).reduce((sum, e) => sum + (e.amount || 0), 0);
  const leftToPay = expenses.filter(e => !e.is_paid).reduce((sum, e) => sum + (e.amount || 0), 0);

  const filteredExpenses = expenses.filter((expense) => {
    if (!`${expense.name} ${expense.category}`.toLowerCase().includes(search.toLowerCase())) return false;
    if (filter === "paid") return expense.is_paid;
    if (filter === "unpaid") return !expense.is_paid;
    return true;
  });

  useEffect(() => {
    loadExpenses();
    loadMonthlySummaries();
  }, [year, month]);

  useEffect(() => {
    generateAIInsights();
  }, [expenses, monthlySummaries, year, month]);

  const formatDate = (dayOfMonth: number) => {
    return `${String(dayOfMonth).padStart(2, "0")}/${String(month).padStart(2, "0")}/${String(year).slice(2)}`;
  };

  return (
    <main className="expenses-page">
      <WorkspaceHeader section="Expenses" onLogout={onLogout} />

      <div className="workspace-heading">
        <div><span className="workspace-eyebrow">YOUR MONEY, IN FOCUS</span><h1>Monthly expenses</h1><p>A clear view of every month. A little more peace of mind.</p></div>
        <button className="workspace-add" onClick={() => { setEditingExpense(null); setShowAddModal(true); }}><i className="fas fa-plus" /> Add expense</button>
      </div>
      <div className="expenses-layout">
        {/* Monthly history */}
        <aside className="monthly-sidebar" aria-label="Monthly breakdown">
          <div className="monthly-breakdown-section">
            <h3 className="sidebar-title">
              <i className="fas fa-calendar-alt"></i> Monthly breakdown
            </h3>
            <p className="panel-caption">Your last 12 months at a glance</p>
            <div className="sidebar-months">
              {monthlySummaries.map((summary) => {
                const isCurrentMonth = summary.year === year && summary.month === month;
                const monthName = monthNames[summary.month - 1];
                const shortMonthName = monthName.substring(0, 3);

                return (
                  <button
                    key={`${summary.year}-${summary.month}`}
                    className={`month-summary-card ${isCurrentMonth ? "active" : ""}`}
                    aria-current={isCurrentMonth ? "date" : undefined}
                    onClick={() => {
                      const newDate = new Date(summary.year, summary.month - 1, 1);
                      setCurrentDate(newDate);
                    }}
                  >
                    <div className="month-summary-header">
                      <span className="month-name">{shortMonthName} {summary.year}</span>
                      <span className="expense-count">{summary.expense_count} items</span>
                    </div>
                    <div className="month-summary-amount">
                      <div className="amount-label">Total Paid</div>
                      <div className="amount-value">
                        ₹{summary.paid_amount.toLocaleString("en-IN")}
                      </div>
                    </div>
                    <div className="month-summary-progress">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${summary.total_amount > 0 ? (summary.paid_amount / summary.total_amount) * 100 : 0}%`
                        }}
                      ></div>
                    </div>
                    <div className="month-summary-footer">
                      <span className="footer-left">₹{summary.left_to_pay.toLocaleString("en-IN")} left</span>
                      <span className="footer-percent">
                        {summary.total_amount > 0
                          ? Math.round((summary.paid_amount / summary.total_amount) * 100)
                          : 0}%
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>


        </aside>

        {/* Selected month ledger */}
        <div className="expenses-container">
          <div className="expenses-sticky-header">
          <div className="expenses-header">
            <button aria-label="Previous month" onClick={goToPreviousMonth} className="month-nav-btn">
              <i className="fas fa-chevron-left"></i>
            </button>
            <div className="month-title">
              <h2>{monthNames[month - 1]} {year}</h2>
              <p className="month-subtitle">Your monthly expense ledger</p>
            </div>
            <button aria-label="Next month" onClick={goToNextMonth} className="month-nav-btn">
              <i className="fas fa-chevron-right"></i>
            </button>
          </div>

          <div className="expenses-stats">
            <div className="completion-count">
              <span className="count-number">{completedCount}</span>
              <span className="count-separator">/</span>
              <span className="count-total">{totalCount}</span>
              <span className="count-label">Completed</span>
            </div>
            <div className="filter-buttons">
              <button
                onClick={() => setFilter("all")}
                className={`filter-btn ${filter === "all" ? "active" : ""}`}
              >
                All
              </button>
              <button
                onClick={() => setFilter("paid")}
                className={`filter-btn ${filter === "paid" ? "active" : ""}`}
              >
                Paid
              </button>
              <button
                onClick={() => setFilter("unpaid")}
                className={`filter-btn ${filter === "unpaid" ? "active" : ""}`}
              >
                Unpaid
              </button>
            </div>
            <div className="action-buttons">
              <button
                onClick={markAllAsPaid}
                className="mark-all-paid-btn"
                title="Mark all expenses as paid"
                disabled={expenses.length === 0 || completedCount === totalCount}
              >
                <i className="fas fa-check-double"></i> Mark All Paid
              </button>
              {(currentDate.getMonth() !== new Date().getMonth() || year !== new Date().getFullYear()) && (
                <button onClick={goToToday} className="today-btn">
                  <i className="fas fa-calendar-day"></i> Today
                </button>
              )}
            </div>
          </div>

          {!loading && (
            <div className="expenses-totals">
              <div className="total-card total-amount">
                <div className="total-icon">
                  <i className="fas fa-receipt"></i>
                </div>
                <div className="total-content">
                  <div className="total-label">Total Amount</div>
                  <div className="total-value">₹{totalAmount.toLocaleString("en-IN")}</div>
                </div>
              </div>
              <div className="total-card paid-amount">
                <div className="total-icon">
                  <i className="fas fa-check-circle"></i>
                </div>
                <div className="total-content">
                  <div className="total-label">Paid</div>
                  <div className="total-value">₹{paidAmount.toLocaleString("en-IN")}</div>
                </div>
              </div>
              <div className="total-card left-amount">
                <div className="total-icon">
                  <i className="fas fa-hourglass-half"></i>
                </div>
                <div className="total-content">
                  <div className="total-label">Left to Pay</div>
                  <div className="total-value">₹{leftToPay.toLocaleString("en-IN")}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        <label className="expense-search"><i className="fas fa-search" /><input aria-label="Search expenses" placeholder="Search expenses or categories..." value={search} onChange={e => setSearch(e.target.value)} /><span>{filteredExpenses.length} items</span></label>
        <div className="expenses-scrollable-content">
        {loadError && <div className="expense-error" role="alert">{loadError} <button onClick={() => loadExpenses()}>Retry</button></div>}
        {loading ? (
          <div className="expenses-loading">
            <i className="fas fa-spinner fa-spin"></i> Loading expenses...
          </div>
        ) : (
          <div className="expenses-list">
            {filteredExpenses.length === 0 ? (
              <div className="no-expenses">
                <i className="fas fa-filter"></i>
                <p>No {filter === "paid" ? "paid" : filter === "unpaid" ? "unpaid" : ""} expenses found</p>
              </div>
            ) : (
              filteredExpenses.map((expense) => (
              <div key={expense.id} className={`expense-item ${expense.is_paid ? "paid" : ""}`}>
                <label className="expense-checkbox">
                  <input
                    type="checkbox"
                    aria-label={`Mark ${expense.name} ${expense.is_paid ? "unpaid" : "paid"}`}
                    checked={expense.is_paid}
                    onChange={() => togglePaid(expense.id, expense.is_paid)}
                  />
                  <span className="checkbox-custom"></span>
                </label>
                <div className="expense-content">
                  <div className="expense-name">{expense.name}</div>
                  <div className="expense-meta">
                    <span className="expense-date">
                      {formatDate(expense.day_of_month)}
                    </span>
                    {expense.category && (
                      <>
                        <span className="meta-separator">•</span>
                        <span className="expense-category">{expense.category}</span>
                      </>
                    )}

                  </div>
                </div>
                <div className="expense-row-amount"><strong>{expense.amount == null ? "Not set" : `\u20b9${Number(expense.amount).toLocaleString("en-IN")}`}</strong><span className={expense.is_paid ? "status-paid" : "status-unpaid"}>{expense.is_paid ? "Paid" : "Unpaid"}</span></div>
                <div className="expense-actions">
                  <button
                    onClick={() => handleEditClick(expense)}
                    className="expense-edit-btn"
                    title="Edit expense"
                  >
                    <i className="fas fa-edit"></i>
                  </button>
                  <button
                    onClick={() => handleDeleteClick(expense)}
                    className="expense-delete-btn"
                    title="Delete expense"
                  >
                    <i className="fas fa-trash"></i>
                  </button>
                </div>
              </div>
            ))
            )}
          </div>
        )}
        </div>

          <button onClick={() => setShowAddModal(true)} className="add-expense-fab" aria-label="Add expense">
            <i className="fas fa-plus"></i>
          </button>
        </div>
        <aside className="advisor-sidebar" aria-label="Financial advisor">          {/* AI Financial Advisor */}
          <div className="ai-insights-panel">
            <h3 className="sidebar-title">
              <i className="fas fa-wand-magic-sparkles"></i> AI Financial Advisor
            </h3>
            <p className="panel-caption">Your monthly money companion</p>
            <div className="advisor-overview"><span className="advisor-mode">SPENDING SNAPSHOT</span><strong>{totalAmount > 0 ? Math.round(paidAmount / totalAmount * 100) : 0}%</strong><span>of this month's amount is paid</span><div className="advisor-meter"><span style={{width: `${totalAmount > 0 ? Math.min(100, paidAmount / totalAmount * 100) : 0}%`}} /></div><button onClick={() => setFilter("unpaid")}>Review unpaid expenses <i className="fas fa-arrow-right" /></button></div>
            {aiInsights.length > 0 ? (
              <>
                <div className="insights-list">
                  {aiInsights.map((insight, idx) => (
                    <div key={idx} className={`insight-card insight-${insight.type}`}>
                      <div className="insight-header">
                        <i className={`fas ${insight.icon}`}></i>
                        <span className="insight-category">{insight.category}</span>
                      </div>
                      <h4 className="insight-title">{insight.title}</h4>
                      <p className="insight-description">{insight.description}</p>
                      {insight.potential_savings > 0 && (
                        <div className="insight-savings">
                          <i className="fas fa-piggy-bank"></i>
                          <span>Potential savings: <strong>₹{insight.potential_savings.toLocaleString("en-IN")}/mo</strong></span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <div className="ai-disclaimer">
                  <i className="fas fa-info-circle"></i>
                  <small>Calculated from your recorded expenses. Rule-based insights; no AI model is connected.</small>
                </div>
              </>
            ) : (
              <div className="no-insights">
                <i className="fas fa-chart-line" style={{fontSize: '32px', color: '#cbd5e1', marginBottom: '12px'}}></i>
                <p>No insights for this month yet</p>
                <small>Add expenses to see your monthly overview</small>
              </div>
            )}
          </div>
        </aside>
      </div>

      {showAddModal && (
        <AddExpenseModal
          onClose={() => {
            setShowAddModal(false);
            setEditingExpense(null);
          }}
          onSuccess={() => {
            setShowAddModal(false);
            setEditingExpense(null);
            loadExpenses(true); // Preserve scroll position
            loadMonthlySummaries();
          }}
          editingExpense={editingExpense}
          currentYear={year}
          currentMonth={month}
        />
      )}

      {showDeleteModal && expenseToDelete && (
        <DeleteConfirmModal
          expense={expenseToDelete}
          currentMonth={monthNames[month - 1]}
          currentYear={year}
          onClose={() => {
            setShowDeleteModal(false);
            setExpenseToDelete(null);
          }}
          onDelete={async (deleteType) => {
            await deleteExpenseFinal(expenseToDelete.id, deleteType);
            setShowDeleteModal(false);
            setExpenseToDelete(null);
            loadExpenses(true);
            loadMonthlySummaries();
          }}
        />
      )}
    </main>
  );
}

interface DeleteConfirmModalProps {
  expense: Expense;
  currentMonth: string;
  currentYear: number;
  onClose: () => void;
  onDelete: (deleteType: "this_month" | "all") => Promise<void>;
}

function DeleteConfirmModal({ expense, currentMonth, currentYear, onClose, onDelete }: DeleteConfirmModalProps) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (deleteType: "this_month" | "all") => {
    setDeleting(true);
    try {
      await onDelete(deleteType);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content delete-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2><i className="fas fa-trash-alt"></i> Delete Expense</h2>
          <button onClick={onClose} className="modal-close" aria-label="Close dialog">
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="modal-body">
          <div className="delete-warning">
            <i className="fas fa-exclamation-triangle"></i>
            <p>You're about to delete <strong>"{expense.name}"</strong></p>
          </div>

          {expense.is_recurring ? (
            <>
              <p className="delete-description">
                This is a <strong>recurring expense</strong> that appears every month.
                Choose how you want to delete it:
              </p>

              <div className="delete-options">
                <button
                  onClick={() => handleDelete("this_month")}
                  disabled={deleting}
                  className="delete-option-btn this-month"
                >
                  <i className="fas fa-calendar-day"></i>
                  <span className="option-title">Delete {currentMonth} {currentYear} Only</span>
                  <span className="option-desc">Removes this expense only for this month</span>
                </button>

                <button
                  onClick={() => handleDelete("all")}
                  disabled={deleting}
                  className="delete-option-btn all-months"
                >
                  <i className="fas fa-calendar-times"></i>
                  <span className="option-title">Delete All Occurrences</span>
                  <span className="option-desc">Permanently removes this expense from all months</span>
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="delete-description">
                This is a <strong>one-time expense</strong> for {currentMonth} {currentYear}.
              </p>
              <div className="delete-options">
                <button
                  onClick={() => handleDelete("all")}
                  disabled={deleting}
                  className="delete-option-btn danger-single"
                >
                  <i className="fas fa-trash"></i>
                  <span className="option-title">Delete This Expense</span>
                  <span className="option-desc">This action cannot be undone</span>
                </button>
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn-secondary" disabled={deleting}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

interface AddExpenseModalProps {
  onClose: () => void;
  onSuccess: () => void;
  editingExpense: Expense | null;
  currentYear: number;
  currentMonth: number;
}

function AddExpenseModal({ onClose, onSuccess, editingExpense, currentYear, currentMonth }: AddExpenseModalProps) {
  const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];
  const [formData, setFormData] = useState({
    name: editingExpense?.name || "",
    amount: editingExpense?.amount ? String(editingExpense.amount) : "",
    day_of_month: editingExpense?.day_of_month ? String(editingExpense.day_of_month) : "1",
    category: editingExpense?.category || "Bills",
    description: editingExpense?.description || "",
    is_recurring: editingExpense?.is_recurring ?? true
  });
  const [saving, setSaving] = useState(false);
  const isEditing = !!editingExpense;

  const categories = ["Bills", "Insurance", "EMI", "Investments", "Payments", "Maintenance", "Other"];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const payload: any = {
        ...formData,
        amount: formData.amount ? parseFloat(formData.amount) : null,
        day_of_month: parseInt(formData.day_of_month),
        enabled: true,
        is_recurring: formData.is_recurring
      };

      // If one-time expense, add viewing year/month
      if (!formData.is_recurring) {
        payload.specific_year = currentYear;
        payload.specific_month = currentMonth;
      } else {
        payload.specific_year = null;
        payload.specific_month = null;
      }

      const url = isEditing ? `${API}/api/expenses/${editingExpense.id}` : `${API}/api/expenses`;
      const method = isEditing ? "PUT" : "POST";

      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error("Could not save the expense");
      onSuccess();
    } catch (error) {
      console.error("Failed to add expense:", error);
      alert("Failed to add expense");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" role="dialog" aria-modal="true" aria-label={isEditing ? "Edit expense" : "Add expense"} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{isEditing ? "Edit Expense" : "Add Monthly Expense"}</h2>
          <button onClick={onClose} className="modal-close" aria-label="Close dialog">
            <i className="fas fa-times"></i>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="expense-form">
          <div className="form-group">
            <label>Expense Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Electricity Bill"
              required
              autoFocus
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Amount (₹)</label>
              <input
                type="number"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                placeholder="Optional"
                step="0.01"
              />
            </div>

            <div className="form-group">
              <label>Due Date *</label>
              <select
                value={formData.day_of_month}
                onChange={(e) => setFormData({ ...formData, day_of_month: e.target.value })}
                required
              >
                {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
                  <option key={day} value={day}>{day}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Category</label>
            <select
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Expense Type</label>
            <div className="expense-type-toggle">
              <button
                type="button"
                className={`type-btn ${formData.is_recurring ? "active" : ""}`}
                onClick={() => setFormData({ ...formData, is_recurring: true })}
              >
                <i className="fas fa-sync-alt"></i>
                <span>Recurring</span>
                <small>Appears every month</small>
              </button>
              <button
                type="button"
                className={`type-btn ${!formData.is_recurring ? "active" : ""}`}
                onClick={() => setFormData({ ...formData, is_recurring: false })}
              >
                <i className="fas fa-calendar-day"></i>
                <span>One-Time</span>
                <small>Only for {monthNames[currentMonth - 1]} {currentYear}</small>
              </button>
            </div>
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Optional notes"
              rows={3}
            />
          </div>

          <div className="form-actions">
            <button type="button" onClick={onClose} className="btn-cancel">
              Cancel
            </button>
            <button type="submit" disabled={saving} className="btn-submit">
              {saving ? (isEditing ? "Updating..." : "Adding...") : (isEditing ? "Update Expense" : "Add Expense")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
