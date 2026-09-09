from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,Header,Request,Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func,select,text
from sqlalchemy.orm import Session
from .db import init_db,SessionLocal,engine
from .models import Stock,ReviewRun,MonthlyExpense,ExpensePayment,SIPDatePreference,SIPDateHistory,UserStockPreference,BudgetPlan,BudgetCategory,PortfolioHolding,NotificationPreference,NotificationReminder,NotificationDelivery,PushDevice,User,UserSession
from datetime import date,datetime,timezone
import hmac
from .services.planner import build_recommendations
from .services.scheduler import start_scheduler,monthly_review
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
from .services.notification_center import dispatch_all_users,dispatch_due,get_preferences,provider_status,public_firebase_config,send_test_notification,schedule_test_notification
from fastapi import HTTPException
from pydantic import BaseModel,Field
from contextvars import ContextVar
from .auth import authenticated_user,clear_login_failures,consume_email_code,create_session,enforce_login_limit,find_user,hash_password,issue_email_code,normalize_email,normalize_phone,public_user,record_login_failure,revoke_session,session_token_hash,verify_password
from .migrations import OWNED_TABLES,transfer_legacy_data

request_user_id:ContextVar[int|None]=ContextVar("request_user_id",default=None)

class RegisterInput(BaseModel):
    full_name:str=Field(min_length=2,max_length=120)
    email:str=Field(min_length=5,max_length=254)
    phone:str=Field(default="",max_length=20)
    password:str=Field(min_length=8,max_length=128)
    verification_code:str=Field(pattern="^\\d{6}$")

class PasswordLoginInput(BaseModel):
    identifier:str=Field(min_length=3,max_length=254)
    password:str=Field(min_length=1,max_length=128)

class PasswordChangeInput(BaseModel):
    current_password:str=Field(min_length=1,max_length=128)
    new_password:str=Field(min_length=8,max_length=128)

class ProfileUpdateInput(BaseModel):
    full_name:str=Field(min_length=2,max_length=120)
    phone:str=Field(default="",max_length=20)

class AdminUserUpdateInput(BaseModel):
    active:bool|None=None
    role:str|None=Field(default=None,pattern="^(user|admin)$")

class EmailCodeRequestInput(BaseModel):
    email:str=Field(min_length=5,max_length=254)

class EmailCodeLoginInput(EmailCodeRequestInput):
    code:str=Field(pattern="^\\d{6}$")


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

class NotificationPreferenceInput(BaseModel):
    email_address:str=Field(default="",max_length=254)
    email_enabled:bool=False
    push_enabled:bool=True
    expense_due_enabled:bool=True
    budget_alert_enabled:bool=True
    monthly_report_enabled:bool=True
    failure_alerts_enabled:bool=True
    budget_threshold:int=Field(default=90,ge=50,le=100)
    default_lead_minutes:int=Field(default=1440,ge=0,le=10080)
    quiet_start:int=Field(default=22,ge=0,le=23)
    quiet_end:int=Field(default=7,ge=0,le=23)
    timezone:str=Field(default="Asia/Kolkata",pattern="^[A-Za-z_]+/[A-Za-z_]+$")

class NotificationReminderInput(BaseModel):
    kind:str=Field(pattern="^(stock_buy|sip|credit_card|custom)$")
    title:str=Field(min_length=1,max_length=160)
    details:str=Field(default="",max_length=500)
    symbol:str=Field(default="",max_length=40)
    amount:float|None=Field(default=None,ge=0)
    due_at:datetime
    recurrence:str=Field(default="once",pattern="^(once|weekly|monthly)$")
    remind_before_minutes:int=Field(default=1440,ge=0,le=10080)
    channels:list[str]=Field(default_factory=lambda:["push","email"])
    enabled:bool=True

class PushDeviceInput(BaseModel):
    token:str=Field(min_length=20,max_length=4096)
    device_label:str=Field(default="Web browser",max_length=100)

