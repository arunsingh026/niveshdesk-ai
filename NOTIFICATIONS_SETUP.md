# NiveshDesk notification setup (free tier)

The Notification Center stores reminders in the existing NiveshDesk database. An hourly GitHub Actions workflow securely asks the live API to dispatch due items. The API sends browser/mobile web push through Firebase Cloud Messaging (FCM) and reports through Resend.

## 1. Create the provider accounts

1. Create a Firebase project on the Spark (no-cost) plan.
2. Add a Web app, enable Cloud Messaging, and create a Web Push certificate (VAPID key).
3. In Firebase project settings, create a service-account private key JSON file. Never commit this file.
4. Create a free Resend account and API key. For initial testing, `onboarding@resend.dev` can send only to the Resend account owner; verify a domain later if you want another sender.

## 2. Configure PythonAnywhere securely

Add these values to the PythonAnywhere WSGI environment before the app import, or load them from a private `.env` file. The Firebase service account value must be the complete JSON serialized on one line.

```env
PUBLIC_APP_URL=https://arunsingh026.pythonanywhere.com
NOTIFICATION_CRON_TOKEN=<a-long-random-value>
RESEND_API_KEY=re_...
RESEND_FROM=NiveshDesk <onboarding@resend.dev>
FIREBASE_SERVICE_ACCOUNT_JSON={...}
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=...firebaseapp.com
FIREBASE_PROJECT_ID=...
FIREBASE_STORAGE_BUCKET=...firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=...
FIREBASE_APP_ID=...
FIREBASE_VAPID_KEY=...
```

Reload the PythonAnywhere web app after changing environment values.

## 3. Configure GitHub Actions

In **Repository → Settings → Secrets and variables → Actions**:

- Add secret `NOTIFICATION_CRON_TOKEN` with exactly the same random value as PythonAnywhere.
- Optionally add variable `NOTIFICATION_APP_URL`; it defaults to the current PythonAnywhere URL.

Run **Notification Dispatch → Run workflow** once to verify the protected endpoint.

## 4. Connect devices

- Desktop/Android: open Notification Center and select **Enable alerts**.
- iPhone/iPad: in Safari choose **Share → Add to Home Screen**, open the installed NiveshDesk app, then select **Enable alerts**. Apple only allows web push permission for Home Screen web apps.

Provider secrets remain server-side. Firebase web configuration and the VAPID public key are intentionally public identifiers; the service-account JSON and Resend API key are never returned by the API.
