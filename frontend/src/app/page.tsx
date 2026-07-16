import { ArrowRight, Globe2, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Marketing/entry screen. Kept intentionally simple for the foundation
 * phase — links straight into the auth flow and dashboard shell.
 */
export default function HomePage() {
  const pillars = [
    {
      icon: Globe2,
      title: "Multi-region routing",
      description: "Traffic and settlement instructions route across regional nodes with locality-aware failover.",
    },
    {
      icon: ShieldCheck,
      title: "Identity-bound settlement",
      description: "Every settlement instruction is cryptographically bound to a verified identity record.",
    },
    {
      icon: Zap,
      title: "Autonomous reconciliation",
      description: "Ledger state reconciles continuously across regions without manual batch jobs.",
    },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <span className="text-sm font-semibold tracking-tight">
            Settlement<span className="text-primary">Network</span>
          </span>
          <div className="flex items-center gap-3">
            <Button variant="ghost" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild>
              <Link href="/dashboard">
                Open console
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto max-w-4xl px-6 py-24 text-center">
          <p className="mb-4 text-xs font-medium uppercase tracking-widest text-primary">
            Foundation build — no business logic yet
          </p>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Autonomous Multi-Region
            <br />
            Payment &amp; Identity Settlement Network
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-muted-foreground">
            The architectural foundation for a settlement network spanning regions, currencies, and identity
            domains — this scaffold ships the platform, not yet the product.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Button size="lg" asChild>
              <Link href="/dashboard">
                Enter console
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-6 px-6 pb-24 sm:grid-cols-3">
          {pillars.map(({ icon: Icon, title, description }) => (
            <Card key={title}>
              <CardHeader>
                <Icon className="mb-2 h-5 w-5 text-primary" />
                <CardTitle className="text-base">{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
              </CardHeader>
              <CardContent />
            </Card>
          ))}
        </section>
      </main>
    </div>
  );
}
