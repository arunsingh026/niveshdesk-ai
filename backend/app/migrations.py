from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


OWNED_TABLES = (
    "review_runs",
    "monthly_expenses",
    "expense_payments",
    "sip_date_preferences",
    "sip_date_history",
    "user_stock_preferences",
    "budget_plans",
    "budget_categories",
    "portfolio_holdings",
    "notification_preferences",
    "notification_reminders",
    "push_devices",
    "notification_deliveries",
    "notification_dispatch_runs",
)


def _rebuild_sqlite_budget_plans(conn) -> None:
    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    conn.exec_driver_sql("""
        CREATE TABLE budget_plans_v2 (
            id INTEGER NOT NULL PRIMARY KEY,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            income NUMERIC(14,2) NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            user_id INTEGER REFERENCES users(id),
            CONSTRAINT uq_budget_plan_user_month UNIQUE (user_id, year, month)
        )
    """)
    conn.exec_driver_sql("""
        INSERT INTO budget_plans_v2 (id,year,month,income,notes,created_at,updated_at,user_id)
        SELECT id,year,month,income,notes,created_at,updated_at,user_id FROM budget_plans
    """)
    conn.exec_driver_sql("DROP TABLE budget_plans")
    conn.exec_driver_sql("ALTER TABLE budget_plans_v2 RENAME TO budget_plans")
    conn.exec_driver_sql("CREATE INDEX ix_budget_plans_year ON budget_plans (year)")
    conn.exec_driver_sql("CREATE INDEX ix_budget_plans_month ON budget_plans (month)")
    conn.exec_driver_sql("CREATE INDEX ix_budget_plans_user_id ON budget_plans (user_id)")
    conn.exec_driver_sql("PRAGMA foreign_keys=ON")


def migrate_user_ownership(engine: Engine) -> None:
    """Add ownership safely to an existing single-user database.

    Existing records are assigned to a disabled local-only account. They can be
    transferred to the real owner after that person registers, without exposing
    the old portfolio to the first public visitor.
    """
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    added_to_budget = False
    with engine.begin() as conn:
        for table in OWNED_TABLES:
            if table not in existing:
                continue
            columns = {item["name"] for item in inspect(conn).get_columns(table)}
            if "user_id" not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER"))
                added_to_budget = added_to_budget or table == "budget_plans"

    if added_to_budget and engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            _rebuild_sqlite_budget_plans(conn)
            conn.commit()

    with engine.begin() as conn:
        has_legacy_data = any(
            conn.execute(text(f"SELECT 1 FROM {table} WHERE user_id IS NULL LIMIT 1")).first()
            for table in OWNED_TABLES if table in existing
        )
        if not has_legacy_data:
            return
        legacy_id = conn.execute(text("SELECT id FROM users WHERE is_legacy_owner = true LIMIT 1")).scalar()
        if not legacy_id:
            result = conn.execute(text("""
                INSERT INTO users (full_name,email,password_hash,email_verified,phone_verified,active,is_legacy_owner,created_at)
                VALUES ('Legacy owner','legacy@niveshdesk.local',NULL,false,false,false,true,CURRENT_TIMESTAMP)
            """))
            legacy_id = result.lastrowid
            if not legacy_id:
                legacy_id = conn.execute(text("SELECT id FROM users WHERE is_legacy_owner = true LIMIT 1")).scalar_one()
        for table in OWNED_TABLES:
            if table in existing:
                conn.execute(text(f"UPDATE {table} SET user_id = :user_id WHERE user_id IS NULL"), {"user_id": legacy_id})
        if "notification_preferences" in existing:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_notification_preferences_user_id ON notification_preferences (user_id)"))
        if "sip_date_preferences" in existing:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_sip_date_preferences_user_id ON sip_date_preferences (user_id)"))


def transfer_legacy_data(engine: Engine, destination_email: str) -> int:
    """Administrative deployment helper; intentionally not exposed as an API."""
    with engine.begin() as conn:
        destination = conn.execute(text("SELECT id FROM users WHERE email = :email AND active = true"), {"email": destination_email.lower()}).scalar()
        legacy = conn.execute(text("SELECT id FROM users WHERE is_legacy_owner = true LIMIT 1")).scalar()
        if not destination or not legacy:
            return 0
        changed = 0
        destination_preference = conn.execute(text("SELECT id FROM notification_preferences WHERE user_id = :destination LIMIT 1"), {"destination": destination}).scalar()
        legacy_preference = conn.execute(text("SELECT id FROM notification_preferences WHERE user_id = :legacy LIMIT 1"), {"legacy": legacy}).scalar()
        if destination_preference and legacy_preference:
            conn.execute(text("DELETE FROM notification_preferences WHERE id = :preference"), {"preference": destination_preference})
        for table in OWNED_TABLES:
            result = conn.execute(text(f"UPDATE {table} SET user_id = :destination WHERE user_id = :legacy"), {"destination": destination, "legacy": legacy})
            changed += result.rowcount or 0
        return changed
