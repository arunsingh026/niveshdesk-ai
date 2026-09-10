"""PythonAnywhere WSGI entry point for the FastAPI application."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path.home() / "niveshdesk-ai"
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{PROJECT_ROOT / 'niveshdesk.db'}",
)
os.environ.setdefault("STATIC_DIR", str(PROJECT_ROOT / "static"))

sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from a2wsgi import ASGIMiddleware
from app.db import init_db
from app.main import app
from app.services.scheduler import start_scheduler

init_db()
start_scheduler()
application = ASGIMiddleware(app)