class NotificationTestInput(BaseModel):
    channel:str=Field(pattern="^(push|email)$")
    delay_minutes:int=Field(default=0)
    device_token:str=Field(default="",max_length=4096)
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
allowed_origins=list(dict.fromkeys([
    settings.public_app_url.rstrip("/"),"http://localhost:5173","http://127.0.0.1:5173"
]))
app.add_middleware(CORSMiddleware,allow_origins=allowed_origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?::\d+)?$",
    allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.middleware("http")
async def require_account_session(request:Request,call_next):
    path=request.url.path
    public=(request.method=="OPTIONS" or path=="/health" or path.startswith("/api/auth/") or
        path=="/api/notifications/firebase-config" or path=="/api/notifications/dispatch" or
        not path.startswith("/api/"))
    token=None
    if not public:
        with SessionLocal() as auth_db:
            user=authenticated_user(auth_db,request)
            if not user:
                return JSONResponse(status_code=401,content={"detail":"Sign in to open your workspace"})
            if user.must_change_password:
                return JSONResponse(status_code=403,content={"detail":"Change your temporary password to continue","code":"password_change_required"})
            token=request_user_id.set(user.id)
    try:
        return await call_next(request)
    finally:
        if token is not None:
            request_user_id.reset(token)

def get_db():
    db=SessionLocal()
    user_id=request_user_id.get()
    if user_id:
        db.info["user_id"]=user_id
    try: yield db
    finally: db.close()
@app.get("/health")
def health(): return {"status":"ok","timezone":settings.app_timezone}

def validate_password_strength(password:str):
    if not any(char.islower() for char in password) or not any(char.isupper() for char in password) or not any(char.isdigit() for char in password):
        raise HTTPException(status_code=400,detail="Password needs uppercase, lowercase, and a number")

@app.post("/api/auth/register",status_code=201)
def register_account(payload:RegisterInput,request:Request,response:Response,db:Session=Depends(get_db)):
    if not settings.allow_registration:
        raise HTTPException(status_code=403,detail="New registrations are temporarily closed")
    email=normalize_email(payload.email)
    phone=normalize_phone(payload.phone)
    if not email and not phone:
        raise HTTPException(status_code=400,detail="Enter an email address or phone number")
    validate_password_strength(payload.password)
    if email and db.scalar(select(User.id).where(User.email==email)):
        raise HTTPException(status_code=409,detail="An account already uses this email")
    if phone and db.scalar(select(User.id).where(User.phone==phone)):
        raise HTTPException(status_code=409,detail="An account already uses this phone number")
    consume_email_code(db,email,payload.verification_code,purpose="register")
    user=User(full_name=payload.full_name.strip(),email=email,phone=phone,password_hash=hash_password(payload.password),email_verified=True)
    db.add(user); db.flush()
    db.add(NotificationPreference(user_id=user.id,email_address=email or ""))
    result=create_session(db,user,request,response)
    result["message"]="Your private workspace is ready"
    return result

@app.post("/api/auth/login/password")
def login_with_password(payload:PasswordLoginInput,request:Request,response:Response,db:Session=Depends(get_db)):
    enforce_login_limit(db,payload.identifier)
    user=find_user(db,payload.identifier)
    if not user or not user.active or not verify_password(payload.password,user.password_hash):
        record_login_failure(db,payload.identifier)
        raise HTTPException(status_code=401,detail="Email, phone number, or password is incorrect")
    clear_login_failures(db,payload.identifier)
    return create_session(db,user,request,response)

@app.post("/api/auth/code/request",status_code=202)
def request_email_code(payload:EmailCodeRequestInput,db:Session=Depends(get_db)):
    email=normalize_email(payload.email)
    issue_email_code(db,email)
    return {"message":"If an account exists, a six-digit code has been sent"}

@app.post("/api/auth/register/code",status_code=202)
def request_registration_code(payload:EmailCodeRequestInput,db:Session=Depends(get_db)):
    email=normalize_email(payload.email)
    issue_email_code(db,email,purpose="register")
    return {"message":"A six-digit verification code has been sent"}

@app.post("/api/auth/login/code")
def login_with_email_code(payload:EmailCodeLoginInput,request:Request,response:Response,db:Session=Depends(get_db)):
    email=normalize_email(payload.email)
    user=consume_email_code(db,email,payload.code)
    return create_session(db,user,request,response)

