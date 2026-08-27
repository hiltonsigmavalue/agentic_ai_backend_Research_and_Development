from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "SigmaValue PayU API"
    environment: str = "development"
    database_url: str
    payu_merchant_key: str
    payu_salt: str
    payu_payment_url: str = "https://test.payu.in/_payment"
    payu_postservice_url: str = "https://test.payu.in/merchant/postservice.php?form=2"
    public_base_url: str
    frontend_url: str = "http://localhost:3000"
    international_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
