import json
import os
import uuid
import shutil
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List

from app.database import SessionLocal
from app.models.models import UserProfile
from app.ai_agents.financial_mri import FinancialMRI
from app.ai_agents.pension_ai import PensionAI

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def safe_float(val, default=0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_json(val):
    if isinstance(val, (list, dict)):
        return val
    if not val:
        return []
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


def age_from_range(age_range):
    if not age_range:
        return 40
    if age_range == "65+":
        return 67
    if "-" in age_range:
        parts = age_range.split("-")
        return (int(parts[0]) + int(parts[1])) // 2
    return 40


@router.get("/onboarding")
def onboarding_get(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)
    return templates.TemplateResponse("onboarding.html", {"request": request})


@router.post("/onboarding/ai-review")
async def ai_review(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    data = await request.json()

    gaps = []
    insights = []

    age_range = data.get("age_range", "")
    marital_status = data.get("marital_status", "")
    dependants = data.get("dependants", "")
    uk_resident = data.get("uk_resident", "")
    roles = safe_json(data.get("roles", ""))
    ir35_status = data.get("ir35_status", "")
    private_structure = data.get("private_structure", "")
    income_streams = safe_json(data.get("income_streams", ""))
    tax_filing = data.get("tax_filing", "")
    tax_code = data.get("tax_code", "")
    student_loan = data.get("student_loan", "")
    tax_paid = safe_float(data.get("tax_paid", 0))
    pensions_data = safe_json(data.get("pensions_data", ""))
    companies_data = safe_json(data.get("companies_data", ""))
    investment_wrappers = safe_json(data.get("investment_wrappers", ""))
    debt_breakdown = safe_json(data.get("debt_breakdown", ""))
    document_types = safe_json(data.get("document_types", ""))

    total_income = sum(s.get("amount", 0) for s in income_streams)
    total_pension_value = sum(p.get("value", 0) for p in pensions_data)
    total_pension_contrib = sum(p.get("annual_contribution", 0) for p in pensions_data)
    total_investments = sum(w.get("value", 0) for w in investment_wrappers)
    total_debt = sum(d.get("balance", 0) for d in debt_breakdown)

    if not age_range:
        gaps.append({"question": "Have you selected your age range?"})
    if not marital_status:
        gaps.append({"question": "Have you selected your marital status?"})
    if not roles:
        gaps.append({"question": "Have you selected your professional roles?"})
    if not tax_filing:
        gaps.append({"question": "Have you confirmed how you file your taxes?"})

    if "locum" in roles and not ir35_status:
        gaps.append({"question": "Do you know your IR35 status for locum work?"})
    if "locum" in roles and ir35_status == "unsure":
        gaps.append({"question": "Would you like an IR35 assessment for your locum contracts?"})
    if "private_practice" in roles and not private_structure:
        gaps.append({"question": "Is your private practice income received as a sole trader or through a company?"})

    if total_income > 100000 and "sa302" not in document_types and "tax_return" not in document_types:
        gaps.append({"question": "Your income exceeds \u00a3100k. Do you have your SA302 or tax return available?"})
    if total_income > 100000 and tax_code == "1257L":
        gaps.append({"question": "Income over \u00a3100k usually means a reduced personal allowance. Is your tax code definitely 1257L?"})

    has_nhs_pension = any(p.get("type", "").startswith("nhs") for p in pensions_data)
    has_sipp = any(p.get("type", "") == "sipp" for p in pensions_data)
    if ("nhs_consultant" in roles or "gp_partner" in roles or "gp_salaried" in roles) and not has_nhs_pension:
        gaps.append({"question": "You work in the NHS but haven't added an NHS pension. Do you have an NHS pension?"})
    if total_pension_value > 0 and "nhs_pension" not in document_types and "sipp_statement" not in document_types:
        gaps.append({"question": "You have pensions but no pension statement uploaded. Can you upload your annual benefit statement?"})

    if total_pension_contrib > 60000:
        gaps.append({"question": "Your total pension contributions exceed the \u00a360,000 annual allowance. Have you used carry forward from previous years?"})
    if total_income > 260000 and total_pension_contrib > 10000:
        gaps.append({"question": "Income above \u00a3260k triggers pension taper. Are you aware your annual allowance may be reduced to \u00a310,000?"})

    has_company = any(c.get("type", "") for c in companies_data)
    if ("ltd_director" in roles or "fic_director" in roles) and not has_company:
        gaps.append({"question": "You selected a company director role but haven't added any companies. Do you have a limited company or FIC?"})
    if has_company and "company_accounts" not in document_types and "ct600" not in document_types:
        gaps.append({"question": "You have company structures but no accounts or CT600 uploaded. Can you provide company financial documents?"})

    for i, comp in enumerate(companies_data):
        pct = comp.get("shareholding_pct", 0)
        others = comp.get("other_shareholders", 0)
        if pct < 100 and others == 0:
            gaps.append({"question": f"Company {i+1}: You own {pct}% but listed 0 other shareholders. Are there other shareholders?"})

    if total_investments > 0 and "investment_portfolio" not in document_types and "isa_statement" not in document_types:
        gaps.append({"question": "You have investments but no portfolio or ISA statement uploaded. Can you provide investment documentation?"})

    mortgage_debt = sum(d.get("balance", 0) for d in debt_breakdown if d.get("type") == "mortgage")
    if mortgage_debt > 0 and "mortgage_statement" not in document_types:
        gaps.append({"question": "You have a mortgage but no statement uploaded. Can you provide your mortgage statement?"})

    has_will = "will" in document_types
    has_insurance = "insurance_policies" in document_types
    if not has_will and (marital_status == "married" or dependants not in ("0", "")):
        gaps.append({"question": "Do you have a will in place?"})
    if not has_insurance and total_income > 50000:
        gaps.append({"question": "Do you have life insurance or income protection?"})

    isa_value = sum(w.get("value", 0) for w in investment_wrappers if "isa" in w.get("type", ""))
    if isa_value == 0 and total_income > 30000:
        gaps.append({"question": "Have you used your ISA allowance this tax year?"})

    vct_value = sum(w.get("value", 0) for w in investment_wrappers if w.get("type") == "vct")
    eis_value = sum(w.get("value", 0) for w in investment_wrappers if w.get("type") == "eis_seis")
    if total_income > 150000 and vct_value == 0 and eis_value == 0:
        gaps.append({"question": "As a higher earner, have you considered VCT or EIS for income tax relief?"})

    age_mid = age_from_range(age_range)
    doctor_profile = {
        "income_level": total_income,
        "debt_level": total_debt,
        "savings": total_investments,
        "pension": total_pension_value,
        "pension_contributions": total_pension_contrib,
        "total_investments": total_investments,
        "company_structure": companies_data[0].get("type", "none") if companies_data else "none",
        "tax_paid": tax_paid,
        "risk_tolerance": "medium",
    }

    mri_agent = FinancialMRI()
    mri_score = mri_agent.calculate_mri_score(doctor_profile)
    leakage = mri_agent.analyze_leakage(doctor_profile)
    insights.extend(leakage)

    if total_income > 0:
        effective_rate = (tax_paid / total_income) * 100
        insights.append(f"Effective tax rate: {effective_rate:.1f}%")

    if total_income > 100000:
        lost_allowance = min((total_income - 100000) / 2, 12570)
        extra_tax = lost_allowance * 0.4
        insights.append(f"Personal allowance tapering: \u00a3{lost_allowance:,.0f} allowance lost, approx \u00a3{extra_tax:,.0f} additional tax")

    if "locum" in roles and ir35_status == "inside":
        insights.append("Inside IR35 locum work is taxed as employment — limited tax planning options")
    if "locum" in roles and ir35_status == "outside":
        insights.append("Outside IR35 — company structure can provide significant tax efficiency")

    if total_pension_contrib > 0 and total_income > 260000:
        tapered_allowance = max(10000, 60000 - ((total_income - 260000) / 2))
        if total_pension_contrib > tapered_allowance:
            excess = total_pension_contrib - tapered_allowance
            insights.append(f"Pension taper: annual allowance reduced to \u00a3{tapered_allowance:,.0f}. Excess contributions of \u00a3{excess:,.0f} may attract a tax charge")

    for p in pensions_data:
        if p.get("type", "").startswith("nhs") and p.get("value", 0) > 0:
            pval = p.get("value", 0)
            contrib = p.get("annual_contribution", 0)
            if contrib > 0:
                pension_ai = PensionAI(pval, contrib, total_income, age_mid)
                result = pension_ai.model()
                insights.append(f"{p['type'].upper().replace('_',' ')} pension projected at 65: \u00a3{result['future_value']:,.0f}")
                if result["taper_warning"]:
                    insights.append("Lifetime Allowance warning — pension projected to exceed LTA threshold")

    if has_sipp and total_income > 0:
        sipp_pensions = [p for p in pensions_data if p.get("type") == "sipp"]
        for sp in sipp_pensions:
            insights.append(f"SIPP value: \u00a3{sp.get('value',0):,.0f} with \u00a3{sp.get('annual_contribution',0):,.0f}/year contributions")

    for comp in companies_data:
        ctype = comp.get("type", "").upper()
        retained = comp.get("retained_profits", 0)
        divs = comp.get("dividends_paid", 0)
        turnover = comp.get("turnover", 0)
        if retained > 0:
            corp_tax = retained * 0.25 if turnover > 250000 else retained * 0.19
            insights.append(f"{ctype}: \u00a3{retained:,.0f} retained profits — approx \u00a3{corp_tax:,.0f} corporation tax")
        if divs > 2000:
            div_tax = (divs - 2000) * 0.3375 if total_income > 125140 else (divs - 2000) * 0.0875
            insights.append(f"{ctype}: \u00a3{divs:,.0f} dividends — approx \u00a3{div_tax:,.0f} dividend tax (above \u00a32k allowance)")

    if total_debt > 0 and total_income > 0:
        dti = (total_debt / total_income) * 100
        insights.append(f"Debt-to-income ratio: {dti:.0f}%")

    cc_debt = sum(d.get("balance", 0) for d in debt_breakdown if d.get("type") == "credit_cards")
    if cc_debt > 5000:
        insights.append(f"Credit card debt of \u00a3{cc_debt:,.0f} — high-interest debt should be prioritised")

    if len(roles) >= 3:
        insights.append("Multiple income streams detected — complex tax profile may benefit from specialist advice")

    return JSONResponse({
        "gaps": gaps,
        "insights": insights,
        "mri_score": mri_score,
    })


@router.post("/onboarding")
async def onboarding_post(
    request: Request,
    age_range: str = Form(""),
    marital_status: str = Form(""),
    dependants: str = Form("0"),
    uk_resident: str = Form("yes"),
    roles: str = Form(""),
    ir35_status: str = Form(""),
    private_structure: str = Form(""),
    ir35_factors: str = Form(""),
    income_streams: str = Form(""),
    tax_filing: str = Form(""),
    tax_code: str = Form(""),
    student_loan: str = Form("none"),
    tax_paid: float = Form(0),
    pensions_data: str = Form(""),
    companies_data: str = Form(""),
    investment_wrappers: str = Form(""),
    debt_breakdown: str = Form(""),
    document_types: str = Form(""),
    files: List[UploadFile] = File(None),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)

    roles_list = safe_json(roles)
    income_streams_list = safe_json(income_streams)
    pensions_list = safe_json(pensions_data)
    companies_list = safe_json(companies_data)
    wrappers_list = safe_json(investment_wrappers)
    debts_list = safe_json(debt_breakdown)
    doc_types_list = safe_json(document_types)

    age_mid = age_from_range(age_range)

    personal_data = {
        "age_range": age_range,
        "marital_status": marital_status,
        "dependants": dependants,
        "uk_resident": uk_resident,
    }

    ir35_factors_data = safe_json(ir35_factors) if ir35_factors else {}
    if isinstance(ir35_factors_data, list):
        ir35_factors_data = {}

    tax_status_data = {
        "filing": tax_filing,
        "tax_code": tax_code,
        "student_loan": student_loan,
        "ir35_status": ir35_status,
        "private_structure": private_structure,
        "ir35_factors": ir35_factors_data,
    }

    total_income = sum(s.get("amount", 0) for s in income_streams_list)
    total_investments = sum(w.get("value", 0) for w in wrappers_list)
    total_debts = sum(d.get("balance", 0) for d in debts_list)

    total_pension_value = sum(p.get("value", 0) for p in pensions_list)
    total_pension_contrib = sum(p.get("annual_contribution", 0) for p in pensions_list)
    pension_type = pensions_list[0].get("type", "") if pensions_list else ""
    pension_legacy = {
        "type": pension_type,
        "value": total_pension_value,
        "annual_contributions": total_pension_contrib,
    }

    investments_legacy = [{"type": "Portfolio", "amount": total_investments}] if total_investments > 0 else []

    company_structure = "none"
    if companies_list:
        company_structure = companies_list[0].get("type", "none")

    uploaded_files = []
    if files:
        for doc in files:
            if doc.filename and doc.size and doc.size > 0:
                ext = os.path.splitext(doc.filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue
                if doc.size > MAX_FILE_SIZE:
                    continue
                safe_name = f"{uuid.uuid4().hex}{ext}"
                filepath = os.path.join(UPLOAD_DIR, safe_name)
                content = await doc.read()
                with open(filepath, "wb") as f:
                    f.write(content)
                uploaded_files.append({
                    "filename": safe_name,
                    "original_name": doc.filename,
                    "type": ext.lstrip("."),
                })

    for dt in doc_types_list:
        already = any(uf.get("original_name", "").startswith(dt) for uf in uploaded_files)
        if not already:
            uploaded_files.append({"type": dt, "filename": None, "original_name": dt, "status": "declared"})

    db = SessionLocal()
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

        if profile:
            profile.age = age_mid
            profile.roles = roles_list
            profile.personal = personal_data
            profile.income_streams = income_streams_list
            profile.tax_status = tax_status_data
            profile.pensions = pensions_list
            profile.companies = companies_list
            profile.investment_wrappers = wrappers_list
            profile.debt_breakdown = debts_list
            profile.company_structure = company_structure
            profile.income = total_income
            profile.tax_paid = tax_paid
            profile.investments = investments_legacy
            profile.debts = total_debts
            profile.pension = pension_legacy
            profile.risk_tolerance = "medium"
            existing_files = profile.files_uploaded or []
            profile.files_uploaded = existing_files + uploaded_files
        else:
            profile = UserProfile(
                user_id=user_id,
                age=age_mid,
                roles=roles_list,
                personal=personal_data,
                income_streams=income_streams_list,
                tax_status=tax_status_data,
                pensions=pensions_list,
                companies=companies_list,
                investment_wrappers=wrappers_list,
                debt_breakdown=debts_list,
                company_structure=company_structure,
                income=total_income,
                tax_paid=tax_paid,
                investments=investments_legacy,
                debts=total_debts,
                pension=pension_legacy,
                risk_tolerance="medium",
                files_uploaded=uploaded_files,
            )
            db.add(profile)

        db.commit()
        request.session["has_profile"] = True
    finally:
        db.close()

    return RedirectResponse("/dashboard", status_code=303)
