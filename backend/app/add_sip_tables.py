"""
Add SIP date optimization tables
Run this once to create the new tables
"""
from .db import init_db, engine
from sqlalchemy import text

def add_sip_tables():
    """Create SIP date preference and history tables"""
    with engine.connect() as conn:
        # Check if tables exist
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name='sip_date_preferences'
        """))

        if not result.fetchone():
            print("Creating SIP tables...")

            # Create SIP date preferences table
            conn.execute(text("""
                CREATE TABLE sip_date_preferences (
                    id SERIAL PRIMARY KEY,
                    start_date INTEGER NOT NULL DEFAULT 5,
                    end_date INTEGER NOT NULL DEFAULT 10,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Create SIP date history table
            conn.execute(text("""
                CREATE TABLE sip_date_history (
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

            # Insert default preference
            conn.execute(text("""
                INSERT INTO sip_date_preferences (start_date, end_date)
                VALUES (5, 10)
            """))

            conn.commit()
            print("✓ SIP tables created successfully!")
        else:
            print("✓ SIP tables already exist")

if __name__ == "__main__":
    print("Setting up SIP optimization tables...\n")
    add_sip_tables()