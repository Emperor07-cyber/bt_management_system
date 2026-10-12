import React, { useEffect, useMemo, useState } from "react";
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  X,
  Car,
  RefreshCw,
  UserRound,
  Wrench,
  RotateCcw,
  Upload,
  Download,
  History,
} from "lucide-react";
import api from "../services/api";
import "./Fleet.css";

const EMPTY_VEHICLE = {
  vehicle_code: "",
  registration_number: "",
  vehicle_type: "CAR",
  make: "",
  model: "",
  year: "",
  color: "",
  vin: "",
  engine_number: "",
  purchase_date: "",
  purchase_price: "",
  status: "AVAILABLE",
  current_mileage: 0,
  notes: "",
};

const EMPTY_ASSIGNMENT = {
  vehicle: "",
  employee: "",
  location: "",
  assignment_date: "",
  return_date: "",
  purpose: "",
  notes: "",
};

const EMPTY_MAINTENANCE = {
  vehicle: "",
  maintenance_type: "SERVICE",
  maintenance_date: "",
  mileage: "",
  description: "",
  service_provider: "",
  cost: "0",
  next_service_date: "",
  next_service_mileage: "",
  notes: "",
};

const VEHICLE_TYPES = [
  ["CAR", "Car"],
  ["VAN", "Van"],
  ["TRUCK", "Truck"],
  ["BUS", "Bus"],
  ["MOTORCYCLE", "Motorcycle"],
  ["OTHER", "Other"],
];

const VEHICLE_STATUSES = [
  ["AVAILABLE", "Available"],
  ["ASSIGNED", "Assigned"],
  ["MAINTENANCE", "Maintenance"],
  ["INACTIVE", "Inactive"],
  ["DISPOSED", "Disposed"],
];

const MAINTENANCE_TYPES = [
  ["SERVICE", "Service"],
  ["REPAIR", "Repair"],
  ["INSPECTION", "Inspection"],
  ["TYRE", "Tyre"],
  ["OIL_CHANGE", "Oil Change"],
  ["OTHER", "Other"],
];

const CREATE_ROLES = ["Admin", "Manager", "Fleet Staff"];

function listOf(response) {
  const data = response?.data;
  return Array.isArray(data) ? data : data?.results || [];
}

function rolesFromStorage() {
  try {
    const roles = JSON.parse(localStorage.getItem("roles") || "[]");
    return Array.isArray(roles) ? roles : [];
  } catch {
    return [];
  }
}

function canCreate(roles) {
  return roles.some((role) => CREATE_ROLES.includes(role));
}

function canDelete(roles) {
  return roles.includes("Admin");
}

function canUpdate(roles) {
  return canCreate(roles);
}

function employeeName(employee, employees = []) {
  if (!employee) return "—";
  if (typeof employee === "object") {
    return (
      [employee.first_name, employee.last_name].filter(Boolean).join(" ").trim() ||
      employee.full_name ||
      employee.name ||
      employee.employee_number ||
      employee.id ||
      "—"
    );
  }
  const found = employees.find((item) => String(item.id) === String(employee));
  return found
    ? [found.first_name, found.last_name].filter(Boolean).join(" ").trim() ||
      found.employee_number ||
      found.name ||
      "—"
    : String(employee);
}

function locationName(location, locations = []) {
  if (!location) return "—";
  if (typeof location === "object") {
    return (
      location.name ||
      location.location_name ||
      location.location_code ||
      location.code ||
      "—"
    );
  }
  const found = locations.find((item) => String(item.id) === String(location));
  return found?.name || found?.location_name || found?.location_code || String(location);
}

function vehicleLabel(vehicle, vehicles = []) {
  if (!vehicle) return "—";
  if (typeof vehicle === "object") {
    return (
      vehicle.vehicle_code ||
      vehicle.registration_number ||
      `${vehicle.make || ""} ${vehicle.model || ""}`.trim() ||
      vehicle.id ||
      "—"
    );
  }
  const found = vehicles.find((item) => String(item.id) === String(vehicle));
  return found
    ? `${found.vehicle_code || found.registration_number || "Vehicle"}${
        found.registration_number && found.vehicle_code
          ? ` — ${found.registration_number}`
          : ""
      }`
    : String(vehicle);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString();
}

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isNaN(number)
    ? String(value)
    : new Intl.NumberFormat("en-NG", {
        style: "currency",
        currency: "NGN",
        minimumFractionDigits: 2,
      }).format(number);
}

function statusLabel(status) {
  return (
    VEHICLE_STATUSES.find(([value]) => value === status)?.[1] ||
    status ||
    "Unknown"
  );
}

function maintenanceLabel(type) {
  return (
    MAINTENANCE_TYPES.find(([value]) => value === type)?.[1] ||
    type ||
    "—"
  );
}

function errorMessage(error, fallback) {
  if (error?.userMessage) return error.userMessage;
  const data = error?.response?.data;
  if (typeof data === "string") return data;
  if (data?.detail) return data.detail;
  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
      .join(" | ");
  }
  return fallback;
}

