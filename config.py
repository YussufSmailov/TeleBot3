from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    student_bot_token: str
    admin_bot_token: str

    database_url: str

    google_sheets_key_file: str = "credentials.json"
    google_sheet_id: str
    google_credentials_base64: str = ""

    timezone: str = "Asia/Almaty"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
