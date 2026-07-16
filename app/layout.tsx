import type { Metadata } from "next";

import { QueryProvider } from "@/components/providers/query-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

// NOTE: Deliberately using the system font stack (defined via CSS variables
// in globals.css) instead of next/font/google. This keeps the build fully
// offline-capable — no network fetch to Google Fonts is required at build
// or deploy time, which matters for air-gapped/enterprise CI environments.
// Swap in next/font/google or next/font/local here if a custom typeface is
// required later.

export const metadata: Metadata = {
  title: "Autonomous Multi-Region Payment & Identity Settlement Network",
  description: "Operations console foundation — settlement, identity, and regional routing infrastructure.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <QueryProvider>
            <TooltipProvider>{children}</TooltipProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
