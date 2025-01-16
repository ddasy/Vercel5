from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # OKX API Configuration
    OKX_API_KEY: str = ""
    OKX_SECRET_KEY: str = ""
    OKX_PASSPHRASE: str = ""
    OKX_API_URL: str = "https://www.okx.com"  # Production URL
    
    # Webhook Configuration
    WEBHOOK_SECRET: str = ""  # For verifying webhook signatures
    WEBHOOK_DOMAIN: str = "vercel5-mocha.vercel.app"  # Webhook receiving domain
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()
