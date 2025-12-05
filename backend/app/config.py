import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/support_tickets"
        )
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


settings = Settings()