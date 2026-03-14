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
import { Building2, Plus, TrendingUp, Percent, PoundSterling } from "lucide-react";
import { type Fic, insertFicSchema } from "@shared/schema";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { z } from "zod";

const ficFormSchema = insertFicSchema.extend({
  ficName: z.string().min(1, "Name is required"),
  capital: z.number().min(1, "Capital must be positive"),
  corporationTax: z.number().min(0).max(1),
});

type FicFormValues = z.infer<typeof ficFormSchema>;

const DEFAULT_USER_ID = "demo-user";

function FicCard({ fic }: { fic: Fic }) {
  const formatCurrency = (v: number) =>
    new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency: "GBP",
      maximumFractionDigits: 0,
    }).format(v);

  const scenarios = [
    { label: "Conservative", rate: 0.04 },
    { label: "Balanced", rate: 0.07 },
    { label: "Aggressive", rate: 0.12 },
  ];

  return (
    <Card className="hover-elevate" data-testid={`card-fic-${fic.id}`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-2 mb-4">
          <div>
            <h3 className="font-semibold" data-testid={`text-fic-name-${fic.id}`}>{fic.ficName}</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Created {fic.createdAt ? new Date(fic.createdAt).toLocaleDateString() : ""}
            </p>
          </div>
          <Badge variant="secondary">{fic.dividendStrategy}</Badge>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="p-2 rounded-md bg-muted/40">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <PoundSterling className="h-3 w-3" />
              Capital
            </p>
            <p className="text-sm font-semibold">{formatCurrency(fic.capital)}</p>
          </div>
          <div className="p-2 rounded-md bg-muted/40">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Percent className="h-3 w-3" />
              Corp Tax
            </p>
            <p className="text-sm font-semibold">{(fic.corporationTax * 100).toFixed(0)}%</p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Projected Annual Returns</p>
          {scenarios.map((s) => (
            <div key={s.label} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{s.label}</span>
              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                {formatCurrency(fic.capital * s.rate)}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function FicsPage() {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);

  const { data: fics, isLoading } = useQuery<Fic[]>({
    queryKey: ["/api/fics"],
  });

  const form = useForm<FicFormValues>({
    resolver: zodResolver(ficFormSchema),
    defaultValues: {
      userId: DEFAULT_USER_ID,
      ficName: "",
      capital: 100000,
      corporationTax: 0.19,
      dividendStrategy: "balanced",
    },
  });

  const mutation = useMutation({
    mutationFn: async (data: FicFormValues) => {
      const res = await apiRequest("POST", "/api/fics", data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/fics"] });
      form.reset();
      setOpen(false);
      toast({ title: "FIC Created", description: "Your Family Investment Company has been added." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to create FIC", variant: "destructive" });
    },
  });

  return (
    <div className="p-6 overflow-y-auto h-full space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-fics-title">FIC Management</h1>
          <p className="text-sm text-muted-foreground">
            Manage your Family Investment Companies
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="button-add-fic">
              <Plus className="mr-2 h-4 w-4" />
              Add FIC
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New FIC</DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
                className="space-y-4"
              >
                <FormField
                  control={form.control}
                  name="ficName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Company Name</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="e.g. Smith Family Investments" data-testid="input-fic-name" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="capital"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Initial Capital</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          {...field}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                          data-testid="input-fic-capital"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="corporationTax"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Corporation Tax Rate</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="0.01"
                          {...field}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                          data-testid="input-fic-tax"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="dividendStrategy"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Dividend Strategy</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger data-testid="select-dividend-strategy">
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
                <Button type="submit" className="w-full" disabled={mutation.isPending} data-testid="button-submit-fic">
                  {mutation.isPending ? "Creating..." : "Create FIC"}
                </Button>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-64 rounded-md" />
          ))}
        </div>
      ) : fics && fics.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {fics.map((fic) => (
            <FicCard key={fic.id} fic={fic} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-12 text-center">
            <Building2 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-30" />
            <h3 className="font-semibold mb-1">No FICs Yet</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create your first Family Investment Company to get started
            </p>
            <Button onClick={() => setOpen(true)} data-testid="button-add-first-fic">
              <Plus className="mr-2 h-4 w-4" />
              Add Your First FIC
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
