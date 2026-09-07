from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import init_db,SessionLocal,engine
from .models import Stock,ReviewRun,MonthlyExpense,ExpensePayment,SIPDatePreference,SIPDateHistory,BudgetPlan,BudgetCategory,PortfolioHolding
from datetime import date
from .services.planner import build_recommendations
from .services.scheduler import start_scheduler,monthly_review,daily_expense_reminder
from .services.notifications import notification_service
from .services.market_data import get_chart_data, MarketDataError
from .services.sip_optimizer import (
    analyze_optimal_sip_dates,
    get_sip_date_preference,
    update_sip_date_preference,
    get_current_optimal_dates,
    confirm_sip_date_change
)
from .config import settings
from fastapi import HTTPException
from pydantic import BaseModel,Field

class BudgetCategoryInput(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    bucket:str=Field(pattern="^(needs|wants|future)$")
    planned_amount:float=Field(ge=0)
    actual_amount:float=Field(ge=0)
    icon:str="fa-receipt"

class BudgetPlanInput(BaseModel):
    income:float=Field(ge=0)
    notes:str=""
    categories:list[BudgetCategoryInput]=Field(default_factory=list)

class HoldingInput(BaseModel):
    name:str=Field(min_length=1,max_length=160)
    asset_type:str=Field(min_length=1,max_length=40)
    symbol:str=""
    units:float|None=Field(default=None,ge=0)
    invested_amount:float=Field(ge=0)
    current_value:float=Field(ge=0)
    platform:str=""
    goal:str=""
    notes:str=""
@asynccontextmanager
async def lifespan(app):
    init_db()
    # Create SIP tables if they don't exist
    from sqlalchemy import text
    with engine.connect() as conn:
        # Add manual_sip_date column to stocks table if it doesn't exist
        try:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='stocks' AND column_name='manual_sip_date'
            """))
            if not result.fetchone():
                print("Adding manual_sip_date column...")
                conn.execute(text("ALTER TABLE stocks ADD COLUMN manual_sip_date INTEGER"))
                conn.commit()
                print("✓ manual_sip_date column added!")
        except Exception as e:
            print(f"Error adding column: {e}")

        # Create SIP tables
        try:
            conn.execute(text("SELECT 1 FROM sip_date_preferences LIMIT 1"))
        except:
            # Tables don't exist, create them
            print("Creating SIP tables...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sip_date_preferences (
                    id SERIAL PRIMARY KEY,
                    start_date INTEGER NOT NULL DEFAULT 5,
                    end_date INTEGER NOT NULL DEFAULT 10,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sip_date_history (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(40) REFERENCES stocks(symbol),
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    optimal_date INTEGER NOT NULL,
                    actual_date INTEGER,
                    avg_nav NUMERIC(14,2) NOT NULL,
                    justification TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("INSERT INTO sip_date_preferences (start_date, end_date) VALUES (5, 10)"))
            conn.commit()
            print("✓ SIP tables created!")
    start_scheduler()
    yield
app=FastAPI(title="My Stock Planner API",version="0.1.0",lifespan=lifespan)
# Allow requests from any origin (for local network access)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
@app.get("/health")
def health(): return {"status":"ok","timezone":settings.app_timezone}
@app.get("/api/stocks")
def stocks(db:Session=Depends(get_db)): return list(db.scalars(select(Stock).order_by(Stock.market_cap,Stock.name)).all())
@app.get("/api/recommendations")
def recommendations(stock_budget:int=35000,mf_budget:int=30000,db:Session=Depends(get_db)): return build_recommendations(list(db.scalars(select(Stock).where(Stock.enabled.is_(True))).all()),stock_budget,mf_budget)
@app.post("/api/review/run")
def run_review(): monthly_review(); return {"status":"completed"}
@app.get("/api/reviews")
def reviews(db:Session=Depends(get_db)): return [{"id":r.id,"run_key":r.run_key,"created_at":r.created_at,"budget":r.budget,"deployed":float(r.deployed),"reserve":float(r.reserve),"status":r.status} for r in db.scalars(select(ReviewRun).order_by(ReviewRun.created_at.desc())).all()]
@app.get("/api/stock/{symbol}/chart")
def stock_chart(symbol: str, period: str = "1m"):
    try:
        chart_data = get_chart_data(symbol, period)
        return chart_data
    except MarketDataError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chart data: {str(e)}")
@app.post("/api/notifications/send")
def send_notifications(stock_budget:int=35000,mf_budget:int=30000,db:Session=Depends(get_db)):
    recommendations=build_recommendations(list(db.scalars(select(Stock).where(Stock.enabled.is_(True))).all()),stock_budget,mf_budget)
    total_budget = stock_budget + mf_budget
    result=notification_service.send_stock_recommendations(recommendations,total_budget)
    return {"status":"completed","result":result}
@app.get("/api/notifications/status")
def notification_status():
    return {
        "email_enabled":notification_service.enable_email,
        "email_configured":bool(notification_service.smtp_user and notification_service.smtp_password),
        "whatsapp_enabled":notification_service.enable_whatsapp,
        "whatsapp_configured":bool(notification_service.twilio_account_sid and notification_service.twilio_auth_token),
        "telegram_enabled":notification_service.enable_telegram,
        "telegram_configured":bool(notification_service.telegram_bot_token and notification_service.telegram_chat_id)
    }

@app.get("/api/expenses")
def get_expenses(db:Session=Depends(get_db)):
    return list(db.scalars(select(MonthlyExpense).where(MonthlyExpense.enabled.is_(True)).order_by(MonthlyExpense.day_of_month)).all())

@app.post("/api/expenses")
def create_expense(expense:dict,db:Session=Depends(get_db)):
    new_expense=MonthlyExpense(**expense)
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense

@app.put("/api/expenses/{expense_id}")
def update_expense(expense_id:int,expense:dict,db:Session=Depends(get_db)):
    existing=db.scalar(select(MonthlyExpense).where(MonthlyExpense.id==expense_id))
    if not existing:
        return {"error":"Expense not found"}
    for key,value in expense.items():
        if hasattr(existing,key) and key!="id":
            setattr(existing,key,value)
    db.commit()
    db.refresh(existing)
    return existing

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id:int,db:Session=Depends(get_db)):
    existing=db.scalar(select(MonthlyExpense).where(MonthlyExpense.id==expense_id))
    if not existing:
        return {"error":"Expense not found"}

    # Delete all payment records for this expense first
    db.execute(select(ExpensePayment).where(ExpensePayment.expense_id==expense_id)).all()
    for payment in db.scalars(select(ExpensePayment).where(ExpensePayment.expense_id==expense_id)):
        db.delete(payment)

    # Now delete the expense
    db.delete(existing)
    db.commit()
    return {"status":"ok","message":"Expense deleted"}

@app.get("/api/expenses/{year}/{month}")
def get_month_expenses(year:int,month:int,db:Session=Depends(get_db)):
    from sqlalchemy import or_, and_

    # Get recurring expenses OR expenses specific to this year/month
    expenses=list(db.scalars(
        select(MonthlyExpense).where(
            MonthlyExpense.enabled.is_(True),
            or_(
                or_(MonthlyExpense.is_recurring.is_(True), MonthlyExpense.is_recurring.is_(None)),
                and_(
                    MonthlyExpense.specific_year==year,
                    MonthlyExpense.specific_month==month
                )
            )
        ).order_by(MonthlyExpense.day_of_month)
    ).all())

    payments={p.expense_id:p for p in db.scalars(select(ExpensePayment).where(ExpensePayment.year==year,ExpensePayment.month==month)).all()}
    result=[]
    for exp in expenses:
        payment=payments.get(exp.id)
        # Skip if hidden for this month
        if payment and payment.notes == "__HIDDEN__":
            continue
        result.append({
            "id":exp.id,"name":exp.name,"amount":float(exp.amount) if exp.amount else None,
            "day_of_month":exp.day_of_month,"category":exp.category,"description":exp.description,
            "is_paid":payment.is_paid if payment else False,
            "paid_date":payment.paid_date.isoformat() if payment and payment.paid_date else None,
            "notes":payment.notes if payment else "",
            "is_recurring":exp.is_recurring if hasattr(exp, 'is_recurring') else True,
            "specific_year":exp.specific_year if hasattr(exp, 'specific_year') else None,
            "specific_month":exp.specific_month if hasattr(exp, 'specific_month') else None
        })
    return result

@app.post("/api/expenses/{expense_id}/pay")
def mark_expense_paid(expense_id:int,payload:dict,db:Session=Depends(get_db)):
    year,month=payload["year"],payload["month"]
    payment=db.scalar(select(ExpensePayment).where(ExpensePayment.expense_id==expense_id,ExpensePayment.year==year,ExpensePayment.month==month))
    if not payment:
        payment=ExpensePayment(expense_id=expense_id,year=year,month=month,is_paid=True,paid_date=date.today())
        db.add(payment)
    else:
        payment.is_paid=True
        payment.paid_date=date.today()
    db.commit()
    return {"status":"ok"}

@app.delete("/api/expenses/{expense_id}/pay")
def unmark_expense_paid(expense_id:int,year:int,month:int,db:Session=Depends(get_db)):
    payment=db.scalar(select(ExpensePayment).where(ExpensePayment.expense_id==expense_id,ExpensePayment.year==year,ExpensePayment.month==month))
    if payment:
        payment.is_paid=False
        payment.paid_date=None
        db.commit()
    return {"status":"ok"}

@app.post("/api/expenses/notify/test")
def test_expense_notifications():
    """Manually trigger expense reminder notifications for testing"""
    daily_expense_reminder()
    return {"status":"completed","message":"Expense notifications sent (if any expenses due today)"}

@app.post("/api/expenses/notify/send")
def send_expense_notifications(expense_ids:list[int],db:Session=Depends(get_db)):
    """Send notifications for specific expenses"""
    expenses=list(db.scalars(select(MonthlyExpense).where(MonthlyExpense.id.in_(expense_ids))).all())
    if not expenses:
        return {"status":"error","message":"No expenses found"}

    expense_list=[{
        "id":exp.id,
        "name":exp.name,
        "amount":float(exp.amount) if exp.amount else None,
        "category":exp.category,
        "description":exp.description
    } for exp in expenses]

    result=notification_service.send_expense_reminders(expense_list,"due_today")
    return {"status":"completed","result":result}

@app.get("/api/sip/preferences")
def get_sip_preferences(db:Session=Depends(get_db)):
    """Get SIP date range preferences"""
    pref=get_sip_date_preference(db)
    return {"start_date":pref.start_date,"end_date":pref.end_date}

@app.put("/api/sip/preferences")
def update_sip_preferences(data:dict,db:Session=Depends(get_db)):
    """Update SIP date range preferences"""
    start_date=data.get("start_date",5)
    end_date=data.get("end_date",10)
    if start_date<1 or start_date>28 or end_date<1 or end_date>28 or start_date>end_date:
        raise HTTPException(status_code=400,detail="Invalid date range")
    pref=update_sip_date_preference(db,start_date,end_date)
    return {"start_date":pref.start_date,"end_date":pref.end_date}

@app.post("/api/sip/analyze")
def analyze_sip_dates(db:Session=Depends(get_db)):
    """Run SIP date analysis for all mutual funds"""
    pref=get_sip_date_preference(db)
    results=analyze_optimal_sip_dates(db,pref.start_date,pref.end_date)
    return {"status":"completed","results":results}

@app.get("/api/sip/optimal-dates")
def get_optimal_dates(db:Session=Depends(get_db)):
    """Get current optimal SIP dates for all mutual funds"""
    return get_current_optimal_dates(db)

@app.post("/api/sip/confirm")
def confirm_date_change(data:dict,db:Session=Depends(get_db)):
    """Confirm SIP date change for a mutual fund"""
    symbol=data.get("symbol")
    new_date=data.get("new_date")
    if not symbol or not new_date:
        raise HTTPException(status_code=400,detail="Missing symbol or new_date")
    result=confirm_sip_date_change(db,symbol,new_date)
    return result

@app.put("/api/sip/manual-date")
def set_manual_sip_date(data:dict,db:Session=Depends(get_db)):
    """Set manual SIP date for a mutual fund"""
    symbol=data.get("symbol")
    manual_date=data.get("manual_date")
    if not symbol:
        raise HTTPException(status_code=400,detail="Missing symbol")

    stock=db.scalar(select(Stock).where(Stock.symbol==symbol))
    if not stock:
        raise HTTPException(status_code=404,detail="Stock not found")

    if manual_date is None:
        # Clear manual override
        stock.manual_sip_date=None
    else:
        if manual_date<1 or manual_date>31:
            raise HTTPException(status_code=400,detail="Date must be between 1 and 31")
        stock.manual_sip_date=manual_date

    db.commit()
    return {"symbol":symbol,"manual_date":stock.manual_sip_date}

@app.get("/api/expenses/monthly-summary")
def get_monthly_summary(db:Session=Depends(get_db)):
    """Get monthly expense summary for the last 12 months"""
    from datetime import datetime

    current_date = datetime.now()
    summaries = []

    for i in range(12):
        # Calculate year and month going backwards
        month_offset = i
        target_year = current_date.year
        target_month = current_date.month - month_offset

        while target_month <= 0:
            target_month += 12
            target_year -= 1

        # Get expenses for this month (same logic as get_month_expenses)
        from sqlalchemy import or_, and_

        expenses = list(db.scalars(
            select(MonthlyExpense).where(
                MonthlyExpense.enabled.is_(True),
                or_(
                    or_(MonthlyExpense.is_recurring.is_(True), MonthlyExpense.is_recurring.is_(None)),
                    and_(
                        MonthlyExpense.specific_year == target_year,
                        MonthlyExpense.specific_month == target_month
                    )
                )
            )
        ).all())

        payments = {p.expense_id: p for p in db.scalars(select(ExpensePayment).where(
            ExpensePayment.year == target_year,
            ExpensePayment.month == target_month
        )).all()}

        # Calculate totals, excluding hidden expenses
        total_amount = 0
        paid_amount = 0
        visible_count = 0

        for exp in expenses:
            payment = payments.get(exp.id)
            # Skip hidden expenses
            if payment and payment.notes == "__HIDDEN__":
                continue

            visible_count += 1
            amount = float(exp.amount) if exp.amount else 0
            total_amount += amount
            if payment and payment.is_paid:
                paid_amount += amount

        summaries.append({
            "year": target_year,
            "month": target_month,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "left_to_pay": total_amount - paid_amount,
            "expense_count": visible_count
        })

    return summaries

# Migration endpoint to add new columns
@app.post("/api/expenses/migrate")
def migrate_expenses(db:Session=Depends(get_db)):
    """Add is_recurring, specific_year, specific_month columns"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            # Check if columns exist
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='monthly_expenses' AND column_name='is_recurring'
            """))
            if not result.fetchone():
                conn.execute(text("ALTER TABLE monthly_expenses ADD COLUMN is_recurring BOOLEAN DEFAULT true"))
                conn.execute(text("ALTER TABLE monthly_expenses ADD COLUMN specific_year INTEGER"))
                conn.execute(text("ALTER TABLE monthly_expenses ADD COLUMN specific_month INTEGER"))
                conn.commit()
                return {"status":"migrated","message":"Columns added successfully"}
            return {"status":"already_migrated","message":"Columns already exist"}
        except Exception as e:
            return {"status":"error","message":str(e)}

@app.post("/api/expenses/{expense_id}/hide-month")
def hide_expense_for_month(expense_id:int,payload:dict,db:Session=Depends(get_db)):
    """Hide a recurring expense for a specific month"""
    year,month=payload["year"],payload["month"]
    
    # Create or update payment record to mark as hidden
    payment=db.scalar(select(ExpensePayment).where(
        ExpensePayment.expense_id==expense_id,
        ExpensePayment.year==year,
        ExpensePayment.month==month
    ))
    
    if not payment:
        # Create a hidden marker
        payment=ExpensePayment(
            expense_id=expense_id,
            year=year,
            month=month,
            is_paid=False,
            notes="__HIDDEN__"  # Special marker to hide this expense
        )
        db.add(payment)
    else:
        payment.notes="__HIDDEN__"
    
    db.commit()
    return {"status":"ok","message":"Expense hidden for this month"}

@app.post("/api/expenses/fix-recurring")
def fix_recurring_expenses(db:Session=Depends(get_db)):
    """Update all existing expenses to have is_recurring=true"""
    from sqlalchemy import text
    with engine.connect() as conn:
        # Update all NULL is_recurring to true
        result = conn.execute(text("""
            UPDATE monthly_expenses 
            SET is_recurring = true 
            WHERE is_recurring IS NULL OR is_recurring = false
        """))
        conn.commit()
        return {"status":"ok","updated":result.rowcount}

DEFAULT_BUDGET_CATEGORIES=[
    {"name":"Home & rent","bucket":"needs","icon":"fa-house"},
    {"name":"Groceries","bucket":"needs","icon":"fa-basket-shopping"},
    {"name":"Utilities & bills","bucket":"needs","icon":"fa-bolt"},
    {"name":"Transport & fuel","bucket":"needs","icon":"fa-car"},
    {"name":"Lifestyle","bucket":"wants","icon":"fa-mug-hot"},
    {"name":"Shopping","bucket":"wants","icon":"fa-bag-shopping"},
    {"name":"SIP & investments","bucket":"future","icon":"fa-seedling"},
    {"name":"Emergency fund","bucket":"future","icon":"fa-shield-heart"},
]

def serialize_budget(plan,db):
    if not plan:
        return {"id":None,"income":0,"notes":"","categories":[
            {"id":None,**item,"planned_amount":0,"actual_amount":0}
            for item in DEFAULT_BUDGET_CATEGORIES
        ]}
    categories=list(db.scalars(select(BudgetCategory).where(BudgetCategory.plan_id==plan.id).order_by(BudgetCategory.id)).all())
    return {"id":plan.id,"income":float(plan.income),"notes":plan.notes,"categories":[
        {"id":item.id,"name":item.name,"bucket":item.bucket,"planned_amount":float(item.planned_amount),"actual_amount":float(item.actual_amount),"icon":item.icon}
        for item in categories
    ]}

@app.get("/api/budget/summary/current")
def current_budget_summary(db:Session=Depends(get_db)):
    today=date.today()
    plan=db.scalar(select(BudgetPlan).where(BudgetPlan.year==today.year,BudgetPlan.month==today.month))
    if not plan:
        return {"income":0,"planned":0,"spent":0,"remaining":0,"savings_rate":0}
    categories=list(db.scalars(select(BudgetCategory).where(BudgetCategory.plan_id==plan.id)).all())
    planned=sum(float(item.planned_amount) for item in categories)
    spent=sum(float(item.actual_amount) for item in categories)
    future=sum(float(item.actual_amount) for item in categories if item.bucket=="future")
    income=float(plan.income)
    return {"income":income,"planned":planned,"spent":spent,"remaining":income-spent,"savings_rate":round(future/income*100,1) if income else 0}

@app.get("/api/budget/{year}/{month}")
def get_budget(year:int,month:int,db:Session=Depends(get_db)):
    if month<1 or month>12:
        raise HTTPException(status_code=400,detail="Month must be between 1 and 12")
    plan=db.scalar(select(BudgetPlan).where(BudgetPlan.year==year,BudgetPlan.month==month))
    return serialize_budget(plan,db)

@app.put("/api/budget/{year}/{month}")
def save_budget(year:int,month:int,payload:BudgetPlanInput,db:Session=Depends(get_db)):
    if month<1 or month>12:
        raise HTTPException(status_code=400,detail="Month must be between 1 and 12")
    plan=db.scalar(select(BudgetPlan).where(BudgetPlan.year==year,BudgetPlan.month==month))
    if not plan:
        plan=BudgetPlan(year=year,month=month,income=payload.income,notes=payload.notes)
        db.add(plan); db.flush()
    else:
        plan.income=payload.income; plan.notes=payload.notes
        for item in db.scalars(select(BudgetCategory).where(BudgetCategory.plan_id==plan.id)).all():
            db.delete(item)
    for item in payload.categories:
        db.add(BudgetCategory(plan_id=plan.id,**item.model_dump()))
    db.commit(); db.refresh(plan)
    return serialize_budget(plan,db)

def serialize_holding(item):
    return {"id":item.id,"name":item.name,"asset_type":item.asset_type,"symbol":item.symbol,
        "units":float(item.units) if item.units is not None else None,"invested_amount":float(item.invested_amount),
        "current_value":float(item.current_value),"platform":item.platform,"goal":item.goal,"notes":item.notes,
        "updated_at":item.updated_at.isoformat() if item.updated_at else None}

@app.get("/api/portfolio/summary")
def portfolio_summary(db:Session=Depends(get_db)):
    holdings=list(db.scalars(select(PortfolioHolding)).all())
    invested=sum(float(item.invested_amount) for item in holdings)
    current=sum(float(item.current_value) for item in holdings)
    return {"invested":invested,"current_value":current,"gain":current-invested,
        "return_percent":round((current-invested)/invested*100,2) if invested else 0,"holdings":len(holdings)}

@app.get("/api/portfolio")
def get_portfolio(db:Session=Depends(get_db)):
    return [serialize_holding(item) for item in db.scalars(select(PortfolioHolding).order_by(PortfolioHolding.current_value.desc())).all()]

@app.post("/api/portfolio")
def create_holding(payload:HoldingInput,db:Session=Depends(get_db)):
    item=PortfolioHolding(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return serialize_holding(item)

@app.put("/api/portfolio/{holding_id}")
def update_holding(holding_id:int,payload:HoldingInput,db:Session=Depends(get_db)):
    item=db.get(PortfolioHolding,holding_id)
    if not item:
        raise HTTPException(status_code=404,detail="Holding not found")
    for key,value in payload.model_dump().items(): setattr(item,key,value)
    db.commit(); db.refresh(item)
    return serialize_holding(item)

@app.delete("/api/portfolio/{holding_id}")
def delete_holding(holding_id:int,db:Session=Depends(get_db)):
    item=db.get(PortfolioHolding,holding_id)
    if not item:
        raise HTTPException(status_code=404,detail="Holding not found")
    db.delete(item); db.commit()
    return {"status":"ok"}
# Serve the production frontend from the same origin as the API.
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/static"))
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        requested_file = STATIC_DIR / full_path
        if full_path and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(STATIC_DIR / "index.html")
