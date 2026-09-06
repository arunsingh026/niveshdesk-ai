from datetime import datetime
from decimal import Decimal
from sqlalchemy import String,Integer,Numeric,Boolean,DateTime,Text,Date,ForeignKey
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
