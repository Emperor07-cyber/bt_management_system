import { useEffect, useMemo, useState } from "react";
import {
  Users,
  Building2,
  MapPin,
  Truck,
  Package,
  Boxes,
  ShoppingCart,
  Wallet,
  Plus,
  RefreshCw,
  AlertTriangle,
  X,
  Search,
  Pencil,
  Trash2,
  UserRound,
} from "lucide-react";

import api from "../services/api";
import "./Company.css";

const MODULES = [
  { value: "INVENTORY", label: "Inventory", icon: Package },
  { value: "FLEET", label: "Fleet", icon: Truck },
  { value: "ASSETS", label: "Assets", icon: Boxes },
  { value: "PROCUREMENT", label: "Procurement", icon: ShoppingCart },
  { value: "FINANCE", label: "Finance", icon: Wallet },
];

const EMPTY_EMPLOYEE = {
  employee_number: "",
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  department: "",
  location: "",
  status: "ACTIVE",
};

const EMPTY_DEPARTMENT = {
  department_code: "",
  name: "",
  description: "",
  manager: "",
  is_active: true,
};

const EMPTY_LOCATION = {
  name: "",
  address: "",
  parent: "",
  is_active: true,
};

const EMPTY_AFFILIATION = {
  employee: "",
  module: "INVENTORY",
  function: "",
  is_active: true,
};

const EMPTY_SUPPLIER = {
  supplier_code: "",
  name: "",
  contact_person: "",
  email: "",
  phone: "",
  address: "",
  tax_number: "",
  is_active: true,
};

const EMPTY_SETTINGS = {
  company_name: "",
  company_code: "",
  address: "",
  phone: "",
  email: "",
  logo_path: "",
  currency_code: "NGN",
  timezone: "Africa/Lagos",
  fiscal_year_start: "",
};

