from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str
    app_timezone: str = "Asia/Kolkata"
    monthly_budget: int = 35000
    mf_budget: int = 30000
    investment_day: int = 5
    reminder_hour: int = 9
    reminder_minute: int = 0
    dry_run_notifications: bool = True
    market_data_provider: str = "yfinance"
    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""
    whatsapp_enabled: bool = False
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_to: str = ""
    whatsapp_api_version: str = "v23.0"
    public_app_url: str = "http://localhost:5173"
    notification_cron_token: str = ""
    resend_api_key: str = ""
    resend_from: str = "NiveshDesk <onboarding@resend.dev>"
    firebase_service_account_json: str = ""
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_project_id: str = ""
    firebase_storage_bucket: str = ""
    firebase_messaging_sender_id: str = ""
    firebase_app_id: str = ""
    firebase_vapid_key: str = ""
    notification_test_cooldown_seconds: int = 10
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
