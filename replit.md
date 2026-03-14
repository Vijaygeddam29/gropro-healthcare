# GroPro Healthcare Wealth Management

## Overview
AI-powered wealth management platform for UK healthcare professionals (doctors, GPs, consultants). Built with Python FastAPI, Jinja2 templates, and SQLAlchemy. Features Financial MRI scoring, FIC management, A/B/C scenario modeling, investment tracking, pension AI, and an advisor marketplace. All text cites specific HMRC legislation (FA 2004, ITA 2007, TCGA 1992, IHTA 1984, NHS Pension Regs) with user's actual £ amounts in Mn format.

## Architecture
- **Backend**: Python FastAPI
- **Frontend**: Jinja2 HTML templates with vanilla CSS/JS
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Server**: Uvicorn on port 5000

## Key Features
1. **Income & Tax Forecast (Dashboard Lead)** — Projected take-home, tax liability breakdown (IT/NI/dividend/SL/HICBC), monthly breakdown, year-on-year comparison, key tax due dates, PA taper detail
2. **Pension Modelling** — Income-aware taper calculation, excess contribution charge, PA recovery via pension contributions, per-scheme projections (NHS 1995/2008/2015 + SIPP)
3. **IR35 Compliance Engine** — Factor-based assessment (control, substitution, MOO, equipment, financial risk, part of org, multiple clients, benefits, intention), single-client warning, ITEPA 2003 Chapter 10 references
4. **Document Upload & AI Extraction** — Upload bank statements/SA302/P60/payslips/pension statements → AI extracts financial data → user approves → profile auto-updates
5. **Financial MRI** — 8 sub-score health areas with expand-on-click, MRI ring gauge, kindergarten explanations
6. **FIC Management** — Family Investment Company optimization with dividend strategies, income splitting, IHT planning
7. **Scenario Modeling** — Do Nothing / Quick Wins / Full Optimisation with 5yr/10yr/20yr projections
8. **Capital Allocation** — Prioritised allocation with tax wrapper order
9. **Investment Recommendations** — Wrapper-specific with priority levels
10. **Net Worth (Dashboard Bottom)** — Total assets/liabilities/equity breakdown
11. **Advisor Marketplace** — Browse verified financial advisors
12. **Deep Onboarding** — 10-step wizard with IR35 factor questions for consultants/locums

## Dashboard Section Order
1. Income & Tax Liability Forecast (OPEN by default)
2. Pension Modelling
3. IR35 Compliance Assessment (if applicable)
4. Financial MRI Score
5. Financial Health Areas (8 sub-scores)
6. Tax Leakage Identified
7. Scenario Comparison
8. Investment Recommendations
9. Capital Allocation Priorities
10. Family Investment Company
11. Investment Wrappers
12. Debt Breakdown
13. Company Structures
14. Current Pension Values
15. Net Worth (BOTTOM)

## Rules Engines (app/ai_agents/)
- `tax_rules.py` - Real HMRC 2024/25 tax calculator (income tax bands, NI Class 1/2/4, dividend tax, CGT, personal allowance tapering, HICBC, student loans). `total_tax_burden()` returns full breakdown.
- `pension_rules.py` - NHS pension schemes (1995/2008/2015 accrual rates), SIPP projections, annual allowance tapering, carry forward
- `company_rules.py` - Corporation tax with marginal relief, optimal salary/dividend split, IR35 scoring, FIC analysis, S455
- `document_extractor.py` - Document type identification + financial data extraction from text (SA302, P60, payslip, pension statement, bank statement, company accounts, mortgage, investment, CT600)

## AI Agents (app/ai_agents/)
- `financial_mri.py` - MRI scoring with net worth + tax burden + leakage
- `scenario_ai.py` - Three scenarios with projections and steps
- `pension_ai.py` - Per-scheme projections with AA/taper/charge analysis
- `fic_optimizer.py` - FIC dividend strategies + income splitting + IHT
- `capital_allocation_ai.py` - Prioritised allocation + wrapper order
- `investment_advisor_ai.py` - Wrapper-specific recommendations

## Onboarding Flow (10 Steps)
1. **Personal** — Age range, marital status, dependants, UK tax residency
2. **Professional Roles** — Multi-select roles + IR35 status (locum) + private structure + IR35 factor questionnaire (9 factors for locum/ltd/private roles)
3. **Income Streams** — Dynamic range sliders per role + rental + dividend
4. **Tax Status** — Filing method, tax code, student loan, tax paid last year
5. **Pensions** — Up to 4 pensions with type/value/contribution
6. **Company Structures** — Up to 3 companies with full details
7. **Investments** — 7 wrapper types with value sliders
8. **Debts** — 5 debt types with balance sliders
9. **Documents** — Tag document types + file upload
10. **AI Review** — Gap analysis + MRI score + AI insights

## Data Model
- `User`: id (String/UUID), email, password_hash, first_name, last_name, role
- `UserProfile`: id, user_id (FK), age, roles (JSON), company_structure, income, tax_paid, investments (JSON), debts, pension (JSON), risk_tolerance, files_uploaded (JSON), personal (JSON), income_streams (JSON), tax_status (JSON with ir35_factors), pensions (JSON), companies (JSON), investment_wrappers (JSON), debt_breakdown (JSON)
- `FIC`, `Investment`, `Advisor` models

## Project Structure
```
app/
  main.py              - FastAPI server entry
  database.py          - SQLAlchemy engine, SessionLocal, Base, get_db
  routes/
    auth.py            - Login/register
    onboarding.py      - 10-step wizard + AI review + IR35 factors capture
    dashboard.py       - Dashboard with tax forecast, IR35, enhanced pension, all AI agents
    documents.py       - Document upload + AI extraction + approval flow
    fic.py             - FIC management
    investments.py     - Investment portfolio
    marketplace.py     - Advisor marketplace
  models/models.py     - SQLAlchemy models
  ai_agents/
    financial_mri.py   - MRI scoring engine
    scenario_ai.py     - A/B/C scenario generator
    pension_ai.py      - Pension modeling
    pension_rules.py   - Pension calculators
    fic_optimizer.py   - FIC optimizer
    capital_allocation_ai.py - Asset allocation
    investment_advisor_ai.py - Investment recommendations
    tax_rules.py       - HMRC tax calculator
    company_rules.py   - Company/IR35 rules
    document_extractor.py - Document AI extraction
  utils/constants.py   - HMRC/pension constants
  templates/           - Jinja2 HTML templates
  static/              - CSS and JS files
  uploads/             - User uploaded documents
```

## Routes
- `/` - Home page
- `/dashboard` - Financial dashboard (tax forecast first, net worth last)
- `/documents` - Document upload with AI extraction and approval
- `/documents/upload` - POST file upload + extraction
- `/documents/approve` - POST approve extracted data
- `/onboarding` - 10-step onboarding wizard
- `/onboarding/ai-review` - AI review endpoint
- `/marketplace` - Advisor marketplace
- `/fic/` - FIC management
- `/investments/` - Investment portfolio
- `/auth/login`, `/auth/register`, `/auth/logout`

## Design
- Scandinavian black/white CSS — no color accents, sharp corners, uppercase labels, light font weights
- All monetary values displayed as £X.XXMn for values >= £1,000,000 via `_mn()` helper and `|mn` Jinja2 filter
- Responsive with mobile breakpoints
- `data-testid` attributes on all interactive and display elements
