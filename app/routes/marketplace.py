from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

advisors = [
    {"name": "Alice Smith", "specialty": "Accountant", "verified": True},
    {"name": "Bob Jones", "specialty": "Investment Advisor", "verified": True},
    {"name": "Claire Lee", "specialty": "Tax Consultant", "verified": False},
]

@router.get("/marketplace", response_class=HTMLResponse)
def marketplace(request: Request):
    user_name = request.session.get("user_name")
    if not user_name:
        return RedirectResponse(url="/auth/login", status_code=303)

    return templates.TemplateResponse("marketplace.html", {"request": request, "advisors": advisors})
