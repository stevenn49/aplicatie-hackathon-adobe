import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Activity, ArrowUpRight, BarChart3, ChevronLeft, ChevronRight, Command, Cpu, Headphones, LayoutDashboard, Menu, MessageCircle, Moon, Search, Sparkles, Sun, Users, X } from "lucide-react";
import FilterBar from "./FilterBar.jsx";
import AssistantChat from "./AssistantChat.jsx";
import { useTheme } from "../context/AppContext.jsx";

const navItems = [
  { to: "/", label: "Market Overview", icon: LayoutDashboard, end: true },
  { to: "/products", label: "Product Analysis", icon: Cpu },
  { to: "/brands", label: "Brand Intelligence", icon: Activity },
  { to: "/sentiment", label: "Sentiment Analysis", icon: MessageCircle },
  { to: "/consumers", label: "Consumer Insights", icon: Users },
  { to: "/marketing", label: "Marketing Analytics", icon: BarChart3 },
  { to: "/competitors", label: "Competitor Analysis", icon: Headphones },
  { to: "/recommendations", label: "AI Recommendations", icon: Sparkles, badge: "5" },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const pageTitle = navItems.find((item) => item.end ? location.pathname === item.to : location.pathname.startsWith(item.to))?.label || "Dashboard";

  useEffect(() => { setMobileOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); }, [location.pathname]);
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

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      {mobileOpen && <button className="mobile-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="brand-lockup"><div className="brand-mark"><Activity size={18} strokeWidth={2.5} /></div><div className="brand-wordmark">market<span>pulse</span><small>INTELLIGENCE</small></div><button className="sidebar-collapse" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>{collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}</button></div>
        <div className="workspace-switch"><span className="workspace-avatar">N</span><span className="workspace-meta"><strong>Northstar Labs</strong><small>Pro workspace</small></span><ChevronRight size={14} /></div>
        <div className="nav-caption">WORKSPACE</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navItems.map(({ to, label, icon: Icon, end, badge }) => <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} title={collapsed ? label : undefined}><Icon size={18} /><span className="nav-label">{label}</span>{badge && <span className="nav-badge">{badge}</span>}</NavLink>)}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-bottom">
          <div className="data-status"><span className="live-dot" /><span className="nav-label">All sources connected</span><span className="status-label">LIVE</span></div>
          <button className="sidebar-upgrade"><div className="upgrade-icon"><Command size={15} /></div><span className="nav-label"><strong>Unlock more insights</strong><small>Explore your Pro plan</small></span><ArrowUpRight size={14} /></button>
          <div className="profile-row"><div className="profile-avatar">SC</div><div className="profile-info"><strong>Stefan C.</strong><small>Marketing lead</small></div><button aria-label="Open account menu" className="icon-button"><Menu size={16} /></button></div>
        </div>
      </aside>
      <div className="main-column">
        <header className="topbar"><button className="mobile-menu icon-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><FilterBar /><div className="topbar-right"><button className="theme-toggle icon-button" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}</button><span className="topbar-avatar">SC</span></div></header>
        <main className="main-content"><Outlet /></main>
        <footer className="app-footer"><span>MarketPulse AI <span className="footer-dot">·</span> Market intelligence, in focus.</span><span><Search size={13} /> Data refreshed 4 min ago <span className="live-dot" /></span></footer>
      </div>
      <AssistantChat pageTitle={pageTitle} pagePath={location.pathname} />
    </div>
  );
}
