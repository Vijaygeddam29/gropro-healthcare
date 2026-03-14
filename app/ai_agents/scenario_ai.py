from app.ai_agents.tax_rules import TaxCalculator
from app.ai_agents.company_rules import CompanyCalculator
from app.utils.constants import (
    PENSION_ANNUAL_ALLOWANCE, ISA_ANNUAL_ALLOWANCE,
    VCT_INCOME_TAX_RELIEF, PERSONAL_ALLOWANCE, PA_TAPER_THRESHOLD,
)


def _mn(v):
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:,.2f}Mn"
    return f"{v:,.0f}"


class ScenarioAI:

    def __init__(self):
        self.tax_calc = TaxCalculator()
        self.company_calc = CompanyCalculator()

    def generate_scenarios(self, doctor_profile):
        profile = self._normalise(doctor_profile)
        income_streams = profile.get("income_streams", [])
        total_income = sum(s.get("amount", 0) for s in income_streams)
        pensions = profile.get("pensions", [])
        pension_contrib = sum(p.get("annual_contribution", 0) for p in pensions)
        wrappers = profile.get("investment_wrappers", [])
        investments = sum(w.get("value", 0) for w in wrappers)
        companies = profile.get("companies", [])

        tax_burden = self.tax_calc.total_tax_burden(profile)
        current_tax = tax_burden.get("total_tax", 0)

        return {
            "do_nothing": self._do_nothing(profile, total_income, investments, current_tax),
            "quick_wins": self._quick_wins(profile, total_income, pension_contrib, investments, current_tax),
            "full_optimisation": self._full_optimisation(profile, total_income, pension_contrib, investments, companies, current_tax),
        }

    def _do_nothing(self, profile, income, investments, current_tax):
        growth = 0.04
        net_worth_base = sum(p.get("value", 0) for p in profile.get("pensions", [])) + investments
        projections = {}
        for years in [5, 10, 20]:
            net = net_worth_base * ((1 + growth) ** years)
            projections[f"{years}yr"] = round(net)

        marginal = self.tax_calc.marginal_rate(income)
        return {
            "name": "Do Nothing",
            "risk": "low",
            "projected_return": growth,
            "notes": f"No changes. Current tax burden: £{_mn(current_tax)}/yr at {marginal * 100:.0f}% marginal rate.",
            "simple": (
                f"Current position unchanged. You pay £{_mn(current_tax)}/yr in total tax. "
                f"Net worth of £{_mn(net_worth_base)} grows at an assumed {growth * 100:.0f}% real return "
                f"(after inflation). No additional tax relief captured. "
                f"Projected net worth: £{_mn(projections.get('5yr', 0))} in 5 years, "
                f"£{_mn(projections.get('10yr', 0))} in 10, £{_mn(projections.get('20yr', 0))} in 20."
            ),
            "annual_tax": round(current_tax),
            "annual_tax_saving": 0,
            "projections": projections,
        }

    def _quick_wins(self, profile, income, pension_contrib, investments, current_tax):
        pension_topup = min(PENSION_ANNUAL_ALLOWANCE - pension_contrib, income * 0.15)
        pension_topup = max(0, pension_topup)

        marginal_rate = self.tax_calc.marginal_rate(income)
        pension_relief = pension_topup * marginal_rate

        isa_value = sum(w.get("value", 0) for w in profile.get("investment_wrappers", []) if "isa" in w.get("type", ""))
        isa_saving = ISA_ANNUAL_ALLOWANCE * 0.02 if isa_value == 0 else 0

        total_saving = round(pension_relief + isa_saving)
        new_tax = current_tax - pension_relief
        growth = 0.06

        net_worth_base = sum(p.get("value", 0) for p in profile.get("pensions", [])) + investments
        projections = {}
        extra_annual = pension_topup + ISA_ANNUAL_ALLOWANCE
        for years in [5, 10, 20]:
            future = net_worth_base * ((1 + growth) ** years)
            future += extra_annual * (((1 + growth) ** years - 1) / growth)
            projections[f"{years}yr"] = round(future)

        steps = []
        if pension_topup > 0:
            steps.append(
                f"FA 2004, s.188: Contribute additional £{_mn(pension_topup)}/yr to pension. "
                f"Tax relief at {int(marginal_rate * 100)}%: £{_mn(pension_relief)}/yr saved"
            )
        if isa_value == 0:
            steps.append(
                f"ISA Regs 1998: Open and fund ISA with up to £{ISA_ANNUAL_ALLOWANCE:,}/yr. "
                f"All growth exempt from CGT and Income Tax"
            )

        debts = profile.get("debt_breakdown", [])
        cc = sum(d.get("balance", 0) for d in debts if d.get("type") == "credit_cards")
        if cc > 0:
            interest = cc * 0.22
            steps.append(
                f"Clear £{_mn(cc)} credit card debt. Saves £{_mn(interest)}/yr in non-deductible interest (22% APR)"
            )

        pa_recovery = 0
        if income > PA_TAPER_THRESHOLD and pension_topup > 0:
            pa_recoverable = min(pension_topup / 2, (income - PA_TAPER_THRESHOLD) / 2)
            pa_recovery = pa_recoverable * 0.4
            if pa_recovery > 500:
                steps.append(
                    f"ITA 2007, s.35: Pension contributions reduce adjusted net income, "
                    f"recovering £{_mn(pa_recoverable)} of Personal Allowance. "
                    f"Additional saving: £{_mn(pa_recovery)}/yr"
                )
                total_saving += round(pa_recovery)

        return {
            "name": "Quick Wins",
            "risk": "low",
            "projected_return": growth,
            "notes": f"Low-effort changes generating £{_mn(total_saving)}/yr in tax savings.",
            "simple": (
                f"Implement straightforward tax relief measures without restructuring. "
                f"Total annual saving: £{_mn(total_saving)}. Tax bill reduces from "
                f"£{_mn(current_tax)} to £{_mn(new_tax)}. "
                f"Projected net worth: £{_mn(projections.get('5yr', 0))} in 5 years, "
                f"£{_mn(projections.get('10yr', 0))} in 10, £{_mn(projections.get('20yr', 0))} in 20."
            ),
            "annual_tax": round(new_tax),
            "annual_tax_saving": total_saving,
            "steps": steps,
            "projections": projections,
        }

    def _full_optimisation(self, profile, income, pension_contrib, investments, companies, current_tax):
        savings = []
        total_saving = 0

        pension_topup = max(0, PENSION_ANNUAL_ALLOWANCE - pension_contrib)
        marginal_rate = self.tax_calc.marginal_rate(income)
        pension_saving = pension_topup * marginal_rate
        if pension_saving > 0:
            savings.append(
                f"FA 2004, s.188: Maximise pension contributions (£{_mn(pension_topup)}/yr). "
                f"Tax relief at {int(marginal_rate * 100)}%: £{_mn(pension_saving)}/yr"
            )
            total_saving += pension_saving

        se_income = sum(s.get("amount", 0) for s in profile.get("income_streams", []) if s.get("source") in ("locum", "private_practice", "medico_legal"))
        if se_income > 50000 and not companies:
            comparison = self.company_calc.vs_sole_trader(se_income)
            structure_saving = comparison.get("annual_saving", 0)
            if structure_saving > 0:
                savings.append(
                    f"Companies Act 2006 / CTA 2010: Incorporate self-employed income "
                    f"(£{_mn(se_income)}). CT at 19-25% replaces IT at {int(marginal_rate * 100)}%. "
                    f"Saving: £{_mn(structure_saving)}/yr"
                )
                total_saving += structure_saving

        if income > PA_TAPER_THRESHOLD:
            pa_saving = min((income - PA_TAPER_THRESHOLD) / 2, PERSONAL_ALLOWANCE) * 0.4
            if pension_topup > 0:
                recoverable = min(pa_saving, pension_saving)
                if recoverable > 500:
                    savings.append(
                        f"ITA 2007, s.35: Pension contributions recover Personal Allowance. "
                        f"Additional saving: £{_mn(recoverable)}/yr"
                    )

        if income > 150000:
            vct_relief = 30000 * VCT_INCOME_TAX_RELIEF
            savings.append(
                f"ITA 2007, Part 6: Invest £30,000 in VCTs. 30% income tax relief: "
                f"£{_mn(vct_relief)}/yr. Dividends tax-free (s.709)"
            )
            total_saving += vct_relief

        growth = 0.08
        net_worth_base = sum(p.get("value", 0) for p in profile.get("pensions", [])) + investments
        projections = {}
        for years in [5, 10, 20]:
            future = net_worth_base * ((1 + growth) ** years)
            future += total_saving * (((1 + growth) ** years - 1) / growth)
            projections[f"{years}yr"] = round(future)

        return {
            "name": "Full Optimisation",
            "risk": "medium",
            "projected_return": growth,
            "notes": f"Comprehensive restructuring. Total annual saving: £{_mn(total_saving)}.",
            "simple": (
                f"Full restructuring of tax position, pension contributions, and investment wrappers. "
                f"Total annual saving: £{_mn(total_saving)}. Tax bill reduces from "
                f"£{_mn(current_tax)} to £{_mn(current_tax - total_saving)}. "
                f"Projected net worth: £{_mn(projections.get('5yr', 0))} in 5 years, "
                f"£{_mn(projections.get('10yr', 0))} in 10, £{_mn(projections.get('20yr', 0))} in 20."
            ),
            "annual_tax": round(current_tax - total_saving),
            "annual_tax_saving": round(total_saving),
            "steps": savings,
            "projections": projections,
        }

    def _normalise(self, doctor_profile):
        if not doctor_profile:
            return {"income_streams": [], "pensions": [], "investment_wrappers": [], "debt_breakdown": [], "companies": [], "personal": {}, "tax_status": {}}
        if "income_streams" in doctor_profile:
            return doctor_profile
        income = doctor_profile.get("income_level", 0)
        return {
            "income_streams": [{"source": "paye", "amount": income}] if income > 0 else [],
            "pensions": [{"type": "sipp", "value": doctor_profile.get("pension", 0), "annual_contribution": doctor_profile.get("pension_contributions", 0)}] if doctor_profile.get("pension", 0) > 0 else [],
            "investment_wrappers": [{"type": "gia", "value": doctor_profile.get("total_investments", 0)}] if doctor_profile.get("total_investments", 0) > 0 else [],
            "debt_breakdown": [{"type": "other_loans", "balance": doctor_profile.get("debt_level", 0)}] if doctor_profile.get("debt_level", 0) > 0 else [],
            "companies": [],
            "personal": {},
            "tax_status": {},
        }
