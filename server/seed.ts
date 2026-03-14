import { db } from "./db";
import { users, fics, investments, advisors, mriResults } from "@shared/schema";
import { sql } from "drizzle-orm";
import { FinancialMRI } from "./ai-agents";

export async function seedDatabase() {
  const existingUsers = await db.select().from(users);
  if (existingUsers.length > 0) return;

  console.log("Seeding database with demo data...");

  const [demoUser] = await db
    .insert(users)
    .values({
      id: "demo-user",
      name: "Dr. Sarah Mitchell",
      email: "sarah.mitchell@nhs.net",
      role: "doctor",
      country: "UK",
      county: "London",
      profession: "GP Partner",
    })
    .returning();

  await db.insert(fics).values([
    {
      userId: demoUser.id,
      ficName: "Mitchell Family Investments Ltd",
      capital: 450000,
      corporationTax: 0.19,
      dividendStrategy: "balanced",
    },
    {
      userId: demoUser.id,
      ficName: "MedVenture Holdings Ltd",
      capital: 180000,
      corporationTax: 0.25,
      dividendStrategy: "aggressive",
    },
    {
      userId: demoUser.id,
      ficName: "Healthcare Property Co",
      capital: 320000,
      corporationTax: 0.19,
      dividendStrategy: "conservative",
    },
  ]);

  await db.insert(investments).values([
    {
      userId: demoUser.id,
      name: "Vanguard FTSE All-World ETF",
      type: "ETF",
      amount: 125000,
      projectedReturn: 7.2,
      riskLevel: "balanced",
    },
    {
      userId: demoUser.id,
      name: "iShares UK Property Fund",
      type: "Property",
      amount: 85000,
      projectedReturn: 5.4,
      riskLevel: "conservative",
    },
    {
      userId: demoUser.id,
      name: "MedTech Ventures Fund III",
      type: "Venture",
      amount: 50000,
      projectedReturn: 15.0,
      riskLevel: "aggressive",
    },
    {
      userId: demoUser.id,
      name: "UK Government Gilts",
      type: "Bonds",
      amount: 60000,
      projectedReturn: 3.8,
      riskLevel: "conservative",
    },
    {
      userId: demoUser.id,
      name: "SIPP - Fidelity Index World",
      type: "SIPP",
      amount: 200000,
      projectedReturn: 6.5,
      riskLevel: "balanced",
    },
  ]);

  await db.insert(advisors).values([
    {
      name: "James Crawford",
      expertise: "Tax Planning",
      specialty: "Healthcare FIC Structures",
      verified: true,
      rating: 4.9,
      contactEmail: "j.crawford@wealthadvisors.co.uk",
      bio: "Specialist in tax-efficient structures for NHS consultants and GP partners. 15 years helping medical professionals optimize their wealth through FICs and pension planning.",
      location: "London",
    },
    {
      name: "Dr. Emma Wilson",
      expertise: "Pension Planning",
      specialty: "NHS Pension & SIPP Optimization",
      verified: true,
      rating: 4.8,
      contactEmail: "emma@pensionpro.co.uk",
      bio: "Former GP turned financial advisor. Unique insight into NHS pension tapering, lifetime allowance planning, and SIPP contributions for medical professionals.",
      location: "Manchester",
    },
    {
      name: "Robert Chen",
      expertise: "Investment Management",
      specialty: "Medical Professional Portfolios",
      verified: true,
      rating: 4.7,
      contactEmail: "r.chen@medicalwealth.co.uk",
      bio: "Portfolio manager specializing in diversified investment strategies for healthcare professionals. Focus on ESG and healthcare sector opportunities.",
      location: "Edinburgh",
    },
    {
      name: "Fiona O'Brien",
      expertise: "FIC Advisory",
      specialty: "Family Investment Companies",
      verified: true,
      rating: 4.6,
      contactEmail: "fiona@ficadvisory.ie",
      bio: "Leading FIC advisor for doctors in Ireland and the UK. Expert in corporation tax planning, dividend strategies, and intergenerational wealth transfer.",
      location: "Dublin",
    },
    {
      name: "Marcus Thompson",
      expertise: "Property Investment",
      specialty: "Medical Property Portfolios",
      verified: false,
      rating: 4.4,
      contactEmail: "marcus@propertymed.co.uk",
      bio: "Specialized in building property portfolios for locum doctors and hospital consultants. Buy-to-let and commercial medical property expertise.",
      location: "Birmingham",
    },
  ]);

  const mriInput = {
    income: 150000,
    expenses: 72000,
    savings: 85000,
    pension: 340000,
    investments: 520000,
    debt: 45000,
  };
  const mri = new FinancialMRI(mriInput);
  const analysis = mri.analysis();

  await db.insert(mriResults).values({
    userId: demoUser.id,
    ...mriInput,
    score: analysis.score,
    advice: analysis.advice,
  });

  console.log("Database seeded successfully.");
}
