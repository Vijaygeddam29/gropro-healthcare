import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { FinancialMRI } from "./ai-agents";
import { mriInputSchema, insertFicSchema, insertInvestmentSchema } from "@shared/schema";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.get("/api/mri", async (_req, res) => {
    try {
      const results = await storage.getMriResults();
      res.json(results);
    } catch (err) {
      res.status(500).json({ message: "Failed to fetch MRI results" });
    }
  });

  app.post("/api/mri", async (req, res) => {
    try {
      const parsed = mriInputSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ message: "Invalid input", errors: parsed.error.errors });
      }

      const mri = new FinancialMRI(parsed.data);
      const analysis = mri.analysis();

      const result = await storage.createMriResult({
        userId: "demo-user",
        ...parsed.data,
        score: analysis.score,
        advice: analysis.advice,
      });

      res.json(result);
    } catch (err) {
      res.status(500).json({ message: "Failed to calculate MRI" });
    }
  });

  app.get("/api/fics", async (_req, res) => {
    try {
      const allFics = await storage.getAllFics();
      res.json(allFics);
    } catch (err) {
      res.status(500).json({ message: "Failed to fetch FICs" });
    }
  });

  app.post("/api/fics", async (req, res) => {
    try {
      const parsed = insertFicSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ message: "Invalid input", errors: parsed.error.errors });
      }
      const fic = await storage.createFic(parsed.data);
      res.json(fic);
    } catch (err) {
      res.status(500).json({ message: "Failed to create FIC" });
    }
  });

  app.get("/api/investments", async (_req, res) => {
    try {
      const allInvestments = await storage.getAllInvestments();
      res.json(allInvestments);
    } catch (err) {
      res.status(500).json({ message: "Failed to fetch investments" });
    }
  });

  app.post("/api/investments", async (req, res) => {
    try {
      const parsed = insertInvestmentSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ message: "Invalid input", errors: parsed.error.errors });
      }
      const investment = await storage.createInvestment(parsed.data);
      res.json(investment);
    } catch (err) {
      res.status(500).json({ message: "Failed to create investment" });
    }
  });

  app.get("/api/advisors", async (_req, res) => {
    try {
      const allAdvisors = await storage.getAllAdvisors();
      res.json(allAdvisors);
    } catch (err) {
      res.status(500).json({ message: "Failed to fetch advisors" });
    }
  });

  return httpServer;
}
