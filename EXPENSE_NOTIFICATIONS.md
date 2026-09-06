# 📬 Expense Notifications Setup Guide

Get daily reminders for your monthly expenses via **Email**, **WhatsApp**, or **Telegram**!

## 🚀 How It Works

- **Automatic Daily Reminders**: Every day at **9:00 AM**, the system checks for expenses due that day
- **Smart Detection**: Only sends reminders for unpaid expenses
- **Multi-Channel**: Choose Email, WhatsApp, Telegram, or all three!

---

## 📧 Email Notifications Setup

### 1. Get App Password (Gmail)
1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Click **Security** → **2-Step Verification** (enable if not already)
3. Scroll to **App passwords** → Create new app password
4. Choose **Mail** and **Other (Custom name)** → Name it "Stock Planner"
5. Copy the 16-character password

### 2. Update `.env` File
```env
# Email Configuration
ENABLE_EMAIL_NOTIFICATIONS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
NOTIFICATION_EMAIL=your-email@gmail.com
```

---

## 💬 WhatsApp Notifications Setup (via Twilio)

### 1. Create Twilio Account
1. Sign up at [Twilio](https://www.twilio.com/try-twilio)
2. Get your **Account SID** and **Auth Token** from dashboard
3. Activate WhatsApp Sandbox: Console → Messaging → Try it out → WhatsApp
4. Send the code (e.g., "join shadow-moon") to **+1 415 523 8886** from your WhatsApp

### 2. Update `.env` File
```env
# WhatsApp Configuration (Twilio)
ENABLE_WHATSAPP_NOTIFICATIONS=true
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+91XXXXXXXXXX  # Your WhatsApp number with country code
```

**Note**: Twilio Sandbox is **FREE** for testing, but messages expire after 24 hours. For production, upgrade to a paid plan ($1.5/month + $0.005/message).

---

## 📱 Telegram Notifications Setup (FREE!)

### 1. Create Telegram Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow instructions
3. Choose a name (e.g., "Expense Reminder") and username (e.g., "my_expense_bot")
4. Copy the **Bot Token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID
1. Start a chat with your new bot (click the link BotFather provides)
2. Send any message (e.g., "Hello")
3. Visit this URL in your browser (replace `YOUR_BOT_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":123456789}` and copy that number

### 3. Update `.env` File
```env
# Telegram Configuration (FREE!)
ENABLE_TELEGRAM_NOTIFICATIONS=true
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

---

## 🧪 Testing Notifications

### Option 1: Web UI Test Button
1. Go to **Monthly Expenses** page
2. Click the **🔔 Test Notify** button in the top-right corner
3. Check your Email/WhatsApp/Telegram for the test notification

### Option 2: API Test (via curl)
```bash
curl -X POST http://localhost:8000/api/expenses/notify/test
```

### Option 3: Manual Trigger for Specific Expenses
```bash
curl -X POST http://localhost:8000/api/expenses/notify/send \
  -H "Content-Type: application/json" \
  -d '{"expense_ids": [1, 2, 3]}'
```

---

## ⏰ Notification Schedule

- **First Reminder**: 11:00 AM daily (Asia/Kolkata timezone)
- **Second Reminder**: 3:00 PM daily (Asia/Kolkata timezone)
- **Trigger**: Automatically checks for expenses due on the current day
- **Condition**: Only sends if expense is **NOT marked as paid**

### Why Two Reminders?
- **Morning (11 AM)**: Start your day with a reminder
- **Afternoon (3 PM)**: Second chance if you missed the morning reminder or forgot to pay

### Change Notification Times
Edit `backend/app/services/scheduler.py`:
```python
# First reminder at 11:00 AM
scheduler.add_job(
    daily_expense_reminder,
    CronTrigger(hour=11, minute=0),
    id="daily-expense-reminder-morning"
)

# Second reminder at 3:00 PM
scheduler.add_job(
    daily_expense_reminder,
    CronTrigger(hour=15, minute=0),  # 15:00 = 3 PM
    id="daily-expense-reminder-afternoon"
)
```

---

## 📊 What You'll Receive

### Email Example:
- ✅ Beautiful HTML template
- 📋 List of all due expenses
- 💰 Total amount
- 📂 Categories and descriptions

### WhatsApp/Telegram Example:
```
💰 *Expenses Due Today*
━━━━━━━━━━━━━━━━━━

📋 Total: 3 expense(s)
💵 Amount: ₹3,500

━━━━━━━━━━━━━━━━━━

*1. Internet Bill*
   📂 Bills
   💰 ₹1,500

*2. Milk Payment*
   📂 Bills
   💰 Not set

*3. Credit Card Payment - ICICI*
   📂 Payments
   💰 ₹2,000

💡 *Don't forget to mark as paid!*
```

---

## 🔧 Troubleshooting

### Email Not Sending
- ✅ Verify Gmail App Password is correct (16 characters, no spaces)
- ✅ Check 2-Step Verification is enabled on Google Account
- ✅ Try with a different email provider if Gmail blocks

### WhatsApp Not Sending
- ✅ Verify you joined the Twilio Sandbox (send join code via WhatsApp)
- ✅ Check Account SID and Auth Token are correct
- ✅ Ensure phone number includes `whatsapp:` prefix and country code

### Telegram Not Sending
- ✅ Verify you sent at least one message to your bot
- ✅ Check Bot Token is correct
- ✅ Verify Chat ID is a number, not text

### No Notifications at All
- ✅ Check if any expenses are due today (day of month matches current date)
- ✅ Verify expenses are NOT already marked as paid
- ✅ Restart Docker containers: `docker-compose restart`
- ✅ Check backend logs: `docker-compose logs api`

---

## 💡 Pro Tips

1. **Use Telegram** - It's completely FREE and very reliable!
2. **Test Early** - Set an expense due today and test notifications before relying on them
3. **Multiple Channels** - Enable all three for redundancy
4. **Mark Paid** - Always mark expenses as paid to stop getting reminders
5. **Customize Messages** - Edit `backend/app/services/notifications.py` to personalize templates

---

## 🎯 Next Steps

1. ✅ Configure at least one notification channel (Email/WhatsApp/Telegram)
2. ✅ Restart Docker: `docker-compose restart`
3. ✅ Click **Test Notify** button in Monthly Expenses
4. ✅ Set expenses with today's date to test automatic reminders
5. ✅ Enjoy never missing a payment again! 🎉

---

**Need Help?** Check backend logs for detailed error messages:
```bash
docker-compose logs -f api
```
