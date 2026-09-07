import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.main import (
    BudgetCategoryInput,
    BudgetPlanInput,
    HoldingInput,
    create_holding,
    get_budget,
    get_portfolio,
    portfolio_summary,
    save_budget,
)


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_budget_round_trip_and_summary():
    db = session()
    saved = save_budget(2026, 9, BudgetPlanInput(
        income=100000,
        notes="September plan",
        categories=[
            BudgetCategoryInput(name="Home", bucket="needs", planned_amount=40000, actual_amount=38000, icon="fa-house"),
            BudgetCategoryInput(name="SIP", bucket="future", planned_amount=20000, actual_amount=20000, icon="fa-seedling"),
        ],
    ), db)
    assert saved["income"] == 100000
    assert get_budget(2026, 9, db)["categories"][1]["name"] == "SIP"


def test_portfolio_round_trip_and_summary():
    db = session()
    create_holding(HoldingInput(
        name="Nifty Index Fund", asset_type="Mutual Fund", symbol="", units=12.5,
        invested_amount=100000, current_value=112500, platform="Direct", goal="Retirement", notes="",
    ), db)
    holdings = get_portfolio(db)
    summary = portfolio_summary(db)
    assert holdings[0]["name"] == "Nifty Index Fund"
    assert summary == {"invested": 100000.0, "current_value": 112500.0, "gain": 12500.0, "return_percent": 12.5, "holdings": 1}
