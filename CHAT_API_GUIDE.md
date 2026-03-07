# Chat API Guide - Complete Flow Documentation

## Overview

The chat API uses Server-Sent Events (SSE) for real-time streaming responses. This enables live updates as the AI thinks, calls tools, and generates content.

## Base URL
```
http://localhost:8000
```

## Authentication

All endpoints require JWT Bearer token (except when `AUTH_BYPASS=true`):
```bash
Authorization: Bearer <access_token>
```

**Get token:**
```bash
POST /auth/login
{
  "email": "user@example.com",
  "password": "password"
}
```

## Send a Message

### Endpoint
```
POST /workspaces/{workspace_id}/chat
```

### Request Body
```json
{
  "message": "Create a mind map about climate change",
  "clear_history": false,  // Optional: clear previous messages
  "file_search": {        // Optional: enable file search
    "enabled": true,
    "vector_store_ids": ["vs_123"]
  }
}
```

### Response
**Streaming SSE** - See below for event types

## Retrieve Chat History

### Endpoint
```
GET /workspaces/{workspace_id}/messages?limit=50
```

### Response
```json
{
  "messages": [
    {
      "id": "msg_123",
      "workspace_id": "ws_456",
      "role": "user",
      "content": "Create a mind map about climate change",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "msg_124",
      "workspace_id": "ws_456",
      "role": "assistant",
      "content": "I'll create a mind map about climate change...",
      "tool_calls": "[...]",  // JSON string of tool calls made
      "created_at": "2024-01-15T10:30:05Z"
    }
  ]
}
```

### Clear History
```bash
DELETE /workspaces/{workspace_id}/messages
```

## SSE Event Types

Events are streamed in real-time as the AI processes your request.

### Event Format
```
event: <event_type>
data: <json_payload>

```

### 1. `thinking_start` / `thinking_end`
Indicates AI is processing/reasoning.
```json
// thinking_start
{ "type": "thinking_start" }

// thinking_end
{ "type": "thinking_end" }
```

**UI Action:** Show "Thinking..." indicator

### 2. `content`
Streaming text content from AI.
```json
{
  "type": "content",
  "content": "Here's your mind map..."
}
```

**UI Action:** Append to message bubble

### 3. `tool_call`
AI is calling a tool (e.g., create_graph, add_node).
```json
{
  "type": "tool_call",
  "tool_name": "add_node",
  "arguments": {
    "artifact_id": "art_123",
    "id": "climate_change",
    "label": "Climate Change",
    "level": 0
  }
}
```

**UI Action:** Show tool indicator (e.g., "🔧 Adding node...")

### 4. `tool_result`
Tool execution completed.
```json
{
  "type": "tool_result",
  "result": {
    "success": true,
    "message": "Added L0: Climate Change"
  }
}
```

**UI Action:** Show success indicator

### 5. `graph_created`
New graph initialized.
```json
{
  "type": "graph_created",
  "data": {
    "artifact_id": "art_123",
    "title": "Climate Change Mind Map",
    "graph_type": "mind_map"
  }
}
```

**UI Action:** Clear canvas, prepare for new graph

### 6. `node_added`
Node added to graph.
```json
{
  "type": "node_added",
  "data": {
    "artifact_id": "art_123",
    "node": {
      "id": "causes",
      "label": "Main Causes",
      "level": 1
    }
  }
}
```

**UI Action:** Render new node on graph

### 7. `edge_added`
Edge/connection added.
```json
{
  "type": "edge_added",
  "data": {
    "artifact_id": "art_123",
    "edge": {
      "id": "climate_change_causes",
      "source": "climate_change",
      "target": "causes",
      "relationship_type": "contains"
    }
  }
}
```

**UI Action:** Draw connection line between nodes

### 8. `node_deleted` / `edge_deleted`
Node or edge removed.
```json
{
  "type": "node_deleted",
  "data": {
    "artifact_id": "art_123",
    "node_id": "old_node"
  }
}
```

**UI Action:** Remove from canvas

### 9. `graph_complete`
Graph building finished.
```json
{
  "type": "graph_complete",
  "data": {
    "artifact_id": "art_123",
    "node_count": 20,
    "edge_count": 35
  }
}
```

**UI Action:** Finalize layout, enable interactions

### 10. `url_fetching` / `url_fetched` / `url_fetch_error`
URL content fetching status.
```json
// url_fetching
{ "type": "url_fetching", "url": "https://example.com" }

// url_fetched
{
  "type": "url_fetched",
  "url": "https://example.com",
  "title": "Example Domain",
  "chunk_index": 0,
  "total_chunks": 5
}

// url_fetch_error
{
  "type": "url_fetch_error",
  "url": "https://example.com",
  "error": "403 Forbidden"
}
```

