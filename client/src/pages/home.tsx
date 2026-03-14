import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Activity,
  Building2,
  TrendingUp,
  Users,
  ArrowRight,
  Shield,
  HeartPulse,
  BarChart3,
} from "lucide-react";

const features = [
  {
    icon: Activity,
    title: "Financial MRI",
    description:
      "Get a comprehensive health score for your finances. Our AI analyzes debt, savings, pension, and investment efficiency.",
  },
  {
    icon: Building2,
    title: "FIC Optimization",
    description:
      "Maximize your Family Investment Company structure with intelligent dividend strategies and tax-efficient capital allocation.",
  },
  {
    icon: TrendingUp,
    title: "Scenario Modeling",
    description:
      "Compare conservative, balanced, and aggressive strategies with projected returns and tax impact analysis.",
  },
  {
    icon: Users,
    title: "Advisor Marketplace",
    description:
      "Connect with verified wealth advisors who specialize in healthcare professional finances.",
  },
];

const stats = [
  { value: "2,400+", label: "Healthcare Professionals" },
  { value: "340M", label: "Assets Under Guidance" },
  { value: "98%", label: "Client Satisfaction" },
  { value: "47", label: "Verified Advisors" },
];

export default function Home() {
  return (
    <div className="min-h-screen overflow-y-auto">
      <section className="relative py-20 px-6 lg:px-12">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/30 dark:from-primary/10 dark:to-accent/10" />
        <div className="relative max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            <HeartPulse className="h-4 w-4" />
            Healthcare Wealth Management
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6"
            data-testid="text-hero-title"
          >
            Grow & Protect Your
            <span className="text-primary block mt-1">Healthcare Wealth</span>
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            Purpose-built wealth management for doctors, consultants, and
            healthcare professionals. AI-powered financial insights, FIC
            optimization, and pension planning.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/dashboard">
              <Button size="lg" data-testid="button-get-started">
                Open Dashboard
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/mri">
              <Button size="lg" variant="outline" data-testid="button-run-mri">
                Run Financial MRI
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="py-12 px-6 lg:px-12">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center" data-testid={`stat-${stat.label.toLowerCase().replace(/\s/g, "-")}`}>
                <p className="text-2xl md:text-3xl font-bold text-primary">
                  {stat.value}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 px-6 lg:px-12">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">
              Intelligent Wealth Tools
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Every tool designed specifically for UK healthcare professionals
              managing complex financial structures.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {features.map((feature) => (
              <Card
                key={feature.title}
                className="hover-elevate"
                data-testid={`card-feature-${feature.title.toLowerCase().replace(/\s/g, "-")}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
                      <feature.icon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1">{feature.title}</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 px-6 lg:px-12">
        <div className="max-w-5xl mx-auto">
          <Card>
            <CardContent className="p-8 md:p-12 text-center">
              <Shield className="h-10 w-10 text-primary mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-3">
                Built for Healthcare Professionals
              </h2>
              <p className="text-muted-foreground max-w-lg mx-auto mb-6">
                Whether you're a GP partner, locum, or hospital consultant,
                GroPro understands the unique financial landscape of medical
                professionals in the UK and Ireland.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Link href="/mri">
                  <Button data-testid="button-start-mri-cta">
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Start Your Financial MRI
                  </Button>
                </Link>
                <Link href="/advisors">
                  <Button variant="outline" data-testid="button-find-advisor-cta">
                    Find an Advisor
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <footer className="py-8 px-6 text-center border-t">
        <p className="text-sm text-muted-foreground">
          GroPro Healthcare Holding Co. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
