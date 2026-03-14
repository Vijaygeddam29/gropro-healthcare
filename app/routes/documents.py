import json
import os
import uuid
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.database import SessionLocal
from app.models.models import UserProfile
from app.ai_agents.document_extractor import DocumentExtractor

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def _mn_filter(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if abs(v) >= 1_000_000:
        return f"\u00a3{v / 1_000_000:,.2f}Mn"
    return f"\u00a3{v:,.0f}"


templates.env.filters["mn"] = _mn_filter


@router.get("/documents", response_class=HTMLResponse)
def documents_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)
    return templates.TemplateResponse("documents.html", {
        "request": request,
        "extraction": None,
        "pending": None,
    })


@router.post("/documents/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse({"error": f"File type {ext} not supported"}, status_code=400)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return JSONResponse({"error": "File too large (max 10MB)"}, status_code=400)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    with open(filepath, "wb") as f:
        f.write(content)

    text_content = ""
    if ext in (".txt", ".csv"):
        try:
            text_content = content.decode("utf-8", errors="ignore")
        except Exception:
            text_content = ""

    extractor = DocumentExtractor()
    doc_type = extractor.identify_document_type(file.filename, text_content)
    extraction = extractor.extract_from_text(text_content, doc_type)
    updates = extractor.build_profile_updates(extraction)

    return JSONResponse({
        "filename": safe_name,
        "original_name": file.filename,
        "document_type": extraction["document_type"],
        "confidence": extraction["confidence"],
        "extracted": extraction["extracted"],
        "proposed_updates": updates,
    })


@router.post("/documents/approve")
async def approve_extraction(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    data = await request.json()
    updates = data.get("updates", {})
    filename = data.get("filename", "")
    original_name = data.get("original_name", "")
    document_type = data.get("document_type", "")

    if not updates:
        return JSONResponse({"error": "No updates to apply"}, status_code=400)

    db = SessionLocal()
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return JSONResponse({"error": "No profile found"}, status_code=404)

        if "income" in updates:
            profile.income = updates["income"]

        if "tax_paid" in updates:
            profile.tax_paid = updates["tax_paid"]

        if "income_streams_update" in updates:
            streams = profile.income_streams or []
            update_src = updates["income_streams_update"]
            source = update_src.get("source", "")
            amount = update_src.get("amount", 0)
            found = False
            for s in streams:
                if s.get("source") == source:
                    s["amount"] = amount
                    found = True
                    break
            if not found:
                streams.append({"source": source, "amount": amount})
            profile.income_streams = streams
            profile.income = sum(s.get("amount", 0) for s in streams)

        if "pension_contribution_update" in updates:
            pensions = profile.pensions or []
            if pensions:
                pensions[0]["annual_contribution"] = updates["pension_contribution_update"]
                profile.pensions = pensions

        if "pension_update" in updates:
            pensions = profile.pensions or []
            pu = updates["pension_update"]
            if pensions:
                if "value" in pu:
                    pensions[0]["value"] = pu["value"]
                if "annual_contribution" in pu:
                    pensions[0]["annual_contribution"] = pu["annual_contribution"]
                if "type" in pu:
                    pensions[0]["type"] = pu["type"]
                profile.pensions = pensions
            else:
                profile.pensions = [{
                    "type": pu.get("type", "sipp"),
                    "value": pu.get("value", 0),
                    "annual_contribution": pu.get("annual_contribution", 0),
                }]

        if "company_update" in updates:
            companies = profile.companies or []
            cu = updates["company_update"]
            if companies:
                if "turnover" in cu:
                    companies[0]["turnover"] = cu["turnover"]
                if "retained_profits" in cu:
                    companies[0]["retained_profits"] = cu["retained_profits"]
                if "dividends_paid" in cu:
                    companies[0]["dividends_paid"] = cu["dividends_paid"]
                profile.companies = companies
            else:
                profile.companies = [{
                    "type": "ltd",
                    "turnover": cu.get("turnover", 0),
                    "retained_profits": cu.get("retained_profits", 0),
                    "dividends_paid": cu.get("dividends_paid", 0),
                    "shareholding_pct": 100,
                    "other_shareholders": 0,
                }]

        if "debt_update" in updates:
            debts = profile.debt_breakdown or []
            du = updates["debt_update"]
            dtype = du.get("type", "other_loans")
            found = False
            for d in debts:
                if d.get("type") == dtype:
                    d["balance"] = du.get("balance", 0)
                    found = True
                    break
            if not found:
                debts.append({"type": dtype, "balance": du.get("balance", 0)})
            profile.debt_breakdown = debts
            profile.debts = sum(d.get("balance", 0) for d in debts)

        if "investment_update" in updates:
            wrappers = profile.investment_wrappers or []
            iu = updates["investment_update"]
            if wrappers:
                wrappers[0]["value"] = iu.get("value", 0)
                profile.investment_wrappers = wrappers

        existing_files = profile.files_uploaded or []
        existing_files.append({
            "filename": filename,
            "original_name": original_name,
            "type": document_type,
            "status": "extracted_and_approved",
        })
        profile.files_uploaded = existing_files

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(profile, "income_streams")
        flag_modified(profile, "pensions")
        flag_modified(profile, "companies")
        flag_modified(profile, "debt_breakdown")
        flag_modified(profile, "investment_wrappers")
        flag_modified(profile, "files_uploaded")

        db.commit()

        return JSONResponse({"success": True, "message": "Profile updated with extracted data"})
    except Exception as e:
        db.rollback()
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        db.close()
