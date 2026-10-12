import { useEffect, useState } from "react";
import {
  BarChart3,
  Package,
  Car,
  ShoppingCart,
  Wallet,
  RefreshCw,
  Search,
} from "lucide-react";

import api from "../services/api";
import { canAccessModule } from "../utils/access";
import "./Reports.css";

function Reports({ userRoles = [] }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const loadReport = async () => {
    try {
      setLoading(true);
      setError("");

      const params = {};

      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const response = await api.get("/reports/dashboard/", {
        params,
      });

      setReport(response.data);
    } catch (err) {
      console.error("Failed to load report:", err);

      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to load reports.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, []);

  const handleFilter = (e) => {
    e.preventDefault();
    loadReport();
  };

  const clearFilters = () => {
    setStartDate("");
    setEndDate("");

    setTimeout(() => {
      loadReport();
    }, 0);
  };

  const formatCurrency = (value) => {
    return Number(value || 0).toLocaleString("en-NG", {
      style: "currency",
      currency: "NGN",
      minimumFractionDigits: 2,
    });
  };

  const canViewProcurement = canAccessModule(userRoles, "procurement");
  const canViewFinance = canAccessModule(userRoles, "finance");

  if (loading) {
    return (
      <div className="reports-page">
        <div className="reports-loading">
          <RefreshCw size={24} className="loading-icon" />
          <p>Loading reports...</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="reports-page">
        <div className="reports-error">
          {error || "No report data available."}
        </div>
      </div>
    );
  }

  return (
    <div className="reports-page">
      <div className="reports-header">
        <div>
          <h1>Reports</h1>
          <p>Overview of your business operations</p>
        </div>

        <button className="refresh-btn" onClick={loadReport}>
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <form className="report-filters" onSubmit={handleFilter}>
        <div className="filter-group">
          <label>Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>

        <button type="submit" className="filter-btn">
          <Search size={17} />
          Apply Filter
        </button>

        <button
          type="button"
          className="clear-filter-btn"
          onClick={clearFilters}
        >
          Clear
        </button>
      </form>

      {error && <div className="reports-error">{error}</div>}

      {/* Summary Cards */}
      <div className="summary-grid">
        <div className="summary-card">
          <div className="summary-icon">
            <Package size={24} />
          </div>
          <div>
            <span>Total Inventory</span>
            <strong>{report.inventory.total_items}</strong>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">
            <Car size={24} />
          </div>
          <div>
            <span>Total Vehicles</span>
            <strong>{report.fleet.total_vehicles}</strong>
          </div>
        </div>

        {canViewProcurement && (
          <div className="summary-card">
            <div className="summary-icon">
              <ShoppingCart size={24} />
            </div>
            <div>
              <span>Purchase Orders</span>
              <strong>{report.procurement.total_purchase_orders}</strong>
            </div>
          </div>
        )}

        {canViewFinance && (
          <div className="summary-card">
            <div className="summary-icon">
              <Wallet size={24} />
            </div>
            <div>
              <span>Total Expenses</span>
              <strong>{formatCurrency(report.finance.total_expenses)}</strong>
            </div>
          </div>
        )}
      </div>

      {/* Report Sections */}
      <div className="reports-grid">
        {/* Inventory */}
        <div className="report-card">
          <div className="report-card-header">
            <div>
              <h2>Inventory</h2>
              <p>Current stock overview</p>
            </div>

            <Package size={25} />
          </div>

          <div className="report-stat">
            <span>Total Items</span>
            <strong>{report.inventory.total_items}</strong>
          </div>

          <div className="report-stat warning">
            <span>Low Stock</span>
            <strong>{report.inventory.low_stock_items}</strong>
          </div>

          <div className="report-stat danger">
            <span>Out of Stock</span>
            <strong>{report.inventory.out_of_stock_items}</strong>
          </div>
        </div>

        {/* Fleet */}
        <div className="report-card">
          <div className="report-card-header">
            <div>
              <h2>Fleet</h2>
              <p>Vehicle availability</p>
            </div>

            <Car size={25} />
          </div>

          <div className="report-stat">
            <span>Total Vehicles</span>
            <strong>{report.fleet.total_vehicles}</strong>
          </div>

          <div className="report-stat success">
            <span>Available</span>
            <strong>{report.fleet.available_vehicles}</strong>
          </div>

          <div className="report-stat warning">
            <span>Assigned</span>
            <strong>{report.fleet.assigned_vehicles}</strong>
          </div>
        </div>

        {/* Procurement */}
        {canViewProcurement && (
          <div className="report-card">
            <div className="report-card-header">
              <div>
                <h2>Procurement</h2>
                <p>Purchasing overview</p>
              </div>

              <ShoppingCart size={25} />
            </div>

            <div className="report-stat">
              <span>Purchase Orders</span>
              <strong>{report.procurement.total_purchase_orders}</strong>
            </div>

            <div className="report-stat">
              <span>Supplier Invoices</span>
              <strong>{report.procurement.total_supplier_invoices}</strong>
            </div>
          </div>
        )}

        {/* Finance */}
        {canViewFinance && (
          <div className="report-card finance-report-card">
            <div className="report-card-header">
              <div>
                <h2>Finance</h2>
                <p>Expense overview</p>
              </div>

              <Wallet size={25} />
            </div>

            <div className="report-stat">
              <span>Total Expenses</span>
              <strong>
                {formatCurrency(report.finance.total_expenses)}
              </strong>
            </div>

            <div className="report-stat success">
              <span>Paid Expenses</span>
              <strong>
                {formatCurrency(report.finance.paid_expenses)}
              </strong>
            </div>

            <div className="report-stat warning">
              <span>Pending Expenses</span>
              <strong>
                {formatCurrency(report.finance.pending_expenses)}
              </strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Reports;