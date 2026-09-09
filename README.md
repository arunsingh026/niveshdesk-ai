# My Stock Planner

A multi-user, India-first personal finance and investment workspace.

## Features
- Monthly portfolio targets and preferred buy ranges
- Whole-share quantity calculation from latest available prices
- Monthly scheduler (default: 5th, 09:00 Asia/Kolkata)
- Email and WhatsApp notification adapters
- Mobile/web Notification Center with FCM push, Resend reports, smart finance reminders, quiet hours, and delivery history
- Private user registration with isolated budgets, expenses, portfolios, reminders, devices, and preferences
- Secure HttpOnly sessions, salted PBKDF2 password hashing, phone-number/password login, and Resend email-code login
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

See `NOTIFICATIONS_SETUP.md` to connect the no-cost Firebase, Resend, and GitHub Actions notification stack.

See `ADMIN_SETUP.md` for the console-only owner provisioning flow and the protected administrator workspace.

## Account security

Set `AUTH_CODE_PEPPER` to a long random value in the private production environment before enabling email-code sign-in. Password and session values are never stored in frontend storage. Existing single-user finance records are migrated to a disabled legacy owner and must be transferred administratively after the real owner registers.

Phone-number + password login is included without an SMS provider. Firebase SMS authentication is intentionally not enabled because Google requires a billing-linked Blaze project for verification SMS; email codes via Resend preserve the no-cost deployment.
