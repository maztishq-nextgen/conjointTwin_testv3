import json as json_module
from typing import Any, Dict, List, Optional
from workspace_store import WorkspaceStore

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_graph",
            "description": "Create a new empty graph. Call this FIRST, then add nodes one by one with add_node, then add edges with add_edge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the graph",
                    },
                    "graph_type": {
                        "type": "string",
                        "enum": ["causal_loop", "mind_map", "concept_map", "systems_thinking"],
                        "description": "Type of graph",
                    },
                },
                "required": ["title", "graph_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_node",
            "description": "Add a node to the graph.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string", "description": "ID of the graph"},
                    "id": {"type": "string", "description": "Unique descriptive node ID (e.g., 'central_ai', 'core_nlp', 'branch_transformers')"},
                    "label": {"type": "string", "description": "Display label (2-5 words)"},
                    "level": {"type": "integer", "description": "Hierarchy level: 0=central topic, 1=core concepts, 2=branches, 3=details, 4+=deeper"},
                },
                "required": ["artifact_id", "id", "label", "level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_edge",
            "description": "Add a single edge/relationship. Call this multiple times, once for each relationship.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string", "description": "ID of the graph"},
                    "source": {"type": "string", "description": "Source node ID"},
                    "target": {"type": "string", "description": "Target node ID"},
                    "relationship_type": {
                        "type": "string",
                        "enum": ["causal_positive", "causal_negative", "related", "contains", "influences"],
                        "description": "causal_positive (+), causal_negative (-), related, contains, influences",
                    },
                },
                "required": ["artifact_id", "source", "target", "relationship_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish_graph",
            "description": "Call this when done adding all nodes and edges to finalize the graph layout.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string", "description": "ID of the graph"},
                },
                "required": ["artifact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_node",
            "description": "Update a node's properties in a graph artifact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string"},
                    "node_id": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["artifact_id", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_node",
            "description": "Delete a node and its connected edges from a graph artifact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string"},
                    "node_id": {"type": "string"},
                },
                "required": ["artifact_id", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_edge",
            "description": "Delete an edge from a graph artifact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string"},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                },
                "required": ["artifact_id", "source", "target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_graph",
            "description": "Get the current state of a graph artifact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string"},
                },
                "required": ["artifact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_graphs",
            "description": "List all graph artifacts in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

# For Responses API - internally-tagged function format (different from Chat Completions)
TOOL_DEFINITIONS_RESPONSES = [
    {"type": "web_search"},  # OpenAI's built-in web search
    {
        "type": "function",
        "name": "create_graph",
        "description": "Create a new empty graph. Call this FIRST, then add nodes one by one with add_node, then add edges with add_edge.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the graph"},
                "graph_type": {
                    "type": "string",
                    "enum": ["causal_loop", "mind_map", "concept_map", "systems_thinking"],
                    "description": "Type of graph",
                },
            },
            "required": ["title", "graph_type"],
        },
    },
    {
        "type": "function",
        "name": "add_node",
        "description": "Add a node to the graph. Level is used for visual hierarchy and layout positioning.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "ID of the graph"},
                "id": {"type": "string", "description": "Unique descriptive node ID (e.g., 'central_ai', 'core_nlp', 'branch_transformers')"},
                "label": {"type": "string", "description": "Display label (2-5 words)"},
                "level": {"type": "integer", "description": "Visual hierarchy level: 0=central topic, 1=core concepts, 2=branches, 3=details, 4+=deeper (used for layout only, does not restrict connections)"},
            },
            "required": ["artifact_id", "id", "label", "level"],
        },
    },
    {
        "type": "function",
        "name": "add_edge",
        "description": "Add a single edge/relationship between any two nodes. Nodes at different levels can connect (e.g., level 4 to level 2). Use 'contains' for parent-child hierarchy, and 'related', 'influences', or 'causal_*' for cross-level or lateral connections.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "ID of the graph"},
                "source": {"type": "string", "description": "Source node ID (any level)"},
                "target": {"type": "string", "description": "Target node ID (any level, can be different from source level)"},
                "relationship_type": {
                    "type": "string",
                    "enum": ["causal_positive", "causal_negative", "related", "contains", "influences"],
                    "description": "Relationship: 'contains' for hierarchy, 'related' for association (any levels), 'influences' for impact (any levels), 'causal_positive' for positive causation (any levels), 'causal_negative' for negative causation (any levels)",
                },
            },
            "required": ["artifact_id", "source", "target", "relationship_type"],
        },
    },
    {
        "type": "function",
        "name": "finish_graph",
        "description": "Call this when done adding all nodes and edges to finalize the graph layout.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "ID of the graph"},
            },
            "required": ["artifact_id"],
        },
    },
    {
        "type": "function",
        "name": "list_graphs",
        "description": "List all graph artifacts in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "type": "function",
        "name": "fetch_url",
        "description": "Fetch and extract text content from a webpage URL. Large pages are automatically split into chunks. Call with chunk_index=0 first to see total chunks available, then fetch additional chunks if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to fetch (including http:// or https://)"},
                "chunk_index": {"type": "integer", "description": "Which chunk to retrieve (0-based). Default is 0 for first chunk.", "default": 0},
                "chunk_size": {"type": "integer", "description": "Characters per chunk. Default is 15000.", "default": 15000},
            },
            "required": ["url"],
        },
    },
]