function Company() {
  const [activeTab, setActiveTab] = useState("employees");

  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [locations, setLocations] = useState([]);
  const [affiliations, setAffiliations] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [companySettings, setCompanySettings] = useState(null);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");

  const [modal, setModal] = useState(null);
  const [editingId, setEditingId] = useState(null);

  const [employeeForm, setEmployeeForm] = useState(EMPTY_EMPLOYEE);
  const [departmentForm, setDepartmentForm] = useState(EMPTY_DEPARTMENT);
  const [locationForm, setLocationForm] = useState(EMPTY_LOCATION);
  const [affiliationForm, setAffiliationForm] = useState(EMPTY_AFFILIATION);
  const [supplierForm, setSupplierForm] = useState(EMPTY_SUPPLIER);
  const [settingsForm, setSettingsForm] = useState(EMPTY_SETTINGS);

  const loadCompanyData = async () => {
    try {
      setLoading(true);
      setErrorMessage("");

      const requests = await Promise.allSettled([
        api.get("/company/employees/"),
        api.get("/company/departments/"),
        api.get("/company/locations/"),
        api.get("/company/employee-affiliations/"),
        api.get("/company/suppliers/"),
        api.get("/company/settings/"),
      ]);

      const [
        employeeResponse,
        departmentResponse,
        locationResponse,
        affiliationResponse,
        supplierResponse,
        settingsResponse,
      ] = requests;

      const failed = requests.find((item) => item.status === "rejected");

      if (failed) {
        throw failed.reason;
      }

      setEmployees(employeeResponse.value.data || []);
      setDepartments(departmentResponse.value.data || []);
      setLocations(locationResponse.value.data || []);
      setAffiliations(affiliationResponse.value.data || []);
      setSuppliers(supplierResponse.value.data || []);

      const settings = settingsResponse.value.data;

      setCompanySettings(
        Array.isArray(settings) ? settings[0] || null : settings || null
      );
    } catch (error) {
      console.error("Failed to load company data:", error);
      setErrorMessage(
        error.userMessage || "Unable to load company information."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCompanyData();
  }, []);

  const notifySuccess = (message) => {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(""), 3500);
  };

  const getDepartmentName = (id) =>
    departments.find((item) => item.id === id)?.name || "—";

  const getLocationName = (id) =>
    locations.find((item) => item.id === id)?.name || "—";

  const getEmployeeName = (id) => {
    const employee = employees.find((item) => item.id === id);

    return employee
      ? `${employee.first_name} ${employee.last_name}`.trim()
      : "—";
  };

  const getModuleLabel = (module) =>
    MODULES.find((item) => item.value === module)?.label || module;

  const filteredEmployees = useMemo(() => {
    const query = search.trim().toLowerCase();

    return employees.filter((employee) => {
      const matchesSearch =
        !query ||
        `${employee.employee_number} ${employee.first_name} ${employee.last_name} ${employee.email} ${employee.phone}`
          .toLowerCase()
          .includes(query);

      const matchesStatus =
        !statusFilter || employee.status === statusFilter;

      const matchesLocation =
        !locationFilter ||
        String(employee.location) === String(locationFilter);

      const matchesDepartment =
        !departmentFilter ||
        String(employee.department) === String(departmentFilter);

      const matchesModule =
        !moduleFilter ||
        (employee.active_affiliations || []).includes(moduleFilter);

      return (
        matchesSearch &&
        matchesStatus &&
        matchesLocation &&
        matchesDepartment &&
        matchesModule
      );
    });
  }, [
    employees,
    search,
    statusFilter,
    locationFilter,
    departmentFilter,
    moduleFilter,
  ]);

  const filteredDepartments = useMemo(() => {
    const query = search.trim().toLowerCase();

    return departments.filter(
      (item) =>
        !query ||
        `${item.department_code} ${item.name} ${item.description}`
          .toLowerCase()
          .includes(query)
    );
  }, [departments, search]);

  const filteredLocations = useMemo(() => {
    const query = search.trim().toLowerCase();

    return locations.filter(
      (item) =>
        !query ||
        `${item.name} ${item.address}`.toLowerCase().includes(query)
    );
  }, [locations, search]);

  const filteredAffiliations = useMemo(() => {
    const query = search.trim().toLowerCase();

    return affiliations.filter((item) => {
      const employeeName = getEmployeeName(item.employee);

      return (
        !query ||
        `${employeeName} ${item.module} ${item.function}`
          .toLowerCase()
          .includes(query)
      );
    });
  }, [affiliations, search, employees]);

  const filteredSuppliers = useMemo(() => {
    const query = search.trim().toLowerCase();

    return suppliers.filter(
      (item) =>
        !query ||
        `${item.supplier_code} ${item.name} ${item.contact_person} ${item.phone} ${item.email}`
          .toLowerCase()
          .includes(query)
    );
  }, [suppliers, search]);

  const handleError = (error, fallback) => {
    setErrorMessage(
      error.response?.data
        ? JSON.stringify(error.response.data)
        : error.userMessage || fallback
    );
  };

  const openCreate = (type) => {
    setEditingId(null);
    setErrorMessage("");

    if (type === "employee") {
      setEmployeeForm({ ...EMPTY_EMPLOYEE });
    }

    if (type === "department") {
      setDepartmentForm({ ...EMPTY_DEPARTMENT });
    }

    if (type === "location") {
      setLocationForm({ ...EMPTY_LOCATION });
    }

    if (type === "affiliation") {
      setAffiliationForm({ ...EMPTY_AFFILIATION });
    }

    if (type === "supplier") {
      setSupplierForm({ ...EMPTY_SUPPLIER });
    }

    if (type === "settings") {
      setSettingsForm(
        companySettings
          ? { ...EMPTY_SETTINGS, ...companySettings }
          : { ...EMPTY_SETTINGS }
      );
    }

    setModal(type);
  };

  const openEdit = (type, record) => {
    setEditingId(record.id);
    setErrorMessage("");

    if (type === "employee") {
      setEmployeeForm({
        ...EMPTY_EMPLOYEE,
        ...record,
        department: record.department || "",
        location: record.location || "",
      });
    }

    if (type === "department") {
      setDepartmentForm({
        ...EMPTY_DEPARTMENT,
        ...record,
        manager: record.manager || "",
      });
    }

    if (type === "location") {
      setLocationForm({
        ...EMPTY_LOCATION,
        ...record,
        parent: record.parent || "",
      });
    }

    if (type === "affiliation") {
      setAffiliationForm({
        ...EMPTY_AFFILIATION,
        ...record,
        employee: record.employee || "",
      });
    }

    if (type === "supplier") {
      setSupplierForm({
        ...EMPTY_SUPPLIER,
        ...record,
      });
    }

    if (type === "settings") {
      setSettingsForm({
        ...EMPTY_SETTINGS,
        ...record,
      });
    }

    setModal(type);
  };

  const closeModal = () => {
    setModal(null);
    setEditingId(null);
  };

  const saveRecord = async (endpoint, data, label) => {
    try {
      if (editingId) {
        await api.patch(`${endpoint}${editingId}/`, data);
      } else {
        await api.post(endpoint, data);
      }

      closeModal();
      await loadCompanyData();

      notifySuccess(
        `${label} ${editingId ? "updated" : "created"} successfully.`
      );
    } catch (error) {
      handleError(error, `Unable to save ${label.toLowerCase()}.`);
    }
  };

  const handleEmployeeSubmit = async (event) => {
    event.preventDefault();

    await saveRecord(
      "/company/employees/",
      {
        ...employeeForm,
        department: employeeForm.department || null,
        location: employeeForm.location || null,
      },
      "Employee"
    );
  };

  const handleDepartmentSubmit = async (event) => {
    event.preventDefault();

    await saveRecord(
      "/company/departments/",
      {
        ...departmentForm,
        manager: departmentForm.manager || null,
      },
      "Department"
    );
  };

  const handleLocationSubmit = async (event) => {
    event.preventDefault();

    await saveRecord(
      "/company/locations/",
      {
        ...locationForm,
        parent: locationForm.parent || null,
      },
      "Location"
    );
  };

  const handleAffiliationSubmit = async (event) => {
    event.preventDefault();

    await saveRecord(
      "/company/employee-affiliations/",
      {
        ...affiliationForm,
        employee: Number(affiliationForm.employee),
      },
      "Module affiliation"
    );
  };

  const handleSupplierSubmit = async (event) => {
    event.preventDefault();

    await saveRecord(
      "/company/suppliers/",
      supplierForm,
      "Supplier"
    );
  };

  const handleSettingsSubmit = async (event) => {
    event.preventDefault();

    try {
      if (companySettings?.id) {
        await api.patch(
          `/company/settings/${companySettings.id}/`,
          settingsForm
        );
      } else {
        await api.post("/company/settings/", settingsForm);
      }

      closeModal();
      await loadCompanyData();
      notifySuccess("Company settings saved successfully.");
    } catch (error) {
      handleError(error, "Unable to save company settings.");
    }
  };

  const deleteRecord = async (endpoint, id, label) => {
    if (
      !window.confirm(
        `Delete this ${label.toLowerCase()}? This action cannot be undone.`
      )
    ) {
      return;
    }

    try {
      await api.delete(`${endpoint}${id}/`);
      await loadCompanyData();
      notifySuccess(`${label} deleted successfully.`);
    } catch (error) {
      handleError(error, `Unable to delete ${label.toLowerCase()}.`);
    }
  };

  const clearFilters = () => {
    setSearch("");
    setStatusFilter("");
    setLocationFilter("");
    setDepartmentFilter("");
    setModuleFilter("");
  };

  const renderEmployeeForm = () => (
    <Modal
      title={editingId ? "Edit Employee" : "Add Employee"}
      onClose={closeModal}
    >
      <form onSubmit={handleEmployeeSubmit}>
        <div className="form-grid">
          <Field label="Employee Number" required>
            <input
              required
              value={employeeForm.employee_number}
              onChange={(e) =>
                setEmployeeForm({
                  ...employeeForm,
                  employee_number: e.target.value,
                })
              }
            />
          </Field>

          <Field label="First Name" required>
            <input
              required
              value={employeeForm.first_name}
              onChange={(e) =>
                setEmployeeForm({
                  ...employeeForm,
                  first_name: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Last Name" required>
            <input
              required
              value={employeeForm.last_name}
              onChange={(e) =>
                setEmployeeForm({
                  ...employeeForm,
                  last_name: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Email">
            <input
              type="email"
              value={employeeForm.email}
              onChange={(e) =>
                setEmployeeForm({
                  ...employeeForm,
                  email: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Phone">
            <input
              value={employeeForm.phone}
              onChange={(e) =>
                setEmployeeForm({
                  ...employeeForm,
                  phone: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Status">
            <select
              value={employeeForm.status}
              onChange={(e) =>
                setEmployeeForm({
                  ...employeeForm,
                  status: e.target.value,
                })
              }
            >
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </Field>

          <Field label="Department">
            <select
              value={employeeForm.department}
              onChange={(e) =>
                setEmployeeForm({
                  ...employeeForm,
                  department: e.target.value,
                })
              }
            >
              <option value="">Select department</option>

              {departments
                .filter((d) => d.is_active)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.department_code} — {d.name}
                  </option>
                ))}
            </select>
          </Field>

          <Field label="Location">
            <select
              value={employeeForm.location}
              onChange={(e) =>
                setEmployeeForm({
                  ...employeeForm,
                  location: e.target.value,
                })
              }
            >
              <option value="">Select location</option>

              {locations
                .filter((l) => l.is_active)
                .map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
            </select>
          </Field>
        </div>

        <FormActions
          onCancel={closeModal}
          submitText={editingId ? "Save Changes" : "Add Employee"}
        />
      </form>
    </Modal>
  );

  const renderDepartmentForm = () => (
    <Modal
      title={editingId ? "Edit Department" : "Add Department"}
      onClose={closeModal}
    >
      <form onSubmit={handleDepartmentSubmit}>
        <div className="form-grid">
          <Field label="Department Code" required>
            <input
              required
              value={departmentForm.department_code}
              onChange={(e) =>
                setDepartmentForm({
                  ...departmentForm,
                  department_code: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Name" required>
            <input
              required
              value={departmentForm.name}
              onChange={(e) =>
                setDepartmentForm({
                  ...departmentForm,
                  name: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Manager">
            <select
              value={departmentForm.manager}
              onChange={(e) =>
                setDepartmentForm({
                  ...departmentForm,
                  manager: e.target.value,
                })
              }
            >
              <option value="">No manager</option>

              {employees
                .filter(
                  (e) =>
                    e.status === "ACTIVE" &&
                    (!departmentForm.department_code ||
                      String(e.department) === String(editingId))
                )
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.employee_number} — {e.first_name} {e.last_name}
                  </option>
                ))}
            </select>
          </Field>

          <Field label="Status">
            <select
              value={departmentForm.is_active ? "true" : "false"}
              onChange={(e) =>
                setDepartmentForm({
                  ...departmentForm,
                  is_active: e.target.value === "true",
                })
              }
            >
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </Field>

          <Field label="Description" full>
            <textarea
              value={departmentForm.description}
              onChange={(e) =>
                setDepartmentForm({
                  ...departmentForm,
                  description: e.target.value,
                })
              }
            />
          </Field>
        </div>

        <FormActions
          onCancel={closeModal}
          submitText={editingId ? "Save Changes" : "Add Department"}
        />
      </form>
    </Modal>
  );

  const renderLocationForm = () => (
    <Modal
      title={editingId ? "Edit Location" : "Add Location"}
      onClose={closeModal}
    >
      <form onSubmit={handleLocationSubmit}>
        <div className="form-grid">
          <Field label="Name" required>
            <input
              required
              value={locationForm.name}
              onChange={(e) =>
                setLocationForm({
                  ...locationForm,
                  name: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Parent Location">
            <select
              value={locationForm.parent}
              onChange={(e) =>
                setLocationForm({
                  ...locationForm,
                  parent: e.target.value,
                })
              }
            >
              <option value="">No parent</option>

              {locations
                .filter(
                  (l) =>
                    l.is_active &&
                    String(l.id) !== String(editingId)
                )
                .map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
            </select>
          </Field>

          <Field label="Status">
            <select
              value={locationForm.is_active ? "true" : "false"}
              onChange={(e) =>
                setLocationForm({
                  ...locationForm,
                  is_active: e.target.value === "true",
                })
              }
            >
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </Field>

          <Field label="Address" full>
            <textarea
              value={locationForm.address}
              onChange={(e) =>
                setLocationForm({
                  ...locationForm,
                  address: e.target.value,
                })
              }
            />
          </Field>
        </div>

        <FormActions
          onCancel={closeModal}
          submitText={editingId ? "Save Changes" : "Add Location"}
        />
      </form>
    </Modal>
  );

  const renderAffiliationForm = () => (
    <Modal
      title={editingId ? "Edit Module Affiliation" : "Assign Module"}
      onClose={closeModal}
    >
      <form onSubmit={handleAffiliationSubmit}>
        <div className="form-grid">
          <Field label="Employee" required full>
            <select
              required
              value={affiliationForm.employee}
              onChange={(e) =>
                setAffiliationForm({
                  ...affiliationForm,
                  employee: e.target.value,
                })
              }
            >
              <option value="">Select employee</option>

              {employees
                .filter((e) => e.status === "ACTIVE")
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.employee_number} — {e.first_name} {e.last_name}
                  </option>
                ))}
            </select>
          </Field>

          <Field label="Module" required>
            <select
              value={affiliationForm.module}
              onChange={(e) =>
                setAffiliationForm({
                  ...affiliationForm,
                  module: e.target.value,
                })
              }
            >
              {MODULES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Function">
            <input
              placeholder="e.g. Driver, Storekeeper"
              value={affiliationForm.function}
              onChange={(e) =>
                setAffiliationForm({
                  ...affiliationForm,
                  function: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Status">
            <select
              value={affiliationForm.is_active ? "true" : "false"}
              onChange={(e) =>
                setAffiliationForm({
                  ...affiliationForm,
                  is_active: e.target.value === "true",
                })
              }
            >
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </Field>
        </div>

        <FormActions
          onCancel={closeModal}
          submitText={editingId ? "Save Changes" : "Assign Module"}
        />
      </form>
    </Modal>
  );

  const renderSupplierForm = () => (
    <Modal
      title={editingId ? "Edit Supplier" : "Add Supplier"}
      onClose={closeModal}
    >
      <form onSubmit={handleSupplierSubmit}>
        <div className="form-grid">
          <Field label="Supplier Code" required>
            <input
              required
              value={supplierForm.supplier_code}
              onChange={(e) =>
                setSupplierForm({
                  ...supplierForm,
                  supplier_code: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Supplier Name" required>
            <input
              required
              value={supplierForm.name}
              onChange={(e) =>
                setSupplierForm({
                  ...supplierForm,
                  name: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Contact Person">
            <input
              value={supplierForm.contact_person}
              onChange={(e) =>
                setSupplierForm({
                  ...supplierForm,
                  contact_person: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Phone">
            <input
              value={supplierForm.phone}
              onChange={(e) =>
                setSupplierForm({
                  ...supplierForm,
                  phone: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Email">
            <input
              type="email"
              value={supplierForm.email}
              onChange={(e) =>
                setSupplierForm({
                  ...supplierForm,
                  email: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Tax Number">
            <input
              value={supplierForm.tax_number}
              onChange={(e) =>
                setSupplierForm({
                  ...supplierForm,
                  tax_number: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Status">
            <select
              value={supplierForm.is_active ? "true" : "false"}
              onChange={(e) =>
                setSupplierForm({
                  ...supplierForm,
                  is_active: e.target.value === "true",
                })
              }
            >
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </Field>

          <Field label="Address" full>
            <textarea
              value={supplierForm.address}
              onChange={(e) =>
                setSupplierForm({
                  ...supplierForm,
                  address: e.target.value,
                })
              }
            />
          </Field>
        </div>

        <FormActions
          onCancel={closeModal}
          submitText={editingId ? "Save Changes" : "Add Supplier"}
        />
      </form>
    </Modal>
  );

  const renderSettingsForm = () => (
    <Modal title="Company Settings" onClose={closeModal}>
      <form onSubmit={handleSettingsSubmit}>
        <div className="form-grid">
          <Field label="Company Name" required>
            <input
              required
              value={settingsForm.company_name}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  company_name: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Company Code" required>
            <input
              required
              value={settingsForm.company_code}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  company_code: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Currency" required>
            <input
              maxLength={3}
              required
              value={settingsForm.currency_code}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  currency_code: e.target.value.toUpperCase(),
                })
              }
            />
          </Field>

          <Field label="Timezone" required>
            <input
              required
              value={settingsForm.timezone}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  timezone: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Phone">
            <input
              value={settingsForm.phone}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  phone: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Email">
            <input
              type="email"
              value={settingsForm.email}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  email: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Fiscal Year Start">
            <input
              type="date"
              value={settingsForm.fiscal_year_start || ""}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  fiscal_year_start: e.target.value || null,
                })
              }
            />
          </Field>

          <Field label="Logo Path">
            <input
              value={settingsForm.logo_path}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  logo_path: e.target.value,
                })
              }
            />
          </Field>

          <Field label="Address" full>
            <textarea
              value={settingsForm.address}
              onChange={(e) =>
                setSettingsForm({
                  ...settingsForm,
                  address: e.target.value,
                })
              }
            />
          </Field>
        </div>

        <FormActions onCancel={closeModal} submitText="Save Settings" />
      </form>
    </Modal>
  );

  const renderEmployees = () => (
    <SectionHeader
      title="Employees"
      description="Operational employees and their company affiliations."
      action={
        <button
          className="primary-button"
          onClick={() => openCreate("employee")}
        >
          <Plus size={17} />
          Add Employee
        </button>
      }
    >
      <div className="company-table-wrapper">
        <table className="company-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Department</th>
              <th>Location</th>
              <th>Modules</th>
              <th>Phone</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {filteredEmployees.map((employee) => (
              <tr key={employee.id}>
                <td>
                  <strong>
                    {employee.first_name} {employee.last_name}
                  </strong>
                  <span className="table-secondary">
                    {employee.employee_number}
                  </span>
                </td>

                <td>
                  {employee.department_name ||
                    getDepartmentName(employee.department)}
                </td>

                <td>
                  {employee.location_name ||
                    getLocationName(employee.location)}
                </td>

                <td>
                  <div className="tag-list">
                    {(employee.active_affiliations || []).map((module) => (
                      <span key={module} className="module-tag">
                        {getModuleLabel(module)}
                      </span>
                    ))}
                  </div>
                </td>

                <td>{employee.phone || "—"}</td>

                <td>
                  <StatusBadge
                    active={employee.status === "ACTIVE"}
                    label={employee.status}
                  />
                </td>

                <td>
                  <Actions
                    onEdit={() => openEdit("employee", employee)}
                    onDelete={() =>
                      deleteRecord(
                        "/company/employees/",
                        employee.id,
                        "Employee"
                      )
                    }
                  />
                </td>
              </tr>
            ))}

            {!filteredEmployees.length && (
              <EmptyRow colSpan={7} text="No employees found." />
            )}
          </tbody>
        </table>
      </div>
    </SectionHeader>
  );

  const renderDepartments = () => (
    <SectionHeader
      title="Departments"
      description="Operational departments within the company."
      action={
        <button
          className="primary-button"
          onClick={() => openCreate("department")}
        >
          <Plus size={17} />
          Add Department
        </button>
      }
    >
      <TableSearchHint text="Use the search bar above to find a department." />

      <div className="company-table-wrapper">
        <table className="company-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Department</th>
              <th>Manager</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {filteredDepartments.map((department) => (
              <tr key={department.id}>
                <td>{department.department_code}</td>

                <td>
                  <strong>{department.name}</strong>

                  {department.description && (
                    <span className="table-secondary">
                      {department.description}
                    </span>
                  )}
                </td>

                <td>
                  {department.manager_name ||
                    getEmployeeName(department.manager)}
                </td>

                <td>
                  <StatusBadge
                    active={department.is_active}
                    label={department.is_active ? "ACTIVE" : "INACTIVE"}
                  />
                </td>

                <td>
                  <Actions
                    onEdit={() => openEdit("department", department)}
                    onDelete={() =>
                      deleteRecord(
                        "/company/departments/",
                        department.id,
                        "Department"
                      )
                    }
                  />
                </td>
              </tr>
            ))}

            {!filteredDepartments.length && (
              <EmptyRow colSpan={5} text="No departments found." />
            )}
          </tbody>
        </table>
      </div>
    </SectionHeader>
  );

  const renderLocations = () => (
    <SectionHeader
      title="Locations / Stores"
      description="Company operating locations used by Assets, Inventory, Fleet and Employees."
      action={
        <button
          className="primary-button"
          onClick={() => openCreate("location")}
        >
          <Plus size={17} />
          Add Location
        </button>
      }
    >
      <div className="company-table-wrapper">
        <table className="company-table">
          <thead>
            <tr>
              <th>Location</th>
              <th>Parent</th>
              <th>Address</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {filteredLocations.map((location) => (
              <tr key={location.id}>
                <td>
                  <strong>{location.name}</strong>
                </td>

                <td>
                  {location.parent_name ||
                    getLocationName(location.parent)}
                </td>

                <td>{location.address || "—"}</td>

                <td>
                  <StatusBadge
                    active={location.is_active}
                    label={location.is_active ? "ACTIVE" : "INACTIVE"}
                  />
                </td>

                <td>
                  <Actions
                    onEdit={() => openEdit("location", location)}
                    onDelete={() =>
                      deleteRecord(
                        "/company/locations/",
                        location.id,
                        "Location"
                      )
                    }
                  />
                </td>
              </tr>
            ))}

            {!filteredLocations.length && (
              <EmptyRow colSpan={5} text="No locations found." />
            )}
          </tbody>
        </table>
      </div>
    </SectionHeader>
  );

  const renderAffiliations = () => (
    <SectionHeader
      title="Module Affiliations"
      description="Connect employees to the operational modules they support."
      action={
        <button
          className="primary-button"
          onClick={() => openCreate("affiliation")}
        >
          <Plus size={17} />
          Assign Module
        </button>
      }
    >
      <div className="company-table-wrapper">
        <table className="company-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Module</th>
              <th>Function</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {filteredAffiliations.map((item) => (
              <tr key={item.id}>
                <td>
                  <strong>
                    {item.employee_name ||
                      getEmployeeName(item.employee)}
                  </strong>
                </td>

                <td>
                  <span className="module-tag">
                    {item.module_label || getModuleLabel(item.module)}
                  </span>
                </td>

                <td>{item.function || "—"}</td>

                <td>
                  <StatusBadge
                    active={item.is_active}
                    label={item.is_active ? "ACTIVE" : "INACTIVE"}
                  />
                </td>

                <td>
                  <Actions
                    onEdit={() => openEdit("affiliation", item)}
                    onDelete={() =>
                      deleteRecord(
                        "/company/employee-affiliations/",
                        item.id,
                        "Module affiliation"
                      )
                    }
                  />
                </td>
              </tr>
            ))}

            {!filteredAffiliations.length && (
              <EmptyRow colSpan={5} text="No module affiliations found." />
            )}
          </tbody>
        </table>
      </div>
    </SectionHeader>
  );

  const renderSuppliers = () => (
    <SectionHeader
      title="Suppliers"
      description="Supplier master records used by Procurement, Assets, Inventory and Finance."
      action={
        <button
          className="primary-button"
          onClick={() => openCreate("supplier")}
        >
          <Plus size={17} />
          Add Supplier
        </button>
      }
    >
      <div className="company-table-wrapper">
        <table className="company-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Supplier</th>
              <th>Contact</th>
              <th>Phone</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {filteredSuppliers.map((supplier) => (
              <tr key={supplier.id}>
                <td>{supplier.supplier_code}</td>

                <td>
                  <strong>{supplier.name}</strong>
                  <span className="table-secondary">
                    {supplier.email || "No email"}
                  </span>
                </td>

                <td>{supplier.contact_person || "—"}</td>
                <td>{supplier.phone || "—"}</td>

                <td>
                  <StatusBadge
                    active={supplier.is_active}
                    label={supplier.is_active ? "ACTIVE" : "INACTIVE"}
                  />
                </td>

                <td>
                  <Actions
                    onEdit={() => openEdit("supplier", supplier)}
                    onDelete={() =>
                      deleteRecord(
                        "/company/suppliers/",
                        supplier.id,
                        "Supplier"
                      )
                    }
                  />
                </td>
              </tr>
            ))}

            {!filteredSuppliers.length && (
              <EmptyRow colSpan={6} text="No suppliers found." />
            )}
          </tbody>
        </table>
      </div>
    </SectionHeader>
  );

  const renderSettings = () => (
    <SectionHeader
      title="Company Settings"
      description="Basic company configuration used across the system."
      action={
        <button
          className="primary-button"
          onClick={() => openCreate("settings")}
        >
          <Pencil size={16} />
          {companySettings ? "Edit Settings" : "Configure Company"}
        </button>
      }
    >
      {companySettings ? (
        <div className="company-settings-card">
          <SettingItem
            label="Company Name"
            value={companySettings.company_name}
          />
          <SettingItem
            label="Company Code"
            value={companySettings.company_code}
          />
          <SettingItem
            label="Currency"
            value={companySettings.currency_code}
          />
          <SettingItem
            label="Timezone"
            value={companySettings.timezone}
          />
          <SettingItem
            label="Phone"
            value={companySettings.phone || "—"}
          />
          <SettingItem
            label="Email"
            value={companySettings.email || "—"}
          />
          <SettingItem
            label="Fiscal Year Start"
            value={companySettings.fiscal_year_start || "—"}
          />
          <SettingItem
            label="Address"
            value={companySettings.address || "—"}
          />
        </div>
      ) : (
        <div className="empty-state">
          <Building2 size={40} />
          <h3>No company settings</h3>
          <p>Configure the company's basic information.</p>
        </div>
      )}
    </SectionHeader>
  );

  const tabs = [
    ["employees", Users, "Employees"],
    ["departments", Building2, "Departments"],
    ["locations", MapPin, "Locations / Stores"],
    ["affiliations", UserRound, "Affiliations"],
    ["suppliers", Truck, "Suppliers"],
    ["settings", Building2, "Settings"],
  ];

  return (
    <div className="company-page">
      <div className="page-heading">
        <div>
          <p className="breadcrumb">Home / Company</p>
          <h1>Company</h1>
          <p className="subtitle">
            Manage the master data used across the company management system.
          </p>
        </div>

        <button
          className="dashboard-refresh"
          onClick={loadCompanyData}
          disabled={loading}
        >
          <RefreshCw
            size={17}
            className={loading ? "dashboard-spinner" : ""}
          />
          Refresh
        </button>
      </div>

      {errorMessage && (
        <div className="company-error">
          <AlertTriangle size={20} />

          <div>
            <strong>Unable to complete request</strong>
            <p>{errorMessage}</p>
          </div>

          <button onClick={() => setErrorMessage("")}>
            <X size={17} />
          </button>
        </div>
      )}

      {successMessage && (
        <div className="company-success">{successMessage}</div>
      )}

      <div className="company-summary-grid">
        <SummaryCard icon={Users} label="Employees" value={employees.length} />
        <SummaryCard
          icon={Building2}
          label="Departments"
          value={departments.length}
        />
        <SummaryCard
          icon={MapPin}
          label="Locations"
          value={locations.length}
        />
        <SummaryCard
          icon={Truck}
          label="Suppliers"
          value={suppliers.length}
        />
      </div>

      <div className="company-card">
        <div className="company-tabs">
          {tabs.map(([key, Icon, label]) => (
            <button
              key={key}
              className={activeTab === key ? "active" : ""}
              onClick={() => {
                setActiveTab(key);
                clearFilters();
              }}
            >
              <Icon size={17} />
              {label}
            </button>
          ))}
        </div>

        <div className="company-toolbar">
          <div className="company-search">
            <Search size={17} />

            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`Search ${activeTab}...`}
            />
          </div>

          {activeTab === "employees" && (
            <>
              <select
                value={locationFilter}
                onChange={(e) => setLocationFilter(e.target.value)}
              >
                <option value="">All locations</option>

                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>

              <select
                value={departmentFilter}
                onChange={(e) => setDepartmentFilter(e.target.value)}
              >
                <option value="">All departments</option>

                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>

              <select
                value={moduleFilter}
                onChange={(e) => setModuleFilter(e.target.value)}
              >
                <option value="">All modules</option>

                {MODULES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </>
          )}

          {(search ||
            statusFilter ||
            locationFilter ||
            departmentFilter ||
            moduleFilter) && (
            <button
              className="secondary-button clear-button"
              onClick={clearFilters}
            >
              Clear
            </button>
          )}
        </div>

        <div className="company-content">
          {activeTab === "employees" && renderEmployees()}
          {activeTab === "departments" && renderDepartments()}
          {activeTab === "locations" && renderLocations()}
          {activeTab === "affiliations" && renderAffiliations()}
          {activeTab === "suppliers" && renderSuppliers()}
          {activeTab === "settings" && renderSettings()}
        </div>
      </div>

      {modal === "employee" && renderEmployeeForm()}
      {modal === "department" && renderDepartmentForm()}
      {modal === "location" && renderLocationForm()}
      {modal === "affiliation" && renderAffiliationForm()}
      {modal === "supplier" && renderSupplierForm()}
      {modal === "settings" && renderSettingsForm()}
    </div>
  );
}

function Modal({ title, onClose, children }) {
  return (
    <div
      className="company-modal-overlay"
      onMouseDown={(e) =>
        e.target === e.currentTarget && onClose()
      }
    >
      <div className="company-modal">
        <div className="company-modal-header">
          <div>
            <h2>{title}</h2>
            <p>Enter the required information below.</p>
          </div>

          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="company-modal-body">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, required, full, children }) {
  return (
    <div className={`form-group ${full ? "full-width" : ""}`}>
      <label>
        {label}
        {required ? " *" : ""}
      </label>

      {children}
    </div>
  );
}

function FormActions({ onCancel, submitText }) {
  return (
    <div className="modal-actions">
      <button
        type="button"
        className="secondary-button"
        onClick={onCancel}
      >
        Cancel
      </button>

      <button type="submit" className="primary-button">
        {submitText}
      </button>
    </div>
  );
}

function SectionHeader({ title, description, action, children }) {
  return (
    <>
      <div className="company-section-header">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>

        {action}
      </div>

      {children}
    </>
  );
}

function SummaryCard({ icon: Icon, label, value }) {
  return (
    <div className="company-summary-card">
      <Icon size={22} />

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function SettingItem({ label, value }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({ active, label }) {
  return (
    <span
      className={`status-badge ${
        active ? "status-active" : "status-inactive"
      }`}
    >
      {label}
    </span>
  );
}

function Actions({ onEdit, onDelete }) {
  return (
    <div className="table-actions">
      <button
        className="icon-button"
        title="Edit"
        onClick={onEdit}
      >
        <Pencil size={15} />
      </button>

      <button
        className="icon-button danger"
        title="Delete"
        onClick={onDelete}
      >
        <Trash2 size={15} />
      </button>
    </div>
  );
}

function EmptyRow({ colSpan, text }) {
  return (
    <tr>
      <td colSpan={colSpan} className="empty-table">
        {text}
      </td>
    </tr>
  );
}

function TableSearchHint({ text }) {
  return <div className="table-hint">{text}</div>;
}

export default Company;