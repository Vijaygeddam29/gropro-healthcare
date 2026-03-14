from app.utils.constants import (
    PERSONAL_ALLOWANCE, BASIC_RATE, HIGHER_RATE, ADDITIONAL_RATE,
    BASIC_RATE_BAND, HIGHER_RATE_BAND, PA_TAPER_THRESHOLD,
    NI_PRIMARY_THRESHOLD, NI_UPPER_EARNINGS_LIMIT, NI_RATE_MAIN, NI_RATE_UPPER,
    NI_CLASS4_LOWER, NI_CLASS4_UPPER, NI_CLASS4_RATE_MAIN, NI_CLASS4_RATE_UPPER,
    DIVIDEND_ALLOWANCE, DIVIDEND_BASIC, DIVIDEND_HIGHER, DIVIDEND_ADDITIONAL,
    STUDENT_LOAN_THRESHOLDS, CHILD_BENEFIT_TAPER_START, CHILD_BENEFIT_TAPER_END,
    CHILD_BENEFIT_WEEKLY_FIRST, CHILD_BENEFIT_WEEKLY_ADDITIONAL,
    MARRIAGE_ALLOWANCE_TRANSFER,
)


class TaxCalculator:

    def personal_allowance(self, gross_income):
        if gross_income <= PA_TAPER_THRESHOLD:
            return PERSONAL_ALLOWANCE
        reduction = (gross_income - PA_TAPER_THRESHOLD) / 2
        return max(0, PERSONAL_ALLOWANCE - reduction)

    def income_tax(self, gross_income, pension_contributions=0):
        taxable = gross_income - pension_contributions
        pa = self.personal_allowance(taxable)
        taxable_after_pa = max(0, taxable - pa)

        basic_taxable = min(taxable_after_pa, BASIC_RATE_BAND)
        higher_taxable = min(max(0, taxable_after_pa - BASIC_RATE_BAND), HIGHER_RATE_BAND - BASIC_RATE_BAND)
        additional_taxable = max(0, taxable_after_pa - HIGHER_RATE_BAND)

        tax = basic_taxable * BASIC_RATE + higher_taxable * HIGHER_RATE + additional_taxable * ADDITIONAL_RATE

        return {
            "total_tax": round(tax, 2),
            "effective_rate": round((tax / gross_income) * 100, 1) if gross_income > 0 else 0,
            "marginal_rate": self.marginal_rate(taxable_after_pa),
            "personal_allowance": round(pa, 2),
            "basic_band_tax": round(basic_taxable * BASIC_RATE, 2),
            "higher_band_tax": round(higher_taxable * HIGHER_RATE, 2),
            "additional_band_tax": round(additional_taxable * ADDITIONAL_RATE, 2),
            "pa_lost": round(max(0, PERSONAL_ALLOWANCE - pa), 2),
        }

    def marginal_rate(self, taxable_income):
        if taxable_income <= BASIC_RATE_BAND:
            return BASIC_RATE
        elif taxable_income <= HIGHER_RATE_BAND:
            return HIGHER_RATE
        return ADDITIONAL_RATE

    def national_insurance_employed(self, gross_salary):
        if gross_salary <= NI_PRIMARY_THRESHOLD:
            return 0
        main_ni = min(gross_salary, NI_UPPER_EARNINGS_LIMIT) - NI_PRIMARY_THRESHOLD
        upper_ni = max(0, gross_salary - NI_UPPER_EARNINGS_LIMIT)
        return round(main_ni * NI_RATE_MAIN + upper_ni * NI_RATE_UPPER, 2)

    def national_insurance_self_employed(self, profits):
        if profits <= NI_CLASS4_LOWER:
            return 0
        main_ni = min(profits, NI_CLASS4_UPPER) - NI_CLASS4_LOWER
        upper_ni = max(0, profits - NI_CLASS4_UPPER)
        return round(main_ni * NI_CLASS4_RATE_MAIN + upper_ni * NI_CLASS4_RATE_UPPER, 2)

    def dividend_tax(self, dividends, other_income=0):
        if dividends <= DIVIDEND_ALLOWANCE:
            return 0
        taxable_divs = dividends - DIVIDEND_ALLOWANCE
        remaining_basic = max(0, BASIC_RATE_BAND - max(0, other_income - self.personal_allowance(other_income)))
        basic_div = min(taxable_divs, remaining_basic)
        remaining_after_basic = taxable_divs - basic_div
        remaining_higher = max(0, HIGHER_RATE_BAND - BASIC_RATE_BAND - max(0, other_income - PERSONAL_ALLOWANCE - BASIC_RATE_BAND))
        higher_div = min(remaining_after_basic, remaining_higher) if remaining_higher > 0 else 0
        additional_div = max(0, remaining_after_basic - higher_div)

        return round(
            basic_div * DIVIDEND_BASIC +
            higher_div * DIVIDEND_HIGHER +
            additional_div * DIVIDEND_ADDITIONAL, 2
        )

    def student_loan_repayment(self, gross_income, plan):
        if plan not in STUDENT_LOAN_THRESHOLDS:
            return 0
        info = STUDENT_LOAN_THRESHOLDS[plan]
        if gross_income <= info["threshold"]:
            return 0
        return round((gross_income - info["threshold"]) * info["rate"], 2)

    def child_benefit_charge(self, adjusted_income, num_children):
        if num_children <= 0 or adjusted_income <= CHILD_BENEFIT_TAPER_START:
            return 0
        annual_benefit = (CHILD_BENEFIT_WEEKLY_FIRST + max(0, num_children - 1) * CHILD_BENEFIT_WEEKLY_ADDITIONAL) * 52
        if adjusted_income >= CHILD_BENEFIT_TAPER_END:
            return round(annual_benefit, 2)
        taper_pct = min(100, ((adjusted_income - CHILD_BENEFIT_TAPER_START) / 200))
        return round(annual_benefit * taper_pct / 100, 2)

    def pension_tax_relief(self, contribution, marginal_rate_pct):
        return round(contribution * marginal_rate_pct, 2)

    def total_tax_burden(self, profile):
        income_streams = profile.get("income_streams", [])
        pensions = profile.get("pensions", [])
        tax_status = profile.get("tax_status", {})
        personal = profile.get("personal", {})

        employed_income = 0
        self_employed_income = 0
        dividend_income = 0
        rental_income = 0

        for s in income_streams:
            source = s.get("source", "")
            amount = s.get("amount", 0)
            if source in ("paye", "nhs_consultant", "gp_salaried", "teaching", "research"):
                employed_income += amount
            elif source in ("locum", "private_practice", "medico_legal", "gp_partner"):
                self_employed_income += amount
            elif source in ("dividend_income",):
                dividend_income += amount
            elif source in ("rental_income",):
                rental_income += amount
            elif source in ("ltd_director",):
                employed_income += min(amount, PERSONAL_ALLOWANCE)
                dividend_income += max(0, amount - PERSONAL_ALLOWANCE)
            elif source in ("fic_director",):
                dividend_income += amount
            else:
                self_employed_income += amount

        total_pension_contrib = sum(p.get("annual_contribution", 0) for p in pensions)

        non_dividend_income = employed_income + self_employed_income + rental_income
        it = self.income_tax(non_dividend_income, total_pension_contrib)
        ni_emp = self.national_insurance_employed(employed_income)
        ni_se = self.national_insurance_self_employed(self_employed_income)
        div_tax = self.dividend_tax(dividend_income, non_dividend_income)

        student_loan = tax_status.get("student_loan", "none")
        sl_repayment = self.student_loan_repayment(non_dividend_income, student_loan)

        dependants = int(personal.get("dependants", "0").replace("+", "")) if personal.get("dependants") else 0
        hicbc = self.child_benefit_charge(non_dividend_income + dividend_income, dependants)

        total_tax = it["total_tax"] + ni_emp + ni_se + div_tax + sl_repayment + hicbc
        total_gross = non_dividend_income + dividend_income

        return {
            "income_tax": it["total_tax"],
            "national_insurance": round(ni_emp + ni_se, 2),
            "dividend_tax": div_tax,
            "student_loan": sl_repayment,
            "child_benefit_charge": hicbc,
            "total_tax": round(total_tax, 2),
            "take_home": round(total_gross - total_tax, 2),
            "effective_rate": round((total_tax / total_gross) * 100, 1) if total_gross > 0 else 0,
            "marginal_rate": it["marginal_rate"],
            "personal_allowance": it["personal_allowance"],
            "pa_lost": it["pa_lost"],
            "pension_relief": round(total_pension_contrib * it["marginal_rate"], 2),
            "gross_income": round(total_gross, 2),
            "employed_income": employed_income,
            "self_employed_income": self_employed_income,
            "dividend_income": dividend_income,
            "rental_income": rental_income,
        }
