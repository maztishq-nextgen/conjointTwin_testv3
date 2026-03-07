# AGENTS.md - AI Coding Agent Guidelines

## Project Overview

This is a Python FastAPI backend for an AI-powered workspace with artifacts, chat, and real-time events. It uses SQLite for persistence, OpenAI for AI capabilities, and JWT for authentication.

## Build/Run Commands

```bash
# Setup environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# Run development server
uvicorn main:app --reload

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Test Commands

```bash
# Run all tests (server must be running on port 8000)
python test_auth.py
python test_chat_artifacts.py
python test_graph_expansion.py
python test_cross_level_connections.py
python test_reasoning_events.py
python test_streaming.py
python test_url_fetch.py
python test_url_pagination.py
python test_file_search.py
python test_explain_endpoints.py

# Run a single test file
python test_auth.py

# Note: Tests require the server running on http://127.0.0.1:8000
# Start server first: uvicorn main:app --reload
```

## Code Style Guidelines

### Imports
- Use standard library imports first, then third-party, then local
- Sort alphabetically within groups
- Use explicit imports (avoid `from module import *`)

```python
# Standard library
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Third-party
import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Local modules
from config import OPENAI_API_KEY
from schemas import WorkspaceCreate
```

### Type Hints
- Use type hints for all function parameters and return types
- Use `Optional[Type]` for nullable values
- Use `Dict[str, Any]` for flexible dicts, specific types when known

```python
def create_workspace(title: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
    ...
```

### Naming Conventions
- **Modules**: lowercase with underscores (e.g., `workspace_store.py`)
- **Classes**: PascalCase (e.g., `WorkspaceStore`, `ChatAgent`)
- **Functions**: snake_case (e.g., `get_workspace`, `format_sse_event`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `OPENAI_API_KEY`, `JWT_ALGORITHM`)
- **Private methods**: prefixed with underscore (e.g., `_init_db`, `_connect`)

### Error Handling
- Use FastAPI's `HTTPException` for API errors with appropriate status codes
- Use specific exceptions for internal logic
- Log errors appropriately with context

```python
if not workspace:
    raise HTTPException(status_code=404, detail="Workspace not found")

try:
    result = some_operation()
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### Async Patterns
- Use `async def` for route handlers and I/O operations
- Use `async for` with generators in streaming endpoints
- Use `await` for async operations

```python
async def stream_generator():
    async for event in agent.chat_stream(message):
        yield format_chat_sse(event)

return StreamingResponse(stream_generator(), media_type="text/event-stream")
```

### Pydantic Schemas
- Define all request/response models in `schemas.py`
- Use `Field()` for validation and descriptions
- Use descriptive model names ending in `Request`, `Response`, or `Base`

```python
class WorkspaceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    project_id: Optional[str] = Field(None, description="Optional project ID")
```

### Database Patterns
- Use `WorkspaceStore` class for all data operations
- Store timestamps as ISO 8601 strings in SQLite
- Use `threading.RLock()` for thread safety
- Handle migrations gracefully with try/except for ALTER TABLE

### SSE/Event Streaming
- Format events consistently with `format_sse_event()` or `format_chat_sse()`
- Include event type, id (optional), and data lines
- End with double newline (`\n\n`)

```python
def format_sse_event(event: Dict[str, Any]) -> str:
    lines = []
    if event.get("id"):
        lines.append(f"id: {event['id']}")
    if event.get("type"):
        lines.append(f"event: {event['type']}")
    for line in json.dumps(event).splitlines():
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"
```

### Configuration
- All env vars in `config.py`
- Use `python-dotenv` to load `.env` file
- Provide sensible defaults for development

### Testing
- Integration tests that hit running server
- Test files named `test_*.py`
- Print formatted output with status indicators (✅ ❌)
- Use requests library for HTTP calls

## Project Structure

```
.
├── main.py              # FastAPI app and routes
├── agent.py             # Chat agent with OpenAI integration
├── agent_responses.py   # Agent response formatting
├── llm_tools.py         # Tool definitions for AI
├── workspace_store.py   # SQLite database operations
├── schemas.py           # Pydantic models
├── auth.py              # JWT authentication
├── config.py            # Environment configuration
├── cost_tracker.py      # OpenAI cost tracking
├── requirements.txt     # Dependencies
└── test_*.py            # Test files
```

## Dependencies

Key packages:
- `fastapi>=0.95.0` - Web framework
- `uvicorn>=0.21.0` - ASGI server
- `pydantic>=2.0.0` - Data validation
- `openai>=1.0.0` - OpenAI API client
- `pyjwt>=2.8.0` - JWT handling
- `passlib[bcrypt]>=1.7.4` - Password hashing
- `python-dotenv>=1.0.0` - Environment variables

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=sk-...
```

Optional:
```
OPENAI_MODEL=gpt-4o
USE_WEB_SEARCH=true
SEARCH_MODEL=gpt-4o-search-preview
JWT_SECRET_KEY=change-in-production
ACCESS_TOKEN_EXPIRE_HOURS=6
REFRESH_TOKEN_EXPIRE_DAYS=7
AUTH_BYPASS=false  # Set true for dev without auth
```
