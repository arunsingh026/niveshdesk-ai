import calendar
import json
from datetime import date, datetime, timedelta, timezone
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    BudgetCategory,
    BudgetPlan,
    ExpensePayment,
    MonthlyExpense,
    NotificationDelivery,
    NotificationPreference,
    NotificationReminder,
    PortfolioHolding,
    PushDevice,
)


def get_preferences(db: Session) -> NotificationPreference:
    preference = db.get(NotificationPreference, 1)
    if not preference:
        preference = NotificationPreference(id=1)
        db.add(preference)
        db.commit()
        db.refresh(preference)
    return preference


def provider_status(db: Session) -> dict[str, Any]:
    preference = get_preferences(db)
    push_configured = bool(
        settings.firebase_project_id
        and settings.firebase_service_account_json
        and settings.firebase_api_key
        and settings.firebase_app_id
        and settings.firebase_messaging_sender_id
        and settings.firebase_vapid_key
    )
    return {
        "push": {
            "enabled": preference.push_enabled,
            "configured": push_configured,
            "devices": len(list(db.scalars(select(PushDevice).where(PushDevice.enabled.is_(True))).all())),
        },
        "email": {
            "enabled": preference.email_enabled,
            "configured": bool(settings.resend_api_key and preference.email_address),
            "address": preference.email_address,
        },
        "scheduler": {
            "configured": bool(settings.notification_cron_token),
            "frequency": "Hourly",
        },
        "free_tier": True,
    }


def public_firebase_config() -> dict[str, str | bool]:
    configured = bool(
        settings.firebase_api_key
        and settings.firebase_project_id
        and settings.firebase_messaging_sender_id
        and settings.firebase_app_id
        and settings.firebase_vapid_key
    )
    return {
        "configured": configured,
        "apiKey": settings.firebase_api_key,
        "authDomain": settings.firebase_auth_domain,
        "projectId": settings.firebase_project_id,
        "storageBucket": settings.firebase_storage_bucket,
        "messagingSenderId": settings.firebase_messaging_sender_id,
        "appId": settings.firebase_app_id,
        "vapidKey": settings.firebase_vapid_key,
    }


def _firebase_access_token() -> str:
    info = json.loads(settings.firebase_service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    credentials.refresh(Request())
    return credentials.token


def _send_push(title: str, body: str, tokens: list[str], link: str) -> tuple[bool, str]:
    if not tokens:
        return False, "No push-enabled device"
    try:
        access_token = _firebase_access_token()
        url = f"https://fcm.googleapis.com/v1/projects/{settings.firebase_project_id}/messages:send"
        failures = []
        with httpx.Client(timeout=20) as client:
            for token in tokens:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={"message": {"token": token, "notification": {"title": title, "body": body}, "webpush": {"fcm_options": {"link": link}}}},
                )
                if response.status_code >= 300:
                    failures.append(response.text[:180])
        return (not failures, "; ".join(failures))
    except Exception as exc:
        return False, str(exc)[:300]


def _email_html(title: str, body: str, cta: str, details: str = "") -> str:
    return f"""<!doctype html><html><body style="margin:0;background:#f2f6f2;font-family:Arial,sans-serif;color:#17342c">
    <div style="max-width:620px;margin:28px auto;background:#fff;border:1px solid #dce7df;border-radius:18px;overflow:hidden">
      <div style="padding:28px;background:#155f4b;color:#fff"><div style="font-size:12px;letter-spacing:2px">NIVESHDESK MONEY ALERT</div><h1 style="margin:12px 0 0;font-size:28px">{escape(title)}</h1></div>
      <div style="padding:30px"><p style="font-size:17px;line-height:1.7">{escape(body)}</p>{details}<a href="{escape(settings.public_app_url)}/notifications" style="display:inline-block;margin-top:18px;padding:13px 20px;border-radius:9px;background:#d79b42;color:#17342c;text-decoration:none;font-weight:bold">{escape(cta)}</a>
      <p style="margin-top:28px;color:#718078;font-size:12px">Planning reminder only. Verify investment and payment details before acting.</p></div>
    </div></body></html>"""


def _send_email(to: str, title: str, body: str, html: str) -> tuple[bool, str]:
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.resend_from, "to": [to], "subject": title, "html": html, "text": body},
            timeout=20,
        )
        response.raise_for_status()
        return True, ""
    except Exception as exc:
        return False, str(exc)[:300]


