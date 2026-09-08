import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.config import settings
from app.db import Base
from app.main import (
    NotificationPreferenceInput,
    NotificationReminderInput,
    PushDeviceInput,
    create_notification_reminder,
    notification_overview,
    register_push_device,
    run_notification_dispatch,
    save_notification_preferences,
)
from app.models import NotificationReminder
from app.services import notification_center


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def preferences(**overrides):
    values = {
        "email_address": "", "email_enabled": False, "push_enabled": True,
        "expense_due_enabled": False, "budget_alert_enabled": False,
        "monthly_report_enabled": False, "failure_alerts_enabled": True,
        "budget_threshold": 90, "default_lead_minutes": 1440,
        "quiet_start": 22, "quiet_end": 7, "timezone": "Asia/Kolkata",
    }
    values.update(overrides)
    return NotificationPreferenceInput(**values)


def test_reminder_round_trip_and_overview():
    db = session()
    due = datetime(2026, 9, 10, 9, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    created = create_notification_reminder(NotificationReminderInput(
        kind="sip", title="Index fund SIP", amount=5000, due_at=due,
        recurrence="monthly", remind_before_minutes=1440, channels=["push", "email"],
    ), db)
    assert created["due_at"] == "2026-09-10T03:30:00Z"
    overview = notification_overview(db)
    assert overview["reminders"][0]["title"] == "Index fund SIP"
    assert overview["preferences"]["timezone"] == "Asia/Kolkata"


def test_dispatch_sends_due_push_and_advances_once(monkeypatch):
    db = session()
    save_notification_preferences(preferences(), db)
    now = datetime(2026, 9, 8, 6, 0)
    created = create_notification_reminder(NotificationReminderInput(
        kind="stock_buy", title="Review ICICI Bank", symbol="ICICIBANK",
        due_at=now + timedelta(minutes=30), recurrence="once",
        remind_before_minutes=60, channels=["push"],
    ), db)
    register_push_device(PushDeviceInput(token="device-token-that-is-long-enough", device_label="iPhone"), db)
    monkeypatch.setattr(settings, "firebase_service_account_json", "{}")
    monkeypatch.setattr(settings, "firebase_project_id", "niveshdesk-test")
    monkeypatch.setattr(notification_center, "_send_push", lambda *args: (True, ""))

    result = notification_center.dispatch_due(db, now=now)
    assert result["events"] == 1
    assert result["results"][0]["channels"] == {"push": "sent"}
    assert db.get(NotificationReminder, created["id"]).enabled is False
    assert notification_center.dispatch_due(db, now=now)["events"] == 0


def test_dispatch_endpoint_rejects_wrong_secret(monkeypatch):
    db = session()
    monkeypatch.setattr(settings, "notification_cron_token", "correct-long-secret")
    with pytest.raises(HTTPException) as error:
        run_notification_dispatch("wrong", db)
    assert error.value.status_code == 401


def test_firebase_public_config_never_contains_private_json(monkeypatch):
    monkeypatch.setattr(settings, "firebase_service_account_json", '{"private_key":"secret"}')
    config = notification_center.public_firebase_config()
    assert "service" not in " ".join(config.keys()).lower()
    assert "secret" not in str(config)
