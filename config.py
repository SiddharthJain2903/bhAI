import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "SECRET_HAI")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///bhai.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Which backend answers messages: "groq" (cloud, free tier) or "ollama" (local, free forever)
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")

    # Groq (https://console.groq.com — free API key, generous free tier)
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

    
