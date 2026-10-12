
import { useEffect, useMemo, useState } from "react";
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  X,
  Package,
  RefreshCw,
  FileSpreadsheet,
  Eye,
  ChevronDown,
  ChevronRight,
  Upload,
  ClipboardCheck,
  ArrowRightLeft,
  History,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";

import api from "../services/api";
import "./Inventory.css";

const emptyItemForm = {
  name: "",
  category: "",
  brand: "",
  model_number: "",
  supplier: "",
  unit: "",
  reorder_level: 0,
  minimum_stock: 0,
  is_active: true,
  description: "",
  specifications: "",
};

const emptyUnitForm = {
  serial_number: "",
  item: "",
  status: "IN_STOCK",
  condition: "GOOD",
  location: "",
  assigned_to: "",
  purchase_price: "",
  purchase_date: "",
  warranty_expiry: "",
  specifications: "",
};

function Inventory() {
  const [activeTab, setActiveTab] = useState("items");

  const [items, setItems] = useState([]);
  const [units, setUnits] = useState([]);
  const [categories, setCategories] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [locations, setLocations] = useState([]);

  const [loading, setLoading] = useState(true);
  const [unitsLoading, setUnitsLoading] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [brandFilter, setBrandFilter] = useState("");
  const [stockStatusFilter, setStockStatusFilter] = useState("");

  const [unitSearch, setUnitSearch] = useState("");
  const [unitStatusFilter, setUnitStatusFilter] = useState("");
  const [unitConditionFilter, setUnitConditionFilter] = useState("");
  const [unitLocationFilter, setUnitLocationFilter] = useState("");

  const [showItemModal, setShowItemModal] = useState(false);
  const [showUnitModal, setShowUnitModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  const [editingItem, setEditingItem] = useState(null);
  const [editingUnit, setEditingUnit] = useState(null);

  const [itemForm, setItemForm] = useState(emptyItemForm);
  const [unitForm, setUnitForm] = useState(emptyUnitForm);

  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);

  const [selectedItem, setSelectedItem] = useState(null);
  const [expandedItems, setExpandedItems] = useState({});

  const [importFile, setImportFile] = useState(null);
  const [importResult, setImportResult] = useState(null);

  // Physical stocktaking
  const [stocktakes, setStocktakes] = useState([]);
  const [stocktakeLoading, setStocktakeLoading] = useState(false);
  const [showStocktakeCreateModal, setShowStocktakeCreateModal] = useState(false);
  const [selectedStocktake, setSelectedStocktake] = useState(null);
  const [stocktakeLines, setStocktakeLines] = useState([]);
  const [stocktakeItemSearch, setStocktakeItemSearch] = useState("");
  const [stocktakeForm, setStocktakeForm] = useState({
    reference: "",
    location: "",
    notes: "",
    item_ids: [],
  });
  const [countValues, setCountValues] = useState({});
  const [showCountModal, setShowCountModal] = useState(false);
  const [confirmingStocktake, setConfirmingStocktake] = useState(false);

  // Stock management
  const [stockSection, setStockSection] = useState("opening");
  const [transactions, setTransactions] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [stockLoading, setStockLoading] = useState(false);
  const [showOpeningStockModal, setShowOpeningStockModal] = useState(false);
  const [showTransactionModal, setShowTransactionModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showOpeningImportModal, setShowOpeningImportModal] = useState(false);
  const [openingStockFile, setOpeningStockFile] = useState(null);
  const [openingImporting, setOpeningImporting] = useState(false);
  const [openingImportResult, setOpeningImportResult] = useState(null);

  const [openingForm, setOpeningForm] = useState({
    item: "",
    quantity: "",
    location: "",
    reference: "",
    notes: "",
  });

  const [transactionForm, setTransactionForm] = useState({
    item: "",
    transaction_type: "RECEIVED",
    quantity: "",
    location: "",
    employee: "",
    reference: "",
    notes: "",
  });

  const [transferForm, setTransferForm] = useState({
    item: "",
    quantity: "",
    source_location: "",
    destination_location: "",
    reference: "",
    notes: "",
  });

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (activeTab === "units") {
      loadUnits();
    }
  }, [activeTab]);

  async function loadInitialData() {
    setLoading(true);
    setError("");

    try {
      const [itemsResponse, categoriesResponse, employeesResponse, locationsResponse] =
        await Promise.all([
          api.get("/inventory/items/"),
          api.get("/inventory/categories/"),
          api.get("/company/employees/"),
          api.get("/company/locations/"),
        ]);

      setItems(normalizeResults(itemsResponse.data));
      setCategories(normalizeResults(categoriesResponse.data));
      setEmployees(normalizeResults(employeesResponse.data));
      setLocations(normalizeResults(locationsResponse.data));
      await loadStocktakes();
    } catch (err) {
      console.error("Failed to load inventory data:", err);
      setError(getErrorMessage(err, "Failed to load inventory data."));
    } finally {
      setLoading(false);
    }
  }

  async function loadUnits(itemId = null) {
    setUnitsLoading(true);

    try {
      let url = "/inventory/units/";

      if (itemId) {
        url += `?item=${itemId}`;
      }

      const response = await api.get(url);
      setUnits(normalizeResults(response.data));
    } catch (err) {
      console.error("Failed to load inventory units:", err);
      setError(getErrorMessage(err, "Failed to load physical units."));
    } finally {
      setUnitsLoading(false);
    }
  }

  async function loadStocktakes() {
    setStocktakeLoading(true);

    try {
      const response = await api.get("/inventory/stocktakes/");
      setStocktakes(normalizeResults(response.data));
    } catch (err) {
      console.error("Failed to load stocktakes:", err);
      setError(getErrorMessage(err, "Failed to load physical stocktakes."));
    } finally {
      setStocktakeLoading(false);
    }
  }

  async function loadStockSection(section = stockSection) {
    setStockLoading(true);
    setError("");

    try {
      if (section === "transactions") {
        const response = await api.get("/inventory/transactions/");
        setTransactions(normalizeResults(response.data));
      } else if (section === "transfers") {
        const response = await api.get("/inventory/transfers/");
        setTransfers(normalizeResults(response.data));
      }
    } catch (err) {
      console.error("Failed to load stock data:", err);
      setError(getErrorMessage(err, "Failed to load stock data."));
    } finally {
      setStockLoading(false);
    }
  }

  useEffect(() => {
    if (activeTab === "stock") {
      loadStockSection(stockSection);
    }
  }, [activeTab, stockSection]);

  function getItemName(itemId) {
    if (!itemId) return "—";

    const item = items.find(
      (itemRecord) => String(itemRecord.id) === String(itemId)
    );

    if (!item) return itemId;

    return `${item.item_code || ""}${item.item_code ? " — " : ""}${item.name || "Unnamed item"}`;
  }

  function getUserDisplayName(userId) {
    if (!userId) return "—";
    return userId;
  }

  function resetOpeningForm() {
    setOpeningForm({
      item: "",
      quantity: "",
      location: "",
      reference: "",
      notes: "",
    });
  }

  function resetTransactionForm() {
    setTransactionForm({
      item: "",
      transaction_type: "RECEIVED",
      quantity: "",
      location: "",
      employee: "",
      reference: "",
      notes: "",
    });
  }

  function resetTransferForm() {
    setTransferForm({
      item: "",
      quantity: "",
      source_location: "",
      destination_location: "",
      reference: "",
      notes: "",
    });
  }

  function openOpeningStockModal() {
    resetOpeningForm();
    setShowOpeningStockModal(true);
  }

  function openTransactionModal() {
    resetTransactionForm();
    setShowTransactionModal(true);
  }

  function openTransferModal() {
    resetTransferForm();
    setShowTransferModal(true);
  }

  async function saveOpeningStock(event) {
    event.preventDefault();

    if (!openingForm.item || !openingForm.quantity || Number(openingForm.quantity) <= 0) {
      setError("Select an item and enter a quantity greater than zero.");
      return;
    }

    setStockLoading(true);
    setError("");

    try {
      await api.post("/inventory/transactions/", {
        item: openingForm.item,
        transaction_type: "RECEIVED",
        quantity: Number(openingForm.quantity),
        location: openingForm.location || null,
        reference: openingForm.reference.trim() || "OPENING-STOCK",
        notes: openingForm.notes.trim(),
      });

      setShowOpeningStockModal(false);
      resetOpeningForm();
      await loadInitialData();
      if (stockSection === "transactions") {
        await loadStockSection("transactions");
      }
    } catch (err) {
      console.error("Failed to save opening stock:", err);
      setError(getErrorMessage(err, "Failed to save opening stock."));
    } finally {
      setStockLoading(false);
    }
  }

  async function saveTransaction(event) {
    event.preventDefault();

    if (!transactionForm.item || !transactionForm.quantity || Number(transactionForm.quantity) <= 0) {
      setError("Select an item and enter a quantity greater than zero.");
      return;
    }

    setStockLoading(true);
    setError("");

    try {
      const payload = {
        item: transactionForm.item,
        transaction_type: transactionForm.transaction_type,
        quantity: Number(transactionForm.quantity),
        reference: transactionForm.reference.trim(),
        notes: transactionForm.notes.trim(),
      };

      if (transactionForm.location) payload.location = transactionForm.location;
      if (transactionForm.employee) payload.employee = transactionForm.employee;

      await api.post("/inventory/transactions/", payload);

      setShowTransactionModal(false);
      resetTransactionForm();
      await loadInitialData();
      await loadStockSection("transactions");
    } catch (err) {
      console.error("Failed to save stock transaction:", err);
      setError(getErrorMessage(err, "Failed to save stock transaction."));
    } finally {
      setStockLoading(false);
    }
  }

  async function saveTransfer(event) {
    event.preventDefault();

    if (
      !transferForm.item ||
      !transferForm.quantity ||
      Number(transferForm.quantity) <= 0 ||
      !transferForm.source_location ||
      !transferForm.destination_location
    ) {
      setError("Item, quantity, source location and destination location are required.");
      return;
    }

    if (String(transferForm.source_location) === String(transferForm.destination_location)) {
      setError("Source and destination locations must be different.");
      return;
    }

    setStockLoading(true);
    setError("");

    try {
      await api.post("/inventory/transfers/", {
        item: transferForm.item,
        quantity: Number(transferForm.quantity),
        source_location: transferForm.source_location,
        destination_location: transferForm.destination_location,
        reference: transferForm.reference.trim(),
        notes: transferForm.notes.trim(),
      });

      setShowTransferModal(false);
      resetTransferForm();
      await loadInitialData();
      await loadStockSection("transfers");
    } catch (err) {
      console.error("Failed to save stock transfer:", err);
      setError(getErrorMessage(err, "Failed to save stock transfer."));
    } finally {
      setStockLoading(false);
    }
  }

  async function handleOpeningStockImport(event) {
    event.preventDefault();

    if (!openingStockFile) {
      setError("Please select an Excel file.");
      return;
    }

    setOpeningImporting(true);
    setError("");
    setOpeningImportResult(null);

    try {
      const formData = new FormData();
      formData.append("file", openingStockFile);
      formData.append("module", "INVENTORY");
      formData.append("import_type", "OPENING_STOCK");

      const response = await api.post(
        "/inventory/transactions/import-opening-stock/",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const batchId = response.data?.batch_id || response.data?.id;

      if (batchId) {
        await api.post(
          `/inventory/transactions/import-opening-stock/${batchId}/confirm/`
        );
      }

      setOpeningImportResult({
        success: true,
        data: response.data,
      });

      setOpeningStockFile(null);
      await loadInitialData();
      if (stockSection === "transactions") {
        await loadStockSection("transactions");
      }
    } catch (err) {
      console.error("Opening stock import failed:", err);

      setOpeningImportResult({
        success: false,
        data: err?.response?.data,
      });

      setError(
        getErrorMessage(
          err,
          "Opening stock import failed. Please review the spreadsheet."
        )
      );
    } finally {
      setOpeningImporting(false);
    }
  }

  function closeOpeningImportModal() {
    if (openingImporting) return;
    setShowOpeningImportModal(false);
    setOpeningStockFile(null);
    setOpeningImportResult(null);
  }

  function normalizeResults(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.results)) return data.results;
    return [];
  }

  function getErrorMessage(err, fallback) {
    return (
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err?.userMessage ||
      fallback
    );
  }

  function getCategoryName(categoryId) {
    if (!categoryId) return "—";

    const category = categories.find(
      (categoryItem) =>
        String(categoryItem.id) === String(categoryId)
    );

    return category?.name || category?.category_name || categoryId;
  }

  function getEmployeeName(employeeId) {
    if (!employeeId) return "Unassigned";

    const employee = employees.find(
      (employeeItem) =>
        String(employeeItem.id) === String(employeeId)
    );

    if (!employee) return employeeId;

    return (
      employee.full_name ||
      employee.name ||
      `${employee.first_name || ""} ${employee.last_name || ""}`.trim() ||
      employee.employee_code ||
      employee.id
    );
  }

  function getLocationName(locationId) {
    if (!locationId) return "—";

    const location = locations.find(
      (locationItem) =>
        String(locationItem.id) === String(locationId)
    );

    return location?.name || location?.location_name || locationId;
  }

  function getStockClass(status) {
    const value = String(status || "").toLowerCase();

    if (value.includes("out")) return "stock-out";
    if (value.includes("low")) return "stock-low";
    if (value.includes("good") || value.includes("normal")) {
      return "stock-good";
    }

    return "stock-normal";
  }

  function getStockLabel(item) {
    if (item.stock_status) {
      return String(item.stock_status).replaceAll("_", " ");
    }

    const stock = Number(item.current_stock || 0);
    const minimum = Number(item.minimum_stock || 0);
    const reorder = Number(item.reorder_level || 0);

    if (stock <= 0) return "Out of Stock";
    if (stock <= minimum || stock <= reorder) return "Low Stock";

    return "In Stock";
  }

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const searchValue = search.trim().toLowerCase();

      const matchesSearch =
        !searchValue ||
        String(item.item_code || "").toLowerCase().includes(searchValue) ||
        String(item.name || "").toLowerCase().includes(searchValue) ||
        String(item.brand || "").toLowerCase().includes(searchValue) ||
        String(item.model_number || "").toLowerCase().includes(searchValue);

      const matchesCategory =
        !categoryFilter ||
        String(item.category) === String(categoryFilter);

      const matchesBrand =
        !brandFilter ||
        String(item.brand || "")
          .toLowerCase()
          .includes(brandFilter.toLowerCase());

      const matchesStockStatus =
        !stockStatusFilter ||
        getStockLabel(item).toLowerCase() ===
          stockStatusFilter.toLowerCase();

      return (
        matchesSearch &&
        matchesCategory &&
        matchesBrand &&
        matchesStockStatus
      );
    });
  }, [
    items,
    search,
    categoryFilter,
    brandFilter,
    stockStatusFilter,
  ]);

  const filteredUnits = useMemo(() => {
    return units.filter((unit) => {
      const searchValue = unitSearch.trim().toLowerCase();

      const item = items.find(
        (itemRecord) =>
          String(itemRecord.id) === String(unit.item)
      );

      const matchesSearch =
        !searchValue ||
        String(unit.serial_number || "")
          .toLowerCase()
          .includes(searchValue) ||
        String(item?.name || "")
          .toLowerCase()
          .includes(searchValue) ||
        String(item?.brand || "")
          .toLowerCase()
          .includes(searchValue) ||
        String(item?.model_number || "")
          .toLowerCase()
          .includes(searchValue);

      const matchesStatus =
        !unitStatusFilter ||
        String(unit.status) === unitStatusFilter;

      const matchesCondition =
        !unitConditionFilter ||
        String(unit.condition) === unitConditionFilter;

      const matchesLocation =
        !unitLocationFilter ||
        String(unit.location) === unitLocationFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesCondition &&
        matchesLocation
      );
    });
  }, [
    units,
    items,
    unitSearch,
    unitStatusFilter,
    unitConditionFilter,
    unitLocationFilter,
  ]);

  function openAddItem() {
    setEditingItem(null);
    setItemForm(emptyItemForm);
    setShowItemModal(true);
  }

  function openEditItem(item) {
    setEditingItem(item);

    setItemForm({
      name: item.name || "",
      category: item.category || "",
      brand: item.brand || "",
      model_number: item.model_number || "",
      supplier: item.supplier || "",
      unit: item.unit || "",
      reorder_level: item.reorder_level ?? 0,
      minimum_stock: item.minimum_stock ?? 0,
      is_active:
        item.is_active === undefined ? true : item.is_active,
      description: item.description || "",
      specifications:
        typeof item.specifications === "object"
          ? JSON.stringify(item.specifications, null, 2)
          : item.specifications || "",
    });

    setShowItemModal(true);
  }

  function closeItemModal() {
    if (saving) return;

    setShowItemModal(false);
    setEditingItem(null);
    setItemForm(emptyItemForm);
  }

  async function saveItem(event) {
    event.preventDefault();

    if (!itemForm.name.trim()) {
      setError("Item name is required.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const payload = {
        ...itemForm,
        name: itemForm.name.trim(),
        specifications: parseSpecifications(itemForm.specifications),
      };

      // Item codes are generated automatically by the backend.
      // Never send item_code from the client. Existing item codes remain unchanged.

      if (!payload.category) delete payload.category;
      if (!payload.supplier) delete payload.supplier;

      if (editingItem) {
        await api.patch(`/inventory/items/${editingItem.id}/`, payload);
      } else {
        await api.post("/inventory/items/", payload);
      }

      closeItemModal();
      await loadInitialData();
    } catch (err) {
      console.error("Failed to save item:", err);
      setError(getErrorMessage(err, "Failed to save inventory item."));
    } finally {
      setSaving(false);
    }
  }

  async function deleteItem(item) {
    const confirmed = window.confirm(
      `Delete "${item.name}" (${item.item_code})?\n\nThis action cannot be undone.`
    );

    if (!confirmed) return;

    setError("");

    try {
      await api.delete(`/inventory/items/${item.id}/`);
      await loadInitialData();
    } catch (err) {
      console.error("Failed to delete item:", err);
      setError(getErrorMessage(err, "Failed to delete inventory item."));
    }
  }

  function parseSpecifications(value) {
    if (!value || !String(value).trim()) {
      return {};
    }

    try {
      return JSON.parse(value);
    } catch {
      return {
        notes: String(value),
      };
    }
  }

  function toggleItem(item) {
    const itemId = String(item.id);

    setExpandedItems((current) => ({
      ...current,
      [itemId]: !current[itemId],
    }));

    if (!expandedItems[itemId]) {
      loadUnits(item.id);
    }
  }

  function openAddUnit(item = null) {
    setEditingUnit(null);

    setUnitForm({
      ...emptyUnitForm,
      item: item?.id || "",
    });

    setShowUnitModal(true);
  }

  function openEditUnit(unit) {
    setEditingUnit(unit);

    setUnitForm({
      serial_number: unit.serial_number || "",
      item: unit.item || "",
      status: unit.status || "IN_STOCK",
      condition: unit.condition || "GOOD",
      location: unit.location || "",
      assigned_to: unit.assigned_to || "",
      purchase_price: unit.purchase_price ?? "",
      purchase_date: unit.purchase_date || "",
      warranty_expiry: unit.warranty_expiry || "",
      specifications:
        typeof unit.specifications === "object"
          ? JSON.stringify(unit.specifications, null, 2)
          : unit.specifications || "",
    });

    setShowUnitModal(true);
  }

  function closeUnitModal() {
    if (saving) return;

    setShowUnitModal(false);
    setEditingUnit(null);
    setUnitForm(emptyUnitForm);
  }

  async function saveUnit(event) {
    event.preventDefault();

    if (!unitForm.item) {
      setError("Please select an inventory item.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const payload = {
        ...unitForm,
        specifications: parseSpecifications(unitForm.specifications),
      };

      if (!payload.location) delete payload.location;
      if (!payload.assigned_to) delete payload.assigned_to;
      if (!payload.purchase_price) delete payload.purchase_price;
      if (!payload.purchase_date) delete payload.purchase_date;
      if (!payload.warranty_expiry) delete payload.warranty_expiry;

      if (editingUnit) {
        await api.patch(
          `/inventory/units/${editingUnit.id}/`,
          payload
        );
      } else {
        await api.post("/inventory/units/", payload);
      }

      closeUnitModal();
      await loadUnits();
      await loadInitialData();
    } catch (err) {
      console.error("Failed to save physical unit:", err);
      setError(
        getErrorMessage(err, "Failed to save physical inventory unit.")
      );
    } finally {
      setSaving(false);
    }
  }

  async function deleteUnit(unit) {
    const confirmed = window.confirm(
      `Delete physical unit "${unit.serial_number || unit.id}"?`
    );

    if (!confirmed) return;

    setError("");

    try {
      await api.delete(`/inventory/units/${unit.id}/`);
      await loadUnits();
      await loadInitialData();
    } catch (err) {
      console.error("Failed to delete unit:", err);
      setError(getErrorMessage(err, "Failed to delete physical unit."));
    }
  }

  async function handleImport(event) {
    event.preventDefault();

    if (!importFile) {
      setError("Please select an Excel file.");
      return;
    }

    setImporting(true);
    setError("");
    setImportResult(null);

    try {
      const formData = new FormData();

      formData.append("file", importFile);
      formData.append("module", "INVENTORY");
      formData.append("import_type", "ITEMS");

      const response = await api.post(
        "/inventory/items/import/",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setImportResult({
        success: true,
        data: response.data,
      });

      setImportFile(null);
      await loadInitialData();
    } catch (err) {
      console.error("Inventory import failed:", err);

      setImportResult({
        success: false,
        data: err?.response?.data,
      });

      setError(
        getErrorMessage(
          err,
          "Import failed. Please check the Excel file."
        )
      );
    } finally {
      setImporting(false);
    }
  }

  function closeImportModal() {
    if (importing) return;

    setShowImportModal(false);
    setImportFile(null);
    setImportResult(null);
  }

  function getUnitItem(unit) {
    return items.find(
      (item) => String(item.id) === String(unit.item)
    );
  }

  function getUnitSpecification(unit) {
    if (!unit.specifications) return "—";

    if (typeof unit.specifications === "string") {
      return unit.specifications;
    }

    return Object.entries(unit.specifications)
      .map(([key, value]) => `${key}: ${value}`)
      .join(" • ");
  }

  const filteredStocktakeItems = useMemo(() => {
    const query = stocktakeItemSearch.trim().toLowerCase();

    return items.filter((item) => {
      if (!query) return true;

      return [
        item.item_code,
        item.name,
        item.brand,
        item.model_number,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(query)
        );
    });
  }, [items, stocktakeItemSearch]);

  function openCreateStocktake() {
    setStocktakeForm({
      reference: "",
      location: "",
      notes: "",
      item_ids: [],
    });
    setStocktakeItemSearch("");
    setShowStocktakeCreateModal(true);
  }

  function toggleStocktakeItem(itemId) {
    setStocktakeForm((current) => ({
      ...current,
      item_ids: current.item_ids.includes(itemId)
        ? current.item_ids.filter((id) => id !== itemId)
        : [...current.item_ids, itemId],
    }));
  }

  async function createStocktake(event) {
    event.preventDefault();

    if (!stocktakeForm.reference.trim()) {
      setError("Stocktake reference is required.");
      return;
    }

    if (!stocktakeForm.location) {
      setError("Please select a location.");
      return;
    }

    if (!stocktakeForm.item_ids.length) {
      setError("Select at least one inventory item.");
      return;
    }

    setStocktakeLoading(true);
    setError("");

    try {
      const response = await api.post("/inventory/stocktakes/", {
        reference: stocktakeForm.reference.trim(),
        location: stocktakeForm.location,
        notes: stocktakeForm.notes,
        item_ids: stocktakeForm.item_ids,
      });

      setShowStocktakeCreateModal(false);
      setStocktakeForm({
        reference: "",
        location: "",
        notes: "",
        item_ids: [],
      });

      await loadStocktakes();

      const id = response.data?.id;
      if (id) {
        await openStocktake(id);
      }
    } catch (err) {
      console.error("Failed to create stocktake:", err);
      setError(getErrorMessage(err, "Failed to create physical stocktake."));
    } finally {
      setStocktakeLoading(false);
    }
  }

  async function openStocktake(stocktakeId) {
    setStocktakeLoading(true);
    setError("");

    try {
      const response = await api.get(
        `/inventory/stocktakes/${stocktakeId}/`
      );

      const data = response.data;
      setSelectedStocktake(data);
      setStocktakeLines(
        normalizeResults(data?.lines || data?.stocktake_lines || data?.items)
      );
    } catch (err) {
      console.error("Failed to load stocktake:", err);
      setError(getErrorMessage(err, "Failed to load stocktake."));
    } finally {
      setStocktakeLoading(false);
    }
  }

  function openCountModal() {
    const values = {};

    stocktakeLines.forEach((line) => {
      values[line.id] =
        line.counted_quantity === null ||
        line.counted_quantity === undefined
          ? ""
          : line.counted_quantity;
    });

    setCountValues(values);
    setShowCountModal(true);
  }

  async function saveStocktakeCounts(event) {
    event.preventDefault();
    setStocktakeLoading(true);
    setError("");

    try {
      for (const line of stocktakeLines) {
        const value = countValues[line.id];

        if (value === "" || value === null || value === undefined) {
          continue;
        }

        await api.patch(
          `/inventory/stocktake-lines/${line.id}/`,
          {
            counted_quantity: Number(value),
          }
        );
      }

      setShowCountModal(false);

      if (selectedStocktake?.id) {
        await openStocktake(selectedStocktake.id);
      }
    } catch (err) {
      console.error("Failed to save stocktake counts:", err);
      setError(getErrorMessage(err, "Failed to save stocktake counts."));
    } finally {
      setStocktakeLoading(false);
    }
  }

  async function confirmStocktake() {
    if (!selectedStocktake?.id) return;

    const confirmed = window.confirm(
      `Confirm stocktake "${selectedStocktake.reference}"?\\n\\nThis will create adjustment ledger entries for any stock variances.`
    );

    if (!confirmed) return;

    setConfirmingStocktake(true);
    setError("");

    try {
      await api.post(
        `/inventory/stocktakes/${selectedStocktake.id}/confirm/`
      );

      await openStocktake(selectedStocktake.id);
      await loadInitialData();
      await loadStocktakes();
    } catch (err) {
      console.error("Failed to confirm stocktake:", err);
      setError(getErrorMessage(err, "Failed to confirm stocktake."));
    } finally {
      setConfirmingStocktake(false);
    }
  }

  function getStocktakeLineItem(line) {
    return items.find(
      (item) => String(item.id) === String(line.item)
    );
  }

  function getLineVariance(line) {
    if (
      line.counted_quantity === null ||
      line.counted_quantity === undefined
    ) {
      return null;
    }

    return (
      Number(line.counted_quantity) -
      Number(line.system_quantity || 0)
    );
  }

  const countedStocktakeLines = stocktakeLines.filter(
    (line) =>
      line.counted_quantity !== null &&
      line.counted_quantity !== undefined
  ).length;

  if (loading) {
    return (
      <div className="inventory-page">
        <div className="inventory-loading">
          <RefreshCw className="spin" size={24} />
          <span>Loading inventory...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="inventory-page">
      <div className="inventory-header">
        <div>
          <div className="page-title-row">
            <Package size={28} />
            <h1>Inventory</h1>
          </div>

          <p>
            Manage inventory items, physical units, stock and
            categories.
          </p>
        </div>

        <div className="header-actions">
          <button
            className="btn btn-secondary"
            onClick={() => setShowImportModal(true)}
          >
            <FileSpreadsheet size={18} />
            Import Items
          </button>

          <button
            className="btn btn-primary"
            onClick={openAddItem}
          >
            <Plus size={18} />
            Add Item
          </button>
        </div>
      </div>

      {error && (
        <div className="inventory-alert">
          <span>{error}</span>

          <button
            className="alert-close"
            onClick={() => setError("")}
          >
            <X size={17} />
          </button>
        </div>
      )}

      <div className="inventory-tabs">
        <button
          type="button"
          className={activeTab === "items" ? "active" : ""}
          onClick={() => setActiveTab("items")}
        >
          Items
        </button>

        <button
          type="button"
          className={activeTab === "units" ? "active" : ""}
          onClick={() => setActiveTab("units")}
        >
          Physical Units
        </button>

        <button
          type="button"
          className={activeTab === "stock" ? "active" : ""}
          onClick={() => setActiveTab("stock")}
        >
          Stock
        </button>

        <button
          type="button"
          className={activeTab === "categories" ? "active" : ""}
          onClick={() => setActiveTab("categories")}
        >
          Categories
        </button>

        <button
          type="button"
          className={`stocktake-tab ${activeTab === "stocktakes" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("stocktakes");
            loadStocktakes();
          }}
        >
          <ClipboardCheck size={16} />
          Stocktakes
        </button>
      </div>

      {activeTab === "items" && (
        <>
          <div className="inventory-toolbar">
            <div className="search-box">
              <Search size={18} />

              <input
                type="text"
                placeholder="Search item code, name, brand or model..."
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
              />
            </div>

            <select
              value={categoryFilter}
              onChange={(event) =>
                setCategoryFilter(event.target.value)
              }
            >
              <option value="">All Categories</option>

              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name || category.category_name}
                </option>
              ))}
            </select>

            <input
              type="text"
              placeholder="Brand"
              value={brandFilter}
              onChange={(event) =>
                setBrandFilter(event.target.value)
              }
            />

            <select
              value={stockStatusFilter}
              onChange={(event) =>
                setStockStatusFilter(event.target.value)
              }
            >
              <option value="">All Stock Status</option>
              <option value="In Stock">In Stock</option>
              <option value="Low Stock">Low Stock</option>
              <option value="Out of Stock">
                Out of Stock
              </option>
            </select>

            <button
              className="refresh-btn"
              title="Refresh"
              onClick={loadInitialData}
            >
              <RefreshCw size={18} />
            </button>
          </div>

          <div className="inventory-card">
            <div className="table-header">
              <div>
                <strong>Inventory Items</strong>
                <span>{filteredItems.length} items</span>
              </div>

              <button
                className="btn btn-primary btn-small"
                onClick={openAddItem}
              >
                <Plus size={16} />
                Add Item
              </button>
            </div>

            {filteredItems.length === 0 ? (
              <div className="empty-state">
                <Package size={42} />
                <h3>No inventory items found</h3>
                <p>
                  Add an item or change your search/filter
                  criteria.
                </p>

                <button
                  className="btn btn-primary"
                  onClick={openAddItem}
                >
                  <Plus size={18} />
                  Add Item
                </button>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="inventory-table">
                  <thead>
                    <tr>
                      <th></th>
                      <th>Item Code</th>
                      <th>Item</th>
                      <th>Category</th>
                      <th>Brand</th>
                      <th>Model</th>
                      <th>Supplier</th>
                      <th>Unit</th>
                      <th>Stock</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredItems.map((item) => {
                      const expanded =
                        !!expandedItems[String(item.id)];

                      return (
                        <tr key={item.id}>
                          <td>
                            <button
                              className="expand-btn"
                              title={
                                expanded
                                  ? "Hide physical units"
                                  : "Show physical units"
                              }
                              onClick={() => toggleItem(item)}
                            >
                              {expanded ? (
                                <ChevronDown size={17} />
                              ) : (
                                <ChevronRight size={17} />
                              )}
                            </button>
                          </td>

                          <td>
                            <strong>{item.item_code}</strong>
                          </td>

                          <td>
                            <div className="item-name-cell">
                              <strong>{item.name}</strong>

                              {item.description && (
                                <small>
                                  {item.description}
                                </small>
                              )}
                            </div>
                          </td>

                          <td>
                            {getCategoryName(item.category)}
                          </td>

                          <td>{item.brand || "—"}</td>

                          <td>{item.model_number || "—"}</td>

                          <td>
                            {item.supplier_name ||
                              item.supplier_display ||
                              item.supplier ||
                              "—"}
                          </td>

                          <td>{item.unit || "—"}</td>

                          <td>
                            <strong>
                              {item.current_stock ?? 0}
                            </strong>
                          </td>

                          <td>
                            <span
                              className={`stock-badge ${getStockClass(
                                getStockLabel(item)
                              )}`}
                            >
                              {getStockLabel(item)}
                            </span>
                          </td>

                          <td>
                            <div className="row-actions">
                              <button
                                className="action-btn"
                                title="View physical units"
                                onClick={() => toggleItem(item)}
                              >
                                <Eye size={17} />
                              </button>

                              <button
                                className="action-btn"
                                title="Edit item"
                                onClick={() =>
                                  openEditItem(item)
                                }
                              >
                                <Pencil size={17} />
                              </button>

                              <button
                                className="action-btn danger"
                                title="Delete item"
                                onClick={() =>
                                  deleteItem(item)
                                }
                              >
                                <Trash2 size={17} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {filteredItems.map((item) => {
                  const expanded =
                    !!expandedItems[String(item.id)];

                  if (!expanded) return null;

                  const itemUnits = units.filter(
                    (unit) =>
                      String(unit.item) === String(item.id)
                  );

                  return (
                    <div
                      key={`units-${item.id}`}
                      className="inline-units-panel"
                    >
                      <div className="inline-units-header">
                        <div>
                          <strong>
                            Physical Units — {item.name}
                          </strong>

                          <span>
                            {item.brand || "No brand"}{" "}
                            {item.model_number || ""}
                          </span>
                        </div>

                        <button
                          className="btn btn-primary btn-small"
                          onClick={() => openAddUnit(item)}
                        >
                          <Plus size={15} />
                          Add Physical Unit
                        </button>
                      </div>

                      {unitsLoading ? (
                        <div className="small-loading">
                          <RefreshCw
                            className="spin"
                            size={18}
                          />
                          Loading units...
                        </div>
                      ) : itemUnits.length === 0 ? (
                        <div className="inline-empty">
                          No physical units have been added
                          for this item.
                        </div>
                      ) : (
                        <div className="unit-cards">
                          {itemUnits.map((unit) => (
                            <div
                              className="unit-card"
                              key={unit.id}
                            >
                              <div className="unit-card-header">
                                <strong>
                                  {unit.serial_number ||
                                    `Unit #${unit.id}`}
                                </strong>

                                <span
                                  className={`unit-status status-${String(
                                    unit.status || ""
                                  ).toLowerCase()}`}
                                >
                                  {String(
                                    unit.status || ""
                                  ).replaceAll("_", " ")}
                                </span>
                              </div>

                              <div className="unit-card-grid">
                                <div>
                                  <label>Serial Number</label>
                                  <span>
                                    {unit.serial_number ||
                                      "—"}
                                  </span>
                                </div>

                                <div>
                                  <label>Condition</label>
                                  <span>
                                    {unit.condition ||
                                      "—"}
                                  </span>
                                </div>

                                <div>
                                  <label>Location</label>
                                  <span>
                                    {getLocationName(
                                      unit.location
                                    )}
                                  </span>
                                </div>

                                <div>
                                  <label>Assigned To</label>
                                  <span>
                                    {getEmployeeName(
                                      unit.assigned_to
                                    )}
                                  </span>
                                </div>

                                <div className="unit-specs">
                                  <label>Specifications</label>
                                  <span>
                                    {getUnitSpecification(
                                      unit
                                    )}
                                  </span>
                                </div>
                              </div>

                              <div className="unit-card-actions">
                                <button
                                  className="action-btn"
                                  onClick={() =>
                                    openEditUnit(unit)
                                  }
                                >
                                  <Pencil size={16} />
                                  Edit
                                </button>

                                <button
                                  className="action-btn danger"
                                  onClick={() =>
                                    deleteUnit(unit)
                                  }
                                >
                                  <Trash2 size={16} />
                                  Delete
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === "units" && (
        <>
          <div className="inventory-toolbar">
            <div className="search-box">
              <Search size={18} />

              <input
                type="text"
                placeholder="Search serial, item, brand..."
                value={unitSearch}
                onChange={(event) =>
                  setUnitSearch(event.target.value)
                }
              />
            </div>

            <select
              value={unitStatusFilter}
              onChange={(event) =>
                setUnitStatusFilter(event.target.value)
              }
            >
              <option value="">All Statuses</option>
              <option value="IN_STOCK">In Stock</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="LOST">Lost</option>
              <option value="DISPOSED">Disposed</option>
            </select>

            <select
              value={unitConditionFilter}
              onChange={(event) =>
                setUnitConditionFilter(event.target.value)
              }
            >
              <option value="">All Conditions</option>
              <option value="GOOD">Good</option>
              <option value="FAIR">Fair</option>
              <option value="POOR">Poor</option>
              <option value="DAMAGED">Damaged</option>
            </select>

            <select
              value={unitLocationFilter}
              onChange={(event) =>
                setUnitLocationFilter(event.target.value)
              }
            >
              <option value="">All Locations</option>

              {locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name || location.location_name}
                </option>
              ))}
            </select>

            <button
              className="refresh-btn"
              title="Refresh"
              onClick={() => loadUnits()}
            >
              <RefreshCw size={18} />
            </button>

            <button
              className="btn btn-primary"
              onClick={() => openAddUnit()}
            >
              <Plus size={18} />
              Add Unit
            </button>
          </div>

          <div className="inventory-card">
            <div className="table-header">
              <div>
                <strong>Physical Inventory Units</strong>
                <span>{filteredUnits.length} units</span>
              </div>
            </div>

            {unitsLoading ? (
              <div className="inventory-loading">
                <RefreshCw className="spin" size={22} />
                <span>Loading physical units...</span>
              </div>
            ) : filteredUnits.length === 0 ? (
              <div className="empty-state">
                <Package size={42} />
                <h3>No physical units found</h3>
                <p>
                  Physical units are the individual items with
                  their own serial numbers and specifications.
                </p>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="inventory-table">
                  <thead>
                    <tr>
                      <th></th>
                      <th>Serial Number</th>
                      <th>Item</th>
                      <th>Brand</th>
                      <th>Model</th>
                      <th>Specifications</th>
                      <th>Status</th>
                      <th>Condition</th>
                      <th>Location</th>
                      <th>Assigned To</th>
                      <th>Actions</th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredUnits.map((unit) => {
                      const item = getUnitItem(unit);

                      return (
                        <tr key={unit.id}>
                          <td>
                            {unit.serial_number || "—"}
                          </td>

                          <td>
                            <strong>
                              {item?.name ||
                                unit.item_name ||
                                "—"}
                            </strong>
                          </td>

                          <td>
                            {item?.brand ||
                              unit.brand ||
                              "—"}
                          </td>

                          <td>
                            {item?.model_number ||
                              unit.model_number ||
                              "—"}
                          </td>

                          <td className="spec-cell">
                            {getUnitSpecification(unit)}
                          </td>

                          <td>
                            <span
                              className={`unit-status status-${String(
                                unit.status || ""
                              ).toLowerCase()}`}
                            >
                              {String(
                                unit.status || ""
                              ).replaceAll("_", " ")}
                            </span>
                          </td>

                          <td>
                            {unit.condition || "—"}
                          </td>

                          <td>
                            {getLocationName(unit.location)}
                          </td>

                          <td>
                            {getEmployeeName(
                              unit.assigned_to
                            )}
                          </td>

                          <td>
                            <div className="row-actions">
                              <button
                                className="action-btn"
                                onClick={() =>
                                  openEditUnit(unit)
                                }
                              >
                                <Pencil size={17} />
                              </button>

                              <button
                                className="action-btn danger"
                                onClick={() =>
                                  deleteUnit(unit)
                                }
                              >
                                <Trash2 size={17} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === "stock" && (
        <div className="inventory-card stock-module">
          <div className="stock-workspace-header">
            <div>
              <strong>Stock Management</strong>
              <span>
                Manage opening balances, stock movements and location transfers.
              </span>
            </div>

            <div className="stock-header-actions">
              {stockSection === "opening" && (
                <>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setShowOpeningImportModal(true)}
                  >
                    <FileSpreadsheet size={17} />
                    Import Opening Stock
                  </button>

                  <button
                    className="btn btn-primary"
                    onClick={openOpeningStockModal}
                  >
                    <Plus size={17} />
                    Opening Stock
                  </button>
                </>
              )}

              {stockSection === "transactions" && (
                <button
                  className="btn btn-primary"
                  onClick={openTransactionModal}
                >
                  <Plus size={17} />
                  New Transaction
                </button>
              )}

              {stockSection === "transfers" && (
                <button
                  className="btn btn-primary"
                  onClick={openTransferModal}
                >
                  <Plus size={17} />
                  New Transfer
                </button>
              )}

              <button
                className="refresh-btn"
                title="Refresh"
                onClick={() => {
                  loadInitialData();
                  loadStockSection(stockSection);
                }}
                disabled={stockLoading}
              >
                <RefreshCw size={18} className={stockLoading ? "spin" : ""} />
              </button>
            </div>
          </div>

          <div className="stock-subtabs" role="tablist" aria-label="Stock management sections">
            <button
              type="button"
              role="tab"
              aria-selected={stockSection === "opening"}
              className={stockSection === "opening" ? "active" : ""}
              onClick={() => setStockSection("opening")}
            >
              <Package size={16} />
              <span>Opening Stock</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={stockSection === "transactions"}
              className={stockSection === "transactions" ? "active" : ""}
              onClick={() => setStockSection("transactions")}
            >
              <History size={16} />
              <span>Stock Transactions</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={stockSection === "transfers"}
              className={stockSection === "transfers" ? "active" : ""}
              onClick={() => setStockSection("transfers")}
            >
              <ArrowRightLeft size={16} />
              <span>Stock Transfers</span>
            </button>
          </div>

          <div className="stock-action-grid">
            <button
              type="button"
              className={`stock-action-card ${stockSection === "opening" ? "selected" : ""}`}
              onClick={() => {
                setStockSection("opening");
                openOpeningStockModal();
              }}
            >
              <span className="stock-action-icon opening"><Package size={19} /></span>
              <span className="stock-action-copy">
                <strong>Opening Stock</strong>
                <small>Set an initial balance for an item and location.</small>
              </span>
              <Plus size={17} />
            </button>

            <button
              type="button"
              className={`stock-action-card ${stockSection === "transactions" ? "selected" : ""}`}
              onClick={() => {
                setStockSection("transactions");
                openTransactionModal();
              }}
            >
              <span className="stock-action-icon transactions"><History size={19} /></span>
              <span className="stock-action-copy">
                <strong>Stock Transactions</strong>
                <small>Record received, issued, returned or adjusted stock.</small>
              </span>
              <Plus size={17} />
            </button>

            <button
              type="button"
              className={`stock-action-card ${stockSection === "transfers" ? "selected" : ""}`}
              onClick={() => {
                setStockSection("transfers");
                openTransferModal();
              }}
            >
              <span className="stock-action-icon transfers"><ArrowRightLeft size={19} /></span>
              <span className="stock-action-copy">
                <strong>Stock Transfer</strong>
                <small>Move stock from one active location to another.</small>
              </span>
              <Plus size={17} />
            </button>

            <button
              type="button"
              className="stock-action-card stocktake-action"
              onClick={() => {
                setActiveTab("stocktakes");
                loadStocktakes();
              }}
            >
              <span className="stock-action-icon stocktakes"><ClipboardCheck size={19} /></span>
              <span className="stock-action-copy">
                <strong>Stocktakes</strong>
                <small>Count physical stock and reconcile variances.</small>
              </span>
              <ChevronRight size={17} />
            </button>
          </div>

          {stockSection === "opening" && (
            <div className="stock-info-card">
              <div className="stock-info-icon">
                <Package size={22} />
              </div>
              <div>
                <strong>Opening stock is recorded through the stock ledger.</strong>
                <p>
                  Use Opening Stock for the initial quantity of an item at a location.
                  Use the Excel import when loading a larger opening balance.
                </p>
              </div>
              <button
                className="btn btn-secondary btn-small"
                onClick={openOpeningStockModal}
              >
                Add Opening Stock
              </button>
            </div>
          )}

          {stockSection === "transactions" && (
            <div className="stock-list-panel">
              {stockLoading ? (
                <div className="small-loading">
                  <RefreshCw size={18} className="spin" />
                  Loading transactions...
                </div>
              ) : transactions.length === 0 ? (
                <div className="empty-state">
                  <Package size={40} />
                  <h3>No stock transactions found</h3>
                  <p>Create a received, issued, returned or adjustment transaction.</p>
                  <button className="btn btn-primary" onClick={openTransactionModal}>
                    <Plus size={17} />
                    New Transaction
                  </button>
                </div>
              ) : (
                <div className="table-wrapper">
                  <table className="inventory-table stock-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Item</th>
                        <th>Type</th>
                        <th>Quantity</th>
                        <th>Location</th>
                        <th>Employee</th>
                        <th>Reference</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((transaction) => (
                        <tr key={transaction.id}>
                          <td>
                            {transaction.created_at
                              ? new Date(transaction.created_at).toLocaleString()
                              : "—"}
                          </td>
                          <td>{getItemName(transaction.item)}</td>
                          <td>
                            <span
                              className={`transaction-badge transaction-${String(
                                transaction.transaction_type || ""
                              ).toLowerCase()}`}
                            >
                              {String(transaction.transaction_type || "").replaceAll(
                                "_",
                                " "
                              )}
                            </span>
                          </td>
                          <td>{transaction.quantity ?? 0}</td>
                          <td>
                            {transaction.location_name ||
                              getLocationName(transaction.location)}
                          </td>
                          <td>
                            {transaction.employee_name ||
                              getEmployeeName(transaction.employee)}
                          </td>
                          <td>{transaction.reference || "—"}</td>
                          <td className="notes-cell">{transaction.notes || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {stockSection === "transfers" && (
            <div className="stock-list-panel">
              {stockLoading ? (
                <div className="small-loading">
                  <RefreshCw size={18} className="spin" />
                  Loading transfers...
                </div>
              ) : transfers.length === 0 ? (
                <div className="empty-state">
                  <Package size={40} />
                  <h3>No stock transfers found</h3>
                  <p>Move stock between active inventory locations.</p>
                  <button className="btn btn-primary" onClick={openTransferModal}>
                    <Plus size={17} />
                    New Transfer
                  </button>
                </div>
              ) : (
                <div className="table-wrapper">
                  <table className="inventory-table stock-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Reference</th>
                        <th>Item</th>
                        <th>Quantity</th>
                        <th>Source</th>
                        <th>Destination</th>
                        <th>Status</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transfers.map((transfer) => (
                        <tr key={transfer.id}>
                          <td>
                            {transfer.created_at
                              ? new Date(transfer.created_at).toLocaleString()
                              : "—"}
                          </td>
                          <td>{transfer.reference || "—"}</td>
                          <td>{getItemName(transfer.item)}</td>
                          <td>{transfer.quantity ?? 0}</td>
                          <td>
                            {transfer.source_location_name ||
                              getLocationName(transfer.source_location)}
                          </td>
                          <td>
                            {transfer.destination_location_name ||
                              getLocationName(transfer.destination_location)}
                          </td>
                          <td>
                            <span
                              className={`transaction-badge transaction-status-${String(
                                transfer.status || ""
                              ).toLowerCase()}`}
                            >
                              {String(transfer.status || "").replaceAll("_", " ")}
                            </span>
                          </td>
                          <td className="notes-cell">{transfer.notes || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === "categories" && (
        <div className="inventory-card">
          <div className="table-header">
            <div>
              <strong>Inventory Categories</strong>
              <span>{categories.length} categories</span>
            </div>
          </div>

          {categories.length === 0 ? (
            <div className="empty-state">
              <Package size={42} />
              <h3>No categories found</h3>
            </div>
          ) : (
            <div className="category-grid">
              {categories.map((category) => {
                const categoryItems = items.filter(
                  (item) =>
                    String(item.category) ===
                    String(category.id)
                );

                return (
                  <div
                    className="category-card"
                    key={category.id}
                  >
                    <div className="category-icon">
                      <Package size={22} />
                    </div>

                    <div>
                      <strong>
                        {category.name ||
                          category.category_name}
                      </strong>

                      <span>
                        {categoryItems.length} item
                        {categoryItems.length === 1
                          ? ""
                          : "s"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === "stocktakes" && (
        <div className="inventory-card stocktake-module">
          <div className="table-header">
            <div>
              <strong>Physical Stocktakes</strong>
              <span>
                Count physical stock by location and reconcile
                variances through the stock ledger.
              </span>
            </div>

            <button
              className="btn btn-primary"
              onClick={openCreateStocktake}
            >
              <ClipboardCheck size={17} />
              Create Stocktake
            </button>
          </div>

          {stocktakeLoading && !selectedStocktake ? (
            <div className="inventory-loading">
              <RefreshCw className="spin" size={22} />
              <span>Loading stocktakes...</span>
            </div>
          ) : stocktakes.length === 0 ? (
            <div className="empty-state">
              <ClipboardCheck size={42} />
              <h3>No physical stocktakes found</h3>
              <p>Create a stocktake to begin counting inventory at a location.</p>
              <button
                className="btn btn-primary"
                onClick={openCreateStocktake}
              >
                <ClipboardCheck size={17} />
                Create Stocktake
              </button>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="inventory-table">
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Location</th>
                    <th>Status</th>
                    <th>Lines</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {stocktakes.map((stocktake) => (
                    <tr key={stocktake.id}>
                      <td>
                        <strong>{stocktake.reference}</strong>
                      </td>
                      <td>
                        {stocktake.location_name ||
                          getLocationName(stocktake.location)}
                      </td>
                      <td>
                        <span
                          className={`stocktake-status status-${String(
                            stocktake.status || ""
                          ).toLowerCase()}`}
                        >
                          {String(stocktake.status || "").replaceAll("_", " ")}
                        </span>
                      </td>
                      <td>
                        {stocktake.line_count ??
                          stocktake.lines_count ??
                          stocktake.lines?.length ??
                          "—"}
                      </td>
                      <td>
                        {stocktake.created_at
                          ? new Date(stocktake.created_at).toLocaleString()
                          : "—"}
                      </td>
                      <td>
                        <button
                          className="action-btn"
                          onClick={() => openStocktake(stocktake.id)}
                          title="View stocktake"
                        >
                          <Eye size={17} />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showOpeningStockModal && (
        <div className="modal-overlay">
          <div className="modal inventory-modal">
            <div className="modal-header">
              <div>
                <h2>Add Opening Stock</h2>
                <p>Record the starting quantity for an item at a location.</p>
              </div>
              <button
                className="icon-btn"
                onClick={() => setShowOpeningStockModal(false)}
                disabled={stockLoading}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={saveOpeningStock}>
              <div className="form-grid">
                <div className="form-group full-width">
                  <label>Item *</label>
                  <select
                    value={openingForm.item}
                    onChange={(event) =>
                      setOpeningForm({
                        ...openingForm,
                        item: event.target.value,
                      })
                    }
                    required
                  >
                    <option value="">Select item</option>
                    {items
                      .filter((item) => item.is_active !== false)
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.item_code} — {item.name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={openingForm.quantity}
                    onChange={(event) =>
                      setOpeningForm({
                        ...openingForm,
                        quantity: event.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Location</label>
                  <select
                    value={openingForm.location}
                    onChange={(event) =>
                      setOpeningForm({
                        ...openingForm,
                        location: event.target.value,
                      })
                    }
                  >
                    <option value="">No location</option>
                    {locations
                      .filter((location) => location.is_active !== false)
                      .map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.name || location.location_name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Reference</label>
                  <input
                    type="text"
                    value={openingForm.reference}
                    onChange={(event) =>
                      setOpeningForm({
                        ...openingForm,
                        reference: event.target.value,
                      })
                    }
                    placeholder="e.g. OPEN-2026-001"
                  />
                </div>

                <div className="form-group full-width">
                  <label>Notes</label>
                  <textarea
                    value={openingForm.notes}
                    onChange={(event) =>
                      setOpeningForm({
                        ...openingForm,
                        notes: event.target.value,
                      })
                    }
                    placeholder="Optional notes..."
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowOpeningStockModal(false)}
                  disabled={stockLoading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={stockLoading}>
                  {stockLoading ? "Saving..." : "Save Opening Stock"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showTransactionModal && (
        <div className="modal-overlay">
          <div className="modal inventory-modal">
            <div className="modal-header">
              <div>
                <h2>New Stock Transaction</h2>
                <p>Record a stock movement without overwriting the ledger history.</p>
              </div>
              <button
                className="icon-btn"
                onClick={() => setShowTransactionModal(false)}
                disabled={stockLoading}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={saveTransaction}>
              <div className="form-grid">
                <div className="form-group full-width">
                  <label>Item *</label>
                  <select
                    value={transactionForm.item}
                    onChange={(event) =>
                      setTransactionForm({
                        ...transactionForm,
                        item: event.target.value,
                      })
                    }
                    required
                  >
                    <option value="">Select item</option>
                    {items
                      .filter((item) => item.is_active !== false)
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.item_code} — {item.name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Transaction Type *</label>
                  <select
                    value={transactionForm.transaction_type}
                    onChange={(event) =>
                      setTransactionForm({
                        ...transactionForm,
                        transaction_type: event.target.value,
                      })
                    }
                  >
                    <option value="RECEIVED">Received</option>
                    <option value="ISSUED">Issued</option>
                    <option value="RETURNED">Returned</option>
                    <option value="ADJUSTMENT">Adjustment</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={transactionForm.quantity}
                    onChange={(event) =>
                      setTransactionForm({
                        ...transactionForm,
                        quantity: event.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Location</label>
                  <select
                    value={transactionForm.location}
                    onChange={(event) =>
                      setTransactionForm({
                        ...transactionForm,
                        location: event.target.value,
                      })
                    }
                  >
                    <option value="">No location</option>
                    {locations
                      .filter((location) => location.is_active !== false)
                      .map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.name || location.location_name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Employee</label>
                  <select
                    value={transactionForm.employee}
                    onChange={(event) =>
                      setTransactionForm({
                        ...transactionForm,
                        employee: event.target.value,
                      })
                    }
                  >
                    <option value="">No employee</option>
                    {employees
                      .filter((employee) => employee.status === "ACTIVE")
                      .map((employee) => (
                        <option key={employee.id} value={employee.id}>
                          {getEmployeeName(employee.id)}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group full-width">
                  <label>Reference</label>
                  <input
                    type="text"
                    value={transactionForm.reference}
                    onChange={(event) =>
                      setTransactionForm({
                        ...transactionForm,
                        reference: event.target.value,
                      })
                    }
                    placeholder="e.g. GRN-2026-001"
                  />
                </div>

                <div className="form-group full-width">
                  <label>Notes</label>
                  <textarea
                    value={transactionForm.notes}
                    onChange={(event) =>
                      setTransactionForm({
                        ...transactionForm,
                        notes: event.target.value,
                      })
                    }
                    placeholder="Optional notes..."
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowTransactionModal(false)}
                  disabled={stockLoading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={stockLoading}>
                  {stockLoading ? "Saving..." : "Save Transaction"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showTransferModal && (
        <div className="modal-overlay">
          <div className="modal inventory-modal">
            <div className="modal-header">
              <div>
                <h2>New Stock Transfer</h2>
                <p>Transfer stock from one location to another.</p>
              </div>
              <button
                className="icon-btn"
                onClick={() => setShowTransferModal(false)}
                disabled={stockLoading}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={saveTransfer}>
              <div className="form-grid">
                <div className="form-group full-width">
                  <label>Item *</label>
                  <select
                    value={transferForm.item}
                    onChange={(event) =>
                      setTransferForm({
                        ...transferForm,
                        item: event.target.value,
                      })
                    }
                    required
                  >
                    <option value="">Select item</option>
                    {items
                      .filter((item) => item.is_active !== false)
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.item_code} — {item.name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={transferForm.quantity}
                    onChange={(event) =>
                      setTransferForm({
                        ...transferForm,
                        quantity: event.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Source Location *</label>
                  <select
                    value={transferForm.source_location}
                    onChange={(event) =>
                      setTransferForm({
                        ...transferForm,
                        source_location: event.target.value,
                      })
                    }
                    required
                  >
                    <option value="">Select source</option>
                    {locations
                      .filter((location) => location.is_active !== false)
                      .map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.name || location.location_name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Destination Location *</label>
                  <select
                    value={transferForm.destination_location}
                    onChange={(event) =>
                      setTransferForm({
                        ...transferForm,
                        destination_location: event.target.value,
                      })
                    }
                    required
                  >
                    <option value="">Select destination</option>
                    {locations
                      .filter((location) => location.is_active !== false)
                      .map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.name || location.location_name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group full-width">
                  <label>Reference *</label>
                  <input
                    type="text"
                    value={transferForm.reference}
                    onChange={(event) =>
                      setTransferForm({
                        ...transferForm,
                        reference: event.target.value,
                      })
                    }
                    placeholder="e.g. TRF-2026-001"
                    required
                  />
                </div>

                <div className="form-group full-width">
                  <label>Notes</label>
                  <textarea
                    value={transferForm.notes}
                    onChange={(event) =>
                      setTransferForm({
                        ...transferForm,
                        notes: event.target.value,
                      })
                    }
                    placeholder="Optional notes..."
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowTransferModal(false)}
                  disabled={stockLoading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={stockLoading}>
                  {stockLoading ? "Saving..." : "Create Transfer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showOpeningImportModal && (
        <div className="modal-overlay">
          <div className="modal import-modal">
            <div className="modal-header">
              <div>
                <h2>Import Opening Stock</h2>
                <p>Upload an Excel file to validate and create opening stock ledger entries.</p>
              </div>

              <button
                className="icon-btn"
                onClick={closeOpeningImportModal}
                disabled={openingImporting}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleOpeningStockImport}>
              <div className="import-content">
                <div className="import-info">
                  <FileSpreadsheet size={46} />
                  <h3>Opening Stock Excel Import</h3>
                  <p>
                    Select an <strong>.xlsx</strong> file. The importer will
                    validate the spreadsheet before the opening balances are confirmed.
                  </p>
                </div>

                <label
                  htmlFor="opening-stock-import-file"
                  className="file-upload-box"
                >
                  <Upload size={28} />
                  <span>
                    {openingStockFile
                      ? openingStockFile.name
                      : "Choose Excel file"}
                  </span>
                  <small>Supported format: .xlsx</small>
                </label>

                <input
                  id="opening-stock-import-file"
                  type="file"
                  accept=".xlsx"
                  className="hidden-file-input"
                  onChange={(event) =>
                    setOpeningStockFile(event.target.files?.[0] || null)
                  }
                />

                {openingImportResult && (
                  <div
                    className={`import-result ${
                      openingImportResult.success ? "success" : "failed"
                    }`}
                  >
                    {openingImportResult.success
                      ? "Opening stock import completed successfully."
                      : "Opening stock import failed. Review the validation errors."}
                  </div>
                )}

                <div className="import-notes">
                  <strong>Recommended columns</strong>
                  <span>
                    Item Code, Quantity, Location, Reference, Notes
                  </span>
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={closeOpeningImportModal}
                  disabled={openingImporting}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={openingImporting || !openingStockFile}
                >
                  {openingImporting ? (
                    <>
                      <RefreshCw size={17} className="spin" />
                      Importing...
                    </>
                  ) : (
                    <>
                      <FileSpreadsheet size={17} />
                      Upload & Confirm
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showStocktakeCreateModal && (
        <div className="modal-overlay">
          <div className="modal inventory-modal stocktake-modal">
            <div className="modal-header">
              <div>
                <h2>Create Physical Stocktake</h2>
                <p>
                  Select a location and the items that will be counted.
                  The system quantity is captured when the stocktake is created.
                </p>
              </div>

              <button
                className="icon-btn"
                onClick={() => setShowStocktakeCreateModal(false)}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={createStocktake}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Reference *</label>
                  <input
                    type="text"
                    value={stocktakeForm.reference}
                    onChange={(event) =>
                      setStocktakeForm({
                        ...stocktakeForm,
                        reference: event.target.value,
                      })
                    }
                    placeholder="e.g. STK-2026-001"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Location *</label>
                  <select
                    value={stocktakeForm.location}
                    onChange={(event) =>
                      setStocktakeForm({
                        ...stocktakeForm,
                        location: event.target.value,
                      })
                    }
                    required
                  >
                    <option value="">Select location</option>
                    {locations
                      .filter((location) => location.is_active !== false)
                      .map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.name || location.location_name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group full-width">
                  <label>Notes</label>
                  <textarea
                    rows="3"
                    value={stocktakeForm.notes}
                    onChange={(event) =>
                      setStocktakeForm({
                        ...stocktakeForm,
                        notes: event.target.value,
                      })
                    }
                    placeholder="Optional notes about this stocktake..."
                  />
                </div>
              </div>

              <div className="stocktake-item-selector">
                <div className="stocktake-selector-header">
                  <div>
                    <strong>Select Items</strong>
                    <span>
                      {stocktakeForm.item_ids.length} selected
                    </span>
                  </div>

                  <div className="search-box">
                    <Search size={17} />
                    <input
                      type="text"
                      placeholder="Search items..."
                      value={stocktakeItemSearch}
                      onChange={(event) =>
                        setStocktakeItemSearch(event.target.value)
                      }
                    />
                  </div>
                </div>

                <div className="stocktake-item-list">
                  {filteredStocktakeItems.map((item) => {
                    const selected = stocktakeForm.item_ids.includes(item.id);

                    return (
                      <label
                        className={`stocktake-item-row ${
                          selected ? "selected" : ""
                        }`}
                        key={item.id}
                      >
                        <input
                          type="checkbox"
                          checked={selected}
                          onChange={() => toggleStocktakeItem(item.id)}
                        />

                        <span>
                          <strong>{item.item_code}</strong>
                          {" — "}
                          {item.name}
                        </span>

                        <small>
                          Current global stock: {item.current_stock ?? 0}
                        </small>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowStocktakeCreateModal(false)}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={stocktakeLoading}
                >
                  {stocktakeLoading ? "Creating..." : "Create Stocktake"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedStocktake && (
        <div className="modal-overlay">
          <div className="modal inventory-modal stocktake-detail-modal">
            <div className="modal-header">
              <div>
                <h2>{selectedStocktake.reference}</h2>
                <p>
                  {selectedStocktake.location_name ||
                    getLocationName(selectedStocktake.location)}
                  {" · "}
                  {String(selectedStocktake.status || "").replaceAll("_", " ")}
                </p>
              </div>

              <button
                className="icon-btn"
                onClick={() => {
                  setSelectedStocktake(null);
                  setStocktakeLines([]);
                }}
              >
                <X size={20} />
              </button>
            </div>

            <div className="stocktake-summary">
              <div>
                <span>Total Lines</span>
                <strong>{stocktakeLines.length}</strong>
              </div>
              <div>
                <span>Counted</span>
                <strong>{countedStocktakeLines}</strong>
              </div>
              <div>
                <span>Remaining</span>
                <strong>
                  {Math.max(
                    stocktakeLines.length - countedStocktakeLines,
                    0
                  )}
                </strong>
              </div>
              <div>
                <span>Status</span>
                <strong>
                  {String(selectedStocktake.status || "").replaceAll("_", " ")}
                </strong>
              </div>
            </div>

            {selectedStocktake.notes && (
              <div className="stocktake-notes">
                {selectedStocktake.notes}
              </div>
            )}

            <div className="table-wrapper stocktake-lines-wrapper">
              <table className="inventory-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>System Qty</th>
                    <th>Physical Count</th>
                    <th>Variance</th>
                  </tr>
                </thead>

                <tbody>
                  {stocktakeLines.map((line) => {
                    const item = getStocktakeLineItem(line);
                    const variance = getLineVariance(line);

                    return (
                      <tr key={line.id}>
                        <td>
                          <strong>
                            {line.item_code ||
                              item?.item_code ||
                              "—"}
                          </strong>
                          <div>
                            {line.item_name || item?.name || "—"}
                          </div>
                        </td>
                        <td>{line.system_quantity ?? 0}</td>
                        <td>
                          {line.counted_quantity === null ||
                          line.counted_quantity === undefined ? (
                            <span className="muted-text">Not counted</span>
                          ) : (
                            line.counted_quantity
                          )}
                        </td>
                        <td>
                          {variance === null ? (
                            "—"
                          ) : (
                            <span
                              className={`variance ${
                                variance > 0
                                  ? "positive"
                                  : variance < 0
                                    ? "negative"
                                    : "zero"
                              }`}
                            >
                              {variance > 0 ? "+" : ""}
                              {variance}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="modal-actions">
              {selectedStocktake.status !== "COMPLETED" &&
                selectedStocktake.status !== "CANCELLED" && (
                  <button
                    className="btn btn-secondary"
                    onClick={openCountModal}
                  >
                    <ClipboardCheck size={17} />
                    Enter Counts
                  </button>
                )}

              {selectedStocktake.status !== "COMPLETED" &&
                selectedStocktake.status !== "CANCELLED" && (
                  <button
                    className="btn btn-primary"
                    disabled={
                      confirmingStocktake ||
                      stocktakeLines.length === 0 ||
                      countedStocktakeLines !== stocktakeLines.length
                    }
                    onClick={confirmStocktake}
                    title={
                      countedStocktakeLines !== stocktakeLines.length
                        ? "All lines must be counted before confirmation."
                        : "Confirm stocktake"
                    }
                  >
                    <CheckCircle size={17} />
                    {confirmingStocktake
                      ? "Confirming..."
                      : "Confirm Stocktake"}
                  </button>
                )}

              <button
                className="btn btn-secondary"
                onClick={() => {
                  setSelectedStocktake(null);
                  setStocktakeLines([]);
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {showCountModal && selectedStocktake && (
        <div className="modal-overlay">
          <div className="modal inventory-modal count-modal">
            <div className="modal-header">
              <div>
                <h2>Enter Physical Counts</h2>
                <p>{selectedStocktake.reference}</p>
              </div>

              <button
                className="icon-btn"
                onClick={() => setShowCountModal(false)}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={saveStocktakeCounts}>
              <div className="count-list">
                {stocktakeLines.map((line) => {
                  const item = getStocktakeLineItem(line);

                  return (
                    <div className="count-row" key={line.id}>
                      <div>
                        <strong>
                          {line.item_code ||
                            item?.item_code ||
                            "—"}
                        </strong>
                        <span>
                          {line.item_name || item?.name || "—"}
                        </span>
                        <small>
                          System quantity: {line.system_quantity ?? 0}
                        </small>
                      </div>

                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={countValues[line.id] ?? ""}
                        onChange={(event) =>
                          setCountValues({
                            ...countValues,
                            [line.id]: event.target.value,
                          })
                        }
                        placeholder="Physical count"
                      />
                    </div>
                  );
                })}
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowCountModal(false)}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={stocktakeLoading}
                >
                  {stocktakeLoading ? "Saving..." : "Save Counts"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showItemModal && (
        <div className="modal-overlay">
          <div className="modal inventory-modal">
            <div className="modal-header">
              <div>
                <h2>
                  {editingItem
                    ? "Edit Inventory Item"
                    : "Add Inventory Item"}
                </h2>

                <p>
                  Define the master item record. Individual
                  physical units can have their own
                  specifications.
                </p>
              </div>

              <button
                className="icon-btn"
                onClick={closeItemModal}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={saveItem}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Item Code</label>

                  <input
                    type="text"
                    value={
                      editingItem?.item_code ||
                      "Generated automatically after saving"
                    }
                    readOnly
                    disabled
                  />

                  <small className="form-help">
                    Item codes are generated automatically in the format
                    BT-000001, BT-000002, etc. They cannot be entered or
                    changed manually.
                  </small>
                </div>

                <div className="form-group">
                  <label>Item Name *</label>

                  <input
                    type="text"
                    value={itemForm.name}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        name: event.target.value,
                      })
                    }
                    placeholder="e.g. Dell Latitude"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Category</label>

                  <select
                    value={itemForm.category}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        category: event.target.value,
                      })
                    }
                  >
                    <option value="">
                      Select category
                    </option>

                    {categories.map((category) => (
                      <option
                        key={category.id}
                        value={category.id}
                      >
                        {category.name ||
                          category.category_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Brand</label>

                  <input
                    type="text"
                    value={itemForm.brand}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        brand: event.target.value,
                      })
                    }
                    placeholder="e.g. Dell"
                  />
                </div>

                <div className="form-group">
                  <label>Model</label>

                  <input
                    type="text"
                    value={itemForm.model_number}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        model_number: event.target.value,
                      })
                    }
                    placeholder="e.g. Latitude 5420"
                  />
                </div>

                <div className="form-group">
                  <label>Supplier</label>

                  <input
                    type="text"
                    value={itemForm.supplier}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        supplier: event.target.value,
                      })
                    }
                    placeholder="Supplier ID"
                  />
                </div>

                <div className="form-group">
                  <label>Unit</label>

                  <input
                    type="text"
                    value={itemForm.unit}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        unit: event.target.value,
                      })
                    }
                    placeholder="e.g. Piece"
                  />
                </div>

                <div className="form-group">
                  <label>Reorder Level</label>

                  <input
                    type="number"
                    min="0"
                    value={itemForm.reorder_level}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        reorder_level: event.target.value,
                      })
                    }
                  />
                </div>

                <div className="form-group">
                  <label>Minimum Stock</label>

                  <input
                    type="number"
                    min="0"
                    value={itemForm.minimum_stock}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        minimum_stock: event.target.value,
                      })
                    }
                  />
                </div>

                <div className="form-group full-width">
                  <label>Description</label>

                  <textarea
                    rows="3"
                    value={itemForm.description}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        description: event.target.value,
                      })
                    }
                    placeholder="Describe this inventory item..."
                  />
                </div>

                <div className="form-group full-width">
                  <label>
                    General Specifications
                  </label>

                  <textarea
                    rows="4"
                    value={itemForm.specifications}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        specifications: event.target.value,
                      })
                    }
                    placeholder='Optional JSON, e.g. {"type":"Laptop"}'
                  />
                </div>

                <div className="checkbox-group">
                  <input
                    type="checkbox"
                    id="item-active"
                    checked={itemForm.is_active}
                    onChange={(event) =>
                      setItemForm({
                        ...itemForm,
                        is_active: event.target.checked,
                      })
                    }
                  />

                  <label htmlFor="item-active">
                    Active item
                  </label>
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={closeItemModal}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  {saving ? (
                    <>
                      <RefreshCw
                        size={17}
                        className="spin"
                      />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Package size={17} />
                      {editingItem
                        ? "Update Item"
                        : "Create Item"}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showUnitModal && (
        <div className="modal-overlay">
          <div className="modal inventory-modal">
            <div className="modal-header">
              <div>
                <h2>
                  {editingUnit
                    ? "Edit Physical Unit"
                    : "Add Physical Unit"}
                </h2>

                <p>
                  Each physical unit can have different
                  specifications, serial numbers and
                  assignments.
                </p>
              </div>

              <button
                className="icon-btn"
                onClick={closeUnitModal}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={saveUnit}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Inventory Item *</label>

                  <select
                    value={unitForm.item}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        item: event.target.value,
                      })
                    }
                    required
                  >
                    <option value="">
                      Select item
                    </option>

                    {items.map((item) => (
                      <option
                        key={item.id}
                        value={item.id}
                      >
                        {item.item_code} — {item.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Serial Number</label>

                  <input
                    type="text"
                    value={unitForm.serial_number}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        serial_number: event.target.value,
                      })
                    }
                    placeholder="Manufacturer serial number"
                  />
                </div>

                <div className="form-group">
                  <label>Status</label>

                  <select
                    value={unitForm.status}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        status: event.target.value,
                      })
                    }
                  >
                    <option value="IN_STOCK">
                      In Stock
                    </option>
                    <option value="ASSIGNED">
                      Assigned
                    </option>
                    <option value="LOST">
                      Lost
                    </option>
                    <option value="DISPOSED">
                      Disposed
                    </option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Condition</label>

                  <select
                    value={unitForm.condition}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        condition: event.target.value,
                      })
                    }
                  >
                    <option value="GOOD">Good</option>
                    <option value="FAIR">Fair</option>
                    <option value="POOR">Poor</option>
                    <option value="DAMAGED">
                      Damaged
                    </option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Location</label>

                  <select
                    value={unitForm.location}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        location: event.target.value,
                      })
                    }
                  >
                    <option value="">
                      Select location
                    </option>

                    {locations.map((location) => (
                      <option
                        key={location.id}
                        value={location.id}
                      >
                        {location.name ||
                          location.location_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Assigned Employee</label>

                  <select
                    value={unitForm.assigned_to}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        assigned_to: event.target.value,
                      })
                    }
                  >
                    <option value="">
                      Unassigned
                    </option>

                    {employees.map((employee) => (
                      <option
                        key={employee.id}
                        value={employee.id}
                      >
                        {getEmployeeName(employee.id)}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Purchase Price</label>

                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={unitForm.purchase_price}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        purchase_price: event.target.value,
                      })
                    }
                  />
                </div>

                <div className="form-group">
                  <label>Purchase Date</label>

                  <input
                    type="date"
                    value={unitForm.purchase_date}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        purchase_date: event.target.value,
                      })
                    }
                  />
                </div>

                <div className="form-group">
                  <label>Warranty Expiry</label>

                  <input
                    type="date"
                    value={unitForm.warranty_expiry}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        warranty_expiry: event.target.value,
                      })
                    }
                  />
                </div>

                <div className="form-group full-width">
                  <label>
                    Physical Unit Specifications
                  </label>

                  <textarea
                    rows="5"
                    value={unitForm.specifications}
                    onChange={(event) =>
                      setUnitForm({
                        ...unitForm,
                        specifications: event.target.value,
                      })
                    }
                    placeholder={
                      '{"ram":"8 GB","storage":"256 GB SSD","processor":"Intel Core i5"}'
                    }
                  />

                  <small className="form-help">
                    Example: DL001 can have 8 GB RAM while
                    DL002 has 16 GB RAM. Specifications belong
                    to the physical unit.
                  </small>
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={closeUnitModal}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  {saving ? (
                    <>
                      <RefreshCw
                        size={17}
                        className="spin"
                      />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Package size={17} />
                      {editingUnit
                        ? "Update Unit"
                        : "Create Unit"}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showImportModal && (
        <div className="modal-overlay">
          <div className="modal import-modal">
            <div className="modal-header">
              <div>
                <h2>Import Inventory Items</h2>

                <p>
                  Upload an Excel spreadsheet containing
                  inventory item records.
                </p>
              </div>

              <button
                className="icon-btn"
                onClick={closeImportModal}
                disabled={importing}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleImport}>
              <div className="import-content">
                <div className="import-info">
                  <FileSpreadsheet size={46} />

                  <h3>Import Items from Excel</h3>

                  <p>
                    Select an <strong>.xlsx</strong> file.
                    The inventory importer will validate the
                    spreadsheet before creating the records.
                  </p>
                </div>

                <label
                  htmlFor="inventory-import-file"
                  className="file-upload-box"
                >
                  <Upload size={28} />

                  <span>
                    {importFile
                      ? importFile.name
                      : "Choose Excel file"}
                  </span>

                  <small>
                    Supported format: .xlsx
                  </small>
                </label>

                <input
                  id="inventory-import-file"
                  type="file"
                  accept=".xlsx"
                  className="hidden-file-input"
                  onChange={(event) =>
                    setImportFile(
                      event.target.files?.[0] || null
                    )
                  }
                />

                {importResult && (
                  <div
                    className={`import-result ${
                      importResult.success
                        ? "success"
                        : "failed"
                    }`}
                  >
                    {importResult.success
                      ? "Import request completed successfully."
                      : "Import failed. Review the validation errors."}
                  </div>
                )}

                <div className="import-notes">
                  <strong>Recommended columns</strong>

                  <span>
                    Item Code, Name, Category, Brand, Model,
                    Supplier, Unit, Reorder Level, Minimum
                    Stock, Description, Specifications
                  </span>
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={closeImportModal}
                  disabled={importing}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={importing || !importFile}
                >
                  {importing ? (
                    <>
                      <RefreshCw
                        size={17}
                        className="spin"
                      />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <FileSpreadsheet size={17} />
                      Upload & Validate
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Inventory;
