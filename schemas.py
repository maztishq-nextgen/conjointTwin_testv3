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


class ChatMessageResponse(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    created_at: datetime


class MessageListResponse(BaseModel):
    messages: List[ChatMessageResponse]


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
