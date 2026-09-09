from datetime import datetime
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.auth import hash_password, verify_password
from app.db import Base
from app.migrations import migrate_user_ownership, provision_owner_admin
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


def test_admin_columns_are_added_to_an_existing_user_table(tmp_path):
    database = tmp_path / "existing-users.db"
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY, full_name VARCHAR(120) NOT NULL,
                email VARCHAR(254), phone VARCHAR(20), password_hash TEXT,
                email_verified BOOLEAN NOT NULL DEFAULT false,
                phone_verified BOOLEAN NOT NULL DEFAULT false,
                active BOOLEAN NOT NULL DEFAULT true,
                is_legacy_owner BOOLEAN NOT NULL DEFAULT false,
                created_at DATETIME NOT NULL, last_login_at DATETIME
            )
        """))
        conn.execute(text("INSERT INTO users (id,full_name,email,created_at) VALUES (1,'Existing','existing@example.com',CURRENT_TIMESTAMP)"))

    migrate_user_ownership(engine)

    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info('users')"))}
        existing = conn.execute(text("SELECT role,must_change_password FROM users WHERE id=1")).one()
        assert {"role", "must_change_password"}.issubset(columns)
        assert existing == ("user", 0)


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


def test_temporary_admin_must_change_password_before_opening_workspace(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(User(full_name="Owner", email="owner@example.com", password_hash=hash_password("TempPass9"),
                    email_verified=True, role="admin", must_change_password=True))
        db.commit()
    monkeypatch.setattr(main, "SessionLocal", factory)

    client = TestClient(main.app)
    login = client.post("/api/auth/login/password", json={"identifier": "owner@example.com", "password": "TempPass9"})
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True
    blocked = client.get("/api/portfolio")
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "password_change_required"

    changed = client.post("/api/auth/password", json={"current_password": "TempPass9", "new_password": "PrivatePass8"})
    assert changed.status_code == 200
    assert changed.json()["user"]["must_change_password"] is False
    assert client.get("/api/portfolio").status_code == 200
    profile = client.patch("/api/auth/profile", json={"full_name": "Owner Name", "phone": "+919876543210"})
    assert profile.status_code == 200
    assert profile.json()["user"]["phone"] == "+919876543210"
    assert client.post("/api/auth/logout").status_code == 204
    phone_login = client.post("/api/auth/login/password", json={"identifier": "+919876543210", "password": "PrivatePass8"})
    assert phone_login.status_code == 200


def test_admin_directory_never_exposes_password_hashes(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add_all([
            User(full_name="Owner", email="owner@example.com", password_hash=hash_password("StrongPass9"), email_verified=True, role="admin"),
            User(full_name="Member", email="member@example.com", password_hash=hash_password("MemberPass9"), email_verified=True),
        ])
        db.commit()
    monkeypatch.setattr(main, "SessionLocal", factory)

    admin = TestClient(main.app)
    member = TestClient(main.app)
    assert admin.post("/api/auth/login/password", json={"identifier": "owner@example.com", "password": "StrongPass9"}).status_code == 200
    assert member.post("/api/auth/login/password", json={"identifier": "member@example.com", "password": "MemberPass9"}).status_code == 200
    assert member.get("/api/admin/overview").status_code == 403
    response = admin.get("/api/admin/overview")
    assert response.status_code == 200
    assert len(response.json()["users"]) == 2
    assert "password_hash" not in response.text.lower()
    assert "pbkdf2_sha256" not in response.text.lower()


def test_owner_admin_provisioning_transfers_protected_legacy_data():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        legacy = User(full_name="Legacy", email="legacy@niveshdesk.local", active=False, is_legacy_owner=True)
        db.add(legacy); db.flush()
        db.add(BudgetPlan(user_id=legacy.id, year=2026, month=9, income=125000))
        db.commit()

    result = provision_owner_admin(engine, "Owner Name", "owner@example.com", "TempPass9")
    assert result["legacy_records_transferred"] == 1
    with factory() as db:
        owner = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert owner.role == "admin"
        assert owner.must_change_password is True
        assert verify_password("TempPass9", owner.password_hash)
        assert db.scalar(select(BudgetPlan)).user_id == owner.id
