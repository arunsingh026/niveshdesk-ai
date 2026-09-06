import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
import httpx

class NotificationService:
    def __init__(self):
        # Email configuration
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.notification_email = os.getenv("NOTIFICATION_EMAIL")

        # WhatsApp configuration (Twilio)
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        self.twilio_whatsapp_to = os.getenv("TWILIO_WHATSAPP_TO")

        # Telegram configuration (FREE alternative)
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        # Feature flags
        self.enable_email = os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "false").lower() == "true"
        self.enable_whatsapp = os.getenv("ENABLE_WHATSAPP_NOTIFICATIONS", "false").lower() == "true"
        self.enable_telegram = os.getenv("ENABLE_TELEGRAM_NOTIFICATIONS", "false").lower() == "true"

    def send_email(self, subject: str, body: str, to_email: Optional[str] = None) -> bool:
        """Send email notification"""
        if not self.enable_email:
            print("Email notifications are disabled")
            return False

        if not all([self.smtp_user, self.smtp_password]):
            print("Email configuration is incomplete")
            return False

        try:
            recipient = to_email or self.notification_email
            if not recipient:
                print("No recipient email configured")
                return False

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = recipient

            html_part = MIMEText(body, 'html')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"Email sent successfully to {recipient}")
            return True

        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False

    def send_telegram(self, message: str) -> bool:
        """Send Telegram notification (FREE alternative to WhatsApp)"""
        if not self.enable_telegram:
            print("Telegram notifications are disabled")
            return False

        if not all([self.telegram_bot_token, self.telegram_chat_id]):
            print("Telegram credentials not configured")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = httpx.post(url, json=data, timeout=20)
            response.raise_for_status()

            print(f"Telegram message sent successfully")
            return True

        except Exception as e:
            print(f"Failed to send Telegram message: {str(e)}")
            return False

    def send_whatsapp(self, message: str, to_number: Optional[str] = None) -> bool:
        """Send WhatsApp notification via Twilio"""
        if not self.enable_whatsapp:
            print("WhatsApp notifications are disabled")
            return False

        if not all([self.twilio_account_sid, self.twilio_auth_token]):
            print("Twilio credentials not configured")
            return False

        try:
            recipient = to_number or self.twilio_whatsapp_to
            if not recipient:
                print("No recipient WhatsApp number configured")
                return False

            # Using Twilio REST API
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
            data = {
                "From": self.twilio_whatsapp_from,
                "To": recipient,
                "Body": message[:1600]  # WhatsApp message limit
            }

            response = httpx.post(
                url,
                data=data,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=20
            )
            response.raise_for_status()

            print(f"WhatsApp message sent successfully to {recipient}")
            return True

        except Exception as e:
            print(f"Failed to send WhatsApp message: {str(e)}")
            return False

    def send_stock_recommendations(self, recommendations: List[dict], budget: int) -> dict:
        """Send stock recommendations via email, WhatsApp, and Telegram"""
        buy_stocks = [r for r in recommendations if r['status'] == 'BUY']

        if not buy_stocks:
            return {"email": False, "whatsapp": False, "telegram": False, "message": "No buy recommendations"}

        # Calculate totals
        total_deploy = sum(r['deploy_amount'] for r in buy_stocks)
        reserve = budget - total_deploy

        # Prepare email content
        email_subject = f"📈 Stock Buy Recommendations - {len(buy_stocks)} Stocks"
        email_body = self._create_email_template(buy_stocks, budget, total_deploy, reserve)

        # Prepare messaging content (works for both WhatsApp and Telegram)
        message_text = self._create_message_text(buy_stocks, budget, total_deploy, reserve)

        # Send notifications
        email_sent = self.send_email(email_subject, email_body)
        whatsapp_sent = self.send_whatsapp(message_text)
        telegram_sent = self.send_telegram(message_text)

        return {
            "email": email_sent,
            "whatsapp": whatsapp_sent,
            "telegram": telegram_sent,
            "buy_count": len(buy_stocks),
            "total_deploy": total_deploy
        }

    def _create_email_template(self, buy_stocks: List[dict], budget: int, deployed: float, reserve: float) -> str:
        """Create HTML email template for stock recommendations"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f6f7f9; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 8px; margin-bottom: 24px; text-align: center; }}
                .header h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
                .summary {{ display: flex; justify-content: space-around; margin-bottom: 24px; padding: 16px; background: #f9fafb; border-radius: 8px; }}
                .summary-item {{ text-align: center; }}
                .summary-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }}
                .summary-value {{ font-size: 20px; font-weight: bold; color: #111827; margin-top: 4px; }}
                .stock-card {{ border: 1px solid #e6e8ec; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
                .stock-name {{ font-size: 18px; font-weight: bold; color: #111827; margin-bottom: 8px; }}
                .stock-details {{ font-size: 14px; color: #6b7280; line-height: 1.8; }}
                .price {{ color: #10b981; font-weight: bold; }}
                .badge {{ display: inline-block; background: #e8f7ed; color: #18733a; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: bold; }}
                .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #e5e7eb; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📈 Stock Buy Recommendations</h1>
                    <p style="margin: 0;">{len(buy_stocks)} stocks recommended for this month</p>
                </div>

                <div class="summary">
                    <div class="summary-item">
                        <div class="summary-label">Budget</div>
                        <div class="summary-value">₹{budget:,}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Deploy</div>
                        <div class="summary-value">₹{deployed:,.0f}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Reserve</div>
                        <div class="summary-value">₹{reserve:,.0f}</div>
                    </div>
                </div>
        """

        for stock in buy_stocks:
            price = stock.get('current_price')
            price_str = f"₹{price:,.2f}" if price else "N/A"
            day_change = stock.get('day_change', 0)
            change_color = "#10b981" if day_change >= 0 else "#ef4444"
            change_symbol = "+" if day_change >= 0 else ""

            html += f"""
                <div class="stock-card">
                    <div class="stock-name">
                        {stock['symbol']} - {stock['name']}
                        <span class="badge">{stock['market_cap'].upper()}</span>
                    </div>
                    <div class="stock-details">
                        <div><strong>Current Price:</strong> <span class="price">{price_str}</span>
            """

            if day_change != 0:
                html += f' <span style="color: {change_color};">({change_symbol}{day_change:.2f})</span>'

            html += f"""
                        </div>
                        <div><strong>Target Amount:</strong> ₹{stock['target_amount']:,}</div>
                        <div><strong>Quantity:</strong> {stock['quantity']} shares</div>
                        <div><strong>Deploy Amount:</strong> ₹{stock['deploy_amount']:,.0f}</div>
                    </div>
                </div>
            """

        html += f"""
                <div class="footer">
                    <p>© {datetime.now().year} Arun Kumar. Generated by Arun's Stock Planner</p>
                    <p>⚠️ Verify live NSE quotes before ordering. This app never executes trades.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _create_message_text(self, buy_stocks: List[dict], budget: int, deployed: float, reserve: float) -> str:
        """Create text message for WhatsApp/Telegram stock recommendations"""
        message = f"📈 *Arun's Stock Planner*\n"
        message += f"*Monthly Buy Recommendations*\n\n"
        message += f"💰 Budget: ₹{budget:,}\n"
        message += f"📊 Deploy: ₹{deployed:,.0f}\n"
        message += f"💵 Reserve: ₹{reserve:,.0f}\n"
        message += f"━━━━━━━━━━━━━━━━━━\n\n"

        for i, stock in enumerate(buy_stocks, 1):
            price = stock.get('current_price')
            price_str = f"₹{price:,.2f}" if price else "N/A"
            day_change = stock.get('day_change', 0)
            change_str = f" ({'+' if day_change >= 0 else ''}{day_change:.2f})" if day_change != 0 else ""

            message += f"*{i}. {stock['symbol']}*\n"
            message += f"   {stock['name']}\n"
            message += f"   💵 Price: {price_str}{change_str}\n"
            message += f"   🎯 Target: ₹{stock['target_amount']:,}\n"
            message += f"   📦 Qty: {stock['quantity']} shares\n"
            message += f"   💰 Deploy: ₹{stock['deploy_amount']:,.0f}\n\n"

        message += f"⚠️ *Verify live NSE quotes before ordering*\n"
        message += f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"

        return message

    def send_expense_reminders(self, expenses: List[dict], reminder_type: str = "due_today") -> dict:
        """Send expense reminders via email, WhatsApp, and Telegram"""
        if not expenses:
            return {"email": False, "whatsapp": False, "telegram": False, "message": "No expenses to notify"}

        # Prepare subject and content
        if reminder_type == "due_today":
            subject = f"💰 {len(expenses)} Expense(s) Due Today"
            title = "Expenses Due Today"
        elif reminder_type == "due_tomorrow":
            subject = f"⏰ {len(expenses)} Expense(s) Due Tomorrow"
            title = "Expenses Due Tomorrow"
        else:
            subject = f"📋 {len(expenses)} Upcoming Expense(s)"
            title = "Upcoming Expenses"

        email_body = self._create_expense_email_template(expenses, title)
        message_text = self._create_expense_message_text(expenses, title)

        # Send notifications
        email_sent = self.send_email(subject, email_body)
        whatsapp_sent = self.send_whatsapp(message_text)
        telegram_sent = self.send_telegram(message_text)

        return {
            "email": email_sent,
            "whatsapp": whatsapp_sent,
            "telegram": telegram_sent,
            "expense_count": len(expenses)
        }

    def _create_expense_email_template(self, expenses: List[dict], title: str) -> str:
        """Create HTML email template for expense reminders"""
        total_amount = sum(exp.get('amount', 0) or 0 for exp in expenses)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f6f7f9; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 8px; margin-bottom: 24px; text-align: center; }}
                .header h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
                .summary {{ display: flex; justify-content: space-around; margin-bottom: 24px; padding: 16px; background: #f9fafb; border-radius: 8px; }}
                .summary-item {{ text-align: center; }}
                .summary-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }}
                .summary-value {{ font-size: 20px; font-weight: bold; color: #111827; margin-top: 4px; }}
                .expense-card {{ border: 1px solid #e6e8ec; border-radius: 8px; padding: 16px; margin-bottom: 12px; background: #fafafa; }}
                .expense-name {{ font-size: 18px; font-weight: bold; color: #111827; margin-bottom: 8px; }}
                .expense-details {{ font-size: 14px; color: #6b7280; line-height: 1.8; }}
                .amount {{ color: #059669; font-weight: bold; font-size: 16px; }}
                .category {{ display: inline-block; background: #e0e7ff; color: #3730a3; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: bold; }}
                .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #e5e7eb; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💰 {title}</h1>
                    <p style="margin: 0;">{len(expenses)} expense(s) need your attention</p>
                </div>

                <div class="summary">
                    <div class="summary-item">
                        <div class="summary-label">Total Expenses</div>
                        <div class="summary-value">{len(expenses)}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Total Amount</div>
                        <div class="summary-value">₹{total_amount:,.0f}</div>
                    </div>
                </div>
        """

        for expense in expenses:
            amount_str = f"₹{expense.get('amount'):,.0f}" if expense.get('amount') else "Amount not set"
            category = expense.get('category', 'Other')
            description = expense.get('description', '')

            html += f"""
                <div class="expense-card">
                    <div class="expense-name">{expense['name']}</div>
                    <div class="expense-details">
                        <span class="category">{category}</span><br/>
                        <span class="amount">{amount_str}</span>
                        {'<br/><span style="font-size: 13px; color: #6b7280;">' + description + '</span>' if description else ''}
                    </div>
                </div>
            """

        html += f"""
                <div class="footer">
                    <p>💡 Track and manage your expenses at your dashboard</p>
                    <p>Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _create_expense_message_text(self, expenses: List[dict], title: str) -> str:
        """Create text message for expense reminders (WhatsApp/Telegram)"""
        total_amount = sum(exp.get('amount', 0) or 0 for exp in expenses)

        message = f"💰 *{title}*\n"
        message += f"━━━━━━━━━━━━━━━━━━\n\n"
        message += f"📋 Total: {len(expenses)} expense(s)\n"

        if total_amount > 0:
            message += f"💵 Amount: ₹{total_amount:,.0f}\n"

        message += f"━━━━━━━━━━━━━━━━━━\n\n"

        for i, expense in enumerate(expenses, 1):
            amount_str = f"₹{expense.get('amount'):,.0f}" if expense.get('amount') else "Not set"
            category = expense.get('category', 'Other')

            message += f"*{i}. {expense['name']}*\n"
            message += f"   📂 {category}\n"
            message += f"   💰 {amount_str}\n"

            if expense.get('description'):
                message += f"   📝 {expense['description']}\n"

            message += "\n"

        message += f"💡 *Don't forget to mark as paid!*\n"
        message += f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"

        return message

# Singleton instance
notification_service = NotificationService()
