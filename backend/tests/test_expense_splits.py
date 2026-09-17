import os

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.db import Base
from app.main import (
    ExpenseSplitInput,
    ExpenseSplitPersonInput,
    ExpenseSplitReminderInput,
    get_expense_split,
    remind_expense_split,
    save_expense_split,
)
from app.models import MonthlyExpense
from app.services import notification_center


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def expense(db, amount=1000):
    item = MonthlyExpense(name="Dinner", amount=amount, day_of_month=17, category="Food")
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_split_must_equal_expense_and_have_contact():
    db = session()
    item = expense(db)
    with pytest.raises(HTTPException) as error:
        save_expense_split(item.id, ExpenseSplitInput(participants=[
            ExpenseSplitPersonInput(name="A", email="a@example.com", share_amount=400),
            ExpenseSplitPersonInput(name="B", phone="+919876543210", share_amount=500),
        ]), db)
    assert error.value.status_code == 400
    assert "total" in error.value.detail


def test_split_round_trip_and_free_phone_handoff(monkeypatch):
    db = session()
    item = expense(db)
    saved = save_expense_split(item.id, ExpenseSplitInput(participants=[
        ExpenseSplitPersonInput(name="A", email="a@example.com", share_amount=600),
        ExpenseSplitPersonInput(name="B", phone="+919876543210", share_amount=400),
    ]), db)
    monkeypatch.setattr(notification_center.settings, "twilio_account_sid", "")
    person = saved["participants"][1]
    result = remind_expense_split(item.id, person["id"], ExpenseSplitReminderInput(channels=["sms"]), db)
    assert get_expense_split(item.id, db)["participants"][0]["share_amount"] == 600
    assert result["results"]["sms"] == "ready_on_device"
    assert result["manual_sms"]["phone"] == "+919876543210"


def test_resend_error_exposes_fix_without_secret(monkeypatch):
    class Response:
        status_code = 400
        text = '{"message":"The example.com domain is not verified"}'
        def json(self):
            return {"message": "The example.com domain is not verified"}

    monkeypatch.setattr(notification_center.settings, "resend_api_key", "re_secret")
    monkeypatch.setattr(notification_center.httpx, "post", lambda *args, **kwargs: Response())
    ok, error = notification_center._send_email("a@example.com", "Test", "Body", "<p>Body</p>")
    assert ok is False
    assert "Verify RESEND_FROM/domain" in error
    assert "re_secret" not in error
