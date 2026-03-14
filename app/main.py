import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth, dashboard, documents, fic, investments, marketplace, onboarding

app = FastAPI(title="GroPro Wealth Platform")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "fallback-dev-secret"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router, prefix="/auth")
app.include_router(onboarding.router)
app.include_router(dashboard.router)
app.include_router(marketplace.router)
app.include_router(fic.router, prefix="/fic")
app.include_router(investments.router, prefix="/investments")
app.include_router(documents.router)

@app.get("/")
async def home(request: Request):
    user_name = request.session.get("user_name")
    first_name = ""
    if user_name:
        first_name = user_name.split()[0] if " " in user_name else user_name
    return templates.TemplateResponse("home.html", {"request": request, "user_name": user_name, "first_name": first_name})
