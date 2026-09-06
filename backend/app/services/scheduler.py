from datetime import datetime,date
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from ..config import settings
from ..db import SessionLocal
from ..models import Stock,ReviewRun,MonthlyExpense,ExpensePayment
from .planner import build_recommendations,summarize
from .notifications import notification_service
scheduler=BackgroundScheduler(timezone=settings.app_timezone)
def monthly_review():
    now=datetime.now(ZoneInfo(settings.app_timezone)); key=now.strftime("%Y-%m")
    with SessionLocal() as db:
        if db.scalar(select(ReviewRun).where(ReviewRun.run_key==key)): return
        rows=build_recommendations(list(db.scalars(select(Stock).where(Stock.enabled.is_(True))).all()),settings.monthly_budget,settings.mf_budget)
        total_budget = settings.monthly_budget + settings.mf_budget
        deployed,reserve=summarize(rows,total_budget)

        # Create simple text body for database storage
        body_lines = [f"Monthly Investment Review - {key}", f"Stock Budget: ₹{settings.monthly_budget:,}", f"MF Budget: ₹{settings.mf_budget:,}", f"Total Deployed: ₹{deployed:,.0f}", f"Reserve: ₹{reserve:,.0f}", ""]
        for r in rows:
            body_lines.append(f"{r['symbol']}: {r['status']} | ₹{r['deploy_amount']:,.0f}")
        body = "\n".join(body_lines)

        run=ReviewRun(run_key=key,budget=total_budget,deployed=deployed,reserve=reserve,status="notification_pending",report=body); db.add(run); db.commit()

        if not settings.dry_run_notifications:
            try:
                notification_service.send_stock_recommendations(rows, total_budget)
                run.status="notified"
            except Exception as e:
                print(f"Failed to send notifications: {e}")
                run.status="notification_failed"
        else:
            run.status="dry_run"
        db.commit()

def daily_expense_reminder():
    """Check for expenses due today and send reminders"""
    now=datetime.now(ZoneInfo(settings.app_timezone))
    today=now.date()
    current_day=today.day
    current_year=today.year
    current_month=today.month

    with SessionLocal() as db:
        # Get all active expenses
        expenses=list(db.scalars(select(MonthlyExpense).where(MonthlyExpense.enabled.is_(True))).all())

        # Filter expenses due today
        due_today=[]
        for expense in expenses:
            if expense.day_of_month==current_day:
                # Check if already paid this month
                payment=db.scalar(select(ExpensePayment).where(
                    ExpensePayment.expense_id==expense.id,
                    ExpensePayment.year==current_year,
                    ExpensePayment.month==current_month
                ))

                if not payment or not payment.is_paid:
                    due_today.append({
                        "id":expense.id,
                        "name":expense.name,
                        "amount":float(expense.amount) if expense.amount else None,
                        "category":expense.category,
                        "description":expense.description
                    })

        if due_today and not settings.dry_run_notifications:
            try:
                notification_service.send_expense_reminders(due_today,"due_today")
                print(f"Sent reminders for {len(due_today)} expenses due today")
            except Exception as e:
                print(f"Failed to send expense reminders: {e}")

def start_scheduler():
    scheduler.add_job(monthly_review,CronTrigger(day=settings.investment_day,hour=settings.reminder_hour,minute=settings.reminder_minute),id="monthly-review",replace_existing=True,misfire_grace_time=3600)
    # First reminder at 11:00 AM
    scheduler.add_job(daily_expense_reminder,CronTrigger(hour=11,minute=0),id="daily-expense-reminder-morning",replace_existing=True,misfire_grace_time=3600)
    # Second reminder at 3:00 PM
    scheduler.add_job(daily_expense_reminder,CronTrigger(hour=15,minute=0),id="daily-expense-reminder-afternoon",replace_existing=True,misfire_grace_time=3600)
    scheduler.start()
