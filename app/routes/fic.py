from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.ai_agents.scenario_ai import ScenarioAI

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

class MockFIC:
    def __init__(self, name, capital, tax, strategy):
        self.fic_name = name
        self.capital = capital
        self.corporation_tax = tax
        self.dividend_strategy = strategy

DEMO_FICS = [
    MockFIC("Mitchell Family Investments Ltd", 450000, 0.19, "balanced"),
    MockFIC("MedVenture Holdings Ltd", 180000, 0.25, "aggressive"),
    MockFIC("Healthcare Property Co", 320000, 0.19, "conservative"),
]

@router.get("/")
async def fic_list(request: Request):
    user_name = request.session.get("user_name")
    if not user_name:
        return RedirectResponse(url="/auth/login", status_code=303)

    fics_with_scenarios = []
    for fic in DEMO_FICS:
        scenario_ai = ScenarioAI()
        scenarios = scenario_ai.generate_scenarios()
        fics_with_scenarios.append({"fic": fic, "scenarios": scenarios})

    return templates.TemplateResponse("fic.html", {
        "request": request,
        "fics": fics_with_scenarios,
    })
