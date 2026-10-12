import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Package,
  Car,
  Building2,
  ShoppingCart,
  Wallet,
  BarChart3,
  Boxes,
  Settings,
  Bell,
  Search,
  Menu,
  X,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";

import Login from "./pages/Login";
import Company from "./pages/Company";
import Assets from "./pages/Assets";
import Inventory from "./pages/Inventory";
import Fleet from "./pages/Fleet";
import Procurement from "./pages/Procurement";
import Finance from "./pages/Finance";
import Reports from "./pages/Reports";

import api from "./services/api";
import {
  canAccessModule,
  canCreateModule,
  canViewFinancialData,
  HIDDEN_MODULES,
  MODULE_PAGES,
} from "./utils/access";
import "./App.css";

function App() {
  const [loggedIn, setLoggedIn] = useState(
    () => Boolean(localStorage.getItem("accessToken"))
  );
  const [authChecking, setAuthChecking] = useState(
    () => Boolean(localStorage.getItem("accessToken"))
  );
  const [currentUser, setCurrentUser] = useState(
    () => localStorage.getItem("username") || "User"
  );
  const [userRoles, setUserRoles] = useState(
    () => JSON.parse(localStorage.getItem("roles") || "[]")
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState("Dashboard");

  const [dashboardData, setDashboardData] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationsLoading, setNotificationsLoading] = useState(false);

  const loadDashboardData = async () => {
    try {
      setDashboardLoading(true);

      const response = await api.get("/reports/dashboard/");
      setDashboardData(response.data);
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
    } finally {
      setDashboardLoading(false);
    }
  };
  const loadNotifications = async () => {
  try {
    setNotificationsLoading(true);

    const response = await api.get("/reports/notifications/");

    setNotifications(
      (response.data.notifications || []).filter(
        (notification) => !HIDDEN_MODULES.includes(notification.type)
      )
    );
  } catch (error) {
    console.error("Failed to load notifications:", error);
  } finally {
    setNotificationsLoading(false);
  }
};

  useEffect(() => {
    const handleAuthLogout = () => {
      setCurrentUser("User");
      setUserRoles([]);
      setDashboardData(null);
      setNotifications([]);
      setSearchQuery("");
      setSearchResults([]);
      setNotificationsOpen(false);
      setCurrentPage("Dashboard");
      setLoggedIn(false);
    };

    window.addEventListener("auth:logout", handleAuthLogout);
    return () => window.removeEventListener("auth:logout", handleAuthLogout);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      if (!localStorage.getItem("accessToken")) {
        setAuthChecking(false);
        return;
      }

      try {
        const response = await api.get("/auth/me/");
        if (cancelled) return;

        const user = response.data;
        const roles = user.roles || [];
        localStorage.setItem("username", user.username || "User");
        localStorage.setItem("roles", JSON.stringify(roles));
        setCurrentUser(user.username || "User");
        setUserRoles(roles);
        setLoggedIn(true);
      } catch {
        if (!cancelled) {
          localStorage.removeItem("accessToken");
          localStorage.removeItem("refreshToken");
          localStorage.removeItem("username");
          localStorage.removeItem("roles");
          setLoggedIn(false);
          setUserRoles([]);
        }
      } finally {
        if (!cancelled) setAuthChecking(false);
      }
    };

    restoreSession();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!loggedIn) return;

    loadDashboardData();
    loadNotifications();
  }, [loggedIn]);

  if (authChecking) {
    return (
      <div className="dashboard-loading">
        <RefreshCw size={28} className="dashboard-spinner" />
        <p>Checking your session...</p>
      </div>
    );
  }

  if (!loggedIn) {
  return (
    <Login
      onLogin={(user) => {
        const userName =
          typeof user === "string"
            ? user
            : user?.username ||
              localStorage.getItem("username") ||
              "User";

        const roles =
          typeof user === "string"
            ? JSON.parse(localStorage.getItem("roles") || "[]")
            : user?.roles || [];

        setCurrentUser(userName);
        setUserRoles(roles);
        setCurrentPage("Dashboard");
        setLoggedIn(true);
      }}
    />
  );
}
  const handleSearch = async (value) => {
  setSearchQuery(value);

  if (!value.trim()) {
    setSearchResults([]);
    return;
  }

  try {
    setSearchLoading(true);

    const response = await api.get(
      `/reports/search/?q=${encodeURIComponent(value)}`
    );

    setSearchResults(
      (response.data.results || []).filter(
        (result) => !HIDDEN_MODULES.includes(result.type)
      )
    );
  } catch (error) {
    console.error("Search failed:", error);
    setSearchResults([]);
  } finally {
    setSearchLoading(false);
  }
};

  const navigation = [
    { name: "Dashboard", icon: LayoutDashboard, visible: true },
    {
    name: "Company",
    icon: Building2,
    visible: canAccessModule(userRoles, "company"),
  },
    { name: "Assets", icon: Boxes, visible: canAccessModule(userRoles, "assets") },
    { name: "Inventory", icon: Package, visible: canAccessModule(userRoles, "inventory") },
    { name: "Fleet", icon: Car, visible: canAccessModule(userRoles, "fleet") },
    { name: "Procurement", icon: ShoppingCart, visible: canAccessModule(userRoles, "procurement") },
    { name: "Finance", icon: Wallet, visible: canAccessModule(userRoles, "finance") },
    { name: "Reports", icon: BarChart3, visible: canAccessModule(userRoles, "reports") },
  ];

  const visibleNavigation = navigation.filter((item) => item.visible);

  const navigateTo = (page) => {
    const pageModule = Object.entries(MODULE_PAGES).find(
      ([, pageName]) => pageName === page
    )?.[0];

    if (pageModule && !canAccessModule(userRoles, pageModule)) {
      return;
    }

    setCurrentPage(page);
    setSidebarOpen(false);
  };

  const formatCurrency = (value) => {
    return Number(value || 0).toLocaleString("en-NG", {
      style: "currency",
      currency: "NGN",
      minimumFractionDigits: 2,
    });
  };
  const handleLogout = () => {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("username");
  localStorage.removeItem("roles");

  setCurrentUser("User");
  setUserRoles([]);
  setDashboardData(null);
  setNotifications([]);
  setSearchQuery("");
  setSearchResults([]);
  setNotificationsOpen(false);
  setCurrentPage("Dashboard");
  setLoggedIn(false);
};
  const renderDashboard = () => {
  if (dashboardLoading && !dashboardData) {
    return (
      <div className="dashboard-loading">
        <RefreshCw size={28} className="dashboard-spinner" />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="dashboard-error">
        <AlertTriangle size={22} />

        <div>
          <strong>Unable to load dashboard</strong>
          <p>Please try refreshing the dashboard.</p>
        </div>

        <button
          className="secondary-button"
          onClick={loadDashboardData}
        >
          <RefreshCw size={17} />
          Retry
        </button>
      </div>
    );
  }

  const assets = dashboardData.assets;
  const inventory = dashboardData.inventory;
  const fleet = dashboardData.fleet;
  const procurement = dashboardData.procurement;
  const finance = dashboardData.finance;
  const canViewFinance = canViewFinancialData(userRoles);
  const canViewAssets = canAccessModule(userRoles, "assets");
  const canViewInventory = canAccessModule(userRoles, "inventory");
  const canViewFleet = canAccessModule(userRoles, "fleet");
  const canViewProcurement = canAccessModule(userRoles, "procurement");
  const recentActivity = (dashboardData.recent_activity || []).filter(
    (activity) => !HIDDEN_MODULES.includes(activity.type)
  );

  return (
    <>
      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <p className="breadcrumb">Home / Dashboard</p>

          <h1>Dashboard</h1>

          <p className="subtitle">
            Welcome back. Here's what's happening across your business.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => {
            const firstAvailable = [
              ["inventory", "Inventory"],
              ["assets", "Assets"],
              ["fleet", "Fleet"],
              ["procurement", "Procurement"],
              ["finance", "Finance"],
            ].find(([module]) => canCreateModule(userRoles, module));

            if (firstAvailable) navigateTo(firstAvailable[1]);
          }}
          disabled={!Object.keys(MODULE_PAGES).some((module) => canCreateModule(userRoles, module))}
        >
          + Add New
        </button>
      </div>

      {/* Dashboard Refresh */}
      <div className="dashboard-toolbar">
        <span>Live business overview</span>

        <button
          className="dashboard-refresh"
          onClick={loadDashboardData}
          disabled={dashboardLoading}
        >
          <RefreshCw
            size={17}
            className={dashboardLoading ? "dashboard-spinner" : ""}
          />
          Refresh
        </button>
      </div>

      {/* Main Stats */}
      <div className="stats-grid">

        {/* Assets */}
        {canViewAssets && (
        <div
          className="stat-card clickable-card"
          onClick={() => navigateTo("Assets")}
        >
          <div className="stat-icon assets-icon">
            <Boxes size={23} />
          </div>

          <div>
            <span>Total Assets</span>
            <h2>{assets.total_assets}</h2>
            <small>All registered assets</small>
          </div>
        </div>
        )}

        {/* Inventory */}
        {canViewInventory && (
        <div
          className="stat-card clickable-card"
          onClick={() => navigateTo("Inventory")}
        >
          <div className="stat-icon inventory-icon">
            <Package size={23} />
          </div>

          <div>
            <span>Inventory Items</span>
            <h2>{inventory.total_items}</h2>
            <small>
              {inventory.low_stock_items} low stock
            </small>
          </div>
        </div>
        )}

        {/* Fleet */}
        {canViewFleet && (
        <div
          className="stat-card clickable-card"
          onClick={() => navigateTo("Fleet")}
        >
          <div className="stat-icon fleet-icon">
            <Car size={23} />
          </div>

          <div>
            <span>Fleet Vehicles</span>
            <h2>{fleet.total_vehicles}</h2>
            <small>
              {fleet.available_vehicles} available
            </small>
          </div>
        </div>
        )}

        {/* Finance */}
        {canViewFinance && (
        <div
          className="stat-card clickable-card"
          onClick={() => navigateTo("Finance")}
        >
          <div className="stat-icon finance-icon">
            <Wallet size={23} />
          </div>

          <div>
            <span>Total Expenses</span>

            <h2>
              {formatCurrency(finance.total_expenses)}
            </h2>

            <small>
              {formatCurrency(finance.paid_expenses)} paid
            </small>
          </div>
        </div>
        )}

      </div>

      {/* Dashboard Cards */}
      <div className="dashboard-grid">

        {/* Business Overview */}
        <div className="dashboard-card">
          <div className="card-header">
            <div>
              <h3>Business Overview</h3>
              <p>Current operational summary</p>
            </div>

            <button onClick={() => navigateTo("Reports")}>
              View Reports
            </button>
          </div>

          <div className="overview-list">

            {canViewInventory && inventory && (
              <>
                <div className="overview-item">
                  <div className="overview-left">
                    <Package size={19} />
                    <span>Inventory</span>
                  </div>
                  <strong>{inventory.total_items} items</strong>
                </div>

                <div className="overview-item">
                  <div className="overview-left">
                    <AlertTriangle size={19} />
                    <span>Low Stock</span>
                  </div>
                  <strong className="warning-text">{inventory.low_stock_items}</strong>
                </div>
              </>
            )}

            {canViewAssets && assets && (
              <div className="overview-item">
                <div className="overview-left">
                  <Boxes size={19} />
                  <span>Assets</span>
                </div>
                <strong>{assets.total_assets}</strong>
              </div>
            )}

            {canViewFleet && fleet && (
              <div className="overview-item">
                <div className="overview-left">
                  <Car size={19} />
                  <span>Available Vehicles</span>
                </div>
                <strong className="success-text">{fleet.available_vehicles}</strong>
              </div>
            )}

            {canViewProcurement && procurement && (
              <>
                <div className="overview-item">
                  <div className="overview-left">
                    <ShoppingCart size={19} />
                    <span>Purchase Orders</span>
                  </div>
                  <strong>{procurement.total_purchase_orders}</strong>
                </div>

                <div className="overview-item">
                  <div className="overview-left">
                    <ShoppingCart size={19} />
                    <span>Supplier Invoices</span>
                  </div>
                  <strong>{procurement.total_supplier_invoices}</strong>
                </div>
              </>
            )}

            {canViewFinance && finance && (
              <div className="overview-item">
                <div className="overview-left">
                  <Wallet size={19} />
                  <span>Pending Expenses</span>
                </div>
                <strong className="warning-text">{formatCurrency(finance.pending_expenses)}</strong>
              </div>
            )}

          </div>
        </div>

        {/* Recent Activity */}
        <div className="dashboard-card">
          <div className="card-header">
            <div>
              <h3>Recent Activity</h3>
              <p>Latest activity for your access</p>
            </div>

            <button onClick={() => navigateTo("Reports")}>
              View All
            </button>
          </div>

          <div className="activity-list">

            {recentActivity.length > 0 ? (
              recentActivity.map((activity, index) => (
                <div
                  className="activity-item"
                  key={`${activity.type}-${index}`}
                >
                  <div
                    className={`activity-icon ${activity.type}`}
                  >
                    {activity.type === "asset" && (
                      <Boxes size={18} />
                    )}

                    {activity.type === "inventory" && (
                      <Package size={18} />
                    )}

                    {activity.type === "fleet" && (
                      <Car size={18} />
                    )}

                    {activity.type === "procurement" && (
                      <ShoppingCart size={18} />
                    )}

                    {activity.type === "finance" && (
                      <Wallet size={18} />
                    )}
                  </div>

                  <div className="activity-content">
                    <strong>
                      {activity.title}
                    </strong>

                    <span>
                      {new Date(
                        activity.date
                      ).toLocaleString("en-NG", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <BarChart3 size={40} />

                <h3>No recent activity</h3>

                <p>
                  Activity will appear here as you use
                  the system.
                </p>
              </div>
            )}

          </div>
        </div>

        {/* Quick Actions */}
        <div className="dashboard-card">
          <div className="card-header">
            <div>
              <h3>Quick Actions</h3>
              <p>Frequently used actions</p>
            </div>
          </div>

          <div className="quick-actions">

            {canViewInventory && (
              <button onClick={() => navigateTo("Inventory")}>
                <Package size={20} />
                <span>{canCreateModule(userRoles, "inventory") ? "Manage Inventory" : "View Inventory"}</span>
              </button>
            )}

            {canViewAssets && (
              <button onClick={() => navigateTo("Assets")}>
                <Boxes size={20} />
                <span>{canCreateModule(userRoles, "assets") ? "Manage Assets" : "View Assets"}</span>
              </button>
            )}

            {canViewFleet && (
              <button onClick={() => navigateTo("Fleet")}>
                <Car size={20} />
                <span>{canCreateModule(userRoles, "fleet") ? "Manage Fleet" : "View Fleet"}</span>
              </button>
            )}

            {canViewProcurement && (
              <button onClick={() => navigateTo("Procurement")}>
                <ShoppingCart size={20} />
                <span>New Purchase</span>
              </button>
            )}

            {canViewFinance && (
              <button onClick={() => navigateTo("Finance")}>
                <Wallet size={20} />
                <span>Manage Finance</span>
              </button>
            )}

            {canAccessModule(userRoles, "reports") && (
              <button onClick={() => navigateTo("Reports")}>
                <BarChart3 size={20} />
                <span>View Reports</span>
              </button>
            )}

          </div>
        </div>

      </div>
    </>
  );
};

  return (
    <div className="app">

      {/* Sidebar */}
      <aside
        className={`sidebar ${
          sidebarOpen ? "open" : ""
        }`}
      >
        <div className="sidebar-header">

          <div className="logo">
            <div className="logo-mark">BT</div>

            <div>
              <h2>BT Management</h2>
              <span>Business Management</span>
            </div>
          </div>

          <button
            className="mobile-close"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={22} />
          </button>

        </div>

        <nav className="navigation">

          <p className="nav-title">
            MAIN MENU
          </p>

          {visibleNavigation.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={`nav-item ${
                  currentPage === item.name
                    ? "active"
                    : ""
                }`}
                onClick={() => navigateTo(item.name)}
              >
                <Icon size={20} />
                <span>{item.name}</span>
              </button>
            );
          })}

        </nav>

        <div className="sidebar-bottom">

          <button className="nav-item">
            <Settings size={20} />
            <span>Settings</span>
          </button>

          <div className="user-card">
            <div className="avatar">
  {currentUser.charAt(0).toUpperCase()}
</div>

            <div>
              <strong>{currentUser}</strong>
              <span>Member</span>
            </div>
          </div>

          <button className="nav-item" onClick={handleLogout}>
            <span>Log out</span>
          </button>

        </div>
      </aside>

      {/* Main */}
      <main className="main-content">

        {/* Topbar */}
        <header className="topbar">

          <button
            className="mobile-menu"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={24} />
          </button>

          <div className="search-container">
  <div className="search-box">
    <Search size={19} />

    <input
      value={searchQuery}
      onChange={(e) => handleSearch(e.target.value)}
      placeholder="Search anything..."
    />

    {searchLoading && (
      <RefreshCw
        size={16}
        className="dashboard-spinner"
      />
    )}
  </div>

  {searchQuery.trim() && (
    <div className="search-results">
      {searchResults.length > 0 ? (
        searchResults.map((result) => (
          <button
            key={`${result.type}-${result.id}`}
            className="search-result"
            onClick={() => {
              const pageMap = {
                asset: "Assets",
                inventory: "Inventory",
                fleet: "Fleet",
                procurement: "Procurement",
                finance: "Finance",
              };

              navigateTo(pageMap[result.type]);
              setSearchQuery("");
              setSearchResults([]);
            }}
          >
            <div className={`search-result-icon ${result.type}`}>
              {result.type === "asset" && <Boxes size={17} />}
              {result.type === "inventory" && <Package size={17} />}
              {result.type === "fleet" && <Car size={17} />}
              {result.type === "procurement" && (
                <ShoppingCart size={17} />
              )}
              {result.type === "finance" && <Wallet size={17} />}
            </div>

            <div className="search-result-info">
              <strong>{result.title}</strong>
              <span>{result.subtitle}</span>
            </div>
          </button>
        ))
      ) : (
        <div className="search-no-results">
          No results found
        </div>
      )}
    </div>
  )}
</div>

          <div className="topbar-actions">

            <div className="notification-wrapper">
  <button
    className="icon-button"
    onClick={() => {
      setNotificationsOpen(!notificationsOpen);
      loadNotifications();
    }}
  >
    <Bell size={21} />

    {notifications.length > 0 && (
      <span className="notification-badge">
        {notifications.length > 99
          ? "99+"
          : notifications.length}
      </span>
    )}
  </button>

  {notificationsOpen && (
    <div className="notification-dropdown">
      <div className="notification-header">
        <div>
          <strong>Notifications</strong>
          <span>
            {notifications.length} alert
            {notifications.length !== 1 ? "s" : ""}
          </span>
        </div>

        <button onClick={loadNotifications}>
          <RefreshCw
            size={15}
            className={
              notificationsLoading
                ? "dashboard-spinner"
                : ""
            }
          />
        </button>
      </div>

      <div className="notification-list">
        {notifications.length > 0 ? (
          notifications.map((notification, index) => (
            <div
              className={`notification-item ${notification.level}`}
              key={`${notification.type}-${notification.id}-${index}`}
            >
              <div className="notification-icon">
                {notification.type === "inventory" && (
                  <Package size={17} />
                )}

                {notification.type === "finance" && (
                  <Wallet size={17} />
                )}

                {notification.type === "fleet" && (
                  <Car size={17} />
                )}

                {notification.type === "procurement" && (
                  <ShoppingCart size={17} />
                )}
              </div>

              <div className="notification-content">
                <strong>{notification.title}</strong>
                <p>{notification.message}</p>
              </div>
            </div>
          ))
        ) : (
          <div className="notification-empty">
            <Bell size={30} />
            <strong>You're all caught up</strong>
            <span>No notifications right now.</span>
          </div>
        )}
      </div>
    </div>
  )}
</div>

            <div className="topbar-user">
              <div className="avatar">
  {currentUser.charAt(0).toUpperCase()}
</div>

              <div className="topbar-user-info">
                <strong>{currentUser}</strong>
                <span>Member</span>
              </div>
            </div>

          </div>
        </header>

        {/* Page */}
        <section className="page-content">

                  {currentPage === "Company" ? (
                    <Company />
                  ) : currentPage === "Assets" ? (
            <Assets />
          ) : currentPage === "Inventory" ? (
            <Inventory />
          ) : currentPage === "Fleet" ? (
            <Fleet />
          ) : currentPage === "Procurement" && canAccessModule(userRoles, "procurement") ? (
            <Procurement />
          ) : currentPage === "Finance" && canAccessModule(userRoles, "finance") ? (
            <Finance />
          ) : currentPage === "Reports" ? (
            <Reports userRoles={userRoles} />
          ) : (
            renderDashboard()
          )}

        </section>

      </main>

      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

    </div>
    
  );
}

export default App;