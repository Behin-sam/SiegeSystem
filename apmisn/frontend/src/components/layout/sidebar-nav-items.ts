import type { NavItem } from "@/types";

/**
 * Primary console navigation. Icons reference lucide-react icon names,
 * resolved to components in sidebar.tsx. Extend this list as new
 * domains (settlements, ledgers, regions, compliance) come online.
 */
export const navItems: NavItem[] = [
  { label: "Overview", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Settlements", href: "/dashboard/settlements", icon: "ArrowLeftRight" },
  { label: "Identity", href: "/dashboard/identity", icon: "Fingerprint" },
  { label: "Regions", href: "/dashboard/regions", icon: "Globe2" },
  { label: "Ledgers", href: "/dashboard/ledgers", icon: "BookText" },
  { label: "Compliance", href: "/dashboard/compliance", icon: "ShieldCheck" },
  { label: "Settings", href: "/dashboard/settings", icon: "Settings" },
];