**UI Action:** Show fetch status/progress

### 11. `file_search_call`
Searching uploaded documents.
```json
{
  "type": "file_search_call",
  "status": "searching",
  "queries": ["climate data", "temperature trends"]
}
```

**UI Action:** Show "Searching documents..."

### 12. `annotations`
File citations from search results.
```json
{
  "type": "annotations",
  "annotations": [
    { "filename": "report.pdf", "file_id": "file_123" }
  ]
}
```

**UI Action:** Display citation badges

### 14. `files_indexing`
Status updates while waiting for uploaded files to be indexed by OpenAI.

**While processing:**
```json
{
  "type": "files_indexing",
  "status": "in_progress",
  "files_processing": 2,
  "elapsed_seconds": 10,
  "estimated_remaining": 110
}
```

**When complete:**
```json
{
  "type": "files_indexing",
  "status": "completed",
  "message": "All files indexed and ready for search."
}
```

**On timeout (after 2 minutes):**
```json
{
  "type": "files_indexing",
  "status": "timeout",
  "message": "Files are still processing. Proceeding without file search."
}
```

**UI Action:** Show progress indicator "Indexing files... (10s / 120s)"

### 15. `done`
Stream complete.
```json
{ "type": "done" }
```

**UI Action:** Hide thinking indicator, enable input

## Complete Flow Example

### 1. User Sends Message
```bash
POST /workspaces/ws_123/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Create a mind map about climate change"
}
```

### 2. Receive SSE Stream
```
event: thinking_start
data: {"type": "thinking_start"}

event: tool_call
data: {"type": "tool_call", "tool_name": "create_graph", "arguments": {...}}

event: tool_result
data: {"type": "tool_result", "result": {"success": true, ...}}

event: graph_created
data: {"type": "graph_created", "data": {"artifact_id": "art_456", ...}}

event: tool_call
data: {"type": "tool_call", "tool_name": "add_node", "arguments": {...}}

event: tool_result
data: {"type": "tool_result", "result": {"success": true, ...}}

event: node_added
data: {"type": "node_added", "data": {"node": {"id": "climate", ...}}}

// ... more tool calls for nodes and edges ...

event: tool_call
data: {"type": "tool_call", "tool_name": "finish_graph", ...}

event: graph_complete
data: {"type": "graph_complete", "data": {"node_count": 20, ...}}

event: content
data: {"type": "content", "content": "Here's your climate change mind map..."}

event: done
data: {"type": "done"}
```

### 3. Fetch Updated Messages
```bash
GET /workspaces/ws_123/messages
```

## Error Handling

### HTTP Errors
- `400` - Bad Request (invalid JSON)
- `401` - Unauthorized (invalid/missing token)
- `404` - Workspace not found
- `500` - Server error

### SSE Errors
Errors stream as content:
```json
{
  "type": "content",
  "content": "Error: Rate limit exceeded"
}
```

## JavaScript Client Example

```javascript
async function sendMessage(workspaceId, message) {
  const response = await fetch(`/workspaces/${workspaceId}/chat`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const eventType = line.slice(7);
        // Next line should be data:
      } else if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        handleEvent(data);
      }
    }
  }
}

function handleEvent(event) {
  switch (event.type) {
    case 'thinking_start':
      showThinkingIndicator();
      break;
    case 'node_added':
      renderNode(event.data.node);
      break;
    case 'edge_added':
      renderEdge(event.data.edge);
      break;
    case 'content':
      appendMessage(event.content);
      break;
    case 'done':
      hideThinkingIndicator();
      break;
  }
}
```

## Key Behaviors

1. **One Graph Per Workspace** - Each workspace has exactly one graph artifact
2. **create_graph Resets** - Calling create_graph clears the existing graph
3. **Follow-ups Edit** - Subsequent messages add to/expand the existing graph
4. **Incremental Updates** - Nodes/edges stream one-by-one for live visualization
5. **Tool Results First** - AI always confirms tool execution before continuing
6. **Streaming Content** - Text content streams in real-time as it's generated

## Tips

- Always wait for `done` event before allowing new input
- Handle `url_fetch_error` gracefully (some sites block bots)
- Cache `artifact_id` from `graph_created` for follow-up requests
- Use `limit` parameter when fetching history (default 50, max 100)
- Clear history with DELETE when starting fresh topics
