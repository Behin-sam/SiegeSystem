"use client";

import {
  ArrowLeftRight,
  BookText,
  Fingerprint,
  Globe2,
  LayoutDashboard,
  Network,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { navItems } from "@/components/layout/sidebar-nav-items";

const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard,
  ArrowLeftRight,
  Fingerprint,
  Globe2,
  BookText,
  ShieldCheck,
  Settings,
};

interface SidebarProps {
  className?: string;
  onNavigate?: () => void;
}

/**
 * Primary console sidebar. Fixed on desktop (see DashboardShell), rendered
 * inside a Sheet on mobile. Active route is highlighted with a sliding
 * indicator driven by Framer Motion's layout animation.
 */
export function Sidebar({ className, onNavigate }: SidebarProps) {
  const pathname = usePathname();

  return (
    <div className={cn("flex h-full w-64 flex-col bg-sidebar text-sidebar-foreground", className)}>
      <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-6">
        <Network className="h-5 w-5 text-primary" />
        <span className="text-sm font-semibold tracking-tight">
          Settlement<span className="text-primary">Network</span>
        </span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        {navItems.map((item) => {
          const Icon = iconMap[item.icon] ?? LayoutDashboard;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "text-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              )}
            >
              {isActive && (
                <motion.span
                  layoutId="sidebar-active-indicator"
                  className="absolute inset-0 rounded-md bg-sidebar-accent"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
              <Icon className="relative z-10 h-4 w-4 shrink-0" />
              <span className="relative z-10">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border px-6 py-4">
        <div className="flex items-center gap-2 text-xs text-sidebar-foreground/50">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          All regions operational
        </div>
      </div>
    </div>
  );
}
