import type { ReactNode } from "react";

import { Navbar } from "@/components/layout/navbar";
import { Sidebar } from "@/components/layout/sidebar";

/**
 * Responsive dashboard frame: fixed sidebar on desktop (>= md), slide-over
 * sidebar on mobile (via Navbar's Sheet trigger), sticky top navbar, and a
 * scrollable content region. All dashboard route groups render inside this.
 */
export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-muted/30">
      <aside className="hidden md:block">
        <Sidebar />
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
