import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Activity,
  TrendingUp,
  Building2,
  PiggyBank,
  ArrowUpRight,
  ArrowDownRight,
  Target,
  Wallet,
} from "lucide-react";
import { Link } from "wouter";
import type { MriResult, Fic, Investment } from "@shared/schema";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
} from "recharts";

const CHART_COLORS = [
  "hsl(200, 85%, 42%)",
  "hsl(160, 75%, 32%)",
  "hsl(280, 70%, 38%)",
  "hsl(40, 85%, 42%)",
  "hsl(320, 75%, 40%)",
];

function ScoreGauge({ score }: { score: number }) {
  const getColor = (s: number) => {
    if (s >= 75) return "text-emerald-500";
    if (s >= 50) return "text-amber-500";
    return "text-red-500";
  };
  const getLabel = (s: number) => {
    if (s >= 75) return "Excellent";
    if (s >= 50) return "Good";
    if (s >= 25) return "Fair";
    return "Needs Attention";
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
          <circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth="10"
          />
          <circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="currentColor"
            strokeWidth="10"
            strokeDasharray={`${(score / 100) * 314} 314`}
            strokeLinecap="round"
            className={getColor(score)}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${getColor(score)}`} data-testid="text-mri-score">
            {score}
          </span>
          <span className="text-xs text-muted-foreground">/ 100</span>
        </div>
      </div>
      <Badge variant="secondary" className="mt-2" data-testid="badge-mri-label">
        {getLabel(score)}
      </Badge>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-md" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Skeleton className="h-72 rounded-md lg:col-span-2" />
        <Skeleton className="h-72 rounded-md" />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: mriData, isLoading: mriLoading } = useQuery<MriResult[]>({
    queryKey: ["/api/mri"],
  });

  const { data: ficsData, isLoading: ficsLoading } = useQuery<Fic[]>({
    queryKey: ["/api/fics"],
  });

  const { data: investmentsData, isLoading: investmentsLoading } = useQuery<Investment[]>({
    queryKey: ["/api/investments"],
  });

  const isLoading = mriLoading || ficsLoading || investmentsLoading;

  if (isLoading) return <DashboardSkeleton />;

  const latestMri = mriData && mriData.length > 0 ? mriData[mriData.length - 1] : null;

  const totalFicCapital = ficsData?.reduce((sum, f) => sum + f.capital, 0) ?? 0;
  const totalInvestments = investmentsData?.reduce((sum, i) => sum + i.amount, 0) ?? 0;
  const avgReturn = investmentsData && investmentsData.length > 0
    ? investmentsData.reduce((sum, i) => sum + i.projectedReturn, 0) / investmentsData.length
    : 0;

  const allocationData = investmentsData
    ? Object.entries(
        investmentsData.reduce(
          (acc, inv) => {
            acc[inv.type] = (acc[inv.type] || 0) + inv.amount;
            return acc;
          },
          {} as Record<string, number>,
        ),
      ).map(([name, value]) => ({ name, value }))
    : [];

  const scenarioData = [
    { name: "Conservative", return: totalFicCapital * 0.04, tax: totalFicCapital * 0.19 },
    { name: "Balanced", return: totalFicCapital * 0.07, tax: totalFicCapital * 0.19 * 0.9 },
    { name: "Aggressive", return: totalFicCapital * 0.12, tax: totalFicCapital * 0.19 * 0.85 },
  ];

  const projectionData = Array.from({ length: 10 }, (_, i) => ({
    year: `Year ${i + 1}`,
    conservative: Math.round(totalFicCapital * Math.pow(1.04, i + 1)),
    balanced: Math.round(totalFicCapital * Math.pow(1.07, i + 1)),
    aggressive: Math.round(totalFicCapital * Math.pow(1.12, i + 1)),
  }));

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency: "GBP",
      notation: v > 999999 ? "compact" : "standard",
      maximumFractionDigits: 0,
    }).format(v);

  return (
    <div className="p-6 overflow-y-auto h-full space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-dashboard-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Your wealth overview at a glance</p>
        </div>
        <Link href="/mri">
          <Button variant="outline" size="sm" data-testid="button-run-new-mri">
            <Activity className="mr-2 h-4 w-4" />
            Run Financial MRI
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card data-testid="card-mri-score">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-1 mb-2">
              <p className="text-sm text-muted-foreground">MRI Score</p>
              <Activity className="h-4 w-4 text-primary" />
            </div>
            <p className="text-2xl font-bold">
              {latestMri ? latestMri.score : "--"}{" "}
              <span className="text-sm text-muted-foreground font-normal">/ 100</span>
            </p>
          </CardContent>
        </Card>

        <Card data-testid="card-fic-capital">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-1 mb-2">
              <p className="text-sm text-muted-foreground">FIC Capital</p>
              <Building2 className="h-4 w-4 text-primary" />
            </div>
            <p className="text-2xl font-bold">{formatCurrency(totalFicCapital)}</p>
          </CardContent>
        </Card>

        <Card data-testid="card-investments">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-1 mb-2">
              <p className="text-sm text-muted-foreground">Total Invested</p>
              <TrendingUp className="h-4 w-4 text-primary" />
            </div>
            <p className="text-2xl font-bold">{formatCurrency(totalInvestments)}</p>
          </CardContent>
        </Card>

        <Card data-testid="card-avg-return">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-1 mb-2">
              <p className="text-sm text-muted-foreground">Avg. Return</p>
              <Target className="h-4 w-4 text-primary" />
            </div>
            <p className="text-2xl font-bold flex items-center gap-1">
              {avgReturn.toFixed(1)}%
              {avgReturn > 5 ? (
                <ArrowUpRight className="h-4 w-4 text-emerald-500" />
              ) : (
                <ArrowDownRight className="h-4 w-4 text-amber-500" />
              )}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2" data-testid="card-projection-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">10-Year Capital Projection</CardTitle>
          </CardHeader>
          <CardContent>
            {totalFicCapital > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={projectionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis
                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                    tick={{ fontSize: 11 }}
                    stroke="hsl(var(--muted-foreground))"
                  />
                  <Tooltip
                    formatter={(v: number) => formatCurrency(v)}
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                  />
                  <Area type="monotone" dataKey="conservative" stroke={CHART_COLORS[1]} fill={CHART_COLORS[1]} fillOpacity={0.1} strokeWidth={2} />
                  <Area type="monotone" dataKey="balanced" stroke={CHART_COLORS[0]} fill={CHART_COLORS[0]} fillOpacity={0.15} strokeWidth={2} />
                  <Area type="monotone" dataKey="aggressive" stroke={CHART_COLORS[2]} fill={CHART_COLORS[2]} fillOpacity={0.1} strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-60 flex items-center justify-center text-muted-foreground text-sm">
                <div className="text-center">
                  <PiggyBank className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p>Add a FIC to see capital projections</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card data-testid="card-mri-gauge">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Financial Health</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center">
            {latestMri ? (
              <>
                <ScoreGauge score={latestMri.score} />
                <div className="mt-4 w-full space-y-2">
                  {latestMri.advice.slice(0, 3).map((a, i) => (
                    <div
                      key={i}
                      className="text-xs text-muted-foreground flex items-start gap-2"
                      data-testid={`text-advice-${i}`}
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1 shrink-0" />
                      {a}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
                <div className="text-center">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p>Run your first Financial MRI</p>
                  <Link href="/mri">
                    <Button size="sm" variant="outline" className="mt-3" data-testid="button-first-mri">
                      Get Started
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card data-testid="card-allocation">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Capital Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            {allocationData.length > 0 ? (
              <div className="flex items-center gap-6">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie
                      data={allocationData}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {allocationData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2 flex-1">
                  {allocationData.map((item, i) => (
                    <div key={item.name} className="flex items-center justify-between text-sm" data-testid={`allocation-${item.name.toLowerCase()}`}>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }}
                        />
                        <span>{item.name}</span>
                      </div>
                      <span className="text-muted-foreground">{formatCurrency(item.value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-40 flex items-center justify-center text-muted-foreground text-sm">
                <div className="text-center">
                  <Wallet className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p>No investments yet</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card data-testid="card-scenarios">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Scenario Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            {totalFicCapital > 0 ? (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={scenarioData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis
                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                    tick={{ fontSize: 11 }}
                    stroke="hsl(var(--muted-foreground))"
                  />
                  <Tooltip
                    formatter={(v: number) => formatCurrency(v)}
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="return" fill={CHART_COLORS[0]} radius={[4, 4, 0, 0]} name="Return" />
                  <Bar dataKey="tax" fill={CHART_COLORS[3]} radius={[4, 4, 0, 0]} name="Tax" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-44 flex items-center justify-center text-muted-foreground text-sm">
                <div className="text-center">
                  <Building2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p>Add a FIC to see scenarios</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
