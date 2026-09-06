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
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
