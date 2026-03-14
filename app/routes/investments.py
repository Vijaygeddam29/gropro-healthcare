from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.ai_agents.pension_ai import PensionAI

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEMO_INVESTMENTS = [
    {"name": "Vanguard FTSE All-World ETF", "type": "ETF", "amount": 125000, "projected_return": 7.2, "risk": "balanced"},
    {"name": "iShares UK Property Fund", "type": "Property", "amount": 85000, "projected_return": 5.4, "risk": "conservative"},
    {"name": "MedTech Ventures Fund III", "type": "Venture", "amount": 50000, "projected_return": 15.0, "risk": "aggressive"},
    {"name": "UK Government Gilts", "type": "Bonds", "amount": 60000, "projected_return": 3.8, "risk": "conservative"},
    {"name": "SIPP - Fidelity Index World", "type": "SIPP", "amount": 200000, "projected_return": 6.5, "risk": "balanced"},
]

@router.get("/")
async def investments_list(request: Request):
    user_name = request.session.get("user_name")
    if not user_name:
        return RedirectResponse(url="/auth/login", status_code=303)

    total = sum(i["amount"] for i in DEMO_INVESTMENTS)

    pension_ai = PensionAI(pension_value=340000, contribution=40000, income=150000, age=42)
    pension_model = pension_ai.model()

    return templates.TemplateResponse("investments.html", {
        "request": request,
        "investments": DEMO_INVESTMENTS,
        "total": total,
        "pension": pension_model,
    })
