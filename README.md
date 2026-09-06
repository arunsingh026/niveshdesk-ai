# My Stock Planner

A personal monthly Indian-equity investment planner for a ₹35,000/month strategy.

## Features
- Monthly portfolio targets and preferred buy ranges
- Whole-share quantity calculation from latest available prices
- Monthly scheduler (default: 5th, 09:00 Asia/Kolkata)
- Email and WhatsApp notification adapters
- Manual trade execution only; no broker orders
- PostgreSQL persistence
- FastAPI backend + React/Vite frontend
- Docker Compose

## Quick start
```bash
cp .env.example .env
docker compose up --build
docker compose exec api python -m app.seed
```
Frontend: http://localhost:5173
API docs: http://localhost:8000/docs

Market data defaults to yfinance (`SYMBOL.NS`). For production, replace it with a licensed NSE/broker feed if you need real-time accuracy.

Email can use SMTP. WhatsApp uses the official Meta Cloud API adapter. Keep `DRY_RUN_NOTIFICATIONS=true` until credentials are configured and tested.

Google documents `gmail.send` as a Gmail API scope for sending mail: https://developers.google.com/identity/protocols/oauth2/scopes

This application is a planning/reminder tool, not an autonomous trading system or financial-advice engine. Verify live NSE quotes before placing orders.