def _event_sent(db: Session, event_key: str) -> bool:
    return db.scalar(select(NotificationDelivery.id).where(NotificationDelivery.event_key == event_key, NotificationDelivery.status == "sent")) is not None


def _record(db: Session, event: dict[str, Any], channel: str, ok: bool, error: str) -> None:
    existing = db.scalar(select(NotificationDelivery).where(NotificationDelivery.event_key == event["event_key"], NotificationDelivery.channel == channel))
    if existing:
        existing.status = "sent" if ok else "failed"
        existing.error = error
        existing.sent_at = datetime.utcnow()
    else:
        db.add(NotificationDelivery(
            reminder_id=event.get("reminder_id"), event_key=event["event_key"], kind=event["kind"],
            channel=channel, title=event["title"], status="sent" if ok else "failed", error=error,
        ))


def _advance(reminder: NotificationReminder) -> None:
    if reminder.recurrence == "once":
        reminder.enabled = False
        return
    due = reminder.due_at
    if reminder.recurrence == "weekly":
        reminder.due_at = due + timedelta(days=7)
    elif reminder.recurrence == "monthly":
        year = due.year + (1 if due.month == 12 else 0)
        month = 1 if due.month == 12 else due.month + 1
        reminder.due_at = due.replace(year=year, month=month, day=min(due.day, calendar.monthrange(year, month)[1]))


def _monthly_report(db: Session, today: date) -> dict[str, Any]:
    holdings = list(db.scalars(select(PortfolioHolding)).all())
    invested = sum(float(item.invested_amount) for item in holdings)
    current = sum(float(item.current_value) for item in holdings)
    gain = current - invested
    details = f"<div style='padding:18px;background:#f2f6f2;border-radius:12px'><b>Current value:</b> ₹{current:,.0f}<br><b>Invested:</b> ₹{invested:,.0f}<br><b>Gain / loss:</b> ₹{gain:,.0f}<br><b>Holdings:</b> {len(holdings)}</div>"
    return {
        "event_key": f"portfolio-report-{today:%Y-%m}", "kind": "portfolio_report",
        "title": f"Your {today.strftime('%B')} portfolio snapshot",
        "body": f"Your portfolio is ₹{current:,.0f} across {len(holdings)} holdings, with an overall change of ₹{gain:,.0f}.",
        "details": details, "channels": ["email"],
    }


