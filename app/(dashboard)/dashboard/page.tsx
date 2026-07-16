"use client";

import { motion } from "framer-motion";
import { ArrowLeftRight, Fingerprint, Globe2, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Dashboard overview shell. Displays structural placeholder metrics only —
 * no live data wiring yet, since business/domain logic is out of scope for
 * this phase. Cards demonstrate the layout grid future widgets will use.
 */
const metrics = [
  { label: "Active regions", value: "—", icon: Globe2, status: "Pending integration" },
  { label: "Settlements today", value: "—", icon: ArrowLeftRight, status: "Pending integration" },
  { label: "Verified identities", value: "—", icon: Fingerprint, status: "Pending integration" },
  { label: "Compliance flags", value: "—", icon: ShieldCheck, status: "Pending integration" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <Badge variant="secondary">Foundation build</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Structural scaffold for the settlement network console. Widgets below are placeholders pending
          domain logic.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric, i) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: i * 0.05 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{metric.label}</CardTitle>
                <metric.icon className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">{metric.value}</div>
                <p className="mt-1 text-xs text-muted-foreground">{metric.status}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Next steps</CardTitle>
          <CardDescription>This foundation is ready for domain logic to be layered in.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="list-inside list-disc space-y-1.5 text-sm text-muted-foreground">
            <li>Wire settlement, identity, and ledger data models on the backend.</li>
            <li>Replace placeholder metrics with live React Query-backed widgets.</li>
            <li>Add role-based access control on top of the existing JWT auth.</li>
            <li>Introduce region-aware routing and reconciliation services.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