@app.get("/api/auth/me")
def current_account(request:Request,db:Session=Depends(get_db)):
    user=authenticated_user(db,request)
    if not user:
        raise HTTPException(status_code=401,detail="Sign in to open your workspace")
    return {"user":public_user(user)}

@app.post("/api/auth/password")
def change_account_password(payload:PasswordChangeInput,request:Request,db:Session=Depends(get_db)):
    user=authenticated_user(db,request)
    if not user or not verify_password(payload.current_password,user.password_hash):
        raise HTTPException(status_code=401,detail="Current password is incorrect")
    validate_password_strength(payload.new_password)
    if verify_password(payload.new_password,user.password_hash):
        raise HTTPException(status_code=400,detail="Choose a password you have not just used")
    user.password_hash=hash_password(payload.new_password)
    user.must_change_password=False
    current_token=request.cookies.get(settings.auth_cookie_name)
    current_hash=session_token_hash(current_token) if current_token else ""
    for session in db.scalars(select(UserSession).where(UserSession.user_id==user.id,UserSession.token_hash!=current_hash)).all():
        db.delete(session)
    db.commit()
    return {"message":"Password updated","user":public_user(user)}

@app.patch("/api/auth/profile")
def update_account_profile(payload:ProfileUpdateInput,request:Request,db:Session=Depends(get_db)):
    user=authenticated_user(db,request)
    if not user:
        raise HTTPException(status_code=401,detail="Sign in to open your workspace")
    if user.must_change_password:
        raise HTTPException(status_code=403,detail="Change your temporary password first")
    phone=normalize_phone(payload.phone)
    if phone and db.scalar(select(User.id).where(User.phone==phone,User.id!=user.id)):
        raise HTTPException(status_code=409,detail="Another account already uses this phone number")
    user.full_name=payload.full_name.strip()
    user.phone=phone
    db.commit()
    return {"message":"Profile updated","user":public_user(user)}

@app.post("/api/auth/logout",status_code=204)
def logout_account(request:Request,response:Response,db:Session=Depends(get_db)):
    user=authenticated_user(db,request)
    if user:
        db.info["user_id"]=user.id
        for device in db.scalars(select(PushDevice).where(PushDevice.enabled.is_(True))).all():
            device.enabled=False
        db.commit()
    revoke_session(db,request,response)
    response.status_code=204
    return response

def require_admin(db:Session) -> User:
    user_id=request_user_id.get()
    user=db.get(User,user_id) if user_id else None
    if not user or user.role!="admin" or not user.active:
        raise HTTPException(status_code=403,detail="Administrator access required")
    return user

def user_record_counts(db:Session,user_id:int) -> dict:
    counts={}
    for table in OWNED_TABLES:
        counts[table]=db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE user_id=:user_id"),{"user_id":user_id}).scalar() or 0
    return counts

@app.get("/api/admin/overview")
def admin_overview(db:Session=Depends(get_db)):
    admin=require_admin(db)
    users=list(db.scalars(select(User).order_by(User.created_at.desc())).all())
    payload=[]
    for user in users:
        if user.is_legacy_owner:
            continue
        details=public_user(user)
        details.update({
            "active":user.active,
            "created_at":user.created_at.isoformat()+"Z",
            "last_login_at":user.last_login_at.isoformat()+"Z" if user.last_login_at else None,
            "active_sessions":db.scalar(select(func.count(UserSession.id)).where(UserSession.user_id==user.id)) or 0,
            "record_counts":user_record_counts(db,user.id),
        })
        payload.append(details)
    legacy=db.scalar(select(User).where(User.is_legacy_owner.is_(True)))
    return {"current_admin":public_user(admin),"users":payload,"legacy_record_counts":user_record_counts(db,legacy.id) if legacy else {}}

