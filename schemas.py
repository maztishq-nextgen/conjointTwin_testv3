from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Workspace title")
    project_id: Optional[str] = Field(None, description="Optional project ID associated with this workspace")
    owner_id: Optional[str] = Field(None, description="Optional owner identifier")


class WorkspaceResponse(BaseModel):
    id: str
    title: str
    project_id: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WorkspacesResponse(BaseModel):
    workspaces: List[WorkspaceResponse]


class ArtifactCreateRequest(BaseModel):
    type: str = Field(..., description="Artifact MIME type (e.g., text/html)")
    title: Optional[str] = Field(None, description="Optional artifact title")
    content: str = Field(..., description="Full artifact content")
    created_by: Optional[str] = Field(None, description="Optional creator identifier")


class ArtifactUpdateRequest(BaseModel):
    content: str = Field(..., description="Full artifact content")
    created_by: Optional[str] = Field(None, description="Optional creator identifier")


class ArtifactResponse(BaseModel):
    id: str
    workspace_id: str
    type: str
    title: Optional[str] = None
    content: str
    version_id: str
    created_at: datetime
    updated_at: datetime


class ArtifactSummary(BaseModel):
    id: str
    workspace_id: str
    type: str
    title: Optional[str] = None
    latest_version_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ArtifactListResponse(BaseModel):
    artifacts: List[ArtifactSummary]


class EventCreateRequest(BaseModel):
    type: str = Field(..., description="Event type")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    artifact_id: Optional[str] = Field(None, description="Associated artifact ID")


class EventResponse(BaseModel):
    id: int
    workspace_id: str
    type: str
    artifact_id: Optional[str] = None
    payload: Dict[str, Any]
    created_at: datetime


class EventListResponse(BaseModel):
    events: List[EventResponse]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to send to the AI")
    url: Optional[str] = Field(default=None, description="Optional URL for the AI to fetch and analyze")
    force_web_search: bool = Field(default=False, description="Force the AI to use web search for current information")
    enable_file_search: bool = Field(default=True, description="Enable file search in workspace vector stores")
    max_file_search_results: Optional[int] = Field(default=None, description="Maximum number of file search results to retrieve")
    include_file_search_results: bool = Field(default=False, description="Include raw file search results in response")


class ChatMessageResponse(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    created_at: datetime


class MessageListResponse(BaseModel):
    messages: List[ChatMessageResponse]


class ExplainNodeRequest(BaseModel):
    node_id: str = Field(..., description="Node ID to explain")


class ExplainEdgeRequest(BaseModel):
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")


# Authentication schemas
class UserCreate(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    name: Optional[str] = Field(None, description="User display name")


class UserLogin(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    is_active: bool = True
    total_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token to exchange for new tokens")


class GraphNode(BaseModel):
    id: str
    label: str
    type: Optional[str] = None  # e.g., "concept", "variable", "factor"
    description: Optional[str] = None
    x: Optional[float] = None  # position for rendering
    y: Optional[float] = None


class GraphEdge(BaseModel):
    id: str
    source: str  # node id
    target: str  # node id
    label: Optional[str] = None
    relationship_type: str = "related"  # "causal_positive", "causal_negative", "related", "contains", etc.
    weight: Optional[float] = None


class GraphData(BaseModel):
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    graph_type: str = "concept_map"  # "concept_map", "causal_loop", "mind_map", "systems_thinking"
    metadata: Dict[str, Any] = {}


class VectorStoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Name for the vector store")


class VectorStoreResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    openai_vector_store_id: str
    created_at: datetime


class VectorStoreListResponse(BaseModel):
    vector_stores: List[VectorStoreResponse]


class VectorStoreFileResponse(BaseModel):
    id: str
    vector_store_id: str
    openai_file_id: str
    filename: str
    status: str
    created_at: datetime


class VectorStoreFileListResponse(BaseModel):
    files: List[VectorStoreFileResponse]
