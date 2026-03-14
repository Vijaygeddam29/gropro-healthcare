import {
  type User, type InsertUser,
  type Fic, type InsertFic,
  type Investment, type InsertInvestment,
  type Advisor, type InsertAdvisor,
  type MriResult, type InsertMri,
  users, fics, investments, advisors, mriResults,
} from "@shared/schema";
import { db } from "./db";
import { eq } from "drizzle-orm";

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  getAllFics(): Promise<Fic[]>;
  getFicsByUser(userId: string): Promise<Fic[]>;
  createFic(fic: InsertFic): Promise<Fic>;
  getAllInvestments(): Promise<Investment[]>;
  getInvestmentsByUser(userId: string): Promise<Investment[]>;
  createInvestment(investment: InsertInvestment): Promise<Investment>;
  getAllAdvisors(): Promise<Advisor[]>;
  createAdvisor(advisor: InsertAdvisor): Promise<Advisor>;
  getMriResults(): Promise<MriResult[]>;
  getMriByUser(userId: string): Promise<MriResult[]>;
  createMriResult(mri: InsertMri): Promise<MriResult>;
}

export class DatabaseStorage implements IStorage {
  async getUser(id: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }

  async createUser(user: InsertUser): Promise<User> {
    const [created] = await db.insert(users).values(user).returning();
    return created;
  }

  async getAllFics(): Promise<Fic[]> {
    return db.select().from(fics);
  }

  async getFicsByUser(userId: string): Promise<Fic[]> {
    return db.select().from(fics).where(eq(fics.userId, userId));
  }

  async createFic(fic: InsertFic): Promise<Fic> {
    const [created] = await db.insert(fics).values(fic).returning();
    return created;
  }

  async getAllInvestments(): Promise<Investment[]> {
    return db.select().from(investments);
  }

  async getInvestmentsByUser(userId: string): Promise<Investment[]> {
    return db.select().from(investments).where(eq(investments.userId, userId));
  }

  async createInvestment(investment: InsertInvestment): Promise<Investment> {
    const [created] = await db.insert(investments).values(investment).returning();
    return created;
  }

  async getAllAdvisors(): Promise<Advisor[]> {
    return db.select().from(advisors);
  }

  async createAdvisor(advisor: InsertAdvisor): Promise<Advisor> {
    const [created] = await db.insert(advisors).values(advisor).returning();
    return created;
  }

  async getMriResults(): Promise<MriResult[]> {
    return db.select().from(mriResults);
  }

  async getMriByUser(userId: string): Promise<MriResult[]> {
    return db.select().from(mriResults).where(eq(mriResults.userId, userId));
  }

  async createMriResult(mri: InsertMri): Promise<MriResult> {
    const [created] = await db.insert(mriResults).values(mri).returning();
    return created;
  }
}

export const storage = new DatabaseStorage();