@app.patch("/api/admin/users/{user_id}")
def update_admin_user(user_id:int,payload:AdminUserUpdateInput,db:Session=Depends(get_db)):
    admin=require_admin(db)
    target=db.get(User,user_id)
    if not target or target.is_legacy_owner:
        raise HTTPException(status_code=404,detail="User not found")
    if target.id==admin.id and (payload.active is False or payload.role=="user"):
        raise HTTPException(status_code=400,detail="You cannot remove your own administrator access")
    if payload.active is not None:
        target.active=payload.active
    if payload.role is not None:
        target.role=payload.role
    if payload.active is False:
        for session in db.scalars(select(UserSession).where(UserSession.user_id==target.id)).all():
            db.delete(session)
    db.commit()
    return {"user":public_user(target),"active":target.active}

@app.post("/api/admin/users/{user_id}/revoke-sessions")
def revoke_user_sessions(user_id:int,db:Session=Depends(get_db)):
    admin=require_admin(db)
    target=db.get(User,user_id)
    if not target or target.is_legacy_owner:
        raise HTTPException(status_code=404,detail="User not found")
    if target.id==admin.id:
        raise HTTPException(status_code=400,detail="Use password change to secure your own sessions")
    count=0
    for session in db.scalars(select(UserSession).where(UserSession.user_id==target.id)).all():
        db.delete(session); count+=1
    db.commit()
    return {"revoked_sessions":count}

@app.post("/api/admin/claim-legacy-data")
def claim_legacy_data(db:Session=Depends(get_db)):
    admin=require_admin(db)
    email=admin.email or ""
    db.commit()
    changed=transfer_legacy_data(engine,email)
    return {"records_transferred":changed}
@app.get("/api/stocks")
def stocks(db:Session=Depends(get_db)): return list(db.scalars(select(Stock).order_by(Stock.market_cap,Stock.name)).all())
@app.get("/api/recommendations")
def recommendations(stock_budget:int=35000,mf_budget:int=30000,db:Session=Depends(get_db)): return build_recommendations(list(db.scalars(select(Stock).where(Stock.enabled.is_(True))).all()),stock_budget,mf_budget)
@app.post("/api/review/run")
def run_review(db:Session=Depends(get_db)): monthly_review(db.info.get("user_id")); return {"status":"completed"}
@app.get("/api/reviews")
def reviews(db:Session=Depends(get_db)): return [{"id":r.id,"run_key":r.run_key.split("-",1)[-1] if r.run_key.startswith("u") else r.run_key,"created_at":r.created_at,"budget":r.budget,"deployed":float(r.deployed),"reserve":float(r.reserve),"status":r.status} for r in db.scalars(select(ReviewRun).order_by(ReviewRun.created_at.desc())).all()]
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
    buys=[item for item in recommendations if item.get("status")=="BUY"]
    details=", ".join(f"{item['symbol']} ₹{item['deploy_amount']:,.0f}" for item in buys[:8]) or "No buys are inside the configured price ranges today."
    db.add(NotificationReminder(kind="stock_buy",title="Your stock plan is ready",details=details,
        due_at=datetime.utcnow(),recurrence="once",remind_before_minutes=0,channels="push,email"))
    db.commit()
    return {"status":"completed","result":dispatch_due(db,source="stock_review"),"recommendations":len(recommendations)}
@app.get("/api/notifications/status")
def notification_status(db:Session=Depends(get_db)):
    return provider_status(db)

def serialize_notification_preferences(item:NotificationPreference):
    return {key:getattr(item,key) for key in (
        "email_address","email_enabled","push_enabled","expense_due_enabled","budget_alert_enabled",
        "monthly_report_enabled","failure_alerts_enabled","budget_threshold","default_lead_minutes",
        "quiet_start","quiet_end","timezone"
    )}

def serialize_reminder(item:NotificationReminder):
    return {"id":item.id,"kind":item.kind,"title":item.title,"details":item.details,"symbol":item.symbol,
        "amount":float(item.amount) if item.amount is not None else None,
        "due_at":item.due_at.isoformat()+"Z","recurrence":item.recurrence,
        "remind_before_minutes":item.remind_before_minutes,"channels":[value for value in item.channels.split(",") if value],
        "enabled":item.enabled}

