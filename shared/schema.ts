import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, real, timestamp, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  role: text("role").notNull(),
  country: text("country").notNull().default("UK"),
  county: text("county").notNull().default(""),
  profession: text("profession").notNull(),
  createdAt: timestamp("created_at").defaultNow(),
});

export const fics = pgTable("fics", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id),
  ficName: text("fic_name").notNull(),
  capital: real("capital").notNull(),
  corporationTax: real("corporation_tax").notNull().default(0.19),
  dividendStrategy: text("dividend_strategy").notNull().default("balanced"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const investments = pgTable("investments", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  ficId: varchar("fic_id").references(() => fics.id),
  userId: varchar("user_id").notNull().references(() => users.id),
  type: text("type").notNull(),
  name: text("name").notNull(),
  amount: real("amount").notNull(),
  projectedReturn: real("projected_return").notNull(),
  riskLevel: text("risk_level").notNull().default("balanced"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const advisors = pgTable("advisors", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: text("name").notNull(),
  expertise: text("expertise").notNull(),
  specialty: text("specialty").notNull(),
  verified: boolean("verified").notNull().default(false),
  rating: real("rating").notNull().default(0),
  contactEmail: text("contact_email").notNull(),
  bio: text("bio").notNull().default(""),
  location: text("location").notNull().default(""),
});

export const mriResults = pgTable("mri_results", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id),
  income: real("income").notNull(),
  expenses: real("expenses").notNull(),
  savings: real("savings").notNull(),
  pension: real("pension").notNull(),
  investments: real("investments").notNull(),
  debt: real("debt").notNull(),
  score: integer("score").notNull(),
  advice: text("advice").array().notNull(),
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).omit({ id: true, createdAt: true });
export const insertFicSchema = createInsertSchema(fics).omit({ id: true, createdAt: true });
export const insertInvestmentSchema = createInsertSchema(investments).omit({ id: true, createdAt: true });
export const insertAdvisorSchema = createInsertSchema(advisors).omit({ id: true });
export const insertMriSchema = createInsertSchema(mriResults).omit({ id: true, createdAt: true });

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type InsertFic = z.infer<typeof insertFicSchema>;
export type Fic = typeof fics.$inferSelect;
export type InsertInvestment = z.infer<typeof insertInvestmentSchema>;
export type Investment = typeof investments.$inferSelect;
export type InsertAdvisor = z.infer<typeof insertAdvisorSchema>;
export type Advisor = typeof advisors.$inferSelect;
export type InsertMri = z.infer<typeof insertMriSchema>;
export type MriResult = typeof mriResults.$inferSelect;

export const mriInputSchema = z.object({
  income: z.number().min(0),
  expenses: z.number().min(0),
  savings: z.number().min(0),
  pension: z.number().min(0),
  investments: z.number().min(0),
  debt: z.number().min(0),
});

export type MriInput = z.infer<typeof mriInputSchema>;
