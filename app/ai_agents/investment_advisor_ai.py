from app.ai_agents.tax_rules import TaxCalculator
from app.ai_agents.company_rules import CompanyCalculator
from app.utils.constants import (
    ISA_ANNUAL_ALLOWANCE, PENSION_ANNUAL_ALLOWANCE, DIVIDEND_ALLOWANCE,
    VCT_INCOME_TAX_RELIEF, EIS_INCOME_TAX_RELIEF, SEIS_INCOME_TAX_RELIEF,
    CGT_HIGHER_RATE, CGT_ANNUAL_EXEMPT,
)


def _mn(v):
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:,.2f}Mn"
    return f"{v:,.0f}"


class InvestmentAdvisorAI:

    def __init__(self, risk_tolerance="medium"):
        self.risk_tolerance = risk_tolerance
        self.tax_calc = TaxCalculator()
        self.company_calc = CompanyCalculator()

    def generate_recommendations(self, doctor_profile):
        profile = self._normalise(doctor_profile)
        income_streams = profile.get("income_streams", [])
        wrappers = profile.get("investment_wrappers", [])
        debts = profile.get("debt_breakdown", [])
        pensions = profile.get("pensions", [])

        total_income = sum(s.get("amount", 0) for s in income_streams)
        total_investments = sum(w.get("value", 0) for w in wrappers)
        cc_debt = sum(d.get("balance", 0) for d in debts if d.get("type") == "credit_cards")
        isa_val = sum(w.get("value", 0) for w in wrappers if "isa" in w.get("type", ""))
        gia_val = sum(w.get("value", 0) for w in wrappers if w.get("type") == "gia")
        btl_val = sum(w.get("value", 0) for w in wrappers if w.get("type") == "buy_to_let")
        total_contrib = sum(p.get("annual_contribution", 0) for p in pensions)

        recs = []
        if cc_debt > 1000:
            recs.append(self._debt_first_rec(cc_debt))
        if total_investments < total_income * 0.5 and total_income > 0:
            recs.append(self._start_investing_rec(total_income, total_investments))
        recs.append(self._isa_rec(isa_val, total_income))
        recs.append(self._pension_rec(total_contrib, total_income))
        if total_income > 100000:
            recs.append(self._vct_rec(total_income, wrappers))
            recs.append(self._eis_rec(total_income, wrappers))
        if gia_val > 20000:
            recs.append(self._gia_warning(gia_val, total_income))
        if btl_val > 0:
            recs.append(self._btl_rec(btl_val, total_income))

        return [r for r in recs if r is not None]

    def _debt_first_rec(self, cc_debt):
        interest = cc_debt * 0.22
        return {
            "title": "Clear Credit Card Debt",
            "priority": "urgent",
            "saving": round(interest),
            "simple": (
                f"You carry £{_mn(cc_debt)} in credit card debt at approximately 22% APR, "
                f"costing £{_mn(interest)}/yr in non-deductible interest. "
                f"Unlike mortgage interest (deductible within a company under CTA 2009), "
                f"consumer debt interest provides zero tax benefit. "
                f"Clearing this balance delivers a guaranteed 22% effective return — "
                f"no regulated investment can match this risk-free."
            ),
        }

    def _isa_rec(self, isa_val, income):
        marginal = 0.45 if income > 125140 else (0.4 if income > 50270 else 0.2)
        div_rate = 0.3375 if income > 50270 else 0.0875
        return {
            "title": "Fund ISA Allowance",
            "priority": "high" if isa_val == 0 else "medium",
            "saving": round(ISA_ANNUAL_ALLOWANCE * 0.02) if isa_val == 0 else 0,
            "simple": (
                f"Under the Individual Savings Account Regulations 1998, you can invest "
                f"up to £{ISA_ANNUAL_ALLOWANCE:,} per tax year. "
                f"{'You have no ISA holdings — this allowance is going unused. ' if isa_val == 0 else f'Current ISA holdings: £{_mn(isa_val)}. '}"
                f"All gains, dividends, and interest within an ISA are entirely exempt from "
                f"Income Tax and Capital Gains Tax (TCGA 1992 exemption). "
                f"At your income level, dividends in a GIA attract tax at {div_rate * 100:.2f}% "
                f"above the £{DIVIDEND_ALLOWANCE:,} allowance; inside an ISA, they are tax-free."
            ),
        }

    def _pension_rec(self, current_contrib, income):
        unused = max(0, PENSION_ANNUAL_ALLOWANCE - current_contrib)
        marginal = 0.45 if income > 125140 else (0.4 if income > 50270 else 0.2)
        relief = unused * marginal
        return {
            "title": "Maximise Pension Contributions",
            "priority": "high",
            "saving": round(relief),
            "simple": (
                f"Finance Act 2004, s.188: You have £{_mn(unused)} of unused Annual Allowance "
                f"(limit: £{PENSION_ANNUAL_ALLOWANCE:,}/yr under s.228). "
                f"At your {int(marginal * 100)}% marginal rate, contributing the full unused amount "
                f"generates £{_mn(relief)} in immediate tax relief. "
                f"Pension contributions also reduce your adjusted net income for Personal Allowance "
                f"tapering (ITA 2007, s.35) and High Income Child Benefit Charge purposes. "
                f"Carry-forward rules (s.186) allow use of unused allowance from the previous three tax years."
            ),
        }

    def _vct_rec(self, income, wrappers):
        vct_val = sum(w.get("value", 0) for w in wrappers if w.get("type") == "vct")
        relief_amount = 30000 * VCT_INCOME_TAX_RELIEF
        return {
            "title": "Venture Capital Trusts (VCTs)",
            "priority": "medium",
            "saving": round(relief_amount) if vct_val == 0 else 0,
            "simple": (
                f"ITA 2007, Part 6: VCTs provide 30% income tax relief on investments up to "
                f"£200,000/yr. A £30,000 investment reduces your Income Tax bill by £{_mn(relief_amount)}. "
                f"{'You have no VCT holdings currently. ' if vct_val == 0 else f'Current VCT holdings: £{_mn(vct_val)}. '}"
                f"Dividends from VCTs are exempt from Income Tax (s.709 ITA 2007). "
                f"Disposals are exempt from CGT provided shares were held for 5+ years (s.151A TCGA 1992). "
                f"Minimum holding period: 5 years to retain the income tax relief."
            ),
        }

    def _eis_rec(self, income, wrappers):
        eis_val = sum(w.get("value", 0) for w in wrappers if w.get("type") == "eis_seis")
        relief_amount = 20000 * EIS_INCOME_TAX_RELIEF
        return {
            "title": "EIS / SEIS Investments",
            "priority": "medium",
            "saving": round(relief_amount) if eis_val == 0 else 0,
            "simple": (
                f"ITA 2007, Part 5: Enterprise Investment Schemes provide 30% income tax relief "
                f"on up to £1,000,000/yr invested. SEIS (Part 5A) provides 50% relief on up to £200,000. "
                f"{'No EIS/SEIS holdings on record. ' if eis_val == 0 else f'Current EIS/SEIS holdings: £{_mn(eis_val)}. '}"
                f"EIS also permits CGT deferral relief (s.150C TCGA 1992) — gains from other disposals "
                f"can be deferred by reinvesting into qualifying EIS shares. "
                f"Loss relief available under ITA 2007, s.131: if the investment fails, "
                f"losses (net of income tax relief) can be offset against your income."
            ),
        }

    def _gia_warning(self, gia_val, income):
        marginal_cgt = CGT_HIGHER_RATE if income > 50270 else 0.10
        annual_gain_est = gia_val * 0.05
        taxable_gain = max(0, annual_gain_est - CGT_ANNUAL_EXEMPT)
        potential_cgt = taxable_gain * marginal_cgt
        return {
            "title": "Restructure GIA Holdings",
            "priority": "medium",
            "saving": round(potential_cgt),
            "simple": (
                f"You hold £{_mn(gia_val)} in a General Investment Account. "
                f"Under TCGA 1992, gains are subject to CGT at {marginal_cgt * 100:.0f}% above "
                f"the £{CGT_ANNUAL_EXEMPT:,} annual exempt amount (s.3). "
                f"Estimated annual CGT exposure: £{_mn(potential_cgt)}. "
                f"Dividends above £{DIVIDEND_ALLOWANCE:,} are taxed under ITTOIA 2005 at 33.75% "
                f"(higher rate). Transferring £{ISA_ANNUAL_ALLOWANCE:,}/yr into an ISA shelters "
                f"future gains and dividends from all tax permanently."
            ),
        }

    def _btl_rec(self, btl_val, income):
        marginal = 0.45 if income > 125140 else (0.4 if income > 50270 else 0.2)
        return {
            "title": "Review Buy-to-Let Tax Position",
            "priority": "low",
            "saving": 0,
            "simple": (
                f"Buy-to-let property value: £{_mn(btl_val)}. "
                f"Since April 2020, s.24 Finance Act 2015 fully restricts mortgage interest "
                f"relief for individual landlords to a basic rate (20%) tax credit — regardless "
                f"of your {int(marginal * 100)}% marginal rate. "
                f"If held through a limited company (Companies Act 2006), mortgage interest "
                f"remains fully deductible against profits under CTA 2009. "
                f"CGT on disposal: 24% (higher rate, from April 2024). "
                f"On incorporation, SDLT and CGT costs must be weighed against long-term savings."
            ),
        }

    def _start_investing_rec(self, income, investments):
        target = income * 3
        gap = target - investments
        monthly = min(1000, gap // 12)
        return {
            "title": "Build Investment Base",
            "priority": "high",
            "saving": 0,
            "simple": (
                f"Total investments: £{_mn(investments)} — below 50% of your £{_mn(income)} "
                f"annual income. A recommended target is 3x income (£{_mn(target)}). "
                f"Start with £{_mn(monthly)}/month into a Stocks & Shares ISA "
                f"(ISA Regs 1998, fully exempt from CGT and Income Tax). "
                f"Once the £{ISA_ANNUAL_ALLOWANCE:,}/yr ISA limit is reached, direct surplus "
                f"to pension (up to £{PENSION_ANNUAL_ALLOWANCE:,}/yr with tax relief under FA 2004)."
            ),
        }

    def _normalise(self, doctor_profile):
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
