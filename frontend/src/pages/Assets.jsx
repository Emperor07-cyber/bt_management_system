import { useEffect, useMemo, useState } from "react";
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  X,
  Package,
  RefreshCw,
  Upload,
  Download,
  History,
  UserCheck,
  RotateCcw,
  Tags,
} from "lucide-react";
import api from "../services/api";
import "./Assets.css";

const emptyForm = {
  name: "",
  description: "",
  category: "",
  manufacturer: "",
  model_number: "",
  serial_number: "",
  purchase_date: "",
  purchase_cost: "",
  warranty_start: "",
  warranty_end: "",
  condition: "NEW",
  status: "AVAILABLE",
  supplier: "",
  location: "",
  notes: "",
};

const toList = (response) => {
  const data = response?.data;
  return Array.isArray(data) ? data : data?.results || [];
};

const employeeName = (employee) => {
  if (!employee) return "";
  if (typeof employee === "string") return employee;
  const fullName = [employee.first_name, employee.last_name]
    .filter(Boolean)
    .join(" ")
    .trim();

  return (
    fullName ||
    employee.name ||
    employee.full_name ||
    employee.employee_number ||
    ""
  );
};

const locationName = (location) => {
  if (!location) return "";
  if (typeof location === "string") return location;
  return location.name || location.location_name || location.location_code || "";
};

const supplierName = (supplier) => {
  if (!supplier) return "";
  if (typeof supplier === "string") return supplier;
  return supplier.name || supplier.company_name || supplier.supplier_name || "";
};

