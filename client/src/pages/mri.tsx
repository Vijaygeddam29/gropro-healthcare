import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  PiggyBank,
  Wallet,
  Building2,
  CreditCard,
} from "lucide-react";
import { mriInputSchema, type MriInput, type MriResult } from "@shared/schema";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

function ScoreDisplay({ result }: { result: MriResult }) {
  const getColor = (s: number) => {
    if (s >= 75) return "text-emerald-500";
    if (s >= 50) return "text-amber-500";
    return "text-red-500";
  };
  const getBg = (s: number) => {
    if (s >= 75) return "bg-emerald-500";
    if (s >= 50) return "bg-amber-500";
    return "bg-red-500";
  };

  const metrics = [
    { label: "Income", value: result.income, icon: Wallet },
    { label: "Expenses", value: result.expenses, icon: CreditCard },
    { label: "Savings", value: result.savings, icon: PiggyBank },
    { label: "Pension", value: result.pension, icon: Building2 },
    { label: "Investments", value: result.investments, icon: TrendingUp },
    { label: "Debt", value: result.debt, icon: AlertTriangle },
  ];

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency: "GBP",
      maximumFractionDigits: 0,
    }).format(v);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="relative w-36 h-36 mx-auto">
          <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
            <circle cx="60" cy="60" r="50" fill="none" stroke="hsl(var(--muted))" strokeWidth="10" />
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              stroke="currentColor"
              strokeWidth="10"
              strokeDasharray={`${(result.score / 100) * 314} 314`}
              strokeLinecap="round"
              className={getColor(result.score)}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-4xl font-bold ${getColor(result.score)}`} data-testid="text-result-score">
              {result.score}
            </span>
            <span className="text-xs text-muted-foreground">/ 100</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="flex items-center gap-2 p-2 rounded-md bg-muted/50">
            <m.icon className="h-4 w-4 text-muted-foreground shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground">{m.label}</p>
              <p className="text-sm font-medium">{formatCurrency(m.value)}</p>
            </div>
          </div>
        ))}
      </div>

      {result.advice.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Recommendations</h4>
          {result.advice.map((a, i) => (
            <div
              key={i}
              className="flex items-start gap-2 p-3 rounded-md bg-muted/40 text-sm"
              data-testid={`text-recommendation-${i}`}
            >
              {a.includes("High debt") || a.includes("Low") ? (
                <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
              )}
              <span>{a}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MriPage() {
  const { toast } = useToast();
  const [latestResult, setLatestResult] = useState<MriResult | null>(null);

  const { data: mriHistory, isLoading } = useQuery<MriResult[]>({
    queryKey: ["/api/mri"],
  });

  const form = useForm<MriInput>({
    resolver: zodResolver(mriInputSchema),
    defaultValues: {
      income: 120000,
      expenses: 60000,
      savings: 50000,
      pension: 20000,
      investments: 30000,
      debt: 10000,
    },
  });

  const mutation = useMutation({
    mutationFn: async (data: MriInput) => {
      const res = await apiRequest("POST", "/api/mri", data);
      return res.json();
    },
    onSuccess: (data: MriResult) => {
      setLatestResult(data);
      queryClient.invalidateQueries({ queryKey: ["/api/mri"] });
      toast({ title: "Financial MRI Complete", description: `Your score: ${data.score}/100` });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to calculate MRI", variant: "destructive" });
    },
  });

  const displayResult = latestResult || (mriHistory && mriHistory.length > 0 ? mriHistory[mriHistory.length - 1] : null);

  const fields: { name: keyof MriInput; label: string; icon: typeof Wallet }[] = [
    { name: "income", label: "Annual Income", icon: Wallet },
    { name: "expenses", label: "Annual Expenses", icon: CreditCard },
    { name: "savings", label: "Total Savings", icon: PiggyBank },
    { name: "pension", label: "Pension Value", icon: Building2 },
    { name: "investments", label: "Investments", icon: TrendingUp },
    { name: "debt", label: "Total Debt", icon: AlertTriangle },
  ];

  return (
    <div className="p-6 overflow-y-auto h-full space-y-6">
      <div>
        <h1 className="text-2xl font-bold" data-testid="text-mri-title">Financial MRI</h1>
        <p className="text-sm text-muted-foreground">
          Comprehensive financial health assessment for healthcare professionals
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card data-testid="card-mri-form">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Enter Your Financial Data
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
                className="space-y-4"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {fields.map((f) => (
                    <FormField
                      key={f.name}
                      control={form.control}
                      name={f.name}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-xs flex items-center gap-1.5">
                            <f.icon className="h-3.5 w-3.5 text-muted-foreground" />
                            {f.label}
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              {...field}
                              onChange={(e) => field.onChange(Number(e.target.value))}
                              data-testid={`input-${f.name}`}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  ))}
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={mutation.isPending}
                  data-testid="button-calculate-mri"
                >
                  {mutation.isPending ? "Calculating..." : "Calculate Financial MRI"}
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>

        <Card data-testid="card-mri-result">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              MRI Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            {mutation.isPending ? (
              <div className="space-y-4">
                <Skeleton className="h-36 w-36 rounded-full mx-auto" />
                <Skeleton className="h-20" />
              </div>
            ) : displayResult ? (
              <ScoreDisplay result={displayResult} />
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
                <div className="text-center">
                  <Activity className="h-10 w-10 mx-auto mb-3 opacity-30" />
                  <p>Enter your financial data and click Calculate</p>
                  <p className="text-xs mt-1 opacity-60">
                    Your score will appear here
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {mriHistory && mriHistory.length > 1 && (
        <Card data-testid="card-mri-history">
          <CardHeader>
            <CardTitle className="text-base">Score History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {mriHistory
                .slice()
                .reverse()
                .map((r, i) => (
                  <div
                    key={r.id}
                    className="flex items-center justify-between p-3 rounded-md bg-muted/30"
                    data-testid={`mri-history-${i}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="text-lg font-bold">{r.score}</div>
                      <div className="text-xs text-muted-foreground">
                        {r.createdAt ? new Date(r.createdAt).toLocaleDateString() : ""}
                      </div>
                    </div>
                    <Progress value={r.score} className="w-24 h-2" />
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
