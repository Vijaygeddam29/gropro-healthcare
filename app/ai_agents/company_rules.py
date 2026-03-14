from app.utils.constants import (
    HMRC_CORPORATION_TAX_SMALL, HMRC_CORPORATION_TAX_MAIN,
    CT_SMALL_PROFITS_LIMIT, CT_MAIN_RATE_LIMIT, CT_MARGINAL_FRACTION,
    DIRECTORS_OPTIMAL_SALARY, EMPLOYERS_NI_RATE, EMPLOYERS_NI_THRESHOLD,
    PERSONAL_ALLOWANCE, BASIC_RATE, HIGHER_RATE, ADDITIONAL_RATE,
    DIVIDEND_ALLOWANCE, DIVIDEND_BASIC, DIVIDEND_HIGHER, DIVIDEND_ADDITIONAL,
    BASIC_RATE_BAND, HIGHER_RATE_BAND, S455_TAX_RATE,
)


class CompanyCalculator:

    def corporation_tax(self, profits, num_associated=1):
        adjusted_small = CT_SMALL_PROFITS_LIMIT / num_associated
        adjusted_main = CT_MAIN_RATE_LIMIT / num_associated

        if profits <= adjusted_small:
            return round(profits * HMRC_CORPORATION_TAX_SMALL, 2)
        elif profits >= adjusted_main:
            return round(profits * HMRC_CORPORATION_TAX_MAIN, 2)
        else:
            main_tax = profits * HMRC_CORPORATION_TAX_MAIN
            marginal_relief = (adjusted_main - profits) * CT_MARGINAL_FRACTION
            return round(main_tax - marginal_relief, 2)

    def optimal_salary_dividend_split(self, company_profits, other_income=0):
        optimal_salary = DIRECTORS_OPTIMAL_SALARY
        employers_ni = max(0, (optimal_salary - EMPLOYERS_NI_THRESHOLD)) * EMPLOYERS_NI_RATE
        remaining_profits = company_profits - optimal_salary - employers_ni
        ct = self.corporation_tax(max(0, remaining_profits))
        distributable = max(0, remaining_profits - ct)

        remaining_basic = max(0, BASIC_RATE_BAND - max(0, optimal_salary + other_income - PERSONAL_ALLOWANCE))
        basic_div = min(distributable, remaining_basic + DIVIDEND_ALLOWANCE)
        higher_div = max(0, distributable - basic_div)

        div_tax_basic = max(0, min(basic_div, basic_div - DIVIDEND_ALLOWANCE)) * DIVIDEND_BASIC
        div_tax_higher = higher_div * DIVIDEND_HIGHER

        total_personal_tax = div_tax_basic + div_tax_higher
        total_take_home = optimal_salary + distributable - total_personal_tax
        total_tax_all = ct + employers_ni + total_personal_tax

        return {
            "optimal_salary": optimal_salary,
            "employers_ni": round(employers_ni, 2),
            "corporation_tax": round(ct, 2),
            "distributable_profits": round(distributable, 2),
            "dividend_tax": round(div_tax_basic + div_tax_higher, 2),
            "total_take_home": round(total_take_home, 2),
            "total_tax": round(total_tax_all, 2),
            "effective_rate": round((total_tax_all / company_profits) * 100, 1) if company_profits > 0 else 0,
        }

    def vs_sole_trader(self, profits):
        from app.ai_agents.tax_rules import TaxCalculator
        tax_calc = TaxCalculator()

        sole_trader_it = tax_calc.income_tax(profits)
        sole_trader_ni = tax_calc.national_insurance_self_employed(profits)
        sole_trader_total = sole_trader_it["total_tax"] + sole_trader_ni
        sole_trader_take_home = profits - sole_trader_total

        ltd = self.optimal_salary_dividend_split(profits)

        saving = sole_trader_total - ltd["total_tax"]

        return {
            "sole_trader_tax": round(sole_trader_total, 2),
            "sole_trader_take_home": round(sole_trader_take_home, 2),
            "ltd_tax": ltd["total_tax"],
            "ltd_take_home": ltd["total_take_home"],
            "annual_saving": round(saving, 2),
            "better_structure": "ltd" if saving > 0 else "sole_trader",
        }

    def ir35_risk_score(self, factors):
        score = 0
        max_score = 0

        checks = [
            ("control", "Does the client control how you do the work?", 20),
            ("substitution", "Can you send someone else to do the work?", -15),
            ("moo", "Is there a mutual obligation to provide/accept work?", 20),
            ("equipment", "Do you use your own equipment?", -10),
            ("financial_risk", "Do you bear financial risk?", -10),
            ("part_of_org", "Are you part of the client's organisation?", 15),
            ("right_of_dismissal", "Can the client dismiss you like an employee?", 10),
            ("multiple_clients", "Do you work for multiple clients?", -10),
            ("benefits", "Do you receive employee benefits?", 10),
            ("intention", "Does the contract state self-employment?", -5),
        ]

        results = []
        for key, question, weight in checks:
            answer = factors.get(key, None)
            max_score += abs(weight)
            if answer is True:
                score += weight
            results.append({"factor": question, "weight": weight, "answer": answer})

        risk_pct = max(0, min(100, (score / max_score) * 100)) if max_score > 0 else 50

        if risk_pct >= 70:
            risk_level = "high"
        elif risk_pct >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_score": round(risk_pct, 1),
            "risk_level": risk_level,
            "factors": results,
        }

    def fic_analysis(self, capital, annual_investment_return=0.06, years=20, num_shareholders=2):
        retained = capital
        growth_history = []

        for year in range(1, years + 1):
            returns = retained * annual_investment_return
            ct = self.corporation_tax(returns)
            retained = retained + returns - ct
            growth_history.append({"year": year, "value": round(retained, 2)})

        annual_dividend_per_person = (retained * annual_investment_return * (1 - HMRC_CORPORATION_TAX_SMALL)) / num_shareholders if num_shareholders > 0 else 0

        return {
            "initial_capital": capital,
            "projected_value": round(retained, 2),
            "years": years,
            "growth_rate": annual_investment_return,
            "annual_dividend_per_shareholder": round(annual_dividend_per_person, 2),
            "num_shareholders": num_shareholders,
            "iht_benefit": "FIC shares can be structured to freeze value for IHT purposes",
        }

    def s455_loan_tax(self, loan_amount):
        tax = loan_amount * S455_TAX_RATE
        return {
            "loan_amount": loan_amount,
            "s455_tax": round(tax, 2),
            "repayment_deadline": "9 months after company year-end",
        }

    def analyse_companies(self, companies_list, total_income):
        results = []
        for comp in companies_list:
            ctype = comp.get("type", "")
            turnover = comp.get("turnover", 0)
            retained = comp.get("retained_profits", 0)
            dividends = comp.get("dividends_paid", 0)
            shareholding = comp.get("shareholding_pct", 100)
            others = comp.get("other_shareholders", 0)

            ct = self.corporation_tax(retained)
            split = self.optimal_salary_dividend_split(turnover)

            your_dividend = dividends * (shareholding / 100) if shareholding > 0 else 0

            result = {
                "type": ctype,
                "turnover": turnover,
                "retained_profits": retained,
                "corporation_tax": ct,
                "your_shareholding": shareholding,
                "your_dividend_share": round(your_dividend, 2),
                "optimal_split": split,
            }

            if ctype.lower() == "fic":
                fic = self.fic_analysis(retained, num_shareholders=others + 1)
                result["fic_projection"] = fic

            results.append(result)

        return results
