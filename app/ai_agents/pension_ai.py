from app.ai_agents.pension_rules import PensionCalculator
from app.utils.constants import (
    PENSION_ANNUAL_ALLOWANCE, PENSION_TAPER_THRESHOLD, PENSION_TAPER_MIN_ALLOWANCE,
    NHS_1995_ACCRUAL, NHS_1995_NPA, NHS_1995_LUMP_SUM_MULTIPLIER,
    NHS_2008_ACCRUAL, NHS_2008_NPA,
    NHS_2015_ACCRUAL, NHS_2015_REVALUATION, NHS_2015_SPA,
)


def _mn(v):
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:,.2f}Mn"
    return f"{v:,.0f}"


class PensionAI:

    def __init__(self, pension_value=0, contribution=0, income=0, age=40):
        self.pension_value = pension_value
        self.contribution = contribution
        self.income = income
        self.age = age
        self.calc = PensionCalculator()

    def model(self):
        proj = self.calc.sipp_projection(self.pension_value, self.contribution, self.age)
        return {
            "future_value": proj["projected_value"],
            "taper_warning": proj["projected_value"] > 1_073_100,
        }

    def full_analysis(self, pensions_list, income, age):
        analysis = self.calc.analyse_pensions(pensions_list, income, age)

        projections = []
        for i, pension in enumerate(pensions_list):
            proj = self.calc.project_pension(pension, income, age)
            proj["simple_explanation"] = self._explain_pension(pension, proj, income)
            projections.append(proj)

        total_contrib = sum(p.get("annual_contribution", 0) for p in pensions_list)
        aa = self.calc.annual_allowance(income)
        unused = max(0, aa - total_contrib)

        recommendations = self._build_recommendations(pensions_list, income, age, aa, total_contrib)

        return {
            "projections": projections,
            "annual_allowance": round(aa),
            "total_contributions": round(total_contrib),
            "unused_allowance": round(unused),
            "excess": round(max(0, total_contrib - aa)),
            "aa_charge_risk": total_contrib > aa,
            "recommendations": recommendations,
        }

    def _explain_pension(self, pension, projection, income):
        ptype = pension.get("type", "").lower()
        value = pension.get("value", 0)
        contrib = pension.get("annual_contribution", 0)
        marginal = 0.45 if income > 125140 else (0.4 if income > 50270 else 0.2)

        if ptype == "nhs_1995":
            annual_pension = projection.get("projected_annual_pension", 0)
            lump = projection.get("projected_lump_sum", 0)
            accrual_frac = f"1/{int(1 / NHS_1995_ACCRUAL)}"
            return (
                f"NHS Pension Scheme 1995 Section (NHS Pension Scheme Regulations 1995): "
                f"Final salary scheme with {accrual_frac}ths accrual rate per year of service. "
                f"Normal Pension Age: {NHS_1995_NPA}. "
                f"Projected annual pension at NPA: £{_mn(annual_pension)}/yr (index-linked). "
                f"Automatic tax-free lump sum: {NHS_1995_LUMP_SUM_MULTIPLIER}x annual pension = "
                f"£{_mn(lump)} (under s.166 Finance Act 2004, limited to 25% of crystallised value). "
                f"This is a defined benefit scheme — your pension is guaranteed regardless of investment performance."
            )
        elif ptype == "nhs_2008":
            annual_pension = projection.get("projected_annual_pension", 0)
            accrual_frac = f"1/{int(1 / NHS_2008_ACCRUAL)}"
            return (
                f"NHS Pension Scheme 2008 Section (NHS Pension Scheme Regulations 2008): "
                f"Final salary scheme with {accrual_frac}ths accrual rate. "
                f"Normal Pension Age: {NHS_2008_NPA}. "
                f"Projected annual pension: £{_mn(annual_pension)}/yr. "
                f"No automatic lump sum — but you may commute up to 25% of the pension "
                f"value for a tax-free lump sum (FA 2004, s.166). Each £1 of pension "
                f"commuted provides approximately £12 of lump sum."
            )
        elif ptype == "nhs_2015":
            annual_pension = projection.get("projected_annual_pension", 0)
            accrual_frac = f"1/{int(1 / NHS_2015_ACCRUAL)}"
            return (
                f"NHS 2015 Scheme (NHS Pension Scheme Regulations 2015): Career Average "
                f"Revalued Earnings (CARE) scheme. Accrual rate: {accrual_frac}ths of "
                f"pensionable earnings each year, revalued annually at CPI + {NHS_2015_REVALUATION * 100:.1f}%. "
                f"State Pension Age linked: currently {NHS_2015_SPA}. "
                f"Projected annual pension at SPA: £{_mn(annual_pension)}/yr. "
                f"No automatic lump sum — commutation available at approximately 12:1 ratio. "
                f"Annual contributions: £{_mn(contrib)} (tiered rate based on pensionable pay "
                f"under the 2015 Regulations)."
            )
        elif ptype == "sipp":
            projected = projection.get("projected_value", 0)
            drawdown = projection.get("annual_drawdown_4pct", 0)
            lump = projection.get("tax_free_lump_sum", 0)
            return (
                f"Self-Invested Personal Pension (SIPP): Defined contribution scheme. "
                f"Current value: £{_mn(value)}. Annual contributions: £{_mn(contrib)} "
                f"(tax relief at {int(marginal * 100)}% under FA 2004, s.188). "
                f"Projected value at retirement: £{_mn(projected)} (assuming 5% net growth). "
                f"25% tax-free lump sum: £{_mn(lump)} (Pension Commencement Lump Sum, FA 2004 s.166). "
                f"Sustainable annual drawdown at 4%: £{_mn(drawdown)}. "
                f"Flexible drawdown available from age 57 (rising from 55 in April 2028, "
                f"Pension Schemes Act 2021)."
            )
        else:
            projected = projection.get("projected_value", 0)
            return (
                f"Pension fund current value: £{_mn(value)}. "
                f"Projected value at retirement: £{_mn(projected)} (5% growth assumed). "
                f"Contributions attract tax relief at your {int(marginal * 100)}% marginal rate "
                f"(FA 2004, s.188). Annual Allowance: £{PENSION_ANNUAL_ALLOWANCE:,}."
            )

    def _build_recommendations(self, pensions_list, income, age, aa, total_contrib):
        recs = []
        unused = max(0, aa - total_contrib)
        marginal = 0.45 if income > 125140 else (0.4 if income > 50270 else 0.2)

        if unused > 5000:
            relief = unused * marginal
            recs.append({
                "title": "Utilise Unused Annual Allowance",
                "saving": round(relief),
                "simple": (
                    f"FA 2004, s.228: Your Annual Allowance is £{_mn(aa)}. "
                    f"Current contributions: £{_mn(total_contrib)}. Unused: £{_mn(unused)}. "
                    f"Additional contributions at your {int(marginal * 100)}% marginal rate "
                    f"generate £{_mn(relief)} in tax relief. "
                    f"Under s.186 carry-forward rules, you may also use unused allowance "
                    f"from the 2021/22, 2022/23, and 2023/24 tax years."
                ),
            })

        if total_contrib > aa:
            excess = total_contrib - aa
            charge = excess * marginal
            recs.append({
                "title": "Annual Allowance Charge",
                "saving": -round(charge),
                "simple": (
                    f"FA 2004, s.227: You have exceeded your Annual Allowance by £{_mn(excess)}. "
                    f"The Annual Allowance Charge (s.227) taxes the excess at your marginal rate: "
                    f"£{_mn(charge)}. This must be reported on your Self Assessment return. "
                    f"If the charge exceeds £2,000, you can elect for your pension scheme to pay it "
                    f"(Scheme Pays, s.237B). Check carry-forward from prior years to reduce or eliminate the charge."
                ),
            })

        has_nhs = any(p.get("type", "").startswith("nhs") for p in pensions_list)
        has_sipp = any(p.get("type", "") == "sipp" for p in pensions_list)
        if has_nhs and not has_sipp and unused > 10000:
            recs.append({
                "title": "Consider Opening a SIPP",
                "saving": 0,
                "simple": (
                    f"You have NHS defined benefit pension(s) but no SIPP. "
                    f"A SIPP provides investment flexibility and earlier access (from age 57 "
                    f"under Pension Schemes Act 2021). With £{_mn(unused)} unused Annual Allowance, "
                    f"SIPP contributions would generate additional tax relief while providing "
                    f"a separate pot with flexible drawdown options not available from the NHS scheme. "
                    f"NHS pension death benefits are scheme-specific; a SIPP can be passed outside "
                    f"your estate for IHT purposes."
                ),
            })

        if income > PENSION_TAPER_THRESHOLD:
            tapered_aa = max(PENSION_TAPER_MIN_ALLOWANCE, aa)
            excess_income = income - PENSION_TAPER_THRESHOLD
            reduction = min(excess_income // 2, PENSION_ANNUAL_ALLOWANCE - PENSION_TAPER_MIN_ALLOWANCE)
            recs.append({
                "title": "Tapered Annual Allowance",
                "saving": 0,
                "simple": (
                    f"FA 2004, s.228ZA: Your adjusted income of £{_mn(income)} exceeds the "
                    f"£{PENSION_TAPER_THRESHOLD:,} threshold income. Your Annual Allowance is "
                    f"tapered by £1 for every £2 above this threshold, reducing it by £{_mn(reduction)} "
                    f"to £{_mn(tapered_aa)}. The minimum tapered allowance is "
                    f"£{PENSION_TAPER_MIN_ALLOWANCE:,}. Salary sacrifice arrangements can reduce "
                    f"adjusted income below the taper threshold."
                ),
            })

        return recs
