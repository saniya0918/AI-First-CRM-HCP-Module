from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI First CRM HCP Module"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/hcp_crm"
    groq_api_key: str = ""
    groq_model: str = "gemma2-9b-it"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
