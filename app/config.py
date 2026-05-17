from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the AI orchestrator service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    portfolio_api_url: str = "http://localhost:8080"
    portfolio_api_version: str = "v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    @property
    def portfolio_api_base(self) -> str:
        base = self.portfolio_api_url.rstrip("/")
        return f"{base}/api/{self.portfolio_api_version}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
