from app.utils.constants import (
    PENSION_ANNUAL_ALLOWANCE, PENSION_TAPER_THRESHOLD, PENSION_TAPER_MIN_ALLOWANCE,
    NHS_1995_ACCRUAL, NHS_1995_LUMP_SUM_MULTIPLIER, NHS_1995_NPA,
    NHS_2008_ACCRUAL, NHS_2008_NPA,
    NHS_2015_ACCRUAL, NHS_2015_REVALUATION, NHS_2015_SPA,
)


class PensionCalculator:

    def annual_allowance(self, adjusted_income, threshold_income=0):
        if adjusted_income <= PENSION_TAPER_THRESHOLD:
            return PENSION_ANNUAL_ALLOWANCE
        reduction = (adjusted_income - PENSION_TAPER_THRESHOLD) / 2
        return max(PENSION_TAPER_MIN_ALLOWANCE, PENSION_ANNUAL_ALLOWANCE - reduction)

    def carry_forward(self, current_year_contrib, prev_year_contribs):
        unused = []
        for year_contrib in prev_year_contribs:
            unused_amount = max(0, PENSION_ANNUAL_ALLOWANCE - year_contrib)
            unused.append(unused_amount)
        total_available = sum(unused)
        excess = max(0, current_year_contrib - PENSION_ANNUAL_ALLOWANCE)
        can_use = min(excess, total_available)
        remaining_excess = excess - can_use
        return {
            "carry_forward_available": round(total_available, 2),
            "carry_forward_used": round(can_use, 2),
            "excess_after_carry_forward": round(remaining_excess, 2),
            "annual_allowance_charge": remaining_excess > 0,
        }

    def nhs_1995_projection(self, years_of_service, final_salary, current_age):
        annual_pension = years_of_service * NHS_1995_ACCRUAL * final_salary
        lump_sum = annual_pension * NHS_1995_LUMP_SUM_MULTIPLIER
        years_to_npa = max(0, NHS_1995_NPA - current_age)
        projected_years = years_of_service + years_to_npa
        projected_pension = projected_years * NHS_1995_ACCRUAL * final_salary
        projected_lump = projected_pension * NHS_1995_LUMP_SUM_MULTIPLIER

        return {
            "scheme": "NHS 1995",
            "type": "Final Salary",
            "accrual_rate": "1/80th",
            "npa": NHS_1995_NPA,
            "current_annual_pension": round(annual_pension, 2),
            "current_lump_sum": round(lump_sum, 2),
            "projected_annual_pension": round(projected_pension, 2),
            "projected_lump_sum": round(projected_lump, 2),
            "years_to_npa": years_to_npa,
        }

    def nhs_2008_projection(self, years_of_service, final_salary, current_age):
        annual_pension = years_of_service * NHS_2008_ACCRUAL * final_salary
        years_to_npa = max(0, NHS_2008_NPA - current_age)
        projected_years = years_of_service + years_to_npa
        projected_pension = projected_years * NHS_2008_ACCRUAL * final_salary

        return {
            "scheme": "NHS 2008",
            "type": "Final Salary",
            "accrual_rate": "1/60th",
            "npa": NHS_2008_NPA,
            "current_annual_pension": round(annual_pension, 2),
            "projected_annual_pension": round(projected_pension, 2),
            "years_to_npa": years_to_npa,
        }

    def nhs_2015_projection(self, current_pot, annual_earnings, contribution_rate, current_age):
        years_to_spa = max(0, NHS_2015_SPA - current_age)
        pot = current_pot

        for year in range(years_to_spa):
            new_pension = annual_earnings * NHS_2015_ACCRUAL
            pot = (pot + new_pension) * (1 + NHS_2015_REVALUATION)

        return {
            "scheme": "NHS 2015",
            "type": "Career Average (CARE)",
            "accrual_rate": "1/54th",
            "revaluation": "CPI + 1.5%",
            "spa": NHS_2015_SPA,
            "current_pot": round(current_pot, 2),
            "projected_annual_pension": round(pot, 2),
            "years_to_spa": years_to_spa,
        }

    def sipp_projection(self, current_value, annual_contribution, current_age, retirement_age=65, growth_rate=0.05):
        years = max(0, retirement_age - current_age)
        pot = current_value
        for _ in range(years):
            pot = (pot + annual_contribution) * (1 + growth_rate)

        tax_free_lump = pot * 0.25
        remaining = pot - tax_free_lump
        annual_drawdown_4pct = remaining * 0.04

        return {
            "scheme": "SIPP",
            "type": "Defined Contribution",
            "current_value": round(current_value, 2),
            "projected_value": round(pot, 2),
            "tax_free_lump_sum": round(tax_free_lump, 2),
            "annual_drawdown_4pct": round(annual_drawdown_4pct, 2),
            "years_to_retirement": years,
            "growth_rate_assumed": growth_rate,
        }

    def project_pension(self, pension_data, income, current_age):
        ptype = pension_data.get("type", "").lower()
        value = pension_data.get("value", 0)
        contrib = pension_data.get("annual_contribution", 0)

        if ptype == "nhs_1995":
            years_service = value / (income * NHS_1995_ACCRUAL) if income > 0 else 10
            return self.nhs_1995_projection(min(years_service, 40), income, current_age)
        elif ptype == "nhs_2008":
            years_service = value / (income * NHS_2008_ACCRUAL) if income > 0 else 10
            return self.nhs_2008_projection(min(years_service, 40), income, current_age)
        elif ptype == "nhs_2015":
            return self.nhs_2015_projection(value, income, 0.068, current_age)
        elif ptype in ("sipp", "personal", "workplace"):
            return self.sipp_projection(value, contrib, current_age)
        else:
            return self.sipp_projection(value, contrib, current_age)

    def analyse_pensions(self, pensions_list, income, current_age):
        results = []
        total_contrib = 0
        for p in pensions_list:
            proj = self.project_pension(p, income, current_age)
            total_contrib += p.get("annual_contribution", 0)
            results.append(proj)

        aa = self.annual_allowance(income)
        excess = max(0, total_contrib - aa)

        return {
            "projections": results,
            "total_contributions": total_contrib,
            "annual_allowance": round(aa, 2),
            "excess_contributions": round(excess, 2),
            "aa_charge": excess > 0,
            "unused_allowance": round(max(0, aa - total_contrib), 2),
        }
