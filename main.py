import asyncio
import json
from typing import Any, Dict, List, Optional

import openai
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from agent_responses import ChatAgentResponses, format_chat_sse
from auth import (
    init_auth,
    hash_password,
    verify_password,
    create_tokens,
    validate_refresh_token,
    get_current_user,
    get_current_user_optional,
)
from config import OPENAI_API_KEY
from schemas import (
    ArtifactCreateRequest,
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactUpdateRequest,
    ChatRequest,
    ChatMessageResponse,
    EventCreateRequest,
    EventListResponse,
    EventResponse,
    ExplainNodeRequest,
    ExplainEdgeRequest,
    MessageListResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    VectorStoreCreate,
    VectorStoreResponse,
    VectorStoreListResponse,
    VectorStoreFileResponse,
    VectorStoreFileListResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspacesResponse,
)
from workspace_store import WorkspaceStore

app = FastAPI(
    title="Artifacts Workspace API",
    description="Backend for AI-powered workspace with artifacts, chat, and real-time events",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = WorkspaceStore()
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize auth module with store
init_auth(store)


def require_workspace(workspace_id: str) -> Dict[str, Any]:
    workspace = store.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def format_sse_event(event: Dict[str, Any]) -> str:
    event_id = event.get("id")
    event_type = event.get("type")
    payload = json.dumps(event)
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if event_type:
        lines.append(f"event: {event_type}")
    for line in payload.splitlines():
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


@app.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(request: WorkspaceCreate):
    workspace = store.create_workspace(
        title=request.title,
        project_id=request.project_id,
        owner_id=request.owner_id,
    )
    store.create_event(
        workspace_id=workspace["id"],
        event_type="workspace_created",
        payload={"title": workspace["title"], "project_id": workspace.get("project_id")},
    )
    return workspace


@app.get("/workspaces", response_model=WorkspacesResponse)
async def list_workspaces(owner_id: Optional[str] = None):
    workspaces = store.list_workspaces(owner_id=owner_id)
    return {"workspaces": workspaces}


@app.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str):
    return require_workspace(workspace_id)


@app.get("/workspaces/{workspace_id}/artifacts", response_model=ArtifactListResponse)
async def list_workspace_artifacts(workspace_id: str):
    require_workspace(workspace_id)
    artifacts = store.list_artifacts(workspace_id)
    return {"artifacts": artifacts}


@app.post("/workspaces/{workspace_id}/artifacts", response_model=ArtifactResponse)
async def create_workspace_artifact(workspace_id: str, request: ArtifactCreateRequest):
    require_workspace(workspace_id)
    artifact = store.create_artifact(
        workspace_id=workspace_id,
        artifact_type=request.type,
        title=request.title,
        content=request.content,
        created_by=request.created_by,
    )
    store.create_event(
        workspace_id=workspace_id,
        event_type="artifact_created",
        artifact_id=artifact["id"],
        payload={"type": artifact["type"], "title": artifact.get("title"), "version_id": artifact["version_id"]},
    )
    return artifact


