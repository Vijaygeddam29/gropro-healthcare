import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TrendingUp, Plus, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { type Investment, insertInvestmentSchema } from "@shared/schema";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { z } from "zod";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";

const COLORS = [
  "hsl(200, 85%, 42%)",
  "hsl(160, 75%, 32%)",
  "hsl(280, 70%, 38%)",
  "hsl(40, 85%, 42%)",
  "hsl(320, 75%, 40%)",
];

const investmentFormSchema = insertInvestmentSchema.extend({
  name: z.string().min(1, "Name is required"),
  amount: z.number().min(1, "Amount must be positive"),
  projectedReturn: z.number().min(0).max(100),
});

type InvestmentFormValues = z.infer<typeof investmentFormSchema>;

const DEFAULT_USER_ID = "demo-user";

function getRiskColor(risk: string) {
  switch (risk) {
    case "conservative":
      return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
    case "balanced":
      return "bg-amber-500/10 text-amber-600 dark:text-amber-400";
    case "aggressive":
      return "bg-red-500/10 text-red-600 dark:text-red-400";
    default:
      return "bg-muted text-muted-foreground";
  }
}

export default function InvestmentsPage() {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);

  const { data: investments, isLoading } = useQuery<Investment[]>({
    queryKey: ["/api/investments"],
  });

  const form = useForm<InvestmentFormValues>({
    resolver: zodResolver(investmentFormSchema),
    defaultValues: {
      userId: DEFAULT_USER_ID,
      ficId: null,
      name: "",
      type: "ETF",
      amount: 10000,
      projectedReturn: 7,
      riskLevel: "balanced",
    },
  });

  const mutation = useMutation({
    mutationFn: async (data: InvestmentFormValues) => {
      const res = await apiRequest("POST", "/api/investments", data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/investments"] });
      form.reset();
      setOpen(false);
      toast({ title: "Investment Added", description: "Your investment has been recorded." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to add investment", variant: "destructive" });
    },
  });

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency: "GBP",
      maximumFractionDigits: 0,
    }).format(v);

  const totalValue = investments?.reduce((s, i) => s + i.amount, 0) ?? 0;

  const byType = investments
    ? Object.entries(
        investments.reduce(
          (acc, inv) => {
            acc[inv.type] = (acc[inv.type] || 0) + inv.amount;
            return acc;
          },
          {} as Record<string, number>,
        ),
      ).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="p-6 overflow-y-auto h-full space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-investments-title">Investments</h1>
          <p className="text-sm text-muted-foreground">
            Track and manage your investment portfolio
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="button-add-investment">
              <Plus className="mr-2 h-4 w-4" />
              Add Investment
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Investment</DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
                className="space-y-4"
              >
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Investment Name</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="e.g. Vanguard FTSE 100" data-testid="input-inv-name" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Type</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger data-testid="select-inv-type">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="ETF">ETF</SelectItem>
                            <SelectItem value="Property">Property</SelectItem>
                            <SelectItem value="Venture">Venture Capital</SelectItem>
                            <SelectItem value="Bonds">Bonds</SelectItem>
                            <SelectItem value="SIPP">SIPP</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="riskLevel"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Risk Level</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger data-testid="select-inv-risk">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="conservative">Conservative</SelectItem>
                            <SelectItem value="balanced">Balanced</SelectItem>
                            <SelectItem value="aggressive">Aggressive</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="amount"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Amount</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            {...field}
                            onChange={(e) => field.onChange(Number(e.target.value))}
                            data-testid="input-inv-amount"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="projectedReturn"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Projected Return %</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.1"
                            {...field}
                            onChange={(e) => field.onChange(Number(e.target.value))}
                            data-testid="input-inv-return"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <Button type="submit" className="w-full" disabled={mutation.isPending} data-testid="button-submit-investment">
                  {mutation.isPending ? "Adding..." : "Add Investment"}
                </Button>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-1" data-testid="card-portfolio-breakdown">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Portfolio Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {byType.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={byType}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {byType.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v: number) => formatCurrency(v)}
                      contentStyle={{
                        background: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "6px",
                        fontSize: "12px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2 mt-2">
                  {byType.map((item, i) => (
                    <div key={item.name} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: COLORS[i % COLORS.length] }}
                        />
                        <span>{item.name}</span>
                      </div>
                      <span className="text-muted-foreground">{formatCurrency(item.value)}</span>
                    </div>
                  ))}
                  <div className="pt-2 border-t flex items-center justify-between text-sm font-semibold">
                    <span>Total</span>
                    <span>{formatCurrency(totalValue)}</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
                <div className="text-center">
                  <TrendingUp className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p>No investments yet</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2" data-testid="card-investments-table">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">All Investments</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-12" />
                ))}
              </div>
            ) : investments && investments.length > 0 ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Risk</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead className="text-right">Return</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {investments.map((inv) => (
                      <TableRow key={inv.id} data-testid={`row-investment-${inv.id}`}>
                        <TableCell className="font-medium">{inv.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{inv.type}</Badge>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`text-xs font-medium px-2 py-0.5 rounded-full ${getRiskColor(inv.riskLevel)}`}
                          >
                            {inv.riskLevel}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">{formatCurrency(inv.amount)}</TableCell>
                        <TableCell className="text-right">
                          <span className="flex items-center justify-end gap-1">
                            {inv.projectedReturn}%
                            {inv.projectedReturn >= 5 ? (
                              <ArrowUpRight className="h-3.5 w-3.5 text-emerald-500" />
                            ) : (
                              <ArrowDownRight className="h-3.5 w-3.5 text-amber-500" />
                            )}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
                <div className="text-center">
                  <TrendingUp className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p>Add your first investment to see it here</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
