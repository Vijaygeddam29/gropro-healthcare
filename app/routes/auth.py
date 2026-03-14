import uuid
import bcrypt
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, UserProfile

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
async def login_page(request: Request):
    error = request.query_params.get("error", "")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        return RedirectResponse(url="/auth/login?error=Invalid+email+or+password", status_code=303)

    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return RedirectResponse(url="/auth/login?error=Invalid+email+or+password", status_code=303)

    request.session["user_id"] = user.id
    if user.first_name:
        request.session["user_name"] = f"{user.first_name} {user.last_name or ''}".strip()
    else:
        request.session["user_name"] = getattr(user, "name", None) or user.email.split("@")[0]
    request.session["user_email"] = user.email

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile:
        request.session["has_profile"] = True
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/onboarding", status_code=303)


@router.get("/register")
async def register_page(request: Request):
    error = request.query_params.get("error", "")
    return templates.TemplateResponse("register.html", {"request": request, "error": error})


@router.post("/register")
async def register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return RedirectResponse(url="/auth/register?error=Email+already+registered", status_code=303)

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        id=str(uuid.uuid4()),
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=hashed,
        role=role,
    )
    db.add(user)
    db.commit()

    request.session["user_id"] = user.id
    request.session["user_name"] = f"{user.first_name} {user.last_name}"
    request.session["user_email"] = user.email
    return RedirectResponse(url="/onboarding", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
