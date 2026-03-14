from app.ai_agents.company_rules import CompanyCalculator
from app.ai_agents.tax_rules import TaxCalculator
from app.utils.constants import (
    DIVIDEND_ALLOWANCE, DIVIDEND_BASIC, DIVIDEND_HIGHER, DIVIDEND_ADDITIONAL,
    HMRC_CORPORATION_TAX_SMALL, HMRC_CORPORATION_TAX_MAIN,
    CT_SMALL_PROFITS_LIMIT, CT_MAIN_RATE_LIMIT,
)


def _mn(v):
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:,.2f}Mn"
    return f"{v:,.0f}"


class FICOptimizer:

    def __init__(self, fic=None, dividend_options=None):
        self.fic = fic
        self.dividend_options = dividend_options
        self.company_calc = CompanyCalculator()
        self.tax_calc = TaxCalculator()

    def optimize(self):
        if self.dividend_options:
            ranked = sorted(self.dividend_options, key=lambda x: x['net_return'], reverse=True)
            return ranked[0:3]
        return []

    def full_analysis(self, companies_list, total_income):
        fic_companies = [c for c in companies_list if c.get("type", "").lower() == "fic"]
        if not fic_companies:
            return None

        results = []
        for fic in fic_companies:
            retained = fic.get("retained_profits", 0)
            dividends = fic.get("dividends_paid", 0)
            shareholding = fic.get("shareholding_pct", 100)
            others = fic.get("other_shareholders", 0)
            num_shareholders = others + 1

            analysis = {
                "capital": retained,
                "strategies": self._dividend_strategies(retained, dividends, num_shareholders, total_income),
                "income_splitting": self._income_splitting(dividends, num_shareholders, total_income),
                "iht_planning": self._iht_explanation(retained),
                "projection": self.company_calc.fic_analysis(retained, num_shareholders=num_shareholders),
            }
            results.append(analysis)

        return results

    def _dividend_strategies(self, retained, current_dividends, num_shareholders, personal_income):
        strategies = []
        marginal_div_rate = DIVIDEND_ADDITIONAL if personal_income > 125140 else (DIVIDEND_HIGHER if personal_income > 50270 else DIVIDEND_BASIC)
        rate_label = f"{marginal_div_rate * 100:.2f}%"

        if num_shareholders > 1:
            per_person = current_dividends / num_shareholders
            if per_person <= DIVIDEND_ALLOWANCE:
                tax = 0
            else:
                tax = (per_person - DIVIDEND_ALLOWANCE) * DIVIDEND_BASIC * num_shareholders
            one_person_tax = max(0, current_dividends - DIVIDEND_ALLOWANCE) * marginal_div_rate
            saving = max(0, one_person_tax - tax)
            strategies.append({
                "name": "Split Dividends Equally",
                "dividends_per_person": round(per_person),
                "total_dividend_tax": round(tax),
                "simple": (
                    f"ITTOIA 2005, s.383: Distribute £{_mn(current_dividends)} equally across "
                    f"{num_shareholders} shareholders (£{_mn(per_person)} each). "
                    f"Each shareholder receives their own £{DIVIDEND_ALLOWANCE:,} tax-free "
                    f"Dividend Allowance (ITA 2007, s.13A). "
                    f"If taken by one person at your {rate_label} rate: tax of £{_mn(one_person_tax)}. "
                    f"Split equally: tax of £{_mn(tax)}. "
                    f"Annual saving: £{_mn(saving)}."
                ),
            })

        ct_rate = f"{HMRC_CORPORATION_TAX_SMALL * 100:.0f}%" if retained <= CT_SMALL_PROFITS_LIMIT else f"{HMRC_CORPORATION_TAX_MAIN * 100:.0f}%"
        ct_amount = retained * (HMRC_CORPORATION_TAX_SMALL if retained <= CT_SMALL_PROFITS_LIMIT else HMRC_CORPORATION_TAX_MAIN)
        strategies.append({
            "name": "Retain & Invest Within FIC",
            "dividends_per_person": 0,
            "total_dividend_tax": 0,
            "simple": (
                f"CTA 2010, s.3: Retain profits within the FIC. Corporation Tax on retained "
                f"profits of £{_mn(retained)}: {ct_rate} = £{_mn(ct_amount)}. "
                f"If extracted as dividends, you would additionally pay dividend tax at "
                f"{rate_label} (ITTOIA 2005). Total combined rate if extracted: "
                f"approximately {(1 - (1 - HMRC_CORPORATION_TAX_SMALL) * (1 - marginal_div_rate)) * 100:.1f}%. "
                f"Retaining profits allows investment growth at the lower corporate tax rate. "
                f"Investment income within the company is subject to CT, not personal tax."
            ),
        })

        if num_shareholders >= 2:
            spouse_div = min(DIVIDEND_ALLOWANCE + 37700, current_dividends)
            your_div = current_dividends - spouse_div
            spouse_tax = max(0, spouse_div - DIVIDEND_ALLOWANCE) * DIVIDEND_BASIC
            your_tax = max(0, your_div - DIVIDEND_ALLOWANCE) * marginal_div_rate
            combined = spouse_tax + your_tax
            one_person_tax = max(0, current_dividends - DIVIDEND_ALLOWANCE) * marginal_div_rate
            saving = max(0, one_person_tax - combined)
            strategies.append({
                "name": "Spouse-Optimised Extraction",
                "dividends_per_person": round(spouse_div),
                "total_dividend_tax": round(combined),
                "simple": (
                    f"ITTOIA 2005: Allocate £{_mn(spouse_div)} to spouse (taxed at basic rate "
                    f"of {DIVIDEND_BASIC * 100:.2f}% under s.8 ITA 2007), £{_mn(your_div)} to you. "
                    f"Spouse tax: £{_mn(spouse_tax)}. Your tax: £{_mn(your_tax)}. "
                    f"Combined: £{_mn(combined)} versus £{_mn(one_person_tax)} if taken alone. "
                    f"Saving: £{_mn(saving)}/yr. "
                    f"Note: HMRC settlements legislation (ITTOIA 2005, s.624) does not apply "
                    f"to dividends on ordinary shares if the spouse owns them outright (Arctic Systems ruling)."
                ),
            })

        return strategies

    def _income_splitting(self, total_dividends, num_shareholders, total_income):
        if num_shareholders <= 1:
            return {
                "available": False,
                "simple": (
                    "Income splitting requires multiple shareholders. Under company law "
                    "(Companies Act 2006), you can issue shares to family members. "
                    "Each shareholder receives their own Dividend Allowance (£1,000) and "
                    "accesses lower tax bands independently."
                ),
            }

        per_person = total_dividends / num_shareholders
        marginal = DIVIDEND_HIGHER if total_income > 50270 else DIVIDEND_BASIC
        one_person_tax = max(0, total_dividends - DIVIDEND_ALLOWANCE) * marginal
        split_tax = max(0, per_person - DIVIDEND_ALLOWANCE) * DIVIDEND_BASIC * num_shareholders
        saving = max(0, one_person_tax - split_tax)

        return {
            "available": True,
            "saving": round(saving),
            "simple": (
                f"ITTOIA 2005, s.383: Splitting £{_mn(total_dividends)} between "
                f"{num_shareholders} shareholders (£{_mn(per_person)} each). "
                f"Single-person tax at {marginal * 100:.2f}%: £{_mn(one_person_tax)}. "
                f"Split tax (each at basic rate {DIVIDEND_BASIC * 100:.2f}%): £{_mn(split_tax)}. "
                f"Annual saving: £{_mn(saving)}. "
                f"Each shareholder uses their £{DIVIDEND_ALLOWANCE:,} allowance (ITA 2007, s.13A) "
                f"and basic rate band independently."
            ),
        }

    def _iht_explanation(self, capital):
        iht_exposure = max(0, capital - 325000) * 0.4
        nil_rate = 325000
        return {
            "potential_iht_saving": round(capital * 0.4),
            "simple": (
                f"IHTA 1984, s.3A: The Nil-Rate Band is £{nil_rate:,}. "
                f"FIC assets of £{_mn(capital)} above this threshold face IHT at 40% "
                f"on death: potential charge of £{_mn(iht_exposure)}. "
                f"Planning options under IHTA 1984: (1) Gift shares — potentially exempt "
                f"transfers (s.3A) fall out of estate after 7 years (s.3, taper relief under s.7). "
                f"(2) Issue different share classes (growth shares to next generation, fixed-value "
                f"shares retained) to freeze estate value. "
                f"(3) Business Property Relief (s.104) may apply at 50% if the FIC qualifies "
                f"as a trading company or holds qualifying business assets."
            ),
        }
