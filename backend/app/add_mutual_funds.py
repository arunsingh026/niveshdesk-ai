"""
Add instrument_type column and insert mutual funds
Run this once to update the database
"""
from sqlalchemy import text
from .db import SessionLocal, engine
from .models import Stock

def add_instrument_type_column():
    """Add instrument_type column if it doesn't exist"""
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='stocks' AND column_name='instrument_type'
        """))

        if not result.fetchone():
            print("Adding instrument_type column...")
            conn.execute(text("ALTER TABLE stocks ADD COLUMN instrument_type VARCHAR(20) DEFAULT 'stock'"))
            conn.commit()
            print("✓ Added instrument_type column")
        else:
            print("✓ instrument_type column already exists")

def add_mutual_funds():
    """Add 6 popular mutual funds"""
    db = SessionLocal()

    mutual_funds = [
        {
            "name": "Parag Parikh Flexicap Fund",
            "symbol": "PPFAS",
            "instrument_type": "mutual_fund",
            "market_cap": "flexi",
            "sector": "Flexi Cap",
            "monthly_target": 5000,
            "min_buy": None,
            "max_buy": None,
            "enabled": True,
            "notes": "International exposure with strong track record"
        },
        {
            "name": "Axis Bluechip Fund",
            "symbol": "AXISBLU",
            "instrument_type": "mutual_fund",
            "market_cap": "large",
            "sector": "Large Cap",
            "monthly_target": 5000,
            "min_buy": None,
            "max_buy": None,
            "enabled": True,
            "notes": "Consistent large cap performer"
        },
        {
            "name": "Mirae Asset Large Cap Fund",
            "symbol": "MIRAELC",
            "instrument_type": "mutual_fund",
            "market_cap": "large",
            "sector": "Large Cap",
            "monthly_target": 5000,
            "min_buy": None,
            "max_buy": None,
            "enabled": True,
            "notes": "Low expense ratio, quality focus"
        },
        {
            "name": "Axis Midcap Fund",
            "symbol": "AXISMID",
            "instrument_type": "mutual_fund",
            "market_cap": "mid",
            "sector": "Mid Cap",
            "monthly_target": 4000,
            "min_buy": None,
            "max_buy": None,
            "enabled": True,
            "notes": "Best midcap fund with strong returns"
        },
        {
            "name": "Quant Small Cap Fund",
            "symbol": "QUANTSC",
            "instrument_type": "mutual_fund",
            "market_cap": "small",
            "sector": "Small Cap",
            "monthly_target": 3000,
            "min_buy": None,
            "max_buy": None,
            "enabled": True,
            "notes": "High risk, high return small cap"
        },
        {
            "name": "ICICI Prudential Nifty 50 Index Fund",
            "symbol": "ICICIN50",
            "instrument_type": "mutual_fund",
            "market_cap": "large",
            "sector": "Index Fund",
            "monthly_target": 5000,
            "min_buy": None,
            "max_buy": None,
            "enabled": True,
            "notes": "Low cost Nifty 50 index tracking"
        }
    ]

    for mf_data in mutual_funds:
        # Check if mutual fund already exists
        existing = db.query(Stock).filter(Stock.symbol == mf_data["symbol"]).first()
        if not existing:
            mf = Stock(**mf_data)
            db.add(mf)
            print(f"✓ Added: {mf_data['name']}")
        else:
            print(f"⊙ Already exists: {mf_data['name']}")

    db.commit()
    db.close()
    print("\n✓ Mutual funds setup complete!")

if __name__ == "__main__":
    print("Setting up mutual funds support...\n")
    add_instrument_type_column()
    add_mutual_funds()