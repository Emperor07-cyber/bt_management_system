import { useEffect, useState } from "react";
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  X,
  Wallet,
  RefreshCw,
} from "lucide-react";
import api from "../services/api";
import "./Finance.css";

function Finance() {
  const [expenses, setExpenses] = useState([]);
  const [categories, setCategories] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [saving, setSaving] = useState(false);

  const [formData, setFormData] = useState({
    category: "",
    expense_number: "",
    expense_date: "",
    description: "",
    amount: "",
    status: "PENDING",
    notes: "",
  });

  const loadExpenses = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/finance/expenses/");

      const data = response.data;

      setExpenses(data.results ? data.results : data);
    } catch (err) {
      console.error("Failed to load expenses:", err);

      if (err.response?.status === 403) {
        setError(
          "You do not have permission to access Finance."
        );
      } else {
        setError("Failed to load expenses.");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await api.get(
        "/finance/expense-categories/"
      );

      const data = response.data;

      setCategories(data.results ? data.results : data);
    } catch (err) {
      console.error(
        "Failed to load expense categories:",
        err
      );
    }
  };

  useEffect(() => {
    loadExpenses();
    loadCategories();
  }, []);

  const filteredExpenses = expenses.filter((expense) => {
    const searchText = search.toLowerCase();

    return (
      expense.expense_number
        ?.toLowerCase()
        .includes(searchText) ||
      expense.description
        ?.toLowerCase()
        .includes(searchText) ||
      expense.status
        ?.toLowerCase()
        .includes(searchText)
    );
  });

  const openAddModal = () => {
    setEditingExpense(null);

    setFormData({
      category: "",
      expense_number: "",
      expense_date: "",
      description: "",
      amount: "",
      status: "PENDING",
      notes: "",
    });

    setShowModal(true);
  };

  const openEditModal = (expense) => {
    setEditingExpense(expense);

    setFormData({
      category:
        typeof expense.category === "object"
          ? expense.category?.id || ""
          : expense.category || "",

      expense_number: expense.expense_number || "",

      expense_date: expense.expense_date || "",

      description: expense.description || "",

      amount: expense.amount || "",

      status: expense.status || "PENDING",

      notes: expense.notes || "",
    });

    setShowModal(true);
  };

  const closeModal = () => {
    if (saving) return;

    setShowModal(false);
    setEditingExpense(null);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      setSaving(true);
      setError("");

      const payload = {
        ...formData,
        category: Number(formData.category),
        amount: Number(formData.amount),
      };

      if (editingExpense) {
        await api.patch(
          `/finance/expenses/${editingExpense.id}/`,
          payload
        );
      } else {
        await api.post(
          "/finance/expenses/",
          payload
        );
      }

      setShowModal(false);
      setEditingExpense(null);

      await loadExpenses();
    } catch (err) {
      console.error(
        "Failed to save expense:",
        err
      );

      setError(
        err.userMessage ||
        (err.response?.status === 403
          ? "Access denied. You do not have permission to save expenses."
          : "Failed to save expense.")
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (expense) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${expense.expense_number}"?`
    );

    if (!confirmed) return;

    try {
      setError("");

      await api.delete(
        `/finance/expenses/${expense.id}/`
      );

      await loadExpenses();
    } catch (err) {
      console.error(
        "Failed to delete expense:",
        err
      );

      setError(
        err.userMessage ||
        (err.response?.status === 403
          ? "Access denied. You do not have permission to delete expenses."
          : "Failed to delete expense.")
      );
    }
  };

  const getCategoryName = (category) => {
    if (!category) return "—";

    if (typeof category === "object") {
      return (
        category.name ||
        category.description ||
        "—"
      );
    }

    const found = categories.find(
      (item) =>
        String(item.id) === String(category)
    );

    return found ? found.name : String(category);
  };

  const getStatusClass = (status) => {
    const normalized = status?.toLowerCase();

    if (normalized === "pending") {
      return "finance-pending";
    }

    if (normalized === "approved") {
      return "finance-approved";
    }

    if (normalized === "paid") {
      return "finance-paid";
    }

    if (normalized === "cancelled") {
      return "finance-cancelled";
    }

    return "finance-default";
  };

  const formatAmount = (amount) => {
    return `₦${Number(amount || 0).toLocaleString(
      "en-NG",
      {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }
    )}`;
  };

  return (
    <div className="finance-page">
      <div className="page-heading finance-heading">
        <div>
          <p className="breadcrumb">
            Home / Finance
          </p>

          <h1>Finance</h1>

          <p className="subtitle">
            Manage expenses and financial records.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={openAddModal}
        >
          <Plus size={18} />
          New Expense
        </button>
      </div>

      {error && (
        <div className="finance-error">
          {error}
        </div>
      )}

      <div className="finance-toolbar">
        <div className="finance-search">
          <Search size={18} />

          <input
            type="text"
            placeholder="Search expenses..."
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
          />
        </div>

        <button
          className="refresh-button"
          onClick={loadExpenses}
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      <div className="finance-card">
        {loading ? (
          <div className="finance-empty">
            <RefreshCw
              size={32}
              className="loading-icon"
            />

            <p>Loading expenses...</p>
          </div>
        ) : filteredExpenses.length === 0 ? (
          <div className="finance-empty">
            <Wallet size={42} />

            <h3>
              No expenses found
            </h3>

            <p>
              {search
                ? "Try a different search."
                : "Create your first expense."}
            </p>
          </div>
        ) : (
          <div className="finance-table-wrapper">
            <table className="finance-table">
              <thead>
                <tr>
                  <th>Expense Number</th>
                  <th>Category</th>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Notes</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredExpenses.map(
                  (expense) => (
                    <tr key={expense.id}>
                      <td>
                        <div className="expense-name">
                          <div className="expense-icon">
                            <Wallet size={17} />
                          </div>

                          <strong>
                            {expense.expense_number}
                          </strong>
                        </div>
                      </td>

                      <td>
                        {getCategoryName(
                          expense.category
                        )}
                      </td>

                      <td>
                        {expense.expense_date || "—"}
                      </td>

                      <td>
                        {expense.description || "—"}
                      </td>

                      <td>
                        <strong>
                          {formatAmount(
                            expense.amount
                          )}
                        </strong>
                      </td>

                      <td>
                        <span
                          className={`finance-status ${getStatusClass(
                            expense.status
                          )}`}
                        >
                          {expense.status ||
                            "UNKNOWN"}
                        </span>
                      </td>

                      <td>
                        <span className="notes-cell">
                          {expense.notes || "—"}
                        </span>
                      </td>

                      <td>
                        <div className="action-buttons">
                          <button
                            className="icon-button edit-button"
                            onClick={() =>
                              openEditModal(
                                expense
                              )
                            }
                            title="Edit expense"
                          >
                            <Pencil size={17} />
                          </button>

                          <button
                            className="icon-button delete-button"
                            onClick={() =>
                              handleDelete(
                                expense
                              )
                            }
                            title="Delete expense"
                          >
                            <Trash2 size={17} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="finance-modal">
            <div className="modal-header">
              <div>
                <h2>
                  {editingExpense
                    ? "Edit Expense"
                    : "New Expense"}
                </h2>

                <p>
                  {editingExpense
                    ? "Update expense information."
                    : "Enter the expense details."}
                </p>
              </div>

              <button
                className="modal-close"
                onClick={closeModal}
                disabled={saving}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="form-grid">
                <div className="form-group">
                  <label>
                    Expense Number *
                  </label>

                  <input
                    name="expense_number"
                    value={
                      formData.expense_number
                    }
                    onChange={handleChange}
                    placeholder="e.g. EXP-2026-002"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>
                    Category *
                  </label>

                  <select
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    required
                  >
                    <option value="">
                      Select category
                    </option>

                    {categories.map(
                      (category) => (
                        <option
                          key={category.id}
                          value={category.id}
                        >
                          {category.name}
                        </option>
                      )
                    )}
                  </select>
                </div>

                <div className="form-group">
                  <label>
                    Expense Date *
                  </label>

                  <input
                    type="date"
                    name="expense_date"
                    value={
                      formData.expense_date
                    }
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>
                    Amount *
                  </label>

                  <input
                    type="number"
                    name="amount"
                    value={formData.amount}
                    onChange={handleChange}
                    placeholder="e.g. 150000"
                    min="0"
                    step="0.01"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>
                    Status *
                  </label>

                  <select
                    name="status"
                    value={formData.status}
                    onChange={handleChange}
                    required
                  >
                    <option value="PENDING">
                      Pending
                    </option>

                    <option value="APPROVED">
                      Approved
                    </option>

                    <option value="PAID">
                      Paid
                    </option>

                    <option value="CANCELLED">
                      Cancelled
                    </option>
                  </select>
                </div>

                <div className="form-group full-width">
                  <label>
                    Description *
                  </label>

                  <input
                    name="description"
                    value={
                      formData.description
                    }
                    onChange={handleChange}
                    placeholder="Describe the expense"
                    required
                  />
                </div>

                <div className="form-group full-width">
                  <label>
                    Notes
                  </label>

                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    placeholder="Additional notes"
                    rows="4"
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={closeModal}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={saving}
                >
                  {saving
                    ? "Saving..."
                    : editingExpense
                    ? "Update Expense"
                    : "Create Expense"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Finance;