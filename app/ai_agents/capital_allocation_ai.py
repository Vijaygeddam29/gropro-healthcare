from app.utils.constants import (
    ISA_ANNUAL_ALLOWANCE, PENSION_ANNUAL_ALLOWANCE, DIVIDEND_ALLOWANCE,
    VCT_INCOME_TAX_RELIEF, EIS_INCOME_TAX_RELIEF,
    CGT_HIGHER_RATE, CGT_ANNUAL_EXEMPT,
)


def _mn(v):
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:,.2f}Mn"
    return f"{v:,.0f}"


class CapitalAllocationAI:

    def __init__(self, total_capital=0, risk_profile="balanced"):
        self.total_capital = total_capital
        self.risk_profile = risk_profile

    def allocate(self):
        profiles = {
            "conservative": {"ETF": 0.40, "Bonds": 0.30, "Property": 0.20, "Cash": 0.10},
            "balanced": {"ETF": 0.35, "Property": 0.25, "Bonds": 0.20, "Venture": 0.10, "Cash": 0.10},
            "aggressive": {"ETF": 0.30, "Venture": 0.25, "Property": 0.25, "Bonds": 0.10, "Cash": 0.10},
        }
        alloc = profiles.get(self.risk_profile, profiles["balanced"])
        return {k: round(v * self.total_capital, 2) for k, v in alloc.items()}

    def full_analysis(self, profile):
        income_streams = profile.get("income_streams", [])
        wrappers = profile.get("investment_wrappers", [])
        debts = profile.get("debt_breakdown", [])
        pensions = profile.get("pensions", [])
        age = profile.get("age", 40)

        total_income = sum(s.get("amount", 0) for s in income_streams)
        total_investments = sum(w.get("value", 0) for w in wrappers)
        total_debt = sum(d.get("balance", 0) for d in debts)

        priorities = self._build_priorities(profile, total_income, total_investments, total_debt, age)
        wrapper_order = self._wrapper_priority(total_income, wrappers, pensions)

        return {
            "priorities": priorities,
            "wrapper_order": wrapper_order,
            "allocation": self.allocate(),
        }

    def _build_priorities(self, profile, income, investments, debt, age):
        priorities = []
        marginal = 0.45 if income > 125140 else (0.4 if income > 50270 else 0.2)

        cc_debt = sum(d.get("balance", 0) for d in profile.get("debt_breakdown", []) if d.get("type") == "credit_cards")
        if cc_debt > 0:
            interest = cc_debt * 0.22
            priorities.append({
                "order": 1,
                "title": "Clear Credit Card Debt",
                "amount": round(cc_debt),
                "simple": (
                    f"Outstanding credit card balance: £{_mn(cc_debt)} at approximately 22% APR, "
                    f"costing £{_mn(interest)}/yr in non-deductible interest. "
                    f"Consumer debt interest provides no tax relief (unlike mortgage interest "
                    f"within a company under CTA 2009). Clearing this delivers a guaranteed "
                    f"22% effective return before any investment allocation."
                ),
            })

        emergency_target = income * 0.25
        priorities.append({
            "order": 2 if cc_debt > 0 else 1,
            "title": "Emergency Fund",
            "amount": round(emergency_target),
            "simple": (
                f"Maintain £{_mn(emergency_target)} (3 months' expenses) in instant-access savings. "
                f"Interest on cash savings is taxable under ITTOIA 2005, but the Personal Savings "
                f"Allowance (ITA 2007, s.12B) exempts the first £500 (higher rate) or £1,000 "
                f"(basic rate) from Income Tax. This reserve prevents forced liquidation of "
                f"investments during market downturns."
            ),
        })

        total_contrib = sum(p.get("annual_contribution", 0) for p in profile.get("pensions", []))
        unused_pension = max(0, PENSION_ANNUAL_ALLOWANCE - total_contrib)
        if unused_pension > 5000 and income > 50000:
            relief = unused_pension * marginal
            priorities.append({
                "order": 3,
                "title": "Pension Contributions",
                "amount": round(unused_pension),
                "simple": (
                    f"FA 2004, s.188: £{_mn(unused_pension)} of unused Annual Allowance available. "
                    f"Tax relief at your {int(marginal * 100)}% marginal rate: £{_mn(relief)} "
                    f"immediate reduction in Income Tax. Pension contributions also reduce "
                    f"adjusted net income for Personal Allowance tapering (ITA 2007, s.35) "
                    f"and HICBC (ITEPA 2003, s.681B). "
                    f"Carry-forward (s.186) permits use of unused allowance from prior 3 years."
                ),
            })

        isa_val = sum(w.get("value", 0) for w in profile.get("investment_wrappers", []) if "isa" in w.get("type", ""))
        priorities.append({
            "order": 4,
            "title": "ISA Contributions",
            "amount": ISA_ANNUAL_ALLOWANCE,
            "simple": (
                f"ISA Regulations 1998: £{ISA_ANNUAL_ALLOWANCE:,}/yr allowance. "
                f"{'No ISA holdings currently — this allowance is unused. ' if isa_val == 0 else f'Current ISA value: £{_mn(isa_val)}. '}"
                f"All gains exempt from CGT (TCGA 1992). All dividends exempt from Income Tax. "
                f"All interest exempt from Income Tax. No reporting requirement on Self Assessment. "
                f"At your {int(marginal * 100)}% rate, this shelters gains that would otherwise "
                f"attract CGT at {CGT_HIGHER_RATE * 100:.0f}% above the £{CGT_ANNUAL_EXEMPT:,} exempt amount."
            ),
        })

        if income > 100000:
            vct_relief = 30000 * VCT_INCOME_TAX_RELIEF
            eis_relief = 20000 * EIS_INCOME_TAX_RELIEF
            priorities.append({
                "order": 5,
                "title": "VCT / EIS Investments",
                "amount": 50000,
                "simple": (
                    f"ITA 2007, Part 6 (VCT) and Part 5 (EIS): "
                    f"VCT: 30% income tax relief on up to £200,000/yr. £30,000 invested = "
                    f"£{_mn(vct_relief)} tax reduction. Dividends tax-free (s.709). "
                    f"EIS: 30% relief on up to £1,000,000/yr. £20,000 invested = "
                    f"£{_mn(eis_relief)} tax reduction. CGT deferral available (s.150C TCGA 1992). "
                    f"Minimum holding: 5 years (VCT) / 3 years (EIS). "
                    f"Higher risk — loss relief available (ITA 2007, s.131) if investment fails."
                ),
            })

        return priorities

    def _wrapper_priority(self, income, wrappers, pensions):
        marginal = 0.45 if income > 125140 else (0.4 if income > 50270 else 0.2)

        order = []
        total_contrib = sum(p.get("annual_contribution", 0) for p in pensions)

        if marginal >= 0.4 and total_contrib < PENSION_ANNUAL_ALLOWANCE:
            unused = PENSION_ANNUAL_ALLOWANCE - total_contrib
            relief = unused * marginal
            order.append({
                "wrapper": "Pension",
                "reason": (
                    f"FA 2004, s.188: {int(marginal * 100)}% tax relief. "
                    f"£{_mn(unused)} unused allowance = £{_mn(relief)} relief"
                ),
                "annual_limit": f"£{PENSION_ANNUAL_ALLOWANCE:,}",
            })

        order.append({
            "wrapper": "ISA",
            "reason": (
                f"ISA Regs 1998: All gains, dividends, interest fully exempt from "
                f"CGT and Income Tax. No annual reporting requirement"
            ),
            "annual_limit": f"£{ISA_ANNUAL_ALLOWANCE:,}",
        })

        if marginal < 0.4 and total_contrib < PENSION_ANNUAL_ALLOWANCE:
            order.append({
                "wrapper": "Pension",
                "reason": f"FA 2004: {int(marginal * 100)}% tax relief on contributions",
                "annual_limit": f"£{PENSION_ANNUAL_ALLOWANCE:,}",
            })

        if income > 100000:
            order.append({
                "wrapper": "VCT / EIS",
                "reason": (
                    f"ITA 2007: 30% income tax relief. VCT dividends tax-free (s.709). "
                    f"EIS: CGT deferral (s.150C TCGA 1992)"
                ),
                "annual_limit": "£200,000 (VCT) / £1,000,000 (EIS)",
            })

        gia_val = sum(w.get("value", 0) for w in wrappers if w.get("type") == "gia")
        order.append({
            "wrapper": "GIA",
            "reason": (
                f"No tax benefits. Gains subject to CGT at {CGT_HIGHER_RATE * 100:.0f}% above "
                f"£{CGT_ANNUAL_EXEMPT:,} exempt amount. Dividends taxed above £{DIVIDEND_ALLOWANCE:,}. "
                f"Use only after tax-efficient wrappers are exhausted"
            ),
            "annual_limit": "Unlimited",
        })

        return order