def normalize_due_at(value:datetime):
    if value.tzinfo:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value

def validate_channels(channels:list[str]):
    cleaned=list(dict.fromkeys(channels))
    if not cleaned or any(channel not in {"push","email"} for channel in cleaned):
        raise HTTPException(status_code=400,detail="Choose push, email, or both")
    return cleaned

@app.get("/api/notifications/overview")
def notification_overview(db:Session=Depends(get_db)):
    preferences=get_preferences(db)
    reminders=list(db.scalars(select(NotificationReminder).order_by(NotificationReminder.enabled.desc(),NotificationReminder.due_at)).all())
    deliveries=list(db.scalars(select(NotificationDelivery).order_by(NotificationDelivery.sent_at.desc()).limit(20)).all())
    devices=list(db.scalars(select(PushDevice).where(PushDevice.enabled.is_(True)).order_by(PushDevice.last_seen_at.desc())).all())
    return {"status":provider_status(db),"preferences":serialize_notification_preferences(preferences),
        "reminders":[serialize_reminder(item) for item in reminders],
        "devices":[{"id":item.id,"label":item.device_label,"last_seen_at":item.last_seen_at.isoformat()+"Z"} for item in devices],
        "deliveries":[{"id":item.id,"kind":item.kind,"channel":item.channel,"title":item.title,"status":item.status,
            "error":item.error,"sent_at":item.sent_at.isoformat()+"Z"} for item in deliveries]}

@app.put("/api/notifications/preferences")
def save_notification_preferences(payload:NotificationPreferenceInput,db:Session=Depends(get_db)):
    item=get_preferences(db)
    for key,value in payload.model_dump().items(): setattr(item,key,value)
    db.commit(); db.refresh(item)
    return serialize_notification_preferences(item)

@app.post("/api/notifications/reminders")
def create_notification_reminder(payload:NotificationReminderInput,db:Session=Depends(get_db)):
    data=payload.model_dump(); data["due_at"]=normalize_due_at(data["due_at"])
    data["channels"]=",".join(validate_channels(data["channels"]))
    item=NotificationReminder(**data); db.add(item); db.commit(); db.refresh(item)
    return serialize_reminder(item)

@app.put("/api/notifications/reminders/{reminder_id}")
def update_notification_reminder(reminder_id:int,payload:NotificationReminderInput,db:Session=Depends(get_db)):
    item=db.get(NotificationReminder,reminder_id)
    if not item: raise HTTPException(status_code=404,detail="Reminder not found")
    data=payload.model_dump(); data["due_at"]=normalize_due_at(data["due_at"])
    data["channels"]=",".join(validate_channels(data["channels"]))
    for key,value in data.items(): setattr(item,key,value)
    db.commit(); db.refresh(item)
    return serialize_reminder(item)

@app.delete("/api/notifications/reminders/{reminder_id}")
def delete_notification_reminder(reminder_id:int,db:Session=Depends(get_db)):
    item=db.get(NotificationReminder,reminder_id)
    if not item: raise HTTPException(status_code=404,detail="Reminder not found")
    for delivery in db.scalars(select(NotificationDelivery).where(NotificationDelivery.reminder_id==reminder_id)).all():
        delivery.reminder_id=None
    db.delete(item); db.commit()
    return {"status":"ok"}

@app.get("/api/notifications/firebase-config")
def firebase_config():
    return public_firebase_config()

@app.post("/api/notifications/devices")
def register_push_device(payload:PushDeviceInput,db:Session=Depends(get_db)):
    user_id=db.info.get("user_id")
    if not user_id:
        item=db.scalar(select(PushDevice).where(PushDevice.token==payload.token))
        if item:
            item.enabled=True; item.device_label=payload.device_label; item.last_seen_at=datetime.utcnow()
        else:
            item=PushDevice(token=payload.token,device_label=payload.device_label); db.add(item)
        db.commit(); db.refresh(item)
        return {"id":item.id,"device_label":item.device_label,"enabled":item.enabled}
    with SessionLocal() as device_db:
        item=device_db.scalar(select(PushDevice).where(PushDevice.token==payload.token))
        if item:
            item.user_id=user_id; item.enabled=True; item.device_label=payload.device_label; item.last_seen_at=datetime.utcnow()
        else:
            item=PushDevice(user_id=user_id,token=payload.token,device_label=payload.device_label); device_db.add(item)
        device_db.commit(); device_db.refresh(item)
        return {"id":item.id,"device_label":item.device_label,"enabled":item.enabled}

