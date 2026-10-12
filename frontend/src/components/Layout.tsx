import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { NAV, navFor } from "../nav";
import { usePresenter } from "../presenter/Presenter";
import { Icon } from "./Icon";
import { Wordmark } from "./Wordmark";

const COLLAPSE_KEY = "georevive.sidebarCollapsed";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    return false;
  }
}

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout, can } = useAuth();
  const presenter = usePresenter();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const location = useLocation();

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  const items = NAV.filter((n) => !n.permission || can(n.permission));

  return (
    <div className="flex h-full">
      <aside
        className={`${collapsed ? "w-16" : "w-56"} flex-shrink-0 bg-brand text-sand flex flex-col transition-all duration-200`}
      >
        <div className="h-14 flex items-center px-3 border-b border-white/10">
          <Link to="/" title="GeoRevive Africa - overview">
            <Wordmark collapsed={collapsed} />
          </Link>
        </div>
        <nav className="flex-1 overflow-y-auto py-2" aria-label="Main">
          {items.map((n) => (
            <NavLink
              key={n.path}
              to={n.path}
              end={n.path === "/"}
              title={n.label}
              className={({ isActive }) =>
                `flex items-center gap-3 mx-2 my-0.5 px-3 py-2 rounded-md text-sm ${
                  isActive ? "bg-ochre text-white" : "text-sand/85 hover:bg-white/10"
                }`
              }
            >
              <Icon name={n.icon} />
              {!collapsed && <span className="truncate">{n.label}</span>}
              {!collapsed && n.step && (
                <span className="ml-auto text-[10px] rounded-full bg-white/15 px-1.5 py-0.5">{n.step}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="m-2 flex items-center justify-center gap-2 rounded-md py-2 text-sand/70 hover:bg-white/10 text-xs"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <Icon name={collapsed ? "chevronRight" : "chevronLeft"} />
          {!collapsed && "Collapse"}
        </button>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 flex-shrink-0 bg-white border-b border-sand-line flex items-center px-4 gap-3">
          <BackButton />
          <Breadcrumbs pathname={location.pathname} />
          <div className="ml-auto flex items-center gap-3">
            {user && (
              <div className="text-right leading-tight">
                <div className="text-sm font-semibold text-brand">{user.display_name}</div>
                <div className="text-[11px] text-brand/60">
                  {user.role_label} · {user.organisation}
                </div>
              </div>
            )}
            <button onClick={presenter.toggle} className={presenter.on ? "btn-accent" : "btn-ghost"} title="Presenter Mode: step guide, large text, → next step, R reset">
              <Icon name="present" size={16} />
              <span className="hidden lg:inline">Presenter</span>
            </button>
            <button onClick={logout} className="btn-ghost" title="Sign out">
              <Icon name="logout" size={16} />
              <span className="hidden xl:inline">Sign out</span>
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

function BackButton() {
  const navigate = useNavigate();
  const location = useLocation();
  if (location.pathname === "/") return null;
  return (
    <button
      className="btn-ghost px-2"
      title="Back"
      onClick={() => (window.history.length > 1 ? navigate(-1) : navigate("/"))}
    >
      <Icon name="back" size={16} />
      <span className="sr-only">Back</span>
    </button>
  );
}

export function Breadcrumbs({ pathname, extra }: { pathname: string; extra?: string }) {
  const item = navFor(pathname);
  const parts = pathname.split("/").filter(Boolean);
  return (
    <nav aria-label="Breadcrumb" className="text-sm text-brand/70 flex items-center gap-1 min-w-0">
      <Link to="/" className="hover:text-ochre">
        Home
      </Link>
      {item && item.path !== "/" && (
        <>
          <span>/</span>
          <Link to={item.path} className={`hover:text-ochre ${parts.length === 1 ? "font-semibold text-brand" : ""}`}>
            {item.label}
          </Link>
        </>
      )}
      {parts.length > 1 && (
        <>
          <span>/</span>
          <span className="font-semibold text-brand truncate">{extra || decodeURIComponent(parts[parts.length - 1])}</span>
        </>
      )}
    </nav>
  );
}