function Assets() {
  const [assets, setAssets] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [locations, setLocations] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [categories, setCategories] = useState([]);

  const [loading, setLoading] = useState(true);
  const [lookupsLoading, setLookupsLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [editingAsset, setEditingAsset] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [categorySaving, setCategorySaving] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newCategoryDescription, setNewCategoryDescription] = useState("");

  const [showImport, setShowImport] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  const [assignments, setAssignments] = useState([]);
  const [showAssignments, setShowAssignments] = useState(false);
  const [showAssignmentModal, setShowAssignmentModal] = useState(false);
  const [assignmentSaving, setAssignmentSaving] = useState(false);
  const [assignmentForm, setAssignmentForm] = useState({
    asset: "",
    employee: "",
    assignment_date: new Date().toISOString().slice(0, 10),
    expected_return_date: "",
    notes: "",
  });

  const [formData, setFormData] = useState(emptyForm);

  const roles = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("roles") || "[]");
    } catch {
      return [];
    }
  }, []);

  const canCreate = roles.some((role) =>
    ["Admin", "Manager", "Asset Staff"].includes(role)
  );
  const canDelete = roles.includes("Admin");

  const loadAssets = async () => {
    try {
      setLoading(true);
      setError("");

      const params = {};
      if (locationFilter) params.location = locationFilter;
      if (statusFilter) params.status = statusFilter;
      if (categoryFilter) params.category = categoryFilter;

      const response = await api.get("/assets/", { params });
      setAssets(toList(response));
    } catch (err) {
      console.error("Failed to load assets:", err);
      setError(
        err.userMessage ||
          (err.response?.status === 403
            ? "You do not have permission to view assets."
            : "Failed to load assets.")
      );
    } finally {
      setLoading(false);
    }
  };

  const loadAssignments = async () => {
    try {
      const response = await api.get("/assets/assignments/");
      setAssignments(toList(response));
    } catch (err) {
      console.error("Failed to load asset assignments:", err);
    }
  };

  const loadLookups = async () => {
    try {
      setLookupsLoading(true);

      const results = await Promise.allSettled([
        api.get("/company/employees/"),
        api.get("/company/locations/"),
        api.get("/company/suppliers/"),
        api.get("/assets/categories/"),
      ]);

      const [employeeResult, locationResult, supplierResult, categoryResult] = results;

      if (employeeResult.status === "fulfilled") {
        setEmployees(toList(employeeResult.value));
      }

      if (locationResult.status === "fulfilled") {
        setLocations(toList(locationResult.value));
      }

      if (supplierResult.status === "fulfilled") {
        setSuppliers(toList(supplierResult.value));
      }

      if (categoryResult.status === "fulfilled") {
        setCategories(toList(categoryResult.value));
      }

      const failed = results.some((result) => result.status === "rejected");
      if (failed) {
        console.warn("One or more Asset lookup lists could not be loaded.");
      }
    } finally {
      setLookupsLoading(false);
    }
  };

  useEffect(() => {
    loadAssets();
  }, [locationFilter, statusFilter, categoryFilter]);

  useEffect(() => {
    loadLookups();
    loadAssignments();
  }, []);

  const openAddModal = () => {
    setEditingAsset(null);
    setFormData({ ...emptyForm });
    setError("");
    setShowModal(true);
  };

  const openEditModal = (asset) => {
    setEditingAsset(asset);
    setFormData({
      name: asset.name || "",
      description: asset.description || "",
      category: asset.category || "",
      manufacturer: asset.manufacturer || "",
      model_number: asset.model_number || "",
      serial_number: asset.serial_number || "",
      purchase_date: asset.purchase_date || "",
      purchase_cost: asset.purchase_cost ?? "",
      warranty_start: asset.warranty_start || "",
      warranty_end: asset.warranty_end || "",
      condition: asset.condition || "NEW",
      status: asset.status || "AVAILABLE",
      supplier:
        typeof asset.supplier === "object"
          ? asset.supplier?.id || ""
          : asset.supplier || "",
      location:
        typeof asset.location === "object"
          ? asset.location?.id || ""
          : asset.location || "",
      notes: asset.notes || "",
    });
    setError("");
    setShowModal(true);
  };

  const closeModal = () => {
    if (saving) return;
    setShowModal(false);
    setEditingAsset(null);
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
        purchase_cost: formData.purchase_cost
          ? Number(formData.purchase_cost)
          : null,
        supplier: formData.supplier ? Number(formData.supplier) : null,
        location: formData.location ? Number(formData.location) : null,
      };


      if (editingAsset) {
        await api.patch(`/assets/${editingAsset.id}/`, payload);
      } else {
        await api.post("/assets/", payload);
      }

      closeModal();
      await loadAssets();
    } catch (err) {
      console.error("Failed to save asset:", err);
      setError(
        err.userMessage ||
          (err.response?.data
            ? JSON.stringify(err.response.data)
            : "Failed to save asset.")
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (asset) => {
    if (!canDelete) {
      setError("You do not have permission to delete assets.");
      return;
    }

    const confirmed = window.confirm(
      `Are you sure you want to delete "${asset.name}"?`
    );

    if (!confirmed) return;

    try {
      setError("");
      await api.delete(`/assets/${asset.id}/`);
      await loadAssets();
    } catch (err) {
      console.error("Failed to delete asset:", err);
      setError(
        err.userMessage ||
          (err.response?.status === 403
            ? "Access denied. You do not have permission to delete assets."
            : "Failed to delete asset.")
      );
    }
  };

  const handleImport = async (event) => {
    event.preventDefault();

    if (!importFile) {
      setError("Please select an Excel file.");
      return;
    }

    try {
      setImporting(true);
      setError("");
      setImportResult(null);

      const data = new FormData();
      data.append("file", importFile);

      const response = await api.post("/assets/import/", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setImportResult(response.data);

      if (response.data.status === "VALIDATED") {
        await loadAssets();
      }
    } catch (err) {
      console.error("Asset import failed:", err);
      setError(
        err.userMessage ||
          err.response?.data?.detail ||
          "Asset import failed."
      );
    } finally {
      setImporting(false);
    }
  };

  const confirmImport = async () => {
    if (!importResult?.batch_id) return;

    try {
      setImporting(true);
      setError("");

      const response = await api.post(
        `/assets/import/${importResult.batch_id}/confirm/`
      );

      setImportResult((previous) => ({
        ...previous,
        ...response.data,
        status: response.data.status || "COMPLETED",
      }));

      await loadAssets();
    } catch (err) {
      console.error("Asset import confirmation failed:", err);
      setError(
        err.userMessage ||
          err.response?.data?.detail ||
          "Asset import confirmation failed."
      );
    } finally {
      setImporting(false);
    }
  };

  const downloadTemplate = async () => {
    try {
      const response = await api.get("/assets/import-template/", {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = "asset_import_template.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download asset template:", err);
      setError("Failed to download the Asset Excel template.");
    }
  };

  const categoryOptions = [...new Set(
    assets.map((asset) => asset.category).filter(Boolean)
  )].sort((a, b) => String(a).localeCompare(String(b)));

  const filteredAssets = assets.filter((asset) => {
    const text = [
      asset.asset_code,
      asset.name,
      asset.category,
      asset.location_name,
      asset.supplier_name,
      locationName(asset.location),
      supplierName(asset.supplier),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return text.includes(search.toLowerCase());
  });

  const displayLocation = (asset) =>
    asset.location_name ||
    locationName(asset.location) ||
    "No location";

  const displaySupplier = (asset) =>
    asset.supplier_name ||
    supplierName(asset.supplier) ||
    "No supplier";

  const statusLabel = {
    AVAILABLE: "Available",
    ASSIGNED: "Assigned",
    MAINTENANCE: "Maintenance",
    RETIRED: "Retired",
  };


  return (
    <div className="assets-page">
      <div className="assets-heading">
        <div>
          <p className="breadcrumb">Home / Assets</p>
          <h1>Assets</h1>
          <p className="assets-subtitle">
            Manage and track your organization's assets.
          </p>
        </div>

        <div className="assets-heading-actions">
          {canCreate && (
            <button
              className="assets-secondary-button"
              onClick={() => {
                setImportResult(null);
                setImportFile(null);
                setShowImport(true);
              }}
            >
              <Upload size={17} />
              Import Excel
            </button>
          )}

          {canCreate && (
            <button className="assets-secondary-button" onClick={() => { setShowAssignments(true); loadAssignments(); }}>
              <UserCheck size={17} />
              Assignments
            </button>
          )}

          {canCreate && (
            <button
              className="assets-secondary-button"
              onClick={() => { setNewCategoryName(""); setNewCategoryDescription(""); setShowCategoryModal(true); }}
              title="Manage asset categories"
            >
              <Tags size={17} />
              Categories
            </button>
          )}

          {canCreate && (
            <button className="assets-primary-button" onClick={openAddModal}>
              <Plus size={18} />
              Add Asset
            </button>
          )}
        </div>
      </div>

      {error && <div className="assets-error">{error}</div>}

      <div className="assets-toolbar">
        <div className="assets-search">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search by asset, location or supplier..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="assets-filter-group">
          <select
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
            disabled={lookupsLoading}
            aria-label="Filter by location"
          >
            <option value="">All locations / stores</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {locationName(location)}
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            {Object.entries(statusLabel).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            aria-label="Filter by category"
          >
            <option value="">All categories</option>
            {categoryOptions.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>

          {(locationFilter || statusFilter || categoryFilter || search) && (
            <button
              type="button"
              className="assets-clear-filter"
              onClick={() => {
                setLocationFilter("");
                setStatusFilter("");
                setCategoryFilter("");
                setSearch("");
              }}
            >
              <X size={16} />
              Clear
            </button>
          )}
        </div>

        <button
          className="refresh-button"
          onClick={() => {
            loadAssets();
            loadLookups();
            loadAssignments();
          }}
          title="Refresh"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      <div className="assets-card">
        <div className="assets-card-header">
          <div>
            <h2>All Assets</h2>
            <p>
              {filteredAssets.length}{" "}
              {filteredAssets.length === 1 ? "asset" : "assets"}
            </p>
          </div>
        </div>

        {loading ? (
          <div className="assets-empty">
            <RefreshCw size={30} className="loading-icon" />
            <h3>Loading assets...</h3>
          </div>
        ) : filteredAssets.length === 0 ? (
          <div className="assets-empty">
            <Package size={38} />
            <h3>No assets found</h3>
            <p>
              {search || locationFilter || statusFilter || categoryFilter
                ? "Try changing your search or filters."
                : "Add your first asset to get started."}
            </p>
          </div>
        ) : (
          <div className="assets-table-wrapper">
            <table className="assets-table">
              <thead>
                <tr>
                  <th>Asset Code</th>
                  <th>Name</th>
                  <th>Category</th>
                                    <th>Location</th>
                  <th>Supplier</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredAssets.map((asset) => (
                  <tr key={asset.id}>
                    <td>
                      <strong>{asset.asset_code || "—"}</strong>
                    </td>
                    <td>{asset.name || "—"}</td>
                    <td>{asset.category || "—"}</td>
                    <td>{displayLocation(asset)}</td>
                    <td>{displaySupplier(asset)}</td>
                    <td>
                      <span
                        className={`status-badge status-${String(
                          asset.status || "default"
                        ).toLowerCase()}`}
                      >
                        {statusLabel[asset.status] || asset.status || "—"}
                      </span>
                    </td>
                    <td>
                      <div className="asset-actions">
                        {canCreate && (
                          <button
                            className="assign-button"
                            onClick={() => {
                              setAssignmentForm({
                                asset: String(asset.id),
                                employee: "",
                                assignment_date: new Date().toISOString().slice(0, 10),
                                expected_return_date: "",
                                notes: "",
                              });
                              setShowAssignmentModal(true);
                            }}
                            title="Assign asset"
                          >
                            <UserCheck size={16} />
                          </button>
                        )}

                        {canCreate && (
                          <button
                            className="edit-button"
                            onClick={() => openEditModal(asset)}
                            title="Edit"
                          >
                            <Pencil size={16} />
                          </button>
                        )}

                        {canDelete && (
                          <button
                            className="delete-button"
                            onClick={() => handleDelete(asset)}
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="asset-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>{editingAsset ? "Edit Asset" : "Add Asset"}</h2>
                <p>
                  {editingAsset
                    ? "Update the asset information."
                    : "Enter the details for the new asset."}
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
                <div className="asset-form-group">
                  <label>Category *</label>
                  <select
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    required
                    disabled={lookupsLoading || categories.length === 0}
                  >
                    <option value="">
                      {lookupsLoading
                        ? "Loading categories..."
                        : categories.length
                        ? "Select category"
                        : "Add a category first"}
                    </option>
                    {categories.map((category) => (
                      <option key={category.id} value={category.name}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                  {categories.length === 0 && (
                    <small className="asset-form-hint">Use Categories above to add your asset categories.</small>
                  )}
                </div>

                <div className="asset-form-group">
                  <label>Name *</label>
                  <input
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="Asset name"
                    required
                  />
                </div>

                <div className="asset-form-group">
                  <label>Location</label>
                  <select
                    name="location"
                    value={formData.location}
                    onChange={handleChange}
                    disabled={lookupsLoading}
                  >
                    <option value="">
                      {lookupsLoading
                        ? "Loading locations..."
                        : "Select location"}
                    </option>
                    {locations.map((location) => (
                      <option key={location.id} value={location.id}>
                        {locationName(location)}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="asset-form-group">
                  <label>Status</label>
                  <select
                    name="status"
                    value={formData.status}
                    onChange={handleChange}
                  >
                    {Object.entries(statusLabel).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="asset-form-group">
                  <label>Asset Code</label>
                  <input
                    value={editingAsset ? (editingAsset.asset_code || "") : "Generated automatically"}
                    readOnly
                    disabled
                    placeholder="Generated automatically"
                  />
                  {!editingAsset && <small className="asset-code-help">System-generated as BT-000001, BT-000002, etc.</small>}
                </div>

                <div className="asset-form-group">
                  <label>Manufacturer</label>
                  <input
                    name="manufacturer"
                    value={formData.manufacturer}
                    onChange={handleChange}
                    placeholder="Manufacturer"
                  />
                </div>

                <div className="asset-form-group">
                  <label>Model Number</label>
                  <input
                    name="model_number"
                    value={formData.model_number}
                    onChange={handleChange}
                    placeholder="Model number"
                  />
                </div>

                <div className="asset-form-group">
                  <label>Serial Number</label>
                  <input
                    name="serial_number"
                    value={formData.serial_number}
                    onChange={handleChange}
                    placeholder="Serial number"
                  />
                </div>

                <div className="asset-form-group">
                  <label>Supplier</label>
                  <select
                    name="supplier"
                    value={formData.supplier}
                    onChange={handleChange}
                    disabled={lookupsLoading}
                  >
                    <option value="">
                      {lookupsLoading
                        ? "Loading suppliers..."
                        : "Select supplier"}
                    </option>
                    {suppliers.map((supplier) => (
                      <option key={supplier.id} value={supplier.id}>
                        {supplierName(supplier)}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="asset-form-group">
                  <label>Purchase Date</label>
                  <input
                    type="date"
                    name="purchase_date"
                    value={formData.purchase_date}
                    onChange={handleChange}
                  />
                </div>

                <div className="asset-form-group">
                  <label>Purchase Cost</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    name="purchase_cost"
                    value={formData.purchase_cost}
                    onChange={handleChange}
                    placeholder="0.00"
                  />
                </div>

                <div className="asset-form-group full-width">
                  <label>Description</label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    placeholder="Asset description"
                    rows="3"
                  />
                </div>

                <div className="asset-form-group full-width">
                  <label>Notes</label>
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    placeholder="Additional notes"
                    rows="3"
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="cancel-button"
                  onClick={closeModal}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="save-button"
                  disabled={saving}
                >
                  {saving
                    ? "Saving..."
                    : editingAsset
                      ? "Save Changes"
                      : "Create Asset"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showAssignments && (
        <div className="modal-overlay" onClick={() => setShowAssignments(false)}>
          <div className="asset-modal assignment-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Asset Assignments</h2>
                <p>Manage current assignments and review assignment history.</p>
              </div>
              <button className="modal-close" onClick={() => setShowAssignments(false)}><X size={20} /></button>
            </div>
            <div className="assignment-list">
              {assignments.length === 0 ? (
                <div className="assets-empty compact-empty">
                  <UserCheck size={32} />
                  <h3>No assignments yet</h3>
                  <p>Assign an asset from the asset list to create the first assignment.</p>
                </div>
              ) : (
                <div className="assets-table-wrapper">
                  <table className="assets-table assignment-table">
                    <thead><tr><th>Asset</th><th>Employee</th><th>Assigned</th><th>Expected Return</th><th>Status</th><th>Action</th></tr></thead>
                    <tbody>
                      {assignments.map((assignment) => (
                        <tr key={assignment.id}>
                          <td><strong>{assignment.asset_code || `Asset #${assignment.asset}`}</strong><br /><span className="assignment-secondary">{assignment.asset_name || ""}</span></td>
                          <td>{assignment.employee_name || `Employee #${assignment.employee}`}</td>
                          <td>{assignment.assignment_date || "—"}</td>
                          <td>{assignment.expected_return_date || "—"}</td>
                          <td><span className={`status-badge ${assignment.status === "ACTIVE" ? "status-assigned" : "status-default"}`}>{assignment.status || "—"}</span></td>
                          <td>
                            {assignment.status === "ACTIVE" && (
                              <button className="return-button" onClick={async () => {
                                if (!window.confirm("Return this asset from the employee?")) return;
                                try {
                                  await api.post(`/assets/assignments/${assignment.id}/return/`);
                                  await Promise.all([loadAssignments(), loadAssets()]);
                                } catch (err) {
                                  setError(err.userMessage || err.response?.data?.detail || "Failed to return asset.");
                                }
                              }} title="Return asset"><RotateCcw size={15} /> Return</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {showAssignmentModal && (
        <div className="modal-overlay" onClick={() => !assignmentSaving && setShowAssignmentModal(false)}>
          <div className="asset-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div><h2>Assign Asset</h2><p>Assign an available asset to an active employee.</p></div>
              <button className="modal-close" onClick={() => !assignmentSaving && setShowAssignmentModal(false)} disabled={assignmentSaving}><X size={20} /></button>
            </div>
            <form onSubmit={async (event) => {
              event.preventDefault();
              try {
                setAssignmentSaving(true); setError("");
                await api.post("/assets/assignments/", {
                  asset: Number(assignmentForm.asset),
                  employee: Number(assignmentForm.employee),
                  assignment_date: assignmentForm.assignment_date,
                  expected_return_date: assignmentForm.expected_return_date || null,
                  notes: assignmentForm.notes,
                });
                setShowAssignmentModal(false);
                await Promise.all([loadAssignments(), loadAssets()]);
              } catch (err) {
                setError(err.userMessage || (err.response?.data ? JSON.stringify(err.response.data) : "Failed to assign asset."));
              } finally { setAssignmentSaving(false); }
            }}>
              <div className="form-grid">
                <div className="asset-form-group"><label>Asset *</label><select required value={assignmentForm.asset} onChange={(e) => setAssignmentForm(p => ({...p, asset:e.target.value}))}><option value="">Select asset</option>{assets.filter(a => a.status === "AVAILABLE").map(a => <option key={a.id} value={a.id}>{a.asset_code} — {a.name}</option>)}</select></div>
                <div className="asset-form-group"><label>Employee *</label><select required value={assignmentForm.employee} onChange={(e) => setAssignmentForm(p => ({...p, employee:e.target.value}))}><option value="">Select employee</option>{employees.filter(e => String(e.status || "").toUpperCase() === "ACTIVE").map(e => <option key={e.id} value={e.id}>{employeeName(e)}</option>)}</select></div>
                <div className="asset-form-group"><label>Assignment Date *</label><input type="date" required value={assignmentForm.assignment_date} onChange={(e) => setAssignmentForm(p => ({...p, assignment_date:e.target.value}))} /></div>
                <div className="asset-form-group"><label>Expected Return Date</label><input type="date" value={assignmentForm.expected_return_date} onChange={(e) => setAssignmentForm(p => ({...p, expected_return_date:e.target.value}))} /></div>
                <div className="asset-form-group full-width"><label>Notes</label><textarea rows="3" value={assignmentForm.notes} onChange={(e) => setAssignmentForm(p => ({...p, notes:e.target.value}))} placeholder="Assignment notes" /></div>
              </div>
              <div className="modal-actions"><button type="button" className="cancel-button" onClick={() => setShowAssignmentModal(false)} disabled={assignmentSaving}>Cancel</button><button type="submit" className="save-button" disabled={assignmentSaving}>{assignmentSaving ? "Assigning..." : "Assign Asset"}</button></div>
            </form>
          </div>
        </div>
      )}

      {showCategoryModal && (
        <div className="modal-overlay" onClick={() => !categorySaving && setShowCategoryModal(false)}>
          <div className="asset-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Asset Categories</h2>
                <p>Create and maintain the categories available when registering assets.</p>
              </div>
              <button className="modal-close" onClick={() => !categorySaving && setShowCategoryModal(false)} disabled={categorySaving}>
                <X size={20} />
              </button>
            </div>

            <div className="category-manager">
              <div className="category-list">
                {categories.length === 0 ? (
                  <div className="assets-empty">No categories have been created yet.</div>
                ) : (
                  categories.map((category) => (
                    <div className="category-row" key={category.id}>
                      <div>
                        <strong>{category.name}</strong>
                        {category.description && <span>{category.description}</span>}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <form onSubmit={async (e) => {
                e.preventDefault();
                if (!newCategoryName.trim()) return;
                try {
                  setCategorySaving(true);
                  setError("");
                  await api.post("/assets/categories/", {
                    name: newCategoryName.trim(),
                    description: newCategoryDescription.trim(),
                  });
                  setNewCategoryName("");
                  setNewCategoryDescription("");
                  const response = await api.get("/assets/categories/");
                  setCategories(toList(response));
                } catch (err) {
                  setError(err.userMessage || (err.response?.data ? JSON.stringify(err.response.data) : "Failed to create category."));
                } finally {
                  setCategorySaving(false);
                }
              }}>
                <div className="asset-form-group">
                  <label>New Category *</label>
                  <input value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} placeholder="e.g. IT Equipment" required />
                </div>
                <div className="asset-form-group">
                  <label>Description</label>
                  <textarea value={newCategoryDescription} onChange={(e) => setNewCategoryDescription(e.target.value)} placeholder="Optional description" rows={3} />
                </div>
                <div className="modal-actions">
                  <button type="submit" className="save-button" disabled={categorySaving}>
                    {categorySaving ? "Adding..." : "Add Category"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {showImport && (
        <div
          className="modal-overlay"
          onClick={() => !importing && setShowImport(false)}
        >
          <div className="asset-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Import Assets</h2>
                <p>
                  Use employee, location and supplier names in the spreadsheet.
                  Database IDs are not required.
                </p>
              </div>

              <button
                className="modal-close"
                onClick={() => !importing && setShowImport(false)}
                disabled={importing}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleImport}>
              <div className="asset-form-group">
                <label>Excel File</label>
                <input
                  type="file"
                  accept=".xlsx,.xlsm"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  disabled={importing}
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="assets-secondary-button"
                  onClick={downloadTemplate}
                  disabled={importing}
                >
                  <Download size={16} />
                  Download Template
                </button>

                <button
                  type="button"
                  className="cancel-button"
                  onClick={() => setShowImport(false)}
                  disabled={importing}
                >
                  Close
                </button>

                <button
                  type="submit"
                  className="save-button"
                  disabled={importing || !importFile}
                >
                  {importing ? "Validating..." : "Upload & Validate"}
                </button>
              </div>
            </form>

            {importResult && (
              <div className="import-result">
                <strong>Import validation</strong>
                <p>File: {importResult.file_name || "—"}</p>
                <p>Total rows: {importResult.total_rows ?? 0}</p>
                <p>Valid rows: {importResult.valid_rows ?? 0}</p>
                <p>Invalid rows: {importResult.invalid_rows ?? 0}</p>

                {importResult.errors?.length > 0 && (
                  <div className="import-errors">
                    {importResult.errors.map((item, index) => (
                      <div key={index}>
                        Row {item.row_number}: {item.message}
                      </div>
                    ))}
                  </div>
                )}

                {importResult.status === "VALIDATED" &&
                  Number(importResult.invalid_rows || 0) === 0 && (
                    <div className="import-confirm">
                      <p className="import-success">
                        Validation passed. The file is ready for confirmation.
                      </p>
                      <button
                        type="button"
                        className="save-button"
                        onClick={confirmImport}
                        disabled={importing}
                      >
                        {importing ? "Importing..." : "Confirm Import"}
                      </button>
                    </div>
                  )}

                {["COMPLETED", "IMPORTED"].includes(importResult.status) && (
                  <p className="import-success">
                    Assets imported successfully.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Assets;