class ToolExecutor:
    """Execute LLM tool calls against the workspace store."""

    def __init__(self, store: WorkspaceStore, workspace_id: str):
        self.store = store
        self.workspace_id = workspace_id
        self.pending_events: List[Dict[str, Any]] = []  # Events to stream incrementally
        self.url_cache: Dict[str, Dict[str, Any]] = {}  # Cache fetched URLs for pagination

    def get_pending_events(self) -> List[Dict[str, Any]]:
        """Get and clear pending incremental events."""
        events = self.pending_events.copy()
        self.pending_events = []
        return events

    def _emit_incremental(self, event_type: str, data: Dict[str, Any]):
        """Queue an incremental event for streaming."""
        self.pending_events.append({"type": event_type, "data": data})

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "create_graph":
            return self._create_empty_graph(arguments)
        elif tool_name == "add_node":
            return self._add_single_node(arguments)
        elif tool_name == "add_edge":
            return self._add_single_edge(arguments)
        elif tool_name == "finish_graph":
            return self._finish_graph(arguments)
        elif tool_name == "update_node":
            return self._update_node(arguments)
        elif tool_name == "delete_node":
            return self._delete_node(arguments)
        elif tool_name == "delete_edge":
            return self._delete_edge(arguments)
        elif tool_name == "get_graph":
            return self._get_graph(arguments)
        elif tool_name == "list_graphs":
            return self._list_graphs()
        elif tool_name == "fetch_url":
            return self._fetch_url(arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _create_empty_graph(self, args: Dict[str, Any]) -> Dict[str, Any]:
        title = args.get("title", "Untitled Graph")
        graph_type = args.get("graph_type", "concept_map")

        graph_data = {
            "graph_type": graph_type,
            "nodes": [],
            "edges": [],
            "metadata": {"created_by": "assistant"},
        }

        artifact = self.store.create_artifact(
            workspace_id=self.workspace_id,
            artifact_type="application/vnd.graph+json",
            title=title,
            content=json_module.dumps(graph_data),
            created_by="assistant",
        )

        artifact_id = artifact["id"]

        self._emit_incremental("graph_created", {
            "artifact_id": artifact_id,
            "title": title,
            "graph_type": graph_type,
        })

        self.store.create_event(
            workspace_id=self.workspace_id,
            event_type="graph_created",
            artifact_id=artifact_id,
            payload={"title": title, "graph_type": graph_type},
        )

        return {
            "success": True,
            "artifact_id": artifact_id,
            "message": f"Created empty {graph_type} graph '{title}'. Now add nodes with add_node.",
        }

    def _add_single_node(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")
        node_id = args.get("id")
        label = args.get("label")
        level = args.get("level", 0)

        graph_data = self._get_graph_data(artifact_id)
        if not graph_data:
            return {"error": f"Graph not found: {artifact_id}"}

        node_data = {
            "id": node_id,
            "label": label,
            "level": level,
        }
        graph_data["nodes"].append(node_data)
        self._save_graph_data(artifact_id, graph_data)

        self._emit_incremental("node_added", {
            "artifact_id": artifact_id,
            "node": node_data,
        })

        return {"success": True, "message": f"Added L{level}: {label}"}

    def _add_single_edge(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")
        source = args.get("source")
        target = args.get("target")
        rel_type = args.get("relationship_type", "related")

        graph_data = self._get_graph_data(artifact_id)
        if not graph_data:
            return {"error": f"Graph not found: {artifact_id}"}

        edge_data = {
            "id": f"{source}_{target}",
            "source": source,
            "target": target,
            "relationship_type": rel_type,
            "label": args.get("label"),
        }
        graph_data["edges"].append(edge_data)
        self._save_graph_data(artifact_id, graph_data)

        self._emit_incremental("edge_added", {
            "artifact_id": artifact_id,
            "edge": edge_data,
        })

        symbol = "+" if rel_type == "causal_positive" else "-" if rel_type == "causal_negative" else "→"
        return {"success": True, "message": f"Added edge: {source} {symbol} {target}"}

    def _finish_graph(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")

        graph_data = self._get_graph_data(artifact_id)
        if not graph_data:
            return {"error": f"Graph not found: {artifact_id}"}

        node_count = len(graph_data.get("nodes", []))
        edge_count = len(graph_data.get("edges", []))

        self._emit_incremental("graph_complete", {
            "artifact_id": artifact_id,
            "node_count": node_count,
            "edge_count": edge_count,
        })

        return {
            "success": True,
            "message": f"Graph complete with {node_count} nodes and {edge_count} edges",
        }

    def _get_graph_data(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        artifact = self.store.get_artifact(artifact_id)
        if not artifact:
            return None
        try:
            return json_module.loads(artifact["content"])
        except json_module.JSONDecodeError:
            return None

    def _save_graph_data(self, artifact_id: str, graph_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.store.update_artifact(
            artifact_id=artifact_id,
            content=json_module.dumps(graph_data),
            created_by="assistant",
        )

    def _add_nodes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")
        new_nodes = args.get("nodes", [])

        graph_data = self._get_graph_data(artifact_id)
        if not graph_data:
            return {"error": f"Graph not found: {artifact_id}"}

        existing_ids = {n["id"] for n in graph_data.get("nodes", [])}
        added = []
        for n in new_nodes:
            if n.get("id") not in existing_ids:
                graph_data["nodes"].append({
                    "id": n.get("id"),
                    "label": n.get("label"),
                    "type": n.get("type"),
                    "description": n.get("description"),
                })
                added.append(n.get("id"))

        self._save_graph_data(artifact_id, graph_data)

        self.store.create_event(
            workspace_id=self.workspace_id,
            event_type="nodes_added",
            artifact_id=artifact_id,
            payload={"node_ids": added},
        )

        return {"success": True, "added_nodes": added, "message": f"Added {len(added)} nodes"}

    def _add_edges(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")
        new_edges = args.get("edges", [])

        graph_data = self._get_graph_data(artifact_id)
        if not graph_data:
            return {"error": f"Graph not found: {artifact_id}"}

        existing_edges = {(e["source"], e["target"]) for e in graph_data.get("edges", [])}
        added = []
        for e in new_edges:
            key = (e.get("source"), e.get("target"))
            if key not in existing_edges:
                graph_data["edges"].append({
                    "id": f"{e.get('source')}_{e.get('target')}",
                    "source": e.get("source"),
                    "target": e.get("target"),
                    "relationship_type": e.get("relationship_type", "related"),
                    "label": e.get("label"),
                })
                added.append(key)

        self._save_graph_data(artifact_id, graph_data)

        self.store.create_event(
            workspace_id=self.workspace_id,
            event_type="edges_added",
            artifact_id=artifact_id,
            payload={"edge_count": len(added)},
        )

        return {"success": True, "added_edges": len(added), "message": f"Added {len(added)} edges"}

    def _update_node(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")
        node_id = args.get("node_id")

        graph_data = self._get_graph_data(artifact_id)
        if not graph_data:
            return {"error": f"Graph not found: {artifact_id}"}

        for node in graph_data.get("nodes", []):
            if node["id"] == node_id:
                if args.get("label"):
                    node["label"] = args["label"]
                if args.get("type"):
                    node["type"] = args["type"]
                if args.get("description"):
                    node["description"] = args["description"]
                
                self._save_graph_data(artifact_id, graph_data)

                self.store.create_event(
                    workspace_id=self.workspace_id,
                    event_type="node_updated",
                    artifact_id=artifact_id,
                    payload={"node_id": node_id},
                )

                return {"success": True, "message": f"Updated node '{node_id}'"}

        return {"error": f"Node not found: {node_id}"}

    def _delete_node(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")
        node_id = args.get("node_id")

        graph_data = self._get_graph_data(artifact_id)
        if not graph_data:
            return {"error": f"Graph not found: {artifact_id}"}

        # Remove node
        graph_data["nodes"] = [n for n in graph_data.get("nodes", []) if n["id"] != node_id]
        # Remove connected edges
        graph_data["edges"] = [
            e for e in graph_data.get("edges", [])
            if e["source"] != node_id and e["target"] != node_id
        ]

        self._save_graph_data(artifact_id, graph_data)

        # Emit incremental event for UI
        self._emit_incremental("node_deleted", {
            "artifact_id": artifact_id,
            "node_id": node_id,
        })

        self.store.create_event(
            workspace_id=self.workspace_id,
            event_type="node_deleted",
            artifact_id=artifact_id,
            payload={"node_id": node_id},
        )

        return {"success": True, "message": f"Deleted node '{node_id}' and its edges"}

    def _delete_edge(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")
        source = args.get("source")
        target = args.get("target")

        graph_data = self._get_graph_data(artifact_id)
        if not graph_data:
            return {"error": f"Graph not found: {artifact_id}"}

        original_count = len(graph_data.get("edges", []))
        graph_data["edges"] = [
            e for e in graph_data.get("edges", [])
            if not (e["source"] == source and e["target"] == target)
        ]

        if len(graph_data["edges"]) == original_count:
            return {"error": f"Edge not found: {source} -> {target}"}

        self._save_graph_data(artifact_id, graph_data)

        # Emit incremental event for UI
        self._emit_incremental("edge_deleted", {
            "artifact_id": artifact_id,
            "source": source,
            "target": target,
        })

        self.store.create_event(
            workspace_id=self.workspace_id,
            event_type="edge_deleted",
            artifact_id=artifact_id,
            payload={"source": source, "target": target},
        )

        return {"success": True, "message": f"Deleted edge '{source}' -> '{target}'"}

    def _get_graph(self, args: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = args.get("artifact_id")
        artifact = self.store.get_artifact(artifact_id)
        if not artifact:
            return {"error": f"Graph not found: {artifact_id}"}

        try:
            graph_data = json_module.loads(artifact["content"])
            return {
                "id": artifact["id"],
                "title": artifact.get("title"),
                "graph_type": graph_data.get("graph_type"),
                "nodes": graph_data.get("nodes", []),
                "edges": graph_data.get("edges", []),
            }
        except json_module.JSONDecodeError:
            return {"error": "Invalid graph data"}

    def _list_graphs(self) -> Dict[str, Any]:
        artifacts = self.store.list_artifacts(self.workspace_id)
        graphs = []
        for a in artifacts:
            if a.get("type") == "application/vnd.graph+json":
                graphs.append({
                    "id": a["id"],
                    "title": a.get("title"),
                })
        return {"graphs": graphs}

    def _fetch_url(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch and extract text content from a URL with pagination support."""
        url = args.get("url")
        chunk_index = args.get("chunk_index", 0)
        chunk_size = args.get("chunk_size", 15000)
        
        if not url:
            return {"error": "No URL provided"}
        
        try:
            import requests
            from bs4 import BeautifulSoup
            import math
            
            # Check if we already have this URL cached
            if url not in self.url_cache:
                # Fetch the URL for the first time
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; WorkspaceBot/1.0)"
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Parse HTML and extract text
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text(separator='\n', strip=True)
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                full_text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Get page title
                title = soup.title.string if soup.title else "Untitled"
                
                # Cache the full content
                self.url_cache[url] = {
                    "title": title,
                    "full_text": full_text,
                    "total_length": len(full_text),
                }
                
                self._emit_incremental("url_fetched", {
                    "url": url,
                    "title": title,
                    "total_length": len(full_text),
                })
            
            # Get cached data
            cached = self.url_cache[url]
            full_text = cached["full_text"]
            title = cached["title"]
            total_length = cached["total_length"]
            
            # Calculate chunking
            total_chunks = math.ceil(total_length / chunk_size)
            
            # Validate chunk_index
            if chunk_index < 0 or chunk_index >= total_chunks:
                return {
                    "error": f"Invalid chunk_index {chunk_index}. Valid range: 0-{total_chunks - 1}",
                    "url": url,
                    "total_chunks": total_chunks,
                }
            
            # Extract the requested chunk
            start_pos = chunk_index * chunk_size
            end_pos = min(start_pos + chunk_size, total_length)
            chunk_content = full_text[start_pos:end_pos]
            
            # Emit event for chunk retrieval
            if chunk_index > 0:
                self._emit_incremental("url_chunk_retrieved", {
                    "url": url,
                    "chunk_index": chunk_index,
                    "chunk_size": len(chunk_content),
                })
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "content": chunk_content,
                "chunk_index": chunk_index,
                "chunk_size": len(chunk_content),
                "total_chunks": total_chunks,
                "total_length": total_length,
                "has_more": chunk_index < total_chunks - 1,
            }
            
        except requests.RequestException as e:
            return {
                "error": f"Failed to fetch URL: {str(e)}",
                "url": url,
            }
        except Exception as e:
            return {
                "error": f"Failed to process URL: {str(e)}",
                "url": url,
            }