@app.delete("/api/notifications/devices")
def unregister_push_device(payload:PushDeviceInput,db:Session=Depends(get_db)):
    item=db.scalar(select(PushDevice).where(PushDevice.token==payload.token))
    if item: item.enabled=False; db.commit()
    return {"status":"ok"}

@app.post("/api/notifications/test")
def test_notification(payload:NotificationTestInput,db:Session=Depends(get_db)):
    try:
        if payload.delay_minutes == 0:
            return send_test_notification(db,payload.channel,payload.device_token)
        reminder=schedule_test_notification(db,payload.channel,payload.delay_minutes)
        return {"status":"scheduled","channel":payload.channel,"delay_minutes":payload.delay_minutes,
            "reminder_id":reminder.id,"due_at":reminder.due_at.isoformat()+"Z"}
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@app.get("/api/notifications/history")
def notification_history(limit:int=20,db:Session=Depends(get_db)):
    safe_limit=max(1,min(limit,100))
    deliveries=list(db.scalars(select(NotificationDelivery).order_by(NotificationDelivery.sent_at.desc()).limit(safe_limit)).all())
    return [{"id":item.id,"kind":item.kind,"channel":item.channel,"title":item.title,"status":item.status,
        "error":item.error,"sent_at":item.sent_at.isoformat()+"Z"} for item in deliveries]

@app.post("/api/notifications/dispatch")
def run_notification_dispatch(x_notification_token:str|None=Header(default=None),db:Session=Depends(get_db)):
    expected=settings.notification_cron_token
    if not expected or not x_notification_token or not hmac.compare_digest(expected,x_notification_token):
        raise HTTPException(status_code=401,detail="Invalid notification scheduler token")
    return dispatch_all_users(source="github_actions")

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
def test_expense_notifications(db:Session=Depends(get_db)):
    """Manually trigger expense reminder notifications for testing"""
    result=dispatch_due(db,source="expense_test")
    return {"status":"completed","message":"Expense notification check completed","result":result}

@app.post("/api/expenses/notify/send")
def send_expense_notifications(expense_ids:list[int],db:Session=Depends(get_db)):
    """Send notifications for specific expenses"""
    expenses=list(db.scalars(select(MonthlyExpense).where(MonthlyExpense.id.in_(expense_ids))).all())
    if not expenses:
        return {"status":"error","message":"No expenses found"}

    now=datetime.utcnow()
    for expense in expenses:
        db.add(NotificationReminder(kind="credit_card",title=f"{expense.name} is due",details=expense.description,
            amount=expense.amount,due_at=now,recurrence="once",remind_before_minutes=0,channels="push,email"))
    db.commit()
    return {"status":"completed","result":dispatch_due(db,source="expense_manual")}

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

    preference=db.scalar(select(UserStockPreference).where(UserStockPreference.symbol==symbol))
    if manual_date is not None and (manual_date<1 or manual_date>31):
        raise HTTPException(status_code=400,detail="Date must be between 1 and 31")
    if not preference:
        preference=UserStockPreference(symbol=symbol,manual_sip_date=manual_date); db.add(preference)
    else:
        preference.manual_sip_date=manual_date

    db.commit()
    return {"symbol":symbol,"manual_date":preference.manual_sip_date}

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
    """Legacy compatibility endpoint; startup migrations now manage the schema."""
    return {"status":"ready","message":"Expense schema is current"}

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
    """Update only the signed-in user's legacy recurring records."""
    items=list(db.scalars(select(MonthlyExpense).where(MonthlyExpense.is_recurring.is_(None))).all())
    for item in items: item.is_recurring=True
    db.commit()
    return {"status":"ok","updated":len(items)}

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
