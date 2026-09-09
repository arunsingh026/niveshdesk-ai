from datetime import datetime,date,timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from ..config import settings
from ..db import SessionLocal
from ..models import Stock,ReviewRun,User
from .planner import build_recommendations,summarize
scheduler=BackgroundScheduler(timezone=settings.app_timezone)
def monthly_review(user_id:int|None=None):
    if user_id is None:
        with SessionLocal() as lookup:
            user_ids=list(lookup.scalars(select(User.id).where(User.active.is_(True),User.is_legacy_owner.is_(False))).all())
        for account_id in user_ids:
            monthly_review(account_id)
        return
    now=datetime.now(ZoneInfo(settings.app_timezone)); key=now.strftime("%Y-%m")
    with SessionLocal() as db:
        db.info["user_id"]=user_id
        storage_key=f"u{user_id}-{key}"
        if db.scalar(select(ReviewRun).where(ReviewRun.run_key==storage_key)): return
        rows=build_recommendations(list(db.scalars(select(Stock).where(Stock.enabled.is_(True))).all()),settings.monthly_budget,settings.mf_budget)
        total_budget = settings.monthly_budget + settings.mf_budget
        deployed,reserve=summarize(rows,total_budget)

        # Create simple text body for database storage
        body_lines = [f"Monthly Investment Review - {key}", f"Stock Budget: ₹{settings.monthly_budget:,}", f"MF Budget: ₹{settings.mf_budget:,}", f"Total Deployed: ₹{deployed:,.0f}", f"Reserve: ₹{reserve:,.0f}", ""]
        for r in rows:
            body_lines.append(f"{r['symbol']}: {r['status']} | ₹{r['deploy_amount']:,.0f}")
        body = "\n".join(body_lines)

        run=ReviewRun(run_key=storage_key,budget=total_budget,deployed=deployed,reserve=reserve,status="ready",report=body); db.add(run)
        db.commit()

def notification_smart_check():
    """Process due finance alerts every minute; GitHub Actions remains the external fallback."""
    from .notification_center import dispatch_all_users
    dispatch_all_users(source="in_app")

def start_scheduler():
    scheduler.add_job(monthly_review,CronTrigger(day=settings.investment_day,hour=settings.reminder_hour,minute=settings.reminder_minute),id="monthly-review",replace_existing=True,misfire_grace_time=3600)
    scheduler.add_job(notification_smart_check,IntervalTrigger(minutes=1),id="notification-smart-check",replace_existing=True,coalesce=True,max_instances=1,misfire_grace_time=120,next_run_time=datetime.now()+timedelta(seconds=10))
    if not scheduler.running:
        scheduler.start()
