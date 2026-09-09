# Owner administrator setup

NiveshDesk has role-based administrator access. The admin console lists safe account metadata, active sessions, and per-user record counts; it never returns password hashes or session tokens.

## Provision the first owner

Run this only from a trusted production console after the database backup and application migration have succeeded. Keep the temporary password out of shell history by reading it silently:

```bash
read -s TEMP_PASSWORD
TEMP_PASSWORD="$TEMP_PASSWORD" python -c 'import os; from app.db import engine; from app.migrations import provision_owner_admin; print(provision_owner_admin(engine, "Owner Name", "owner@example.com", os.environ["TEMP_PASSWORD"], "+919876543210"))'
unset TEMP_PASSWORD
```

The helper:

- creates or updates the named account as `admin`;
- hashes the temporary password immediately;
- revokes any existing sessions for that account;
- marks the account as requiring a password change; and
- transfers records from the disabled legacy owner into the new owner account.

On first sign-in, the user can only access the password-change screen. Finance and admin APIs remain blocked until a new strong password is saved.

## Admin capabilities

- View registered users, roles, account state, last sign-in, active sessions, and record counts.
- Promote or demote other users.
- Pause or restore another user's access.
- Revoke another user's sessions.
- Claim any remaining protected legacy records into the current administrator account.

An administrator cannot demote or deactivate their own account from the web console. Passwords are never visible or recoverable; users must change or reset them instead.