@app.get("/workspaces/{workspace_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(workspace_id: str, artifact_id: str):
    require_workspace(workspace_id)
    artifact = store.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@app.put("/workspaces/{workspace_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(workspace_id: str, artifact_id: str, request: ArtifactUpdateRequest):
    require_workspace(workspace_id)
    artifact = store.get_artifact(artifact_id)
    if not artifact or artifact["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    updated = store.update_artifact(
        artifact_id=artifact_id,
        content=request.content,
        created_by=request.created_by,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Artifact not found")
    store.create_event(
        workspace_id=workspace_id,
        event_type="artifact_updated",
        artifact_id=updated["id"],
        payload={"version_id": updated["version_id"]},
    )
    return updated


@app.get("/workspaces/{workspace_id}/events", response_model=EventListResponse)
async def list_workspace_events(workspace_id: str, since_id: Optional[int] = None, limit: int = 100):
    require_workspace(workspace_id)
    events = store.list_events(workspace_id, since_id=since_id, limit=limit)
    return {"events": events}


@app.post("/workspaces/{workspace_id}/events", response_model=EventResponse)
async def create_workspace_event(workspace_id: str, request: EventCreateRequest):
    require_workspace(workspace_id)
    event = store.create_event(
        workspace_id=workspace_id,
        event_type=request.type,
        artifact_id=request.artifact_id,
        payload=request.payload,
    )
    return event


@app.get("/workspaces/{workspace_id}/events/stream")
async def stream_workspace_events(
    workspace_id: str,
    request: Request,
    since_id: Optional[int] = None,
):
    require_workspace(workspace_id)

    async def event_generator():
        last_id = since_id
        while True:
            if await request.is_disconnected():
                break
            events = store.list_events(workspace_id, since_id=last_id, limit=200)
            if events:
                for event in events:
                    last_id = event.get("id")
                    yield format_sse_event(event)
            else:
                yield ": keep-alive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.delete("/workspaces/{workspace_id}/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(workspace_id: str, artifact_id: str):
    require_workspace(workspace_id)
    artifact = store.get_artifact(artifact_id)
    if not artifact or artifact["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    deleted = store.delete_artifact(artifact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")
    store.create_event(
        workspace_id=workspace_id,
        event_type="artifact_deleted",
        artifact_id=artifact_id,
        payload={},
    )
    return


@app.post("/workspaces/{workspace_id}/chat")
async def chat_with_workspace(workspace_id: str, request: ChatRequest, req: Request):
    require_workspace(workspace_id)
    agent = ChatAgentResponses(store, workspace_id)

    async def stream_generator():
        async for event in agent.chat_stream(
            request.message,
            url=request.url,
            force_web_search=request.force_web_search,
            enable_file_search=request.enable_file_search,
            max_file_search_results=request.max_file_search_results,
            include_file_search_results=request.include_file_search_results,
        ):
            yield format_chat_sse(event)

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@app.get("/workspaces/{workspace_id}/messages", response_model=MessageListResponse)
async def list_workspace_messages(workspace_id: str, limit: int = 50):
    require_workspace(workspace_id)
    messages = store.list_messages(workspace_id, limit=limit)
    return {"messages": messages}


@app.delete("/workspaces/{workspace_id}/messages", status_code=204)
async def clear_workspace_messages(workspace_id: str):
    require_workspace(workspace_id)
    store.clear_messages(workspace_id)
    return


@app.post("/workspaces/{workspace_id}/vector-stores", response_model=VectorStoreResponse)
async def create_vector_store(workspace_id: str, request: VectorStoreCreate):
    require_workspace(workspace_id)
    
    vector_store = openai_client.vector_stores.create(name=request.name)
    
    db_vector_store = store.create_vector_store(
        workspace_id=workspace_id,
        name=request.name,
        openai_vector_store_id=vector_store.id,
    )
    
    store.create_event(
        workspace_id=workspace_id,
        event_type="vector_store_created",
        payload={"name": request.name, "vector_store_id": db_vector_store["id"]},
    )
    
    return db_vector_store


@app.get("/workspaces/{workspace_id}/vector-stores", response_model=VectorStoreListResponse)
async def list_vector_stores(workspace_id: str):
    require_workspace(workspace_id)
    vector_stores = store.list_vector_stores(workspace_id)
    return {"vector_stores": vector_stores}


@app.get("/workspaces/{workspace_id}/vector-stores/{vector_store_id}", response_model=VectorStoreResponse)
async def get_vector_store(workspace_id: str, vector_store_id: str):
    require_workspace(workspace_id)
    vector_store = store.get_vector_store(vector_store_id)
    if not vector_store or vector_store["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Vector store not found")
    return vector_store


@app.post("/workspaces/{workspace_id}/vector-stores/{vector_store_id}/files", response_model=VectorStoreFileResponse)
async def upload_file_to_vector_store(workspace_id: str, vector_store_id: str, file: UploadFile = File(...)):
    require_workspace(workspace_id)
    
    vector_store = store.get_vector_store(vector_store_id)
    if not vector_store or vector_store["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Vector store not found")
    
    file_content = await file.read()
    
    openai_file = openai_client.files.create(
        file=(file.filename, file_content),
        purpose="assistants"
    )
    
    openai_client.vector_stores.files.create(
        vector_store_id=vector_store["openai_vector_store_id"],
        file_id=openai_file.id
    )
    
    db_file = store.add_vector_store_file(
        vector_store_id=vector_store_id,
        openai_file_id=openai_file.id,
        filename=file.filename or "unknown",
        status="completed"
    )
    
    store.create_event(
        workspace_id=workspace_id,
        event_type="vector_store_file_uploaded",
        payload={"vector_store_id": vector_store_id, "filename": file.filename},
    )
    
    return db_file


@app.get("/workspaces/{workspace_id}/vector-stores/{vector_store_id}/files", response_model=VectorStoreFileListResponse)
async def list_vector_store_files(workspace_id: str, vector_store_id: str):
    require_workspace(workspace_id)
    
    vector_store = store.get_vector_store(vector_store_id)
    if not vector_store or vector_store["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Vector store not found")
    
    files = store.list_vector_store_files(vector_store_id)
    return {"files": files}


@app.delete("/workspaces/{workspace_id}/vector-stores/{vector_store_id}", status_code=204)
async def delete_vector_store(workspace_id: str, vector_store_id: str):
    require_workspace(workspace_id)
    
    vector_store = store.get_vector_store(vector_store_id)
    if not vector_store or vector_store["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Vector store not found")
    
    try:
        openai_client.vector_stores.delete(vector_store["openai_vector_store_id"])
    except Exception:
        pass
    
    deleted = store.delete_vector_store(vector_store_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Vector store not found")
    
    store.create_event(
        workspace_id=workspace_id,
        event_type="vector_store_deleted",
        payload={"vector_store_id": vector_store_id},
    )
    
    return


@app.post("/workspaces/{workspace_id}/artifacts/{artifact_id}/explain-node")
async def explain_node(workspace_id: str, artifact_id: str, request: ExplainNodeRequest, req: Request):
    require_workspace(workspace_id)
    
    # Verify artifact exists and belongs to workspace
    artifact = store.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact["workspace_id"] != workspace_id:
        raise HTTPException(status_code=403, detail="Artifact does not belong to workspace")
    
    agent = ChatAgentResponses(store, workspace_id)

    async def stream_generator():
        async for event in agent.explain_node_stream(
            artifact_id=request.artifact_id,
            node_id=request.node_id,
        ):
            yield format_chat_sse(event)

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@app.post("/workspaces/{workspace_id}/artifacts/{artifact_id}/explain-edge")
async def explain_edge(workspace_id: str, artifact_id: str, request: ExplainEdgeRequest, req: Request):
    require_workspace(workspace_id)
    
    # Verify artifact exists and belongs to workspace
    artifact = store.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact["workspace_id"] != workspace_id:
        raise HTTPException(status_code=403, detail="Artifact does not belong to workspace")
    
    agent = ChatAgentResponses(store, workspace_id)

    async def stream_generator():
        async for event in agent.explain_edge_stream(
            artifact_id=request.artifact_id,
            source_id=request.source_id,
            target_id=request.target_id,
        ):
            yield format_chat_sse(event)

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


# Authentication endpoints
@app.get("/auth/status")
async def auth_status():
    """Check if auth bypass is enabled."""
    from config import AUTH_BYPASS, DUMMY_USER_EMAIL
    return {"bypass": AUTH_BYPASS, "dummy_email": DUMMY_USER_EMAIL if AUTH_BYPASS else None}


@app.post("/auth/signup", response_model=UserResponse)
async def signup(request: UserCreate):
    """Register a new user."""
    # Check if user already exists
    existing = store.get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and create user
    hashed_password = hash_password(request.password)
    user = store.create_user(
        email=request.email,
        hashed_password=hashed_password,
        name=request.name,
    )
    
    return user


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: UserLogin):
    """Authenticate user and return tokens."""
    user = store.get_user_by_email(request.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    tokens = create_tokens(user["id"])
    return tokens


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: TokenRefreshRequest):
    """Exchange refresh token for new tokens."""
    user_id = validate_refresh_token(request.refresh_token)
    
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    tokens = create_tokens(user_id)
    return tokens


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user


@app.get("/")
async def root():
    return FileResponse("test-ui-graph.html")


@app.get("/test-ui-graph.html")
async def test_ui_graph():
    return FileResponse("test-ui-graph.html")
