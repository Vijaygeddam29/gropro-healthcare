import type { MriInput } from "@shared/schema";

export class FinancialMRI {
  private income: number;
  private expenses: number;
  private savings: number;
  private pension: number;
  private investments: number;
  private debt: number;

  constructor(input: MriInput) {
    this.income = input.income;
    this.expenses = input.expenses;
    this.savings = input.savings;
    this.pension = input.pension;
    this.investments = input.investments;
    this.debt = input.debt;
  }

  score(): number {
    const netWorth = this.savings + this.pension + this.investments - this.debt;
    const savingsRatio = this.savings / (this.income + 1e-6);
    const debtRatio = this.debt / (this.income + 1e-6);
    const investmentRatio = this.investments / (this.income + 1e-6);
    const pensionRatio = this.pension / (this.income + 1e-6);

    let score = 50;
    score += Math.min(savingsRatio * 40, 15);
    score += Math.min(investmentRatio * 30, 15);
    score += Math.min(pensionRatio * 20, 10);
    score -= Math.min(debtRatio * 50, 25);

    if (netWorth > this.income * 2) score += 10;
    if (this.expenses < this.income * 0.5) score += 5;

    return Math.min(Math.max(Math.round(score), 0), 100);
  }

  analysis(): { score: number; advice: string[] } {
    const score = this.score();
    const advice: string[] = [];

    if (this.debt > this.income * 0.5) {
      advice.push("High debt relative to income - consider structured repayment strategies");
    }
    if (this.savings < this.income * 0.3) {
      advice.push("Low cash buffer - aim for 6-12 months of expenses in liquid savings");
    }
    if (this.pension < this.income * 0.2) {
      advice.push("Pension contributions below optimal - review tapering rules and annual allowance");
    }
    if (this.expenses > this.income * 0.7) {
      advice.push("High expense ratio - review discretionary spending and tax efficiency");
    }
    if (this.investments < this.income * 0.5) {
      advice.push("Consider increasing investment allocation through FIC or SIPP structures");
    }
    if (score >= 75) {
      advice.push("Strong financial position - focus on tax optimization and wealth preservation");
    }

    return { score, advice };
  }
}

export class ScenarioAI {
  generateScenarios(capital: number, taxRate: number) {
    return {
      A: { risk: "conservative", projectedReturn: capital * 0.04, taxImpact: capital * taxRate },
      B: { risk: "balanced", projectedReturn: capital * 0.07, taxImpact: capital * taxRate * 0.9 },
      C: { risk: "aggressive", projectedReturn: capital * 0.12, taxImpact: capital * taxRate * 0.85 },
    };
  }
}

export class PensionAI {
  model(pensionValue: number, contribution: number, age: number) {
    const ltaLimit = 1_073_100;
    const yearsToRetirement = Math.max(65 - age, 0);
    const futureValue = pensionValue + contribution * yearsToRetirement;
    const taperWarning = futureValue > ltaLimit;
    return { futureValue, taperWarning, yearsToRetirement };
  }
}
