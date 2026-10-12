export const MODULE_ROLES = {
  company: ["Admin", "Manager"],

  assets: ["Admin", "Manager", "Asset Staff", "Read Only"],
  inventory: ["Admin", "Manager", "Inventory Staff", "Read Only"],
  fleet: ["Admin", "Manager", "Fleet Staff", "Read Only"],
  procurement: ["Admin", "Manager", "Procurement Staff", "Read Only"],
  finance: ["Admin", "Manager", "Finance Staff", "Read Only"],
  reports: [
    "Admin",
    "Manager",
    "Inventory Staff",
    "Fleet Staff",
    "Asset Staff",
    "Finance Staff",
    "Procurement Staff",
    "Read Only",
  ],
};

export const MODULE_PAGES = {
  company: "Company",

  assets: "Assets",
  inventory: "Inventory",
  fleet: "Fleet",
  procurement: "Procurement",
  finance: "Finance",
  reports: "Reports",
};

export const HIDDEN_MODULES = ["procurement", "finance"];

export function hasRole(roles = [], role) {
  return Array.isArray(roles) && roles.includes(role);
}

export function isAdmin(roles = []) {
  return hasRole(roles, "Admin");
}

export function canAccessModule(roles = [], module) {
  if (!Array.isArray(roles) || HIDDEN_MODULES.includes(module)) return false;

  const allowedRoles = MODULE_ROLES[module] || [];

  return roles.some((role) => allowedRoles.includes(role));
}

export function canCreateModule(roles = [], module) {
  if (!canAccessModule(roles, module)) return false;

  return !hasRole(roles, "Read Only");
}

export function canViewFinancialData(roles = []) {
  return (
    canAccessModule(roles, "finance") &&
    (isAdmin(roles) || hasRole(roles, "Finance Staff"))
  );
}