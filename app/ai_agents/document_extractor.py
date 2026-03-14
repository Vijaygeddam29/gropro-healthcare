import os
import re


class DocumentExtractor:

    DOCUMENT_PATTERNS = {
        "sa302": {
            "keywords": ["sa302", "tax calculation", "self assessment", "hmrc", "tax year"],
            "fields": ["total_income", "tax_due", "tax_paid", "ni_contributions"],
        },
        "p60": {
            "keywords": ["p60", "end of year", "tax deducted", "ni contributions", "employer"],
            "fields": ["gross_pay", "tax_deducted", "ni_contributions", "student_loan"],
        },
        "payslip": {
            "keywords": ["payslip", "pay slip", "net pay", "gross pay", "tax period", "nhs", "basic pay"],
            "fields": ["gross_pay", "tax_deducted", "ni_deducted", "pension_deducted", "net_pay"],
        },
        "pension_statement": {
            "keywords": ["pension", "annual benefit", "retirement", "accrued", "scheme", "sipp", "drawdown"],
            "fields": ["pension_value", "annual_pension", "contributions", "lump_sum"],
        },
        "bank_statement": {
            "keywords": ["statement", "balance", "credit", "debit", "account", "sort code", "transaction"],
            "fields": ["credits_total", "debits_total", "closing_balance", "income_identified", "expenses_identified"],
        },
        "company_accounts": {
            "keywords": ["corporation tax", "directors", "turnover", "profit", "balance sheet", "companies house"],
            "fields": ["turnover", "gross_profit", "net_profit", "corporation_tax", "dividends", "retained_profits"],
        },
        "mortgage_statement": {
            "keywords": ["mortgage", "outstanding balance", "monthly payment", "interest rate", "lender"],
            "fields": ["outstanding_balance", "monthly_payment", "interest_rate"],
        },
        "investment_statement": {
            "keywords": ["investment", "portfolio", "isa", "stocks", "shares", "unit trust", "fund"],
            "fields": ["portfolio_value", "gains_losses", "dividends_received"],
        },
        "ct600": {
            "keywords": ["ct600", "corporation tax return", "chargeable profits", "tax payable"],
            "fields": ["turnover", "chargeable_profits", "ct_payable", "dividends_paid"],
        },
    }

    def identify_document_type(self, filename, text_content=""):
        filename_lower = filename.lower()
        content_lower = text_content.lower() if text_content else ""
        combined = filename_lower + " " + content_lower

        scores = {}
        for doc_type, info in self.DOCUMENT_PATTERNS.items():
            score = 0
            for keyword in info["keywords"]:
                if keyword in combined:
                    score += 1
            if score > 0:
                scores[doc_type] = score

        if not scores:
            return "unknown"

        return max(scores, key=scores.get)

    def extract_from_text(self, text_content, document_type=None):
        if not text_content:
            return {"document_type": document_type or "unknown", "extracted": {}, "confidence": "low"}

        if not document_type:
            document_type = self.identify_document_type("", text_content)

        extracted = {}
        confidence = "medium"

        amounts = re.findall(r'£\s?([\d,]+(?:\.\d{2})?)', text_content)
        amounts = [float(a.replace(',', '')) for a in amounts]

        if document_type == "sa302":
            extracted = self._extract_sa302(text_content, amounts)
        elif document_type == "p60":
            extracted = self._extract_p60(text_content, amounts)
        elif document_type == "payslip":
            extracted = self._extract_payslip(text_content, amounts)
        elif document_type == "pension_statement":
            extracted = self._extract_pension(text_content, amounts)
        elif document_type == "bank_statement":
            extracted = self._extract_bank_statement(text_content, amounts)
        elif document_type == "company_accounts":
            extracted = self._extract_company_accounts(text_content, amounts)
        elif document_type == "mortgage_statement":
            extracted = self._extract_mortgage(text_content, amounts)
        elif document_type == "investment_statement":
            extracted = self._extract_investment(text_content, amounts)
        elif document_type == "ct600":
            extracted = self._extract_ct600(text_content, amounts)
        else:
            if amounts:
                extracted["amounts_found"] = sorted(amounts, reverse=True)[:10]
                confidence = "low"

        if extracted:
            confidence = "high" if len(extracted) >= 3 else "medium"

        return {
            "document_type": document_type,
            "extracted": extracted,
            "confidence": confidence,
        }

    def build_profile_updates(self, extraction_result):
        doc_type = extraction_result.get("document_type", "")
        data = extraction_result.get("extracted", {})
        updates = {}

        if doc_type == "sa302":
            if data.get("total_income"):
                updates["income"] = data["total_income"]
            if data.get("tax_paid"):
                updates["tax_paid"] = data["tax_paid"]

        elif doc_type == "p60":
            if data.get("gross_pay"):
                updates["income_streams_update"] = {
                    "source": "paye",
                    "amount": data["gross_pay"],
                }
            if data.get("tax_deducted"):
                updates["tax_paid"] = data["tax_deducted"]

        elif doc_type == "payslip":
            if data.get("gross_pay"):
                annual = data["gross_pay"] * 12
                updates["income_streams_update"] = {
                    "source": "paye",
                    "amount": annual,
                    "note": f"Annualised from monthly gross of £{data['gross_pay']:,.0f}",
                }
            if data.get("pension_deducted"):
                annual_contrib = data["pension_deducted"] * 12
                updates["pension_contribution_update"] = annual_contrib

        elif doc_type == "pension_statement":
            updates["pension_update"] = {}
            if data.get("pension_value"):
                updates["pension_update"]["value"] = data["pension_value"]
            if data.get("contributions"):
                updates["pension_update"]["annual_contribution"] = data["contributions"]
            if data.get("pension_type"):
                updates["pension_update"]["type"] = data["pension_type"]

        elif doc_type == "bank_statement":
            if data.get("income_identified"):
                updates["income_from_bank"] = data["income_identified"]
            if data.get("expenses_identified"):
                updates["expenses_from_bank"] = data["expenses_identified"]

        elif doc_type in ("company_accounts", "ct600"):
            updates["company_update"] = {}
            if data.get("turnover"):
                updates["company_update"]["turnover"] = data["turnover"]
            if data.get("net_profit") or data.get("chargeable_profits"):
                updates["company_update"]["retained_profits"] = data.get("net_profit") or data.get("chargeable_profits")
            if data.get("dividends") or data.get("dividends_paid"):
                updates["company_update"]["dividends_paid"] = data.get("dividends") or data.get("dividends_paid")

        elif doc_type == "mortgage_statement":
            updates["debt_update"] = {
                "type": "mortgage",
                "balance": data.get("outstanding_balance", 0),
            }

        elif doc_type == "investment_statement":
            if data.get("portfolio_value"):
                updates["investment_update"] = {
                    "value": data["portfolio_value"],
                }

        return updates

    def _extract_sa302(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        for pattern, key in [
            (r'total\s+income[:\s]*£?\s?([\d,]+)', "total_income"),
            (r'tax\s+(?:due|payable|charged)[:\s]*£?\s?([\d,]+)', "tax_due"),
            (r'(?:tax\s+)?(?:already\s+)?paid[:\s]*£?\s?([\d,]+)', "tax_paid"),
            (r'(?:class\s+[24]\s+)?ni\s+contributions?[:\s]*£?\s?([\d,]+)', "ni_contributions"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                extracted[key] = float(match.group(1).replace(',', ''))

        if not extracted and amounts:
            sorted_amounts = sorted(amounts, reverse=True)
            if len(sorted_amounts) >= 2:
                extracted["total_income"] = sorted_amounts[0]
                extracted["tax_paid"] = sorted_amounts[1]

        return extracted

    def _extract_p60(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        for pattern, key in [
            (r'(?:total\s+)?(?:gross\s+)?pay[:\s]*£?\s?([\d,]+)', "gross_pay"),
            (r'tax\s+deducted[:\s]*£?\s?([\d,]+)', "tax_deducted"),
            (r'ni\s+contributions?[:\s]*£?\s?([\d,]+)', "ni_contributions"),
            (r'student\s+loan[:\s]*£?\s?([\d,]+)', "student_loan"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                extracted[key] = float(match.group(1).replace(',', ''))

        return extracted

    def _extract_payslip(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        for pattern, key in [
            (r'(?:basic|gross)\s+pay[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "gross_pay"),
            (r'(?:paye|tax)\s+(?:deducted)?[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "tax_deducted"),
            (r'(?:ni|national\s+insurance)[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "ni_deducted"),
            (r'pension[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "pension_deducted"),
            (r'net\s+pay[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "net_pay"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                extracted[key] = float(match.group(1).replace(',', ''))

        return extracted

    def _extract_pension(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        if "nhs" in text_l and "1995" in text_l:
            extracted["pension_type"] = "nhs_1995"
        elif "nhs" in text_l and "2008" in text_l:
            extracted["pension_type"] = "nhs_2008"
        elif "nhs" in text_l and "2015" in text_l:
            extracted["pension_type"] = "nhs_2015"
        elif "sipp" in text_l or "self-invested" in text_l:
            extracted["pension_type"] = "sipp"

        for pattern, key in [
            (r'(?:total|current)\s+(?:fund|pot|value)[:\s]*£?\s?([\d,]+)', "pension_value"),
            (r'(?:annual|yearly)\s+pension[:\s]*£?\s?([\d,]+)', "annual_pension"),
            (r'(?:annual\s+)?contributions?[:\s]*£?\s?([\d,]+)', "contributions"),
            (r'(?:lump\s+sum|pcls)[:\s]*£?\s?([\d,]+)', "lump_sum"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                extracted[key] = float(match.group(1).replace(',', ''))

        return extracted

    def _extract_bank_statement(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        for pattern, key in [
            (r'(?:closing|final)\s+balance[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "closing_balance"),
            (r'(?:total\s+)?(?:credits?|money\s+in)[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "credits_total"),
            (r'(?:total\s+)?(?:debits?|money\s+out)[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "debits_total"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                extracted[key] = float(match.group(1).replace(',', ''))

        salary_patterns = [r'nhs', r'salary', r'wages', r'locum', r'bma']
        income_total = 0
        for line in text.split('\n'):
            line_l = line.lower()
            for sp in salary_patterns:
                if sp in line_l:
                    line_amounts = re.findall(r'£?\s?([\d,]+(?:\.\d{2})?)', line)
                    for la in line_amounts:
                        val = float(la.replace(',', ''))
                        if val > 500:
                            income_total += val

        if income_total > 0:
            extracted["income_identified"] = income_total

        expense_patterns = [r'mortgage', r'rent', r'insurance', r'electric', r'gas', r'water', r'council']
        expense_total = 0
        for line in text.split('\n'):
            line_l = line.lower()
            for ep in expense_patterns:
                if ep in line_l:
                    line_amounts = re.findall(r'£?\s?([\d,]+(?:\.\d{2})?)', line)
                    for la in line_amounts:
                        val = float(la.replace(',', ''))
                        if val > 50:
                            expense_total += val

        if expense_total > 0:
            extracted["expenses_identified"] = expense_total

        return extracted

    def _extract_company_accounts(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        for pattern, key in [
            (r'turnover[:\s]*£?\s?([\d,]+)', "turnover"),
            (r'gross\s+profit[:\s]*£?\s?([\d,]+)', "gross_profit"),
            (r'(?:net|operating)\s+profit[:\s]*£?\s?([\d,]+)', "net_profit"),
            (r'corporation\s+tax[:\s]*£?\s?([\d,]+)', "corporation_tax"),
            (r'dividends?\s+(?:paid|declared)[:\s]*£?\s?([\d,]+)', "dividends"),
            (r'retained\s+(?:profits?|earnings)[:\s]*£?\s?([\d,]+)', "retained_profits"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                extracted[key] = float(match.group(1).replace(',', ''))

        return extracted

    def _extract_mortgage(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        for pattern, key in [
            (r'(?:outstanding|current)\s+balance[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "outstanding_balance"),
            (r'monthly\s+payment[:\s]*£?\s?([\d,]+(?:\.\d{2})?)', "monthly_payment"),
            (r'interest\s+rate[:\s]*([\d.]+)\s*%', "interest_rate"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                val = match.group(1).replace(',', '')
                extracted[key] = float(val)

        return extracted

    def _extract_investment(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        for pattern, key in [
            (r'(?:total|portfolio)\s+value[:\s]*£?\s?([\d,]+)', "portfolio_value"),
            (r'(?:total\s+)?(?:gains?|growth)[:\s]*£?\s?([\d,]+)', "gains_losses"),
            (r'dividends?\s+(?:received|paid)[:\s]*£?\s?([\d,]+)', "dividends_received"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                extracted[key] = float(match.group(1).replace(',', ''))

        return extracted

    def _extract_ct600(self, text, amounts):
        extracted = {}
        text_l = text.lower()

        for pattern, key in [
            (r'(?:total\s+)?turnover[:\s]*£?\s?([\d,]+)', "turnover"),
            (r'(?:chargeable|taxable)\s+profits?[:\s]*£?\s?([\d,]+)', "chargeable_profits"),
            (r'(?:ct|corporation\s+tax)\s+(?:payable|due)[:\s]*£?\s?([\d,]+)', "ct_payable"),
            (r'dividends?\s+(?:paid|declared)[:\s]*£?\s?([\d,]+)', "dividends_paid"),
        ]:
            match = re.search(pattern, text_l)
            if match:
                extracted[key] = float(match.group(1).replace(',', ''))

        return extracted
