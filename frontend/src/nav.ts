// Navigation: single list used by the sidebar, breadcrumbs and route guards.
export interface NavItem {
  path: string;
  label: string;
  icon: string;
  permission?: string; // hidden unless the user's role has this permission
  step?: number; // master demo path step
}

export const NAV: NavItem[] = [
  { path: "/", label: "Overview", icon: "home" },
  { path: "/sources", label: "Data Sources", icon: "database", permission: "sources.view", step: 1 },
  { path: "/rescue", label: "Data Rescue", icon: "scan", permission: "rescue.view", step: 2 },
  { path: "/review", label: "Review Queue", icon: "check", permission: "facts.review" },
  { path: "/map", label: "Map Explorer", icon: "map", permission: "layers.view_all", step: 3 },
  { path: "/prospectivity", label: "Prospectivity", icon: "target", permission: "model.view", step: 4 },
  { path: "/claims", label: "Claim Check", icon: "report", permission: "claims.create", step: 5 },
  { path: "/dataroom", label: "Data Room", icon: "lock", permission: "dataroom.view", step: 6 },
  { path: "/audit", label: "Audit Log", icon: "list", permission: "audit.view" },
  { path: "/help", label: "How to use", icon: "help" },
];

export function navFor(pathname: string): NavItem | undefined {
  if (pathname === "/") return NAV[0];
  return NAV.filter((n) => n.path !== "/").find((n) => pathname.startsWith(n.path));
}
