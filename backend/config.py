import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "LegalEase")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")

        self.debug = os.getenv(
            "DEBUG",
            "true"
        ).lower() == "true"

        self.demo_mode = os.getenv(
            "DEMO_MODE",
            "true"
        ).lower() == "true"

        self.gemini_api_key = os.getenv(
            "GOOGLE_API_KEY",
            ""
        )

        self.gemini_model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash"
        )


@lru_cache()
def get_settings():
    return Settings()