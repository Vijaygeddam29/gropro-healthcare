import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import {
  Users,
  CheckCircle2,
  Star,
  Mail,
  MapPin,
  Search,
  Briefcase,
} from "lucide-react";
import type { Advisor } from "@shared/schema";
import { useState } from "react";

function AdvisorCard({ advisor }: { advisor: Advisor }) {
  const initials = advisor.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase();

  return (
    <Card className="hover-elevate" data-testid={`card-advisor-${advisor.id}`}>
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <Avatar className="h-12 w-12">
            <AvatarFallback className="bg-primary/10 text-primary font-semibold text-sm">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold" data-testid={`text-advisor-name-${advisor.id}`}>
                {advisor.name}
              </h3>
              {advisor.verified && (
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">{advisor.specialty}</p>
          </div>
        </div>

        <p className="text-sm text-muted-foreground mt-3 line-clamp-2 leading-relaxed">
          {advisor.bio}
        </p>

        <div className="flex items-center gap-3 mt-3 flex-wrap">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Briefcase className="h-3 w-3" />
            {advisor.expertise}
          </div>
          {advisor.location && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <MapPin className="h-3 w-3" />
              {advisor.location}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between mt-4 pt-3 border-t">
          <div className="flex items-center gap-1">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                className={`h-3.5 w-3.5 ${
                  i < Math.floor(advisor.rating)
                    ? "text-amber-400 fill-amber-400"
                    : "text-muted-foreground/30"
                }`}
              />
            ))}
            <span className="text-xs text-muted-foreground ml-1">
              {advisor.rating.toFixed(1)}
            </span>
          </div>
          <Button size="sm" variant="outline" data-testid={`button-contact-${advisor.id}`}>
            <Mail className="mr-1.5 h-3.5 w-3.5" />
            Contact
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdvisorsPage() {
  const [search, setSearch] = useState("");

  const { data: advisors, isLoading } = useQuery<Advisor[]>({
    queryKey: ["/api/advisors"],
  });

  const filtered = advisors?.filter(
    (a) =>
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.expertise.toLowerCase().includes(search.toLowerCase()) ||
      a.specialty.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="p-6 overflow-y-auto h-full space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-advisors-title">
            Advisor Marketplace
          </h1>
          <p className="text-sm text-muted-foreground">
            Connect with verified wealth advisors for healthcare professionals
          </p>
        </div>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search by name, expertise, or specialty..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
          data-testid="input-advisor-search"
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-56 rounded-md" />
          ))}
        </div>
      ) : filtered && filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((advisor) => (
            <AdvisorCard key={advisor.id} advisor={advisor} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-12 text-center">
            <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-30" />
            <h3 className="font-semibold mb-1">No Advisors Found</h3>
            <p className="text-sm text-muted-foreground">
              {search
                ? "Try adjusting your search terms"
                : "Advisors will appear here once available"}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
