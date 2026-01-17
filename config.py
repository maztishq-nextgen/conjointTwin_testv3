import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
# Use search-enabled model for web search capability in Chat Completions
USE_WEB_SEARCH = os.getenv("USE_WEB_SEARCH", "true").lower() == "true"
SEARCH_MODEL = os.getenv("SEARCH_MODEL", "gpt-4o-search-preview")
