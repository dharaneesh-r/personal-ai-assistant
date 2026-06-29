from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = ""
    default_model: str = "llama-3.1-8b-instant"
    chroma_db_path: str = "./data/chroma_db"
    embed_model: str = "all-MiniLM-L6-v2"

    # Security
    api_key: str = ""

    # Rate limiting
    rate_limit_default: int = 60
    rate_limit_agent: int = 10


settings = Settings()
