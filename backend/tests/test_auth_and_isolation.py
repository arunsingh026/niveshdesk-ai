from datetime import datetime
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.auth import hash_password, verify_password
from app.db import Base
from app.migrations import migrate_user_ownership
from app.models import BudgetPlan, PortfolioHolding, User
from app import main


def test_password_is_salted_hashed_and_verifiable():
    first = hash_password("StrongPass9")
    second = hash_password("StrongPass9")
    assert first != second
    assert "StrongPass9" not in first
    assert verify_password("StrongPass9", first) is True
    assert verify_password("WrongPass9", first) is False


def test_user_owned_queries_and_inserts_are_isolated():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as setup:
        first = User(full_name="First", email="first@example.com", password_hash=hash_password("StrongPass9"))
        second = User(full_name="Second", email="second@example.com", password_hash=hash_password("StrongPass9"))
        setup.add_all([first, second]); setup.flush()
        first_id, second_id = first.id, second.id
        setup.add_all([
            BudgetPlan(user_id=first_id, year=2026, month=9, income=100000),
            BudgetPlan(user_id=second_id, year=2026, month=9, income=200000),
        ])
        setup.commit()

    with factory() as first_db:
        first_db.info["user_id"] = first_id
        plans = list(first_db.scalars(select(BudgetPlan)).all())
        assert [float(item.income) for item in plans] == [100000]
        first_plan_id = plans[0].id
        first_db.add(PortfolioHolding(name="Private fund", asset_type="Mutual Fund", invested_amount=10, current_value=11))
        first_db.commit()

    with factory() as second_db:
        second_db.info["user_id"] = second_id
        assert list(second_db.scalars(select(PortfolioHolding)).all()) == []
        assert second_db.get(BudgetPlan, first_plan_id) is None


def test_existing_budget_is_moved_to_disabled_legacy_owner(tmp_path):
    database = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{database}")
    User.__table__.create(engine)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE budget_plans (
                id INTEGER PRIMARY KEY, year INTEGER NOT NULL, month INTEGER NOT NULL,
                income NUMERIC(14,2) NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                UNIQUE(year, month)
            )
        """))
        conn.execute(text("INSERT INTO budget_plans VALUES (1,2026,9,125000,'Owner plan',:now,:now)"), {"now": datetime.utcnow()})

    migrate_user_ownership(engine)

    with engine.connect() as conn:
        owner = conn.execute(text("SELECT id,active,is_legacy_owner FROM users")).mappings().one()
        plan = conn.execute(text("SELECT user_id,income FROM budget_plans")).mappings().one()
        assert owner["active"] == 0 and owner["is_legacy_owner"] == 1
        assert plan["user_id"] == owner["id"]
        indexes = conn.execute(text("PRAGMA index_list('budget_plans')")).all()
        assert any(row[2] == 1 for row in indexes)


def test_registered_accounts_receive_separate_api_workspaces(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(main, "SessionLocal", factory)
    monkeypatch.setattr(main, "consume_email_code", lambda *args, **kwargs: None)

    first = TestClient(main.app)
    second = TestClient(main.app)
    first_registration = first.post("/api/auth/register", json={
        "full_name": "First User", "email": "first@example.com", "phone": "+919876543210", "password": "StrongPass9", "verification_code": "123456",
    })
    second_registration = second.post("/api/auth/register", json={
        "full_name": "Second User", "email": "second@example.com", "phone": "+919876543211", "password": "StrongPass9", "verification_code": "123456",
    })
    assert first_registration.status_code == 201
    assert second_registration.status_code == 201

    saved = first.put("/api/budget/2026/9", json={
        "income": 100000, "notes": "private", "categories": [],
    })
    assert saved.status_code == 200
    assert first.get("/api/budget/2026/9").json()["income"] == 100000
    assert second.get("/api/budget/2026/9").json()["income"] == 0
    assert TestClient(main.app).get("/api/portfolio").status_code == 401
