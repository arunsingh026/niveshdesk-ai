from datetime import datetime
from decimal import Decimal
from sqlalchemy import String,Integer,Numeric,Boolean,DateTime,Text,Date,ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class Stock(Base):
    __tablename__="stocks"
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(120)); symbol:Mapped[str]=mapped_column(String(40),unique=True,index=True)
    instrument_type:Mapped[str]=mapped_column(String(20),default="stock"); market_cap:Mapped[str]=mapped_column(String(20)); sector:Mapped[str]=mapped_column(String(80))
    monthly_target:Mapped[int]=mapped_column(Integer); min_buy:Mapped[Decimal|None]=mapped_column(Numeric(14,2),nullable=True); max_buy:Mapped[Decimal|None]=mapped_column(Numeric(14,2),nullable=True)
    enabled:Mapped[bool]=mapped_column(Boolean,default=True); notes:Mapped[str]=mapped_column(Text,default="")
    manual_sip_date:Mapped[int|None]=mapped_column(Integer,nullable=True)
class ReviewRun(Base):
    __tablename__="review_runs"
    id:Mapped[int]=mapped_column(primary_key=True); run_key:Mapped[str]=mapped_column(String(80),unique=True,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); budget:Mapped[int]=mapped_column(Integer)
    deployed:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0); reserve:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0)
    status:Mapped[str]=mapped_column(String(30),default="created"); report:Mapped[str]=mapped_column(Text,default="")

class MonthlyExpense(Base):
    __tablename__="monthly_expenses"
    id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(200))
    amount:Mapped[Decimal|None]=mapped_column(Numeric(14,2),nullable=True); day_of_month:Mapped[int]=mapped_column(Integer)
    category:Mapped[str]=mapped_column(String(50),default=""); description:Mapped[str]=mapped_column(Text,default="")
    enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    is_recurring:Mapped[bool]=mapped_column(Boolean,default=True)
    specific_year:Mapped[int|None]=mapped_column(Integer,nullable=True)
    specific_month:Mapped[int|None]=mapped_column(Integer,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class ExpensePayment(Base):
    __tablename__="expense_payments"
    id:Mapped[int]=mapped_column(primary_key=True); expense_id:Mapped[int]=mapped_column(Integer,ForeignKey("monthly_expenses.id"))
    year:Mapped[int]=mapped_column(Integer); month:Mapped[int]=mapped_column(Integer)
    paid_date:Mapped[datetime|None]=mapped_column(Date,nullable=True); is_paid:Mapped[bool]=mapped_column(Boolean,default=False)
    notes:Mapped[str]=mapped_column(Text,default="")

class SIPDatePreference(Base):
    __tablename__="sip_date_preferences"
    id:Mapped[int]=mapped_column(primary_key=True)
    start_date:Mapped[int]=mapped_column(Integer,default=5)
    end_date:Mapped[int]=mapped_column(Integer,default=10)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class SIPDateHistory(Base):
    __tablename__="sip_date_history"
    id:Mapped[int]=mapped_column(primary_key=True)
    symbol:Mapped[str]=mapped_column(String(40),ForeignKey("stocks.symbol"))
    year:Mapped[int]=mapped_column(Integer)
    month:Mapped[int]=mapped_column(Integer)
    optimal_date:Mapped[int]=mapped_column(Integer)
    actual_date:Mapped[int|None]=mapped_column(Integer,nullable=True)
    avg_nav:Mapped[Decimal]=mapped_column(Numeric(14,2))
    justification:Mapped[str]=mapped_column(Text,default="")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class BudgetPlan(Base):
    __tablename__="budget_plans"
    __table_args__=(UniqueConstraint("year","month",name="uq_budget_plan_month"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    year:Mapped[int]=mapped_column(Integer,index=True)
    month:Mapped[int]=mapped_column(Integer,index=True)
    income:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0)
    notes:Mapped[str]=mapped_column(Text,default="")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class BudgetCategory(Base):
    __tablename__="budget_categories"
    id:Mapped[int]=mapped_column(primary_key=True)
    plan_id:Mapped[int]=mapped_column(Integer,ForeignKey("budget_plans.id"),index=True)
    name:Mapped[str]=mapped_column(String(100))
    bucket:Mapped[str]=mapped_column(String(20),default="needs")
    planned_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0)
    actual_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0)
    icon:Mapped[str]=mapped_column(String(40),default="fa-receipt")

class PortfolioHolding(Base):
    __tablename__="portfolio_holdings"
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(160))
    asset_type:Mapped[str]=mapped_column(String(40),index=True)
    symbol:Mapped[str]=mapped_column(String(40),default="")
    units:Mapped[Decimal|None]=mapped_column(Numeric(18,4),nullable=True)
    invested_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0)
    current_value:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0)
    platform:Mapped[str]=mapped_column(String(80),default="")
    goal:Mapped[str]=mapped_column(String(100),default="")
    notes:Mapped[str]=mapped_column(Text,default="")
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class NotificationPreference(Base):
    __tablename__="notification_preferences"
    id:Mapped[int]=mapped_column(primary_key=True,default=1)
    email_address:Mapped[str]=mapped_column(String(254),default="")
    email_enabled:Mapped[bool]=mapped_column(Boolean,default=False)
    push_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    expense_due_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    budget_alert_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    monthly_report_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    failure_alerts_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    budget_threshold:Mapped[int]=mapped_column(Integer,default=90)
    default_lead_minutes:Mapped[int]=mapped_column(Integer,default=1440)
    quiet_start:Mapped[int]=mapped_column(Integer,default=22)
    quiet_end:Mapped[int]=mapped_column(Integer,default=7)
    timezone:Mapped[str]=mapped_column(String(60),default="Asia/Kolkata")
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class NotificationReminder(Base):
    __tablename__="notification_reminders"
    id:Mapped[int]=mapped_column(primary_key=True)
    kind:Mapped[str]=mapped_column(String(30),index=True)
    title:Mapped[str]=mapped_column(String(160))
    details:Mapped[str]=mapped_column(Text,default="")
    symbol:Mapped[str]=mapped_column(String(40),default="")
    amount:Mapped[Decimal|None]=mapped_column(Numeric(14,2),nullable=True)
    due_at:Mapped[datetime]=mapped_column(DateTime,index=True)
    recurrence:Mapped[str]=mapped_column(String(20),default="once")
    remind_before_minutes:Mapped[int]=mapped_column(Integer,default=1440)
    channels:Mapped[str]=mapped_column(String(40),default="push,email")
    enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class PushDevice(Base):
    __tablename__="push_devices"
    id:Mapped[int]=mapped_column(primary_key=True)
    token:Mapped[str]=mapped_column(Text,unique=True)
    device_label:Mapped[str]=mapped_column(String(100),default="Web browser")
    enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    last_seen_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class NotificationDelivery(Base):
    __tablename__="notification_deliveries"
    __table_args__=(UniqueConstraint("event_key","channel",name="uq_notification_event_channel"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    reminder_id:Mapped[int|None]=mapped_column(Integer,ForeignKey("notification_reminders.id"),nullable=True)
    event_key:Mapped[str]=mapped_column(String(180),index=True)
    kind:Mapped[str]=mapped_column(String(30))
    channel:Mapped[str]=mapped_column(String(20))
    title:Mapped[str]=mapped_column(String(160))
    status:Mapped[str]=mapped_column(String(20),default="pending")
    error:Mapped[str]=mapped_column(Text,default="")
    sent_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
