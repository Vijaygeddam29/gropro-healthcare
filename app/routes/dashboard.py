from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import UserProfile
from app.ai_agents.financial_mri import FinancialMRI
from app.ai_agents.scenario_ai import ScenarioAI
from app.ai_agents.investment_advisor_ai import InvestmentAdvisorAI
from app.ai_agents.capital_allocation_ai import CapitalAllocationAI
from app.ai_agents.pension_ai import PensionAI
from app.ai_agents.fic_optimizer import FICOptimizer
from app.ai_agents.tax_rules import TaxCalculator
from app.ai_agents.company_rules import CompanyCalculator
from app.ai_agents.pension_rules import PensionCalculator
from app.utils.constants import (
    PERSONAL_ALLOWANCE, PENSION_ANNUAL_ALLOWANCE, PENSION_TAPER_THRESHOLD,
    PENSION_TAPER_MIN_ALLOWANCE, PA_TAPER_THRESHOLD,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _mn_filter(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if abs(v) >= 1_000_000:
        return f"\u00a3{v / 1_000_000:,.2f}Mn"
    return f"\u00a3{v:,.0f}"


templates.env.filters["mn"] = _mn_filter

ROLE_LABELS = {
    "paye": "PAYE",
    "nhs_consultant": "NHS Consultant",
    "gp_partner": "GP Partner",
    "gp_salaried": "Salaried GP",
    "locum": "Locum",
    "private_practice": "Private Practice",
    "ltd_director": "Ltd Director",
    "partnership": "Partnership",
    "fic_director": "FIC Director",
    "teaching": "Teaching",
    "research": "Research",
    "medico_legal": "Medico-Legal",
}

WRAPPER_LABELS = {
    "cash_isa": "Cash ISA",
    "stocks_shares_isa": "S&S ISA",
    "gia": "GIA",
    "vct": "VCT",
    "eis_seis": "EIS / SEIS",
    "buy_to_let": "Buy-to-Let",
    "other": "Other",
}

DEBT_LABELS = {
    "mortgage": "Mortgage",
    "student_loan": "Student Loan",
    "car_finance": "Car Finance",
    "credit_cards": "Credit Cards",
    "other_loans": "Other Loans",
}

TAX_DUE_DATES = [
    {"date": "31 January 2026", "description": "Balancing payment for 2024/25 + 1st payment on account for 2025/26"},
    {"date": "31 July 2026", "description": "2nd payment on account for 2025/26"},
    {"date": "5 October 2026", "description": "Deadline to register for Self Assessment if new"},
    {"date": "31 January 2027", "description": "Online Self Assessment filing deadline for 2025/26"},
]


def _build_profile_dict(profile, user_name):
    personal = profile.personal or {}
    income_streams = profile.income_streams or []
    tax_status = profile.tax_status or {}
    pensions_list = profile.pensions or []
    companies_list = profile.companies or []
    wrappers_list = profile.investment_wrappers or []
    debts_list = profile.debt_breakdown or []
    age = profile.age or 40
    roles = profile.roles or []

    total_income = sum(s.get("amount", 0) for s in income_streams)
    if total_income == 0:
        total_income = profile.income or 0

    return {
        "name": user_name,
        "age": age,
        "roles": roles,
        "personal": personal,
        "income_streams": income_streams,
        "tax_status": tax_status,
        "pensions": pensions_list,
        "companies": companies_list,
        "investment_wrappers": wrappers_list,
        "debt_breakdown": debts_list,
        "document_types": [],
        "income_level": total_income,
        "company_structure": profile.company_structure or "none",
        "risk_tolerance": profile.risk_tolerance or "medium",
    }


def _compute_tax_forecast(p, tax_paid_last_year):
    tax_calc = TaxCalculator()
    burden = tax_calc.total_tax_burden(p)

    monthly = {}
    for key in ["income_tax", "national_insurance", "dividend_tax", "student_loan", "child_benefit_charge", "total_tax", "take_home"]:
        monthly[key] = round(burden.get(key, 0) / 12, 2)

    burden["monthly"] = monthly
    burden["tax_paid_last_year"] = tax_paid_last_year or 0
    burden["tax_change"] = round(burden["total_tax"] - (tax_paid_last_year or 0), 2)

    if burden["gross_income"] > PA_TAPER_THRESHOLD:
        lost = min((burden["gross_income"] - PA_TAPER_THRESHOLD) / 2, PERSONAL_ALLOWANCE)
        extra = lost * 0.4
        burden["pa_taper_detail"] = (
            f"ITA 2007 s.35: Your adjusted net income of \u00a3{burden['gross_income']:,.0f} exceeds "
            f"\u00a3{PA_TAPER_THRESHOLD:,}. Personal Allowance reduced by \u00a31 for every \u00a32 over "
            f"the threshold. You lose \u00a3{lost:,.0f} of allowance, costing \u00a3{extra:,.0f} in "
            f"additional tax at 40%."
        )
    else:
        burden["pa_taper_detail"] = None

    return burden


def _compute_ir35(p):
    roles = p.get("roles", [])
    tax_status = p.get("tax_status", {})
    companies = p.get("companies", [])

    ir35_relevant = any(r in roles for r in ["locum", "ltd_director", "private_practice"])
    has_ltd = any(c.get("type", "").lower() in ("ltd", "llp") for c in companies)

    if not ir35_relevant and not has_ltd:
        return None

    ir35_factors = tax_status.get("ir35_factors", {})
    if not ir35_factors:
        ir35_factors = {
            "control": tax_status.get("ir35_control", None),
            "substitution": tax_status.get("ir35_substitution", None),
            "moo": tax_status.get("ir35_moo", None),
            "equipment": tax_status.get("ir35_equipment", None),
            "financial_risk": tax_status.get("ir35_financial_risk", None),
            "part_of_org": tax_status.get("ir35_part_of_org", None),
            "right_of_dismissal": tax_status.get("ir35_dismissal", None),
            "multiple_clients": tax_status.get("ir35_multiple_clients", None),
            "benefits": tax_status.get("ir35_benefits", None),
            "intention": tax_status.get("ir35_intention", None),
        }
        all_none = all(v is None for v in ir35_factors.values())
        if all_none:
            single_client = len(companies) <= 1 and "locum" in roles
            ir35_factors = {
                "control": None,
                "substitution": None,
                "moo": None,
                "multiple_clients": not single_client if single_client else None,
            }

    comp_calc = CompanyCalculator()
    ir35_result = comp_calc.ir35_risk_score(ir35_factors)

    ir35_status = tax_status.get("ir35_status", "")
    if ir35_status == "inside":
        ir35_result["risk_level"] = "high"
        ir35_result["risk_score"] = max(ir35_result["risk_score"], 75)

    num_clients = sum(1 for c in companies if c.get("type", "").lower() in ("ltd", "llp"))
    if num_clients <= 1 and "locum" in roles:
        ir35_result["single_client_warning"] = True
    else:
        ir35_result["single_client_warning"] = False

    ir35_result["legislation"] = (
        "Off-payroll working rules (Chapter 10, Part 2 ITEPA 2003, as amended by "
        "Finance Act 2021). The intermediaries legislation (IR35) applies where a worker "
        "provides services through an intermediary (typically a personal service company) "
        "and the relationship would be one of employment if engaged directly. "
        "From April 2021, medium and large clients determine IR35 status for the worker. "
        "Where IR35 applies, the fee-payer must deduct PAYE and NICs as if the worker were an employee."
    )

    return ir35_result


def _compute_enhanced_pension(pensions_list, income, age):
    pension_calc = PensionCalculator()

    aa = pension_calc.annual_allowance(income)
    total_contrib = sum(p.get("annual_contribution", 0) for p in pensions_list)
    excess = max(0, total_contrib - aa)
    unused = max(0, aa - total_contrib)

    marginal = 0.45 if income > 125140 else (0.4 if income > 50270 else 0.2)

    if income > PENSION_TAPER_THRESHOLD:
        reduction = min((income - PENSION_TAPER_THRESHOLD) / 2, PENSION_ANNUAL_ALLOWANCE - PENSION_TAPER_MIN_ALLOWANCE)
        taper_detail = (
            f"FA 2004, s.228ZA: Your adjusted income of \u00a3{income:,.0f} exceeds the "
            f"\u00a3{PENSION_TAPER_THRESHOLD:,} threshold. Your Annual Allowance is reduced by "
            f"\u00a31 for every \u00a32 above \u00a3{PENSION_TAPER_THRESHOLD:,}, cutting "
            f"\u00a3{reduction:,.0f} from the standard \u00a3{PENSION_ANNUAL_ALLOWANCE:,} allowance. "
            f"Your tapered Annual Allowance: \u00a3{aa:,.0f}. "
            f"Minimum tapered allowance: \u00a3{PENSION_TAPER_MIN_ALLOWANCE:,}."
        )
    else:
        taper_detail = None
        reduction = 0

    excess_charge = round(excess * marginal, 2) if excess > 0 else 0
    if excess_charge > 0:
        charge_detail = (
            f"FA 2004, s.227: Contributions of \u00a3{total_contrib:,.0f} exceed your Annual Allowance "
            f"of \u00a3{aa:,.0f} by \u00a3{excess:,.0f}. The Annual Allowance Charge is levied at your "
            f"marginal rate ({int(marginal * 100)}%), resulting in a charge of \u00a3{excess_charge:,.0f}. "
            f"If the charge exceeds \u00a32,000, you may elect Scheme Pays (s.237B FA 2004)."
        )
    else:
        charge_detail = None

    if income > PA_TAPER_THRESHOLD:
        optimal_for_pa = min(income - PA_TAPER_THRESHOLD, PERSONAL_ALLOWANCE * 2)
        optimal_for_pa = min(optimal_for_pa, aa - total_contrib) if aa > total_contrib else 0
        pa_recovery = min(optimal_for_pa / 2, PERSONAL_ALLOWANCE) if optimal_for_pa > 0 else 0
        pa_tax_saving = round(pa_recovery * 0.4, 2) if pa_recovery > 0 else 0
        pa_recovery_detail = (
            f"ITA 2007 s.35 + FA 2004 s.188: Contributing an additional \u00a3{optimal_for_pa:,.0f} "
            f"to pension reduces your adjusted net income, recovering \u00a3{pa_recovery:,.0f} of "
            f"Personal Allowance. Tax saving: \u00a3{pa_tax_saving:,.0f}. Combined with "
            f"{int(marginal * 100)}% relief on the contribution itself, total benefit: "
            f"\u00a3{round(optimal_for_pa * marginal + pa_tax_saving):,.0f}."
        ) if optimal_for_pa > 1000 else None
    else:
        optimal_for_pa = 0
        pa_recovery_detail = None
        pa_tax_saving = 0

    return {
        "annual_allowance": round(aa),
        "total_contributions": round(total_contrib),
        "excess": round(excess),
        "unused_allowance": round(unused),
        "excess_charge": excess_charge,
        "taper_detail": taper_detail,
        "charge_detail": charge_detail,
        "pa_recovery_detail": pa_recovery_detail,
        "optimal_extra_contribution": round(optimal_for_pa),
        "pa_tax_saving": pa_tax_saving,
        "marginal_rate": marginal,
    }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_name = request.session.get("user_name")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        return RedirectResponse(url="/onboarding", status_code=303)

    p = _build_profile_dict(profile, user_name)

    income_streams = p["income_streams"]
    pensions_list = p["pensions"]
    companies_list = p["companies"]
    wrappers_list = p["investment_wrappers"]
    debts_list = p["debt_breakdown"]
    tax_status = p["tax_status"]
    personal = p["personal"]
    age = p["age"]
    roles = p["roles"]

    total_income = sum(s.get("amount", 0) for s in income_streams)
    if total_income == 0:
        total_income = profile.income or 0
    total_investments = sum(w.get("value", 0) for w in wrappers_list)
    old_investments = 0
    if profile.investments:
        old_investments = sum(i.get("amount", 0) for i in profile.investments)
    if old_investments > total_investments:
        total_investments = old_investments
    total_debt = sum(d.get("balance", 0) for d in debts_list) if debts_list else (profile.debts or 0)

    tax_forecast = _compute_tax_forecast(p, profile.tax_paid)

    ir35_result = _compute_ir35(p)

    enhanced_pension = _compute_enhanced_pension(pensions_list, total_income, age) if pensions_list else None

    try:
        mri_agent = FinancialMRI()
        mri_full = mri_agent.full_analysis(p)
    except Exception:
        mri_full = {
            "mri_score": 0,
            "sub_scores": {},
            "net_worth": {"total_assets": 0, "total_liabilities": 0, "net_worth": 0, "pension_assets": 0, "investment_assets": 0, "company_equity": 0},
            "tax_burden": {},
            "leakage": [],
            "explanations": {},
        }

    try:
        scenario_agent = ScenarioAI()
        scenarios = scenario_agent.generate_scenarios(p)
    except Exception:
        scenarios = {}

    try:
        investment_ai = InvestmentAdvisorAI()
        recommendations = investment_ai.generate_recommendations(p)
    except Exception:
        recommendations = []

    try:
        pension_ai = PensionAI()
        pension_analysis = pension_ai.full_analysis(pensions_list, total_income, age) if pensions_list else None
    except Exception:
        pension_analysis = None

    risk_map = {"low": "conservative", "medium": "balanced", "high": "aggressive"}
    risk_profile = risk_map.get(profile.risk_tolerance, "balanced")
    try:
        cap_ai = CapitalAllocationAI(total_investments, risk_profile)
        cap_analysis = cap_ai.full_analysis(p)
    except Exception:
        cap_analysis = None

    try:
        fic_ai = FICOptimizer()
        fic_analysis = fic_ai.full_analysis(companies_list, total_income)
    except Exception:
        fic_analysis = None

    income_display = []
    for stream in income_streams:
        source = stream.get("source", "")
        label = ROLE_LABELS.get(source, source.replace("_", " ").title())
        income_display.append({"label": label, "amount": stream.get("amount", 0)})

    wrapper_display = []
    for w in wrappers_list:
        wtype = w.get("type", "")
        label = WRAPPER_LABELS.get(wtype, wtype.replace("_", " ").title())
        wrapper_display.append({"label": label, "value": w.get("value", 0)})

    debt_display = []
    for d in debts_list:
        dtype = d.get("type", "")
        label = DEBT_LABELS.get(dtype, dtype.replace("_", " ").title())
        debt_display.append({"label": label, "balance": d.get("balance", 0)})

    pension_display = []
    for pp in pensions_list:
        ptype = pp.get("type", "").upper().replace("_", " ")
        pension_display.append({
            "type": ptype,
            "value": pp.get("value", 0),
            "contribution": pp.get("annual_contribution", 0),
        })

    company_display = []
    for c in companies_list:
        ctype = c.get("type", "").upper()
        company_display.append({
            "type": ctype,
            "shareholding": c.get("shareholding_pct", 0),
            "other_shareholders": c.get("other_shareholders", 0),
            "turnover": c.get("turnover", 0),
            "retained": c.get("retained_profits", 0),
            "dividends": c.get("dividends_paid", 0),
        })

    total_expenses = total_debt
    mortgage_annual = sum(d.get("balance", 0) * 0.04 for d in debts_list if d.get("type") == "mortgage")
    other_debt_annual = sum(d.get("balance", 0) * 0.06 for d in debts_list if d.get("type") != "mortgage")
    annual_expenses = round(mortgage_annual + other_debt_annual)

    first_name = user_name.split()[0] if user_name and " " in user_name else (user_name or "")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user_name": user_name,
            "first_name": first_name,
            "mri": mri_full,
            "scenarios": scenarios,
            "recommendations": recommendations,
            "pension_analysis": pension_analysis,
            "cap_analysis": cap_analysis,
            "fic_analysis": fic_analysis,
            "profile": profile,
            "personal": personal,
            "total_income": total_income,
            "total_debt": total_debt,
            "total_investments": total_investments,
            "roles": roles,
            "age": age,
            "income_display": income_display,
            "wrapper_display": wrapper_display,
            "debt_display": debt_display,
            "pension_display": pension_display,
            "company_display": company_display,
            "tax_status": tax_status,
            "tax_forecast": tax_forecast,
            "ir35_result": ir35_result,
            "enhanced_pension": enhanced_pension,
            "tax_due_dates": TAX_DUE_DATES,
            "annual_expenses": annual_expenses,
        }
    )
