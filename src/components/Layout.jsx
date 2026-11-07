import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Activity, ArrowUpRight, BarChart3, ChevronLeft, ChevronRight, Command, Cpu, Headphones, LayoutDashboard, Menu, MessageCircle, Moon, Search, Sparkles, Sun, Users } from "lucide-react";
import FilterBar from "./FilterBar.jsx";
import { useTheme } from "../context/AppContext.jsx";
import { apiBaseUrl, getHealth, getRecommendations } from "../services/api.js";

const navItems = [
  { to: "/", label: "Market Overview", icon: LayoutDashboard, end: true },
  { to: "/products", label: "Product Analysis", icon: Cpu },
  { to: "/brands", label: "Brand Intelligence", icon: Activity },
  { to: "/sentiment", label: "Sentiment Analysis", icon: MessageCircle },
  { to: "/consumers", label: "Consumer Insights", icon: Users },
  { to: "/marketing", label: "Marketing Analytics", icon: BarChart3 },
  { to: "/competitors", label: "Competitor Analysis", icon: Headphones },
  { to: "/recommendations", label: "AI Recommendations", icon: Sparkles },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [health, setHealth] = useState(null);
  const [recommendationCount, setRecommendationCount] = useState(null);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  useEffect(() => { setMobileOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); }, [location.pathname]);

  useEffect(() => {
    let active = true;
    getHealth()
      .then((data) => { if (active) setHealth(data); })
      .catch(() => { if (active) setHealth(null); });
    getRecommendations({})
      .then((data) => { if (active) setRecommendationCount(data.items.length); })
      .catch(() => { if (active) setRecommendationCount(null); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        document.querySelector(".global-search input")?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const databaseOk = health?.database === "healthy";
  const sourceLabel = health
    ? databaseOk ? "Database connected" : "Database unreachable"
    : "API unreachable";
  const sourceStatus = health ? (databaseOk ? "LIVE" : "DOWN") : "OFFLINE";

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      {mobileOpen && <button className="mobile-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><Activity size={18} strokeWidth={2.5} /></div>
          <div className="brand-wordmark">market<span>pulse</span><small>INTELLIGENCE</small></div>
          <button className="sidebar-collapse" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
        <div className="workspace-switch">
          <span className="workspace-avatar">M</span>
          <span className="workspace-meta"><strong>MarketPulse</strong><small>{health?.environment || "local"} workspace</small></span>
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} title={collapsed ? label : undefined}>
              <Icon size={18} />
              <span className="nav-label">{label}</span>
              {to === "/recommendations" && recommendationCount !== null && <span className="nav-badge">{recommendationCount}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-bottom">
          <div className="data-status">
            <span className={databaseOk ? "live-dot" : "live-dot offline"} />
            <span className="nav-label">{sourceLabel}</span>
            <span className="status-label">{sourceStatus}</span>
          </div>
          <button className="sidebar-upgrade" onClick={() => window.open(`${apiBaseUrl}/docs`, "_blank", "noopener")}>
            <div className="upgrade-icon"><Command size={15} /></div>
            <span className="nav-label"><strong>API documentation</strong><small>OpenAPI schema</small></span>
            <ArrowUpRight size={14} />
          </button>
        </div>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <button className="mobile-menu icon-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <FilterBar />
          <div className="topbar-right">
            <button className="theme-toggle icon-button" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <span className="topbar-avatar">MP</span>
          </div>
        </header>
        <main className="main-content"><Outlet /></main>
        <footer className="app-footer">
          <span>MarketPulse AI <span className="footer-dot">·</span> Market intelligence, in focus.</span>
          <span><Search size={13} /> {health ? `${health.llm === "configured" ? "LLM connected" : "LLM not configured"} · ${health.database_backend}` : "API unreachable"} <span className={databaseOk ? "live-dot" : "live-dot offline"} /></span>
        </footer>
      </div>
    </div>
  );
}
