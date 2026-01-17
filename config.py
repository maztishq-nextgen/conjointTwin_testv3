import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
# Use search-enabled model for web search capability in Chat Completions
USE_WEB_SEARCH = os.getenv("USE_WEB_SEARCH", "true").lower() == "true"
SEARCH_MODEL = os.getenv("SEARCH_MODEL", "gpt-4o-search-preview")

# JWT Authentication settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "6"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Auth bypass for development - set to "true" to skip authentication
AUTH_BYPASS = os.getenv("AUTH_BYPASS", "false").lower() == "true"
DUMMY_USER_EMAIL = "dev@localhost"
DUMMY_USER_NAME = "Dev User"