def _collect_events(db: Session, now_utc: datetime, preference: NotificationPreference) -> list[dict[str, Any]]:
    local_now = now_utc.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(preference.timezone))
    events: list[dict[str, Any]] = []
    reminders = list(db.scalars(select(NotificationReminder).where(NotificationReminder.enabled.is_(True)).order_by(NotificationReminder.due_at)).all())
    for reminder in reminders:
        notify_at = reminder.due_at - timedelta(minutes=reminder.remind_before_minutes)
        if notify_at <= now_utc and not _event_sent(db, f"reminder-{reminder.id}-{reminder.due_at.isoformat()}"):
            amount = f" • ₹{float(reminder.amount):,.0f}" if reminder.amount is not None else ""
            local_due = reminder.due_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(preference.timezone))
            events.append({
                "event_key": f"reminder-{reminder.id}-{reminder.due_at.isoformat()}", "reminder_id": reminder.id,
                "kind": reminder.kind, "title": reminder.title, "body": f"Due {local_due.strftime('%d %b, %I:%M %p')} IST{amount}. {reminder.details}".strip(),
                "channels": [channel for channel in reminder.channels.split(",") if channel], "reminder": reminder,
            })

    if preference.expense_due_enabled:
        today = local_now.date()
        expenses = list(db.scalars(select(MonthlyExpense).where(MonthlyExpense.enabled.is_(True), MonthlyExpense.day_of_month <= today.day + max(1, preference.default_lead_minutes // 1440)).order_by(MonthlyExpense.day_of_month)).all())
        payments = {p.expense_id: p for p in db.scalars(select(ExpensePayment).where(ExpensePayment.year == today.year, ExpensePayment.month == today.month)).all()}
        for expense in expenses:
            if expense.is_recurring is False and (expense.specific_year != today.year or expense.specific_month != today.month):
                continue
            payment = payments.get(expense.id)
            if payment and (payment.is_paid or payment.notes == "__HIDDEN__"):
                continue
            key = f"expense-{expense.id}-{today:%Y-%m}"
            if not _event_sent(db, key):
                events.append({"event_key": key, "kind": "credit_card", "title": f"{expense.name} is coming up", "body": f"Due on {expense.day_of_month} {today.strftime('%B')}" + (f" • ₹{float(expense.amount):,.0f}" if expense.amount else ""), "channels": ["push", "email"]})

    if preference.budget_alert_enabled:
        today = local_now.date()
        plan = db.scalar(select(BudgetPlan).where(BudgetPlan.year == today.year, BudgetPlan.month == today.month))
        if plan and float(plan.income) > 0:
            spent = sum(float(row.actual_amount) for row in db.scalars(select(BudgetCategory).where(BudgetCategory.plan_id == plan.id)).all())
            percent = spent / float(plan.income) * 100
            key = f"budget-{today:%Y-%m}-{preference.budget_threshold}"
            if percent >= preference.budget_threshold and not _event_sent(db, key):
                events.append({"event_key": key, "kind": "budget", "title": "Budget needs attention", "body": f"You have used {percent:.0f}% of this month's income budget (₹{spent:,.0f}).", "channels": ["push", "email"]})

    if preference.monthly_report_enabled and local_now.day == 1 and local_now.hour >= 9:
        report = _monthly_report(db, local_now.date())
        if not _event_sent(db, report["event_key"]):
            events.append(report)
    return events


def dispatch_due(db: Session, now: datetime | None = None) -> dict[str, Any]:
    now_utc = (now or datetime.utcnow()).replace(tzinfo=None)
    preference = get_preferences(db)
    local_now = now_utc.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(preference.timezone))
    in_quiet_hours = (preference.quiet_start > preference.quiet_end and (local_now.hour >= preference.quiet_start or local_now.hour < preference.quiet_end)) or (preference.quiet_start < preference.quiet_end and preference.quiet_start <= local_now.hour < preference.quiet_end)
    if in_quiet_hours:
        return {"status": "quiet_hours", "checked_at": now_utc.isoformat() + "Z", "events": 0, "results": []}
    events = _collect_events(db, now_utc, preference)
    devices = [device.token for device in db.scalars(select(PushDevice).where(PushDevice.enabled.is_(True))).all()]
    results = []
    for event in events:
        delivered = False
        channel_results = {}
        for channel in event["channels"]:
            if channel == "push" and preference.push_enabled and settings.firebase_service_account_json and settings.firebase_project_id:
                ok, error = _send_push(event["title"], event["body"], devices, f"{settings.public_app_url}/notifications")
            elif channel == "email" and preference.email_enabled and settings.resend_api_key and preference.email_address:
                html = _email_html(event["title"], event["body"], "Open Notification Center", event.get("details", ""))
                ok, error = _send_email(preference.email_address, event["title"], event["body"], html)
            else:
                ok, error = False, f"{channel.title()} channel is not enabled or configured"
            _record(db, event, channel, ok, error)
            delivered = delivered or ok
            channel_results[channel] = "sent" if ok else "failed"
        if not delivered and preference.failure_alerts_enabled and not _event_sent(db, f"failure-{event['event_key']}"):
            failure_event = {"event_key": f"failure-{event['event_key']}", "kind": "delivery_failure", "title": "A NiveshDesk alert could not be delivered"}
            failure_body = f"Delivery failed for: {event['title']}. Open Notification Center to check channel setup."
            if "email" not in event["channels"] and preference.email_enabled and settings.resend_api_key and preference.email_address:
                ok, error = _send_email(preference.email_address, failure_event["title"], failure_body, _email_html(failure_event["title"], failure_body, "Check notification setup"))
                _record(db, failure_event, "email", ok, error)
            elif "push" not in event["channels"] and preference.push_enabled and settings.firebase_service_account_json and settings.firebase_project_id:
                ok, error = _send_push(failure_event["title"], failure_body, devices, f"{settings.public_app_url}/notifications")
                _record(db, failure_event, "push", ok, error)
        if delivered and event.get("reminder"):
            _advance(event["reminder"])
        results.append({"event_key": event["event_key"], "title": event["title"], "channels": channel_results})
        db.commit()
    return {"status": "completed", "checked_at": now_utc.isoformat() + "Z", "events": len(events), "results": results}
