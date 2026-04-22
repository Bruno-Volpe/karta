from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-1.5-flash"

    # Netactica
    netactica_base_url: str = "https://preprod.netactica.com/netcoreapi"
    netactica_static_url: str = "https://static-content.netactica.io"
    netactica_username: str = "api"
    netactica_password: str = "Netactica@26"
    netactica_user_service: str = "karta"

    # Redis
    redis_url: str = "redis://localhost:6379"


settings = Settings()
