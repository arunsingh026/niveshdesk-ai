# NiveshDesk zero-cost migration

This migration is intentionally staged so the live PythonAnywhere application
stays available until the replacement is proven.

## Target layout

- **Vercel Hobby:** React/Vite frontend, custom domain, HTTPS
- **Supabase Free:** PostgreSQL database
- **Container backend:** the existing FastAPI image
- **Firebase Cloud Messaging:** web/mobile push
- **Resend:** transactional email and email sign-in codes
- **GitHub Actions:** fallback notification dispatch

The FastAPI backend remains a container because it includes PyMuPDF, ReportLab,
yfinance, background scheduling, PDF uploads, and HttpOnly session handling.
Moving it directly into short-lived frontend functions would make minute-level
reminders and PDF processing unreliable.

## Phase 1: deploy the frontend without downtime

1. In Vercel, import `arunsingh026/niveshdesk-ai`.
2. Set **Root Directory** to `frontend`.
3. Keep the detected Vite build settings. `frontend/vercel.json` contains the
   production build, SPA fallback, security headers, and temporary API proxy.
4. Deploy and open the generated `*.vercel.app` URL.
5. Verify registration, password login, dashboard, expenses, budget, portfolio,
   PDF forms, notification permission, immediate push, and email test.

The temporary same-origin proxy sends `/api/*` and `/health` to the current
PythonAnywhere backend. This preserves Secure HttpOnly session cookies and
avoids a risky all-at-once cutover.

## Phase 2: create the Supabase database

1. Create a free Supabase project near the backend region.
2. Open **Connect** and copy the **Session pooler** connection string (port
   `5432`). Session mode is appropriate for this persistent FastAPI service and
   works from IPv4-only hosts.
3. Convert it to an application secret without committing it:

   ```text
   DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:5432/postgres
   DATABASE_SSL_MODE=require
   DATABASE_POOL_SIZE=5
   DATABASE_MAX_OVERFLOW=5
   ```

   The application automatically selects its installed Psycopg 3 driver for
   `postgresql://` and `postgres://` provider URLs.
4. Start a temporary backend instance with this connection. Startup creates the
   current schema and applies the user-ownership migrations.
5. Run the full backend test suite, register a temporary user, and confirm data
   isolation before importing any live records.

Do not put the database password, Firebase service-account JSON, Resend key,
authentication pepper, or cron token in GitHub source or Vercel client-side
variables.

## Phase 3: move the FastAPI container

Deploy the repository root `Dockerfile` to a container host with one instance,
no autoscaling above one instance, and a health check at `/health`. Configure:

```text
DATABASE_URL=<Supabase Session pooler URL>
DATABASE_SSL_MODE=require
PUBLIC_APP_URL=https://YOUR_DOMAIN
AUTH_CODE_PEPPER=<long random secret>
NOTIFICATION_CRON_TOKEN=<long random secret>
RESEND_API_KEY=<secret>
RESEND_FROM=NiveshDesk <notifications@YOUR_DOMAIN>
FIREBASE_SERVICE_ACCOUNT_JSON=<single-line service account JSON>
FIREBASE_API_KEY=<public Firebase web setting>
FIREBASE_AUTH_DOMAIN=<public Firebase web setting>
FIREBASE_PROJECT_ID=<public Firebase web setting>
FIREBASE_STORAGE_BUCKET=<public Firebase web setting>
FIREBASE_MESSAGING_SENDER_ID=<public Firebase web setting>
FIREBASE_APP_ID=<public Firebase web setting>
FIREBASE_VAPID_KEY=<public VAPID key>
DRY_RUN_NOTIFICATIONS=false
```

After backend verification, replace the two PythonAnywhere destinations in
`frontend/vercel.json` with the new HTTPS backend origin and redeploy.

## Phase 4: custom domain and final cutover

1. Add the purchased domain to Vercel and apply the DNS records Vercel shows.
2. Add the production domain to Firebase's authorized domains and Resend's
   verified sending domain.
3. Set `PUBLIC_APP_URL` to the exact production origin (no trailing slash).
4. Run the end-to-end checklist again on the custom domain.
5. Export and import the current database, verify record counts and ownership,
   then switch the API proxy to the new backend.
6. Keep PythonAnywhere unchanged for at least 48 hours. Remove it only after the
   new health endpoint and notification delivery history remain healthy.

## Rollback

If any production check fails, point the Vercel API rewrites back to:

```text
https://arunsingh026.pythonanywhere.com
```

The old application and database are not modified by Phase 1, so rollback is a
single frontend redeploy.