export default function Fleet() {
  const roles = useMemo(rolesFromStorage, []);
  const allowCreate = canCreate(roles);
  const allowUpdate = canUpdate(roles);
  const allowDelete = canDelete(roles);

  const [tab, setTab] = useState("vehicles");
  const [vehicles, setVehicles] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [maintenance, setMaintenance] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [locations, setLocations] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [vehicleModal, setVehicleModal] = useState(false);
  const [assignmentModal, setAssignmentModal] = useState(false);
  const [maintenanceModal, setMaintenanceModal] = useState(false);
  const [historyVehicle, setHistoryVehicle] = useState(null);
  const [importModal, setImportModal] = useState(false);

  const [editingVehicle, setEditingVehicle] = useState(null);
  const [editingAssignment, setEditingAssignment] = useState(null);
  const [editingMaintenance, setEditingMaintenance] = useState(null);

  const [vehicleForm, setVehicleForm] = useState(EMPTY_VEHICLE);
  const [assignmentForm, setAssignmentForm] = useState(EMPTY_ASSIGNMENT);
  const [maintenanceForm, setMaintenanceForm] = useState(EMPTY_MAINTENANCE);

  const [importFile, setImportFile] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [importing, setImporting] = useState(false);

  const notifySuccess = (message) => {
    setError("");
    setSuccess(message);
    window.setTimeout(() => setSuccess(""), 3500);
  };

  const clearMessages = () => {
    setError("");
    setSuccess("");
  };

  const loadData = async (silent = false) => {
    try {
      clearMessages();
      silent ? setRefreshing(true) : setLoading(true);

      const [v, a, m, e, l] = await Promise.all([
        api.get("/fleet/vehicles/"),
        api.get("/fleet/assignments/"),
        api.get("/fleet/maintenance/"),
        api.get("/company/employees/"),
        api.get("/company/locations/"),
      ]);

      setVehicles(listOf(v));
      setAssignments(listOf(a));
      setMaintenance(listOf(m));
      setEmployees(listOf(e));
      setLocations(listOf(l));
    } catch (err) {
      setError(errorMessage(err, "Unable to load fleet data."));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const currentLocationByVehicle = useMemo(() => {
    const map = new Map();
    assignments
      .filter((item) => !item.return_date && item.location)
      .forEach((item) => {
        const vehicleId = typeof item.vehicle === "object" ? item.vehicle.id : item.vehicle;
        map.set(String(vehicleId), item.location);
      });
    return map;
  }, [assignments]);

  const filteredVehicles = useMemo(() => {
    const q = search.trim().toLowerCase();

    return vehicles.filter((vehicle) => {
      const currentLocation = currentLocationByVehicle.get(String(vehicle.id));

      if (locationFilter && String(currentLocation) !== String(locationFilter)) return false;
      if (statusFilter && vehicle.status !== statusFilter) return false;
      if (typeFilter && vehicle.vehicle_type !== typeFilter) return false;

      if (!q) return true;

      return [
        vehicle.vehicle_code,
        vehicle.registration_number,
        vehicle.vehicle_type,
        vehicle.make,
        vehicle.model,
        vehicle.color,
        vehicle.vin,
        vehicle.engine_number,
        vehicle.status,
        locationName(currentLocation, locations),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [vehicles, assignments, currentLocationByVehicle, locations, search, locationFilter, statusFilter, typeFilter]);

  const filteredAssignments = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return assignments;

    return assignments.filter((item) =>
      [
        vehicleLabel(item.vehicle, vehicles),
        employeeName(item.employee, employees),
        locationName(item.location, locations),
        item.assignment_date,
        item.return_date,
        item.purpose,
        item.notes,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [assignments, vehicles, employees, locations, search]);

  const filteredMaintenance = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return maintenance;

    return maintenance.filter((item) =>
      [
        vehicleLabel(item.vehicle, vehicles),
        item.maintenance_type,
        item.type,
        item.description,
        item.service_provider,
        item.notes,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [maintenance, vehicles, search]);

  const summary = useMemo(
    () => ({
      total: vehicles.length,
      available: vehicles.filter((v) => v.status === "AVAILABLE").length,
      assigned: vehicles.filter((v) => v.status === "ASSIGNED").length,
      maintenance: vehicles.filter((v) => v.status === "MAINTENANCE").length,
    }),
    [vehicles]
  );

  const availableVehicles = useMemo(
    () =>
      vehicles.filter(
        (vehicle) =>
          vehicle.status === "AVAILABLE" ||
          String(vehicle.id) === String(assignmentForm.vehicle)
      ),
    [vehicles, assignmentForm.vehicle]
  );

  const openVehicle = (vehicle = null) => {
    clearMessages();
    setEditingVehicle(vehicle);
    setVehicleForm(
      vehicle
        ? {
            vehicle_code: vehicle.vehicle_code || "",
            registration_number: vehicle.registration_number || "",
            vehicle_type: vehicle.vehicle_type || "CAR",
            make: vehicle.make || "",
            model: vehicle.model || "",
            year: vehicle.year ?? "",
            color: vehicle.color || "",
            vin: vehicle.vin || "",
            engine_number: vehicle.engine_number || "",
            purchase_date: vehicle.purchase_date || "",
            purchase_price: vehicle.purchase_price ?? "",
            status: vehicle.status || "AVAILABLE",
            current_mileage: vehicle.current_mileage ?? 0,
            notes: vehicle.notes || "",
          }
        : { ...EMPTY_VEHICLE }
    );
    setVehicleModal(true);
  };

  const saveVehicle = async (event) => {
    event.preventDefault();
    clearMessages();

    try {
      const payload = {
        ...vehicleForm,
        year: vehicleForm.year === "" ? null : Number(vehicleForm.year),
        purchase_price: vehicleForm.purchase_price === "" ? null : vehicleForm.purchase_price,
        current_mileage: Number(vehicleForm.current_mileage || 0),
        vin: vehicleForm.vin || null,
        engine_number: vehicleForm.engine_number || null,
        purchase_date: vehicleForm.purchase_date || null,
      };

      if (editingVehicle) {
        await api.patch(`/fleet/vehicles/${editingVehicle.id}/`, payload);
        notifySuccess("Vehicle updated successfully.");
      } else {
        await api.post("/fleet/vehicles/", payload);
        notifySuccess("Vehicle created successfully.");
      }

      setVehicleModal(false);
      setEditingVehicle(null);
      await loadData(true);
    } catch (err) {
      setError(errorMessage(err, "Unable to save vehicle."));
    }
  };

  const deleteVehicle = async (vehicle) => {
    if (!allowDelete) return;
    if (!window.confirm(`Delete vehicle "${vehicle.vehicle_code}"?`)) return;

    try {
      clearMessages();
      await api.delete(`/fleet/vehicles/${vehicle.id}/`);
      notifySuccess("Vehicle deleted successfully.");
      await loadData(true);
    } catch (err) {
      setError(errorMessage(err, "Unable to delete vehicle."));
    }
  };

  const openAssignment = (item = null) => {
    clearMessages();
    setEditingAssignment(item);

    setAssignmentForm(
      item
        ? {
            vehicle: item.vehicle?.id ?? item.vehicle ?? "",
            employee: item.employee?.id ?? item.employee ?? "",
            location: item.location?.id ?? item.location ?? "",
            assignment_date: item.assignment_date || "",
            return_date: item.return_date || "",
            purpose: item.purpose || "",
            notes: item.notes || "",
          }
        : {
            ...EMPTY_ASSIGNMENT,
            assignment_date: new Date().toISOString().slice(0, 10),
          }
    );

    setAssignmentModal(true);
  };

  const saveAssignment = async (event) => {
    event.preventDefault();
    clearMessages();

    if (!assignmentForm.vehicle || !assignmentForm.assignment_date) {
      setError("Vehicle and assignment date are required.");
      return;
    }

    if (
      assignmentForm.return_date &&
      assignmentForm.return_date < assignmentForm.assignment_date
    ) {
      setError("Return date cannot be earlier than the assignment date.");
      return;
    }

    try {
      const payload = {
        vehicle: Number(assignmentForm.vehicle),
        employee: assignmentForm.employee ? Number(assignmentForm.employee) : null,
        location: assignmentForm.location ? Number(assignmentForm.location) : null,
        assignment_date: assignmentForm.assignment_date,
        return_date: assignmentForm.return_date || null,
        purpose: assignmentForm.purpose,
        notes: assignmentForm.notes,
      };

      if (editingAssignment) {
        await api.patch(`/fleet/assignments/${editingAssignment.id}/`, payload);
        notifySuccess("Assignment updated successfully.");
      } else {
        await api.post("/fleet/assignments/", payload);
        notifySuccess("Vehicle assigned successfully.");
      }

      setAssignmentModal(false);
      setEditingAssignment(null);
      await loadData(true);
    } catch (err) {
      setError(errorMessage(err, "Unable to save assignment."));
    }
  };

  const returnAssignment = async (item) => {
    if (item.return_date) return;
    if (!window.confirm(`Return ${vehicleLabel(item.vehicle, vehicles)}?`)) return;

    try {
      clearMessages();
      await api.patch(`/fleet/assignments/${item.id}/`, {
        return_date: new Date().toISOString().slice(0, 10),
      });
      notifySuccess("Vehicle returned successfully.");
      await loadData(true);
    } catch (err) {
      setError(errorMessage(err, "Unable to return vehicle."));
    }
  };

  const deleteAssignment = async (item) => {
    if (!allowDelete) return;
    if (!window.confirm(`Delete this assignment for ${vehicleLabel(item.vehicle, vehicles)}?`)) return;

    try {
      clearMessages();
      await api.delete(`/fleet/assignments/${item.id}/`);
      notifySuccess("Assignment deleted successfully.");
      await loadData(true);
    } catch (err) {
      setError(errorMessage(err, "Unable to delete assignment."));
    }
  };

  const openVehicleMaintenanceHistory = (vehicle) => {
    clearMessages();
    setHistoryVehicle(vehicle);
  };

  const vehicleMaintenanceHistory = useMemo(() => {
    if (!historyVehicle) return [];
    return maintenance
      .filter((item) => {
        const itemVehicleId = typeof item.vehicle === "object" ? item.vehicle.id : item.vehicle;
        return String(itemVehicleId) === String(historyVehicle.id);
      })
      .sort((a, b) => new Date(b.maintenance_date || 0) - new Date(a.maintenance_date || 0));
  }, [historyVehicle, maintenance]);

  const openMaintenance = (item = null) => {
    clearMessages();
    setEditingMaintenance(item);

    setMaintenanceForm(
      item
        ? {
            vehicle: item.vehicle?.id ?? item.vehicle ?? "",
            maintenance_type: item.maintenance_type || item.type || "SERVICE",
            maintenance_date: item.maintenance_date || "",
            mileage: item.mileage ?? "",
            description: item.description || "",
            service_provider: item.service_provider || "",
            cost: item.cost ?? "0",
            next_service_date: item.next_service_date || "",
            next_service_mileage: item.next_service_mileage ?? "",
            notes: item.notes || "",
          }
        : {
            ...EMPTY_MAINTENANCE,
            maintenance_date: new Date().toISOString().slice(0, 10),
          }
    );

    setMaintenanceModal(true);
  };

  const saveMaintenance = async (event) => {
    event.preventDefault();
    clearMessages();

    if (!maintenanceForm.vehicle || !maintenanceForm.maintenance_date || !maintenanceForm.description) {
      setError("Vehicle, maintenance date and description are required.");
      return;
    }

    if (
      maintenanceForm.next_service_date &&
      maintenanceForm.next_service_date < maintenanceForm.maintenance_date
    ) {
      setError("Next service date cannot be earlier than the maintenance date.");
      return;
    }

    if (
      maintenanceForm.next_service_mileage !== "" &&
      maintenanceForm.mileage !== "" &&
      Number(maintenanceForm.next_service_mileage) < Number(maintenanceForm.mileage)
    ) {
      setError("Next service mileage cannot be lower than the maintenance mileage.");
      return;
    }

    try {
      const payload = {
        vehicle: Number(maintenanceForm.vehicle),
        maintenance_type: maintenanceForm.maintenance_type,
        maintenance_date: maintenanceForm.maintenance_date,
        mileage: Number(maintenanceForm.mileage || 0),
        description: maintenanceForm.description,
        service_provider: maintenanceForm.service_provider,
        cost: maintenanceForm.cost === "" ? "0" : maintenanceForm.cost,
        next_service_date: maintenanceForm.next_service_date || null,
        next_service_mileage:
          maintenanceForm.next_service_mileage === ""
            ? null
            : Number(maintenanceForm.next_service_mileage),
        notes: maintenanceForm.notes,
      };

      if (editingMaintenance) {
        await api.patch(`/fleet/maintenance/${editingMaintenance.id}/`, payload);
        notifySuccess("Maintenance record updated successfully.");
      } else {
        await api.post("/fleet/maintenance/", payload);
        notifySuccess("Maintenance record created successfully.");
      }

      setMaintenanceModal(false);
      setEditingMaintenance(null);
      await loadData(true);
    } catch (err) {
      setError(errorMessage(err, "Unable to save maintenance record."));
    }
  };

  const deleteMaintenance = async (item) => {
    if (!allowDelete) return;
    if (!window.confirm(`Delete maintenance record for ${vehicleLabel(item.vehicle, vehicles)}?`)) return;

    try {
      clearMessages();
      await api.delete(`/fleet/maintenance/${item.id}/`);
      notifySuccess("Maintenance record deleted successfully.");
      await loadData(true);
    } catch (err) {
      setError(errorMessage(err, "Unable to delete maintenance record."));
    }
  };

  const downloadTemplate = async () => {
    try {
      clearMessages();
      const response = await api.get("/fleet/vehicles/import-template/", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "fleet_vehicle_import_template.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(errorMessage(err, "Unable to download the Fleet template."));
    }
  };

  const uploadImport = async () => {
    if (!importFile) {
      setError("Please choose an Excel file first.");
      return;
    }

    try {
      clearMessages();
      setImporting(true);
      setImportResult(null);

      const formData = new FormData();
      formData.append("file", importFile);

      const response = await api.post("/fleet/vehicles/import/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setImportResult(response.data);
      if (response.data.status === "VALIDATED") {
        notifySuccess("Fleet import validated. Review the result before confirming.");
      }
    } catch (err) {
      setImportResult(err.response?.data || null);
      setError(errorMessage(err, "Fleet import validation failed."));
    } finally {
      setImporting(false);
    }
  };

  const confirmImport = async () => {
    if (!importResult?.batch_id || importResult.status !== "VALIDATED") return;

    try {
      clearMessages();
      setImporting(true);

      const response = await api.post(
        `/fleet/vehicles/import/${importResult.batch_id}/confirm/`
      );

      setImportResult((current) => ({ ...current, ...response.data }));
      notifySuccess(`Fleet import completed: ${response.data.imported_rows || 0} vehicle(s) imported.`);
      setImportFile(null);
      await loadData(true);
    } catch (err) {
      setError(errorMessage(err, "Fleet import confirmation failed."));
    } finally {
      setImporting(false);
    }
  };

  const clearFilters = () => {
    setSearch("");
    setLocationFilter("");
    setStatusFilter("");
    setTypeFilter("");
  };

  if (loading) {
    return (
      <div className="fleet-page">
        <div className="fleet-loading">
          <RefreshCw size={22} className="fleet-spin" />
          Loading fleet...
        </div>
      </div>
    );
  }

  return (
    <div className="fleet-page">
      <div className="fleet-header">
        <div>
          <p className="fleet-breadcrumb">Home / Fleet</p>
          <div className="fleet-title-row">
            <Car size={27} />
            <h1>Fleet Management</h1>
          </div>
          <p className="fleet-subtitle">
            Manage company vehicles, driver assignments and maintenance history.
          </p>
        </div>

        <div className="fleet-header-actions">
          {allowCreate && (
            <button className="fleet-btn fleet-btn-primary" onClick={() => openVehicle()}>
              <Plus size={17} /> Add Vehicle
            </button>
          )}
          <button
            className="fleet-btn"
            onClick={() => loadData(true)}
            disabled={refreshing}
          >
            <RefreshCw size={17} className={refreshing ? "fleet-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="fleet-alert fleet-alert-error">
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Close error"><X size={17} /></button>
        </div>
      )}

      {success && (
        <div className="fleet-alert fleet-alert-success">
          <span>{success}</span>
          <button onClick={() => setSuccess("")} aria-label="Close success"><X size={17} /></button>
        </div>
      )}

      <div className="fleet-summary-grid">
        {[
          ["Total Vehicles", summary.total, Car],
          ["Available", summary.available, Car],
          ["Assigned", summary.assigned, UserRound],
          ["Maintenance", summary.maintenance, Wrench],
        ].map(([label, value, Icon]) => (
          <div className="fleet-summary-card" key={label}>
            <div className="fleet-summary-icon"><Icon size={21} /></div>
            <div>
              <p className="fleet-summary-label">{label}</p>
              <p className="fleet-summary-value">{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="fleet-toolbar">
        <div className="fleet-tabs">
          {[
            ["vehicles", "Vehicles", Car],
            ["assignments", "Driver Assignments", UserRound],
            ["maintenance", "Maintenance", Wrench],
          ].map(([value, label, Icon]) => (
            <button
              key={value}
              className={`fleet-tab ${tab === value ? "active" : ""}`}
              onClick={() => {
                setTab(value);
                setSearch("");
              }}
            >
              <Icon size={16} /> {label}
            </button>
          ))}
        </div>

        <div className="fleet-toolbar-right">
          <div className="fleet-search">
            <Search size={17} />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`Search ${tab === "vehicles" ? "vehicles" : tab === "assignments" ? "assignments" : "maintenance"}...`}
            />
          </div>

          {tab === "vehicles" && allowCreate && (
            <>
              <button className="fleet-btn" onClick={() => setImportModal(true)}>
                <Upload size={16} /> Import Excel
              </button>
              <button className="fleet-btn fleet-btn-primary" onClick={() => openVehicle()}>
                <Plus size={16} /> Add Vehicle
              </button>
            </>
          )}

          {tab === "assignments" && allowCreate && (
            <button className="fleet-btn fleet-btn-primary" onClick={() => openAssignment()}>
              <Plus size={16} /> New Assignment
            </button>
          )}

          {tab === "maintenance" && allowCreate && (
            <button className="fleet-btn fleet-btn-primary" onClick={() => openMaintenance()}>
              <Plus size={16} /> Add Maintenance
            </button>
          )}
        </div>
      </div>

      {tab === "vehicles" && (
        <div className="fleet-filter-row">
          <select value={locationFilter} onChange={(e) => setLocationFilter(e.target.value)}>
            <option value="">All locations / stores</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {locationName(location)}
              </option>
            ))}
          </select>

          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {VEHICLE_STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>

          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="">All vehicle types</option>
            {VEHICLE_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>

          {(locationFilter || statusFilter || typeFilter || search) && (
            <button className="fleet-btn" onClick={clearFilters}>Clear Filters</button>
          )}
        </div>
      )}

      {tab === "vehicles" && (
        <div className="fleet-table-card">
          <div className="fleet-card-header">
            <div>
              <h2>Vehicles</h2>
              <p>{filteredVehicles.length} vehicle{filteredVehicles.length === 1 ? "" : "s"}</p>
            </div>
          </div>
          <div className="fleet-table-wrapper">
            <table className="fleet-table">
              <thead>
                <tr>
                  <th>Vehicle</th>
                  <th>Registration</th>
                  <th>Type</th>
                  <th>Make / Model</th>
                  <th>Year</th>
                  <th>Location</th>
                  <th>Mileage</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredVehicles.length === 0 ? (
                  <tr><td colSpan="9" className="fleet-empty">
                    <Car size={34} /><strong>No vehicles found</strong><span>Try changing the search or filters.</span>
                  </td></tr>
                ) : filteredVehicles.map((vehicle) => {
                  const currentLocation = currentLocationByVehicle.get(String(vehicle.id));
                  return (
                    <tr key={vehicle.id}>
                      <td><strong>{vehicle.vehicle_code || "—"}</strong></td>
                      <td><strong>{vehicle.registration_number || "—"}</strong></td>
                      <td>{VEHICLE_TYPES.find(([v]) => v === vehicle.vehicle_type)?.[1] || vehicle.vehicle_type || "—"}</td>
                      <td>{`${vehicle.make || ""} ${vehicle.model || ""}`.trim() || "—"}</td>
                      <td>{vehicle.year || "—"}</td>
                      <td>{locationName(currentLocation, locations)}</td>
                      <td>{Number(vehicle.current_mileage || 0).toLocaleString()} km</td>
                      <td><span className={`fleet-status status-${String(vehicle.status || "").toLowerCase()}`}>{statusLabel(vehicle.status)}</span></td>
                      <td>
                        <div className="fleet-row-actions">
                          <button className="fleet-icon-button" title="View maintenance history" onClick={() => openVehicleMaintenanceHistory(vehicle)}><History size={16} /></button>
                          {allowUpdate && <button className="fleet-icon-button" title="Edit vehicle" onClick={() => openVehicle(vehicle)}><Pencil size={16} /></button>}
                          {allowDelete && <button className="fleet-icon-button danger" title="Delete vehicle" onClick={() => deleteVehicle(vehicle)}><Trash2 size={16} /></button>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "assignments" && (
        <div className="fleet-table-card">
          <div className="fleet-card-header"><div><h2>Driver Assignments</h2><p>{filteredAssignments.length} assignment{filteredAssignments.length === 1 ? "" : "s"}</p></div></div>
          <div className="fleet-table-wrapper">
            <table className="fleet-table">
              <thead><tr><th>Vehicle</th><th>Employee</th><th>Location</th><th>Assignment Date</th><th>Return Date</th><th>Purpose</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>
                {filteredAssignments.length === 0 ? (
                  <tr><td colSpan="8" className="fleet-empty"><UserRound size={34} /><strong>No assignments found</strong><span>Create an assignment to assign a vehicle.</span></td></tr>
                ) : filteredAssignments.map((item) => {
                  const active = !item.return_date;
                  return (
                    <tr key={item.id}>
                      <td><strong>{vehicleLabel(item.vehicle, vehicles)}</strong></td>
                      <td>{employeeName(item.employee, employees)}</td>
                      <td>{locationName(item.location, locations)}</td>
                      <td>{formatDate(item.assignment_date)}</td>
                      <td>{formatDate(item.return_date)}</td>
                      <td>{item.purpose || "—"}</td>
                      <td><span className={`fleet-status ${active ? "status-assigned" : "status-available"}`}>{active ? "Active" : "Returned"}</span></td>
                      <td>
                        <div className="fleet-row-actions">
                          {active && allowUpdate && <button className="fleet-icon-button" title="Return vehicle" onClick={() => returnAssignment(item)}><RotateCcw size={16} /></button>}
                          {allowUpdate && <button className="fleet-icon-button" title="Edit assignment" onClick={() => openAssignment(item)}><Pencil size={16} /></button>}
                          {allowDelete && <button className="fleet-icon-button danger" title="Delete assignment" onClick={() => deleteAssignment(item)}><Trash2 size={16} /></button>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "maintenance" && (
        <div className="fleet-table-card">
          <div className="fleet-card-header"><div><h2>Maintenance</h2><p>{filteredMaintenance.length} maintenance record{filteredMaintenance.length === 1 ? "" : "s"}</p></div></div>
          <div className="fleet-table-wrapper">
            <table className="fleet-table">
              <thead><tr><th>Vehicle</th><th>Type</th><th>Date</th><th>Mileage</th><th>Description</th><th>Provider</th><th>Cost</th><th>Next Service</th><th>Actions</th></tr></thead>
              <tbody>
                {filteredMaintenance.length === 0 ? (
                  <tr><td colSpan="9" className="fleet-empty"><Wrench size={34} /><strong>No maintenance records found</strong><span>Add service and repair history for vehicles.</span></td></tr>
                ) : filteredMaintenance.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{vehicleLabel(item.vehicle, vehicles)}</strong></td>
                    <td>{maintenanceLabel(item.maintenance_type || item.type)}</td>
                    <td>{formatDate(item.maintenance_date)}</td>
                    <td>{Number(item.mileage || 0).toLocaleString()} km</td>
                    <td>{item.description || "—"}</td>
                    <td>{item.service_provider || "—"}</td>
                    <td>{formatMoney(item.cost)}</td>
                    <td>{item.next_service_date ? formatDate(item.next_service_date) : item.next_service_mileage != null ? `${Number(item.next_service_mileage).toLocaleString()} km` : "—"}</td>
                    <td>
                      <div className="fleet-row-actions">
                        {allowUpdate && <button className="fleet-icon-button" title="Edit maintenance" onClick={() => openMaintenance(item)}><Pencil size={16} /></button>}
                        {allowDelete && <button className="fleet-icon-button danger" title="Delete maintenance" onClick={() => deleteMaintenance(item)}><Trash2 size={16} /></button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {vehicleModal && (
        <div className="fleet-modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && setVehicleModal(false)}>
          <div className="fleet-modal">
            <div className="fleet-modal-header"><div><h2>{editingVehicle ? "Edit Vehicle" : "Add Vehicle"}</h2><p>Enter vehicle information.</p></div><button className="fleet-modal-close" onClick={() => setVehicleModal(false)}><X size={20} /></button></div>
            <form onSubmit={saveVehicle}>
              <div className="fleet-form-grid">
                {[
                  ["vehicle_code", "Vehicle Code", "text", true],
                  ["registration_number", "Registration Number", "text", true],
                  ["make", "Make", "text", true],
                  ["model", "Model", "text", true],
                  ["year", "Year", "number", false],
                  ["color", "Color", "text", false],
                  ["vin", "VIN", "text", false],
                  ["engine_number", "Engine Number", "text", false],
                  ["purchase_date", "Purchase Date", "date", false],
                  ["purchase_price", "Purchase Price", "number", false],
                  ["current_mileage", "Current Mileage", "number", false],
                ].map(([name, label, type, required]) => (
                  <div className="fleet-form-group" key={name}>
                    <label>{label}{required ? " *" : ""}</label>
                    <input name={name} type={type} min={type === "number" ? "0" : undefined} step={name === "purchase_price" ? "0.01" : "1"} value={vehicleForm[name]} onChange={(e) => setVehicleForm({ ...vehicleForm, [name]: e.target.value })} required={required} />
                  </div>
                ))}
                <div className="fleet-form-group"><label>Vehicle Type *</label><select name="vehicle_type" value={vehicleForm.vehicle_type} onChange={(e) => setVehicleForm({ ...vehicleForm, vehicle_type: e.target.value })}>{VEHICLE_TYPES.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></div>
                <div className="fleet-form-group"><label>Status *</label><select name="status" value={vehicleForm.status} onChange={(e) => setVehicleForm({ ...vehicleForm, status: e.target.value })}>{VEHICLE_STATUSES.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></div>
                <div className="fleet-form-group full"><label>Notes</label><textarea rows="4" value={vehicleForm.notes} onChange={(e) => setVehicleForm({ ...vehicleForm, notes: e.target.value })} /></div>
              </div>
              <div className="fleet-modal-footer"><button type="button" className="fleet-btn" onClick={() => setVehicleModal(false)}>Cancel</button><button type="submit" className="fleet-btn fleet-btn-primary">{editingVehicle ? "Update Vehicle" : "Create Vehicle"}</button></div>
            </form>
          </div>
        </div>
      )}

      {assignmentModal && (
        <div className="fleet-modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && setAssignmentModal(false)}>
          <div className="fleet-modal">
            <div className="fleet-modal-header"><div><h2>{editingAssignment ? "Edit Driver Assignment" : "New Driver Assignment"}</h2><p>Assign a vehicle to an employee and location.</p></div><button className="fleet-modal-close" onClick={() => setAssignmentModal(false)}><X size={20} /></button></div>
            <form onSubmit={saveAssignment}>
              <div className="fleet-form-grid">
                <div className="fleet-form-group"><label>Vehicle *</label><select value={assignmentForm.vehicle} onChange={(e) => setAssignmentForm({ ...assignmentForm, vehicle: e.target.value })} required><option value="">Select vehicle</option>{availableVehicles.map((v) => <option key={v.id} value={v.id}>{vehicleLabel(v)}{v.registration_number ? ` — ${v.registration_number}` : ""}</option>)}</select></div>
                <div className="fleet-form-group"><label>Employee / Driver</label><select value={assignmentForm.employee} onChange={(e) => setAssignmentForm({ ...assignmentForm, employee: e.target.value })}><option value="">Select employee</option>{employees.map((e) => <option key={e.id} value={e.id}>{employeeName(e)}</option>)}</select></div>
                <div className="fleet-form-group"><label>Location / Store</label><select value={assignmentForm.location} onChange={(e) => setAssignmentForm({ ...assignmentForm, location: e.target.value })}><option value="">Select location</option>{locations.map((l) => <option key={l.id} value={l.id}>{locationName(l)}</option>)}</select></div>
                <div className="fleet-form-group"><label>Assignment Date *</label><input type="date" value={assignmentForm.assignment_date} onChange={(e) => setAssignmentForm({ ...assignmentForm, assignment_date: e.target.value })} required /></div>
                <div className="fleet-form-group"><label>Return Date</label><input type="date" min={assignmentForm.assignment_date || undefined} value={assignmentForm.return_date} onChange={(e) => setAssignmentForm({ ...assignmentForm, return_date: e.target.value })} /></div>
                <div className="fleet-form-group full"><label>Purpose</label><input value={assignmentForm.purpose} onChange={(e) => setAssignmentForm({ ...assignmentForm, purpose: e.target.value })} placeholder="e.g. Official field operations" /></div>
                <div className="fleet-form-group full"><label>Notes</label><textarea rows="4" value={assignmentForm.notes} onChange={(e) => setAssignmentForm({ ...assignmentForm, notes: e.target.value })} /></div>
              </div>
              <div className="fleet-modal-footer"><button type="button" className="fleet-btn" onClick={() => setAssignmentModal(false)}>Cancel</button><button type="submit" className="fleet-btn fleet-btn-primary">{editingAssignment ? "Update Assignment" : "Assign Vehicle"}</button></div>
            </form>
          </div>
        </div>
      )}

      {historyVehicle && (
        <div className="fleet-modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && setHistoryVehicle(null)}>
          <div className="fleet-modal fleet-history-modal">
            <div className="fleet-modal-header">
              <div>
                <h2>Maintenance History</h2>
                <p>{vehicleLabel(historyVehicle)}{historyVehicle.registration_number ? ` — ${historyVehicle.registration_number}` : ""}</p>
              </div>
              <button className="fleet-modal-close" onClick={() => setHistoryVehicle(null)} aria-label="Close maintenance history"><X size={20} /></button>
            </div>
            <div className="fleet-history-summary">
              <div><span>Total records</span><strong>{vehicleMaintenanceHistory.length}</strong></div>
              <div><span>Current status</span><strong>{statusLabel(historyVehicle.status)}</strong></div>
              <div><span>Current mileage</span><strong>{Number(historyVehicle.current_mileage || 0).toLocaleString()} km</strong></div>
            </div>
            <div className="fleet-history-content">
              {vehicleMaintenanceHistory.length === 0 ? (
                <div className="fleet-empty fleet-history-empty">
                  <Wrench size={38} />
                  <strong>No maintenance history</strong>
                  <span>No service or repair records have been recorded for this vehicle.</span>
                  {allowCreate && <button className="fleet-btn fleet-btn-primary" onClick={() => { setHistoryVehicle(null); openMaintenance({ vehicle: historyVehicle.id }); }}>
                    <Plus size={16} /> Add Maintenance Record
                  </button>}
                </div>
              ) : (
                <div className="fleet-history-list">
                  {vehicleMaintenanceHistory.map((item) => (
                    <div className="fleet-history-item" key={item.id}>
                      <div className="fleet-history-icon"><Wrench size={17} /></div>
                      <div className="fleet-history-main">
                        <div className="fleet-history-top">
                          <strong>{maintenanceLabel(item.maintenance_type || item.type)}</strong>
                          <span>{formatDate(item.maintenance_date)}</span>
                        </div>
                        <p>{item.description || "No description provided."}</p>
                        <div className="fleet-history-meta">
                          <span>{item.service_provider || "No provider recorded"}</span>
                          <span>{Number(item.mileage || 0).toLocaleString()} km</span>
                          <span>{formatMoney(item.cost)}</span>
                          {item.next_service_date && <span>Next: {formatDate(item.next_service_date)}</span>}
                          {item.next_service_mileage != null && <span>Next: {Number(item.next_service_mileage).toLocaleString()} km</span>}
                        </div>
                        {item.notes && <div className="fleet-history-notes">{item.notes}</div>}
                      </div>
                      <div className="fleet-history-actions">
                        {allowUpdate && <button className="fleet-icon-button" title="Edit maintenance" onClick={() => { setHistoryVehicle(null); openMaintenance(item); }}><Pencil size={16} /></button>}
                        {allowDelete && <button className="fleet-icon-button danger" title="Delete maintenance" onClick={() => { deleteMaintenance(item); }}><Trash2 size={16} /></button>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {maintenanceModal && (
        <div className="fleet-modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && setMaintenanceModal(false)}>
          <div className="fleet-modal">
            <div className="fleet-modal-header"><div><h2>{editingMaintenance ? "Edit Maintenance Record" : "Add Maintenance Record"}</h2><p>Record service, repairs and upcoming maintenance.</p></div><button className="fleet-modal-close" onClick={() => setMaintenanceModal(false)}><X size={20} /></button></div>
            <form onSubmit={saveMaintenance}>
              <div className="fleet-form-grid">
                <div className="fleet-form-group"><label>Vehicle *</label><select value={maintenanceForm.vehicle} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, vehicle: e.target.value })} required><option value="">Select vehicle</option>{vehicles.map((v) => <option key={v.id} value={v.id}>{vehicleLabel(v)}{v.registration_number ? ` — ${v.registration_number}` : ""}</option>)}</select></div>
                <div className="fleet-form-group"><label>Maintenance Type *</label><select value={maintenanceForm.maintenance_type} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, maintenance_type: e.target.value })}>{MAINTENANCE_TYPES.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></div>
                <div className="fleet-form-group"><label>Maintenance Date *</label><input type="date" value={maintenanceForm.maintenance_date} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, maintenance_date: e.target.value })} required /></div>
                <div className="fleet-form-group"><label>Mileage</label><input type="number" min="0" value={maintenanceForm.mileage} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, mileage: e.target.value })} /></div>
                <div className="fleet-form-group"><label>Service Provider</label><input value={maintenanceForm.service_provider} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, service_provider: e.target.value })} /></div>
                <div className="fleet-form-group"><label>Cost</label><input type="number" min="0" step="0.01" value={maintenanceForm.cost} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, cost: e.target.value })} /></div>
                <div className="fleet-form-group"><label>Next Service Date</label><input type="date" min={maintenanceForm.maintenance_date || undefined} value={maintenanceForm.next_service_date} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, next_service_date: e.target.value })} /></div>
                <div className="fleet-form-group"><label>Next Service Mileage</label><input type="number" min="0" value={maintenanceForm.next_service_mileage} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, next_service_mileage: e.target.value })} /></div>
                <div className="fleet-form-group full"><label>Description *</label><textarea rows="4" value={maintenanceForm.description} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, description: e.target.value })} required /></div>
                <div className="fleet-form-group full"><label>Notes</label><textarea rows="3" value={maintenanceForm.notes} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, notes: e.target.value })} /></div>
              </div>
              <div className="fleet-modal-footer"><button type="button" className="fleet-btn" onClick={() => setMaintenanceModal(false)}>Cancel</button><button type="submit" className="fleet-btn fleet-btn-primary">{editingMaintenance ? "Update Maintenance" : "Save Maintenance"}</button></div>
            </form>
          </div>
        </div>
      )}

      {importModal && (
        <div className="fleet-modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && setImportModal(false)}>
          <div className="fleet-modal fleet-import-modal">
            <div className="fleet-modal-header"><div><h2>Import Vehicles from Excel</h2><p>Upload, validate, review errors, then confirm the import.</p></div><button className="fleet-modal-close" onClick={() => setImportModal(false)}><X size={20} /></button></div>
            <div className="fleet-import-body">
              <div className="fleet-import-actions">
                <button className="fleet-btn" onClick={downloadTemplate}><Download size={16} /> Download Template</button>
              </div>
              <input type="file" accept=".xlsx,.xlsm" onChange={(e) => { setImportFile(e.target.files?.[0] || null); setImportResult(null); }} />
              {importFile && <p className="fleet-import-file">{importFile.name}</p>}
              <button className="fleet-btn fleet-btn-primary" onClick={uploadImport} disabled={importing || !importFile}>
                {importing ? "Processing..." : "Upload & Validate"}
              </button>

              {importResult && (
                <div className="fleet-import-result">
                  <h3>Validation Result</h3>
                  <div className="fleet-import-stats">
                    <span>Total: <strong>{importResult.total_rows ?? 0}</strong></span>
                    <span>Valid: <strong>{importResult.valid_rows ?? 0}</strong></span>
                    <span>Invalid: <strong>{importResult.invalid_rows ?? 0}</strong></span>
                    <span>Status: <strong>{importResult.status || "—"}</strong></span>
                  </div>

                  {Array.isArray(importResult.errors) && importResult.errors.length > 0 && (
                    <div className="fleet-import-errors">
                      {importResult.errors.map((item, index) => (
                        <div key={`${item.row_number}-${index}`}>
                          <strong>Row {item.row_number}</strong>
                          {item.column_name ? ` — ${item.column_name}` : ""}: {item.message}
                        </div>
                      ))}
                    </div>
                  )}

                  {importResult.status === "VALIDATED" && (
                    <button className="fleet-btn fleet-btn-primary" onClick={confirmImport} disabled={importing}>
                      {importing ? "Importing..." : "Confirm Import"}
                    </button>
                  )}

                  {importResult.status === "COMPLETED" && (
                    <p className="fleet-import-success">Import completed successfully.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
