"""
Configurações centrais do YahConect.
Lê variáveis de ambiente (.env) usando python-dotenv.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "YahConect")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Sao_Paulo")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./yahconect.db")

    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "changeme")
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    GRAPH_API_VERSION: str = "v20.0"

    @property
    def graph_api_base_url(self) -> str:
        return f"https://graph.facebook.com/{self.GRAPH_API_VERSION}"


settings = Settings()
