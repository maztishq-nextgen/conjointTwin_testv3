# Artifacts Workspace API

AI-powered workspace backend with chat, artifacts, and real-time events. Similar to how Cursor/Windsurf work — you chat with an AI, it creates/edits artifacts, and a frontend can render them in real-time.

## Features

- **Chat with AI** — streaming responses with thinking indicators
- **Tool-use** — AI can create, update, delete artifacts
- **Artifacts** — versioned content (HTML, JSON, Markdown, etc.)
- **Events** — real-time SSE stream for frontend updates
- **Messages** — conversation history per workspace

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run server
uvicorn main:app --reload
```

## Endpoints

### Workspaces
- `POST /workspaces` — create workspace
- `GET /workspaces` — list workspaces
- `GET /workspaces/{id}` — get workspace

### Chat
- `POST /workspaces/{id}/chat` — chat with AI (SSE stream)
- `GET /workspaces/{id}/messages` — get chat history
- `DELETE /workspaces/{id}/messages` — clear chat history

### Artifacts
- `POST /workspaces/{id}/artifacts` — create artifact
- `GET /workspaces/{id}/artifacts` — list artifacts
- `GET /workspaces/{id}/artifacts/{artifact_id}` — get artifact content
- `PUT /workspaces/{id}/artifacts/{artifact_id}` — update artifact
- `DELETE /workspaces/{id}/artifacts/{artifact_id}` — delete artifact

### Events
- `GET /workspaces/{id}/events` — list events
- `POST /workspaces/{id}/events` — create event
- `GET /workspaces/{id}/events/stream` — SSE stream

## Quick Test

```bash
BASE_URL=http://localhost:8000

# Create workspace
WS=$(curl -sS -X POST "$BASE_URL/workspaces" \
  -H "Content-Type: application/json" \
  -d '{"title":"My Workspace"}')
echo "$WS"

WS_ID=$(echo "$WS" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

# Chat with AI (will create an artifact)
curl -N -X POST "$BASE_URL/workspaces/$WS_ID/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Create a simple HTML landing page with a hero section"}'

# List artifacts created by AI
curl -sS "$BASE_URL/workspaces/$WS_ID/artifacts"

# Stream events (in another terminal)
curl -N "$BASE_URL/workspaces/$WS_ID/events/stream"
```

## SSE Event Types

| Event | Description |
|-------|-------------|
| `workspace_created` | New workspace created |
| `artifact_created` | New artifact created |
| `artifact_updated` | Artifact content updated |
| `artifact_deleted` | Artifact deleted |
| `chat_user_message` | User sent a chat message |
| `chat_assistant_message` | AI responded |
| `tool_call` | AI called a tool |

## Chat Stream Events

When you call `/chat`, you receive SSE events:

```
event: thinking_start
data: {"type": "thinking_start", "content": ""}

event: content
data: {"type": "content", "content": "I'll create..."}

event: tool_call
data: {"type": "tool_call", "tool_name": "create_artifact", ...}

event: tool_result
data: {"type": "tool_result", "result": {"success": true, ...}}

event: done
data: {"type": "done", "content": "I've created..."}
```
