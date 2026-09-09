# NiveshDesk multi-user authentication

NiveshDesk supports three no-cost sign-in paths:

- Verified email address and password
- Mobile number and password (use E.164 format, such as `+919876543210`)
- A six-digit one-time code sent to the account email through Resend

Sessions use a random server-side token. Only its SHA-256 digest is stored in the database, while the browser receives the original in a `Secure`, `HttpOnly`, `SameSite=Lax` cookie. Passwords use per-account salts and PBKDF2-SHA256 with 600,000 iterations. Five failed password attempts lock that identifier for 15 minutes.

## Private environment values

```env
PUBLIC_APP_URL=https://your-app.example
AUTH_SESSION_DAYS=30
AUTH_CODE_MINUTES=10
AUTH_CODE_PEPPER=<long-random-secret>
ALLOW_REGISTRATION=true
RESEND_API_KEY=<server-side-resend-key>
```

Generate `AUTH_CODE_PEPPER` outside source control and store it only in the production environment. Email-code sign-in stays unavailable until both it and `RESEND_API_KEY` are configured.

New accounts verify their email with a six-digit Resend code before creation. A mobile number is an optional login identifier paired with the account password; it is not presented as an SMS-verified number.

## Existing-data migration

At first startup, existing single-user data is assigned to a disabled `legacy@niveshdesk.local` account. It is never given to the first public registration. After the real owner registers, transfer it from a trusted PythonAnywhere console:

```python
from app.db import engine
from app.migrations import transfer_legacy_data
print(transfer_legacy_data(engine, "owner@example.com"))
```

Back up the database before deploying this migration. Do not expose the transfer helper as an HTTP endpoint.

## Why SMS codes are not included

Firebase requires a billing-linked Blaze project to send phone verification SMS. Phone-number + password login and Resend email codes keep this deployment on no-cost services. If paid SMS is approved later, Firebase phone verification can be added as an optional provider.
