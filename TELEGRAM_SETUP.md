# Telegram Notification Setup (FREE)

## Step 1: Create a Telegram Bot

1. Open Telegram app on your phone/computer
2. Search for **@BotFather**
3. Start a chat and send: `/newbot`
4. Follow instructions:
   - Bot name: `Arun Stock Planner Bot`
   - Username: `arun_stock_planner_bot` (must end with 'bot')
5. **Copy the Bot Token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Step 2: Get Your Chat ID

1. Start a chat with your new bot
2. Send any message to it (like "Hello")
3. Visit this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":123456789}` - that's your Chat ID

## Step 3: Configure Backend

Add these to your `.env` file:

```env
# Telegram Notifications (FREE)
ENABLE_TELEGRAM_NOTIFICATIONS=true
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Step 4: Restart Backend

```bash
docker compose restart api
```

## Example Configuration:

```env
ENABLE_TELEGRAM_NOTIFICATIONS=true
TELEGRAM_BOT_TOKEN=6234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
TELEGRAM_CHAT_ID=987654321
```

Done! You'll receive instant stock notifications on Telegram.
