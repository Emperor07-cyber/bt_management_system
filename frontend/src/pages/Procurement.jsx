import { useEffect, useState } from "react";
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  X,
  ShoppingCart,
  RefreshCw,
} from "lucide-react";
import api from "../services/api";
import "./Procurement.css";

function Procurement() {
  const [orders, setOrders] = useState([]);
  const [supplierList, setSupplierList] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [editingOrder, setEditingOrder] = useState(null);
  const [saving, setSaving] = useState(false);

  const [formData, setFormData] = useState({
    order_number: "",
    supplier: "",
    order_date: "",
    expected_delivery_date: "",
    status: "PENDING",
    notes: "",
  });

  // =========================
  // LOAD PURCHASE ORDERS
  // =========================

  const loadOrders = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get(
  "/company/suppliers/"
);

      const data = response.data;

      setOrders(data.results ? data.results : data);
    } catch (err) {
      console.error("Failed to load procurement:", err);

      setError(
        err.userMessage ||
          (err.response?.status === 403
            ? "Access denied. You do not have permission to access Procurement."
            : "Failed to load purchase orders.")
      );
    } finally {
      setLoading(false);
    }
  };

  // =========================
  // LOAD SUPPLIERS
  // =========================

  const loadSuppliers = async () => {
  try {
    const response = await api.get("/company/suppliers/");

    const data = response.data;

    setSupplierList(
      data.results ? data.results : data
    );
  } catch (err) {
    console.error("Failed to load suppliers:", err);
  }
};

  // =========================
  // INITIAL LOAD
  // =========================

  useEffect(() => {
    loadOrders();
    loadSuppliers();
  }, []);

  // =========================
  // SEARCH
  // =========================

  const filteredOrders = orders.filter((order) => {
    const searchText = search.toLowerCase();

    const supplierName =
      typeof order.supplier === "object"
        ? order.supplier?.name || ""
        : String(order.supplier || "");

    return (
      order.order_number
        ?.toLowerCase()
        .includes(searchText) ||
      supplierName
        .toLowerCase()
        .includes(searchText) ||
      order.status
        ?.toLowerCase()
        .includes(searchText)
    );
  });

  // =========================
  // ADD ORDER
  // =========================

  const openAddModal = () => {
    setEditingOrder(null);

    setFormData({
      order_number: "",
      supplier: "",
      order_date: "",
      expected_delivery_date: "",
      status: "PENDING",
      notes: "",
    });

    setShowModal(true);
  };

  // =========================
  // EDIT ORDER
  // =========================

  const openEditModal = (order) => {
    setEditingOrder(order);

    setFormData({
      order_number: order.order_number || "",

      supplier:
        typeof order.supplier === "object"
          ? order.supplier?.id || ""
          : order.supplier || "",

      order_date: order.order_date || "",

      expected_delivery_date:
        order.expected_delivery_date || "",

      status: order.status || "PENDING",

      notes: order.notes || "",
    });

    setShowModal(true);
  };

  // =========================
  // CLOSE MODAL
  // =========================

  const closeModal = () => {
    if (saving) return;

    setShowModal(false);
    setEditingOrder(null);
  };

  // =========================
  // FORM CHANGE
  // =========================

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]:
        name === "supplier"
          ? value
          : value,
    }));
  };

  // =========================
  // SUBMIT
  // =========================

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      setSaving(true);
      setError("");

      const payload = {
        ...formData,
        supplier: Number(formData.supplier),
      };

      if (editingOrder) {
        await api.patch(
          `/procurement/purchase-orders/${editingOrder.id}/`,
          payload
        );
      } else {
        await api.post(
          "/procurement/purchase-orders/",
          payload
        );
      }

      setShowModal(false);
      setEditingOrder(null);

      await loadOrders();
    } catch (err) {
      console.error(
        "Failed to save purchase order:",
        err
      );

      setError(
        err.userMessage ||
          (err.response?.status === 403
            ? "Access denied. You do not have permission to save purchase orders."
            : "Failed to save purchase order.")
      );
    } finally {
      setSaving(false);
    }
  };

  // =========================
  // DELETE
  // =========================

  const handleDelete = async (order) => {
  const confirmed = window.confirm(
    `Are you sure you want to delete "${order.order_number}"?`
  );

  if (!confirmed) return;

  try {
    setError("");

    await api.delete(
      `/procurement/purchase-orders/${order.id}/`
    );

    await loadOrders();
  } catch (err) {
    console.error(
      "Failed to delete purchase order:",
      err
    );

    console.log("Delete error response:", err.response);
    console.log(
      "Delete error data:",
      err.response?.data
    );

    if (err.userMessage) {
      setError(err.userMessage);
    } else if (err.response?.data?.detail) {
      setError(err.response.data.detail);
    } else if (err.response?.status === 403) {
      setError(
        "You do not have permission to delete purchase orders."
      );
    } else if (err.response?.status === 400) {
      setError(
        "This purchase order cannot be deleted because it has related goods receipts or supplier invoices."
      );
    } else {
      setError(
        "Failed to delete purchase order."
      );
    }
  }
};

  // =========================
  // STATUS CLASS
  // =========================

  const getStatusClass = (status) => {
    const normalized = status?.toLowerCase();

    if (normalized === "pending") {
      return "procurement-pending";
    }

    if (
      normalized === "approved" ||
      normalized === "completed"
    ) {
      return "procurement-approved";
    }

    if (
      normalized === "cancelled" ||
      normalized === "canceled"
    ) {
      return "procurement-cancelled";
    }

    if (
      normalized === "received" ||
      normalized === "delivered"
    ) {
      return "procurement-received";
    }

    return "procurement-default";
  };

  // =========================
  // SUPPLIER DISPLAY
  // =========================

  const getSupplierName = (supplier) => {
    if (!supplier) {
      return "—";
    }

    if (typeof supplier === "object") {
      return (
        supplier.name ||
        supplier.supplier_code ||
        "—"
      );
    }

    const foundSupplier = supplierList.find(
      (item) =>
        String(item.id) === String(supplier)
    );

    if (foundSupplier) {
      return foundSupplier.name;
    }

    return String(supplier);
  };

  return (
    <div className="procurement-page">

      {/* =========================
          HEADER
      ========================= */}

      <div className="page-heading procurement-heading">
        <div>
          <p className="breadcrumb">
            Home / Procurement
          </p>

          <h1>Procurement</h1>

          <p className="subtitle">
            Manage purchase orders and supplier procurement.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={openAddModal}
        >
          <Plus size={18} />
          New Purchase Order
        </button>
      </div>

      {/* =========================
          ERROR
      ========================= */}

      {error && (
        <div className="procurement-error">
          {error}
        </div>
      )}

      {/* =========================
          TOOLBAR
      ========================= */}

      <div className="procurement-toolbar">

        <div className="procurement-search">
          <Search size={18} />

          <input
            type="text"
            placeholder="Search purchase orders..."
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
          />
        </div>

        <button
          className="refresh-button"
          onClick={loadOrders}
        >
          <RefreshCw size={18} />
          Refresh
        </button>

      </div>

      {/* =========================
          PURCHASE ORDERS TABLE
      ========================= */}

      <div className="procurement-card">

        {loading ? (

          <div className="procurement-empty">

            <RefreshCw
              size={32}
              className="loading-icon"
            />

            <p>
              Loading purchase orders...
            </p>

          </div>

        ) : filteredOrders.length === 0 ? (

          <div className="procurement-empty">

            <ShoppingCart size={42} />

            <h3>
              No purchase orders found
            </h3>

            <p>
              {search
                ? "Try a different search."
                : "Create your first purchase order."}
            </p>

          </div>

        ) : (

          <div className="procurement-table-wrapper">

            <table className="procurement-table">

              <thead>
                <tr>
                  <th>Order Number</th>
                  <th>Supplier</th>
                  <th>Order Date</th>
                  <th>Expected Delivery</th>
                  <th>Status</th>
                  <th>Notes</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>

                {filteredOrders.map((order) => (

                  <tr key={order.id}>

                    <td>

                      <div className="order-name">

                        <div className="order-icon">
                          <ShoppingCart size={17} />
                        </div>

                        <strong>
                          {order.order_number}
                        </strong>

                      </div>

                    </td>

                    <td>
                      {getSupplierName(
                        order.supplier
                      )}
                    </td>

                    <td>
                      {order.order_date || "—"}
                    </td>

                    <td>
                      {order.expected_delivery_date ||
                        "—"}
                    </td>

                    <td>

                      <span
                        className={`procurement-status ${getStatusClass(
                          order.status
                        )}`}
                      >
                        {order.status || "UNKNOWN"}
                      </span>

                    </td>

                    <td>

                      <span className="notes-cell">
                        {order.notes || "—"}
                      </span>

                    </td>

                    <td>

                      <div className="action-buttons">

                        <button
                          className="icon-button edit-button"
                          onClick={() =>
                            openEditModal(order)
                          }
                          title="Edit order"
                        >
                          <Pencil size={17} />
                        </button>

                        <button
                          className="icon-button delete-button"
                          onClick={() =>
                            handleDelete(order)
                          }
                          title="Delete order"
                        >
                          <Trash2 size={17} />
                        </button>

                      </div>

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        )}

      </div>

      {/* =========================
          MODAL
      ========================= */}

      {showModal && (

        <div className="modal-overlay">

          <div className="procurement-modal">

            <div className="modal-header">

              <div>

                <h2>
                  {editingOrder
                    ? "Edit Purchase Order"
                    : "New Purchase Order"}
                </h2>

                <p>
                  {editingOrder
                    ? "Update purchase order information."
                    : "Enter the purchase order details."}
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

                {/* ORDER NUMBER */}

                <div className="form-group">

                  <label>
                    Order Number *
                  </label>

                  <input
                    name="order_number"
                    value={formData.order_number}
                    onChange={handleChange}
                    placeholder="e.g. PO-001"
                    required
                  />

                </div>

                {/* SUPPLIER */}

                <div className="form-group">

                  <label>
                    Supplier *
                  </label>

                  <select
                    name="supplier"
                    value={formData.supplier}
                    onChange={handleChange}
                    required
                  >

                    <option value="">
                      Select supplier
                    </option>

                    {supplierList.map(
                      (supplier) => (

                        <option
                          key={supplier.id}
                          value={supplier.id}
                        >
                          {supplier.supplier_code} -{" "}
                          {supplier.name}
                        </option>

                      )
                    )}

                  </select>

                </div>

                {/* ORDER DATE */}

                <div className="form-group">

                  <label>
                    Order Date *
                  </label>

                  <input
                    type="date"
                    name="order_date"
                    value={formData.order_date}
                    onChange={handleChange}
                    required
                  />

                </div>

                {/* EXPECTED DELIVERY */}

                <div className="form-group">

                  <label>
                    Expected Delivery
                  </label>

                  <input
                    type="date"
                    name="expected_delivery_date"
                    value={
                      formData.expected_delivery_date
                    }
                    onChange={handleChange}
                  />

                </div>

                {/* STATUS */}

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

                    <option value="RECEIVED">
                      Received
                    </option>

                    <option value="COMPLETED">
                      Completed
                    </option>

                    <option value="CANCELLED">
                      Cancelled
                    </option>

                  </select>

                </div>

                {/* NOTES */}

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

              {/* MODAL ACTIONS */}

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
                    : editingOrder
                    ? "Update Order"
                    : "Create Order"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  );
}

export default Procurement;