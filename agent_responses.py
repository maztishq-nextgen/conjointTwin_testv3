import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import openai

from config import OPENAI_API_KEY, OPENAI_MODEL
from cost_tracker import cost_tracker
from llm_tools import TOOL_DEFINITIONS_RESPONSES, ToolExecutor
from workspace_store import WorkspaceStore

SYSTEM_PROMPT = """You are an AI assistant that can answer questions using uploaded documents and create topic exploration mind maps.

<capabilities>
1. **Answer questions** using file_search to retrieve information from uploaded documents
2. **Create mind maps** with hierarchical structures when explicitly requested
3. **Use web_search** for current events or information not in your knowledge base
</capabilities>

<file_search_usage>
When workspace contains uploaded files, you have automatic access to file_search:
- File search retrieves relevant excerpts from documents
- Always cite sources using the provided file citations
- If search returns results, USE THEM to answer - don't say you lack information
- Synthesize information from multiple search results when needed
- Quote directly from documents when appropriate
</file_search_usage>

<question_answering_mode>
For general questions about uploaded documents:
1. File search will automatically retrieve relevant content
2. Read and synthesize the search results
3. Provide a comprehensive answer with citations
4. Quote key passages when helpful
5. If results are insufficient, acknowledge limitations
</question_answering_mode>

<mind_map_creation_mode>
When user asks to "create a mind map" or "visualize as a graph":

**Tools:**
- **web_search(query)** - Search web for current information
- **fetch_url(url, chunk_index=0, chunk_size=15000)** - Fetch and read content from a specific URL
  * Large pages are split into 15k character chunks
  * First call returns chunk 0 with total_chunks and has_more fields
  * If has_more=true, call again with chunk_index=1, 2, etc. to get remaining content
  * Example: fetch_url(url, chunk_index=0) then fetch_url(url, chunk_index=1)
- **create_graph(title, graph_type)** - Initialize mind map (call FIRST)
- **add_node(artifact_id, id, label, level)** - Add single node
  * level is for visual hierarchy (0=central, 1=core, 2=branch, 3=detail, 4+=deeper)
- **add_edge(artifact_id, source, target, relationship_type)** - Connect nodes
  * Edges can connect nodes at ANY level (e.g., level 4 can connect to level 2)
  * Use 'contains' for hierarchical parent-child relationships
  * Use 'related', 'influences', 'causal_positive', 'causal_negative' for cross-level connections
- **finish_graph(artifact_id)** - Finalize graph
- **list_graphs()** - Find existing graphs

**Workflow:**
1. Gather information (file_search or web_search if needed)
2. Plan structure: L0 (central) → L1 (core concepts) → L2 (branches) → L3 (details)
3. create_graph → get artifact_id
4. Batch add_node calls (parallelize)
5. Batch add_edge calls (parallelize)
   * Add hierarchical edges (contains) for tree structure
   * Add cross-level edges (related, influences, causal) for connections between different branches/levels
6. finish_graph

**Node Levels (for layout):**
- L0: Central node (1 node)
- L1: Core concepts (2-4 nodes)
- L2: Branches (3-6 nodes)
- L3: Details (4-8 nodes)
- L4+: Deeper details (optional)

**Relationship Types:**
- **contains**: Parent-child hierarchy (typically same or adjacent levels)
- **related**: General association (any levels)
- **influences**: One affects another (any levels)
- **causal_positive**: Causes increase/positive effect (any levels)
- **causal_negative**: Causes decrease/negative effect (any levels)

**Constraints:**
- Total nodes: 10-20
- Node labels: 2-5 words
- For follow-ups: edit existing graph
- Create cross-level connections when concepts relate across different branches

**Expanding Existing Graphs:**
When user asks to "expand on [node_name]" or "elaborate on [topic]" in context of a graph:
1. Use list_graphs() to find the relevant graph artifact_id
2. Add new nodes as children/related to the specified node
3. Connect new nodes with appropriate edges (contains for hierarchy, related/influences for associations)
4. Use finish_graph() when done
5. DO NOT just provide text explanation - actually modify the graph structure

Example: "expand on agriculture" → add nodes like "crop_types", "livestock_systems", "soil_management", etc. as children or related nodes
</mind_map_creation_mode>

<decision_logic>
- If user asks a QUESTION about documents → Answer using file search results
- If user asks to CREATE/VISUALIZE a mind map → Use graph tools
- If user asks to EXPAND/ELABORATE on a node in a graph → Use graph tools to add nodes
- If user asks about CURRENT EVENTS → Use web_search first
- Default mode: Answer questions directly, create graphs only when explicitly requested
</decision_logic>"""


class ChatAgentResponses:
    """Agent that handles chat using Responses API with web search support."""

    def __init__(self, store: WorkspaceStore, workspace_id: str):
        self.store = store
        self.workspace_id = workspace_id
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.tool_executor = ToolExecutor(store, workspace_id)

    async def chat_stream(
        self,
        user_message: str,
        url: Optional[str] = None,
        force_web_search: bool = False,
        enable_file_search: bool = True,
        max_file_search_results: Optional[int] = None,
        include_file_search_results: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        self.store.add_message(self.workspace_id, "user", content=user_message)
        
        self.store.create_event(
            workspace_id=self.workspace_id,
            event_type="chat_user_message",
            payload={"content": user_message, "url": url},
        )
        
        try:
            # If URL provided, fetch it first
            url_content = None
            if url:
                yield {"type": "url_fetching", "url": url}
                fetch_result = self.tool_executor.execute("fetch_url", {"url": url})
                
                if fetch_result.get("success"):
                    url_content = fetch_result.get("content", "")
                    yield {
                        "type": "url_fetched",
                        "url": url,
                        "title": fetch_result.get("title", ""),
                        "content_length": fetch_result.get("content_length", 0),
                    }
                else:
                    yield {
                        "type": "url_fetch_error",
                        "url": url,
                        "error": fetch_result.get("error", "Unknown error"),
                    }
            
            # Build initial input
            full_message = user_message
            if url_content:
                full_message = f"{user_message}\n\n[Content from {url}]\n{url_content}"
            
            input_items = [
                {"type": "message", "role": "system", "content": SYSTEM_PROMPT},
                {"type": "message", "role": "user", "content": full_message}
            ]
            
            # Build tools list
            tools = []
            
            # Add web_search if forced
            if force_web_search:
                tools.append({"type": "web_search"})
            
            # Add file_search if enabled and workspace has vector stores
            if enable_file_search:
                vector_stores = self.store.list_vector_stores(self.workspace_id)
                if vector_stores:
                    vector_store_ids = [vs["openai_vector_store_id"] for vs in vector_stores]
                    file_search_tool = {
                        "type": "file_search",
                        "vector_store_ids": vector_store_ids
                    }
                    if max_file_search_results is not None:
                        file_search_tool["max_num_results"] = max_file_search_results
                    tools.append(file_search_tool)
            
            # Add custom function tools
            custom_tools = [t for t in TOOL_DEFINITIONS_RESPONSES if t.get("type") not in ["web_search", "file_search"]]
            tools.extend(custom_tools)
            
            previous_response_id = None
            max_turns = 10  # Prevent infinite loops
            turn = 0
            function_call_outputs = []
            
            while turn < max_turns:
                turn += 1
                yield {"type": "thinking_start", "content": ""}
                
                # Use Responses API
                if previous_response_id and len(function_call_outputs) > 0:
                    # Continue with function outputs
                    response = self.client.responses.create(
                        model=OPENAI_MODEL,
                        previous_response_id=previous_response_id,
                        input=function_call_outputs,
                        tools=tools,
                        stream=False,
                        include=["file_search_call.results"] if include_file_search_results else None,
                    )
                elif input_items:
                    # First turn
                    response = self.client.responses.create(
                        model=OPENAI_MODEL,
                        input=input_items,
                        tools=tools,
                        stream=False,
                        include=["file_search_call.results"] if include_file_search_results else None,
                    )
                    # Clear input_items after first use
                    input_items = None
                else:
                    # Should not reach here
                    break

                yield {"type": "thinking_end", "content": ""}

                # Store response ID for next turn
                previous_response_id = response.id
                
                # Parse response output
                collected_content = ""
                has_function_calls = False
                function_call_outputs = []
                
                for output_item in response.output:
                    if output_item.type == "file_search_call":
                        yield {
                            "type": "file_search_call",
                            "file_search_id": output_item.id,
                            "status": output_item.status,
                            "queries": getattr(output_item, "queries", []),
                            "search_results": getattr(output_item, "search_results", None) if include_file_search_results else None,
                        }
                    
                    elif output_item.type == "message":
                        for content_part in output_item.content:
                            if hasattr(content_part, "text"):
                                text = content_part.text
                                collected_content += text
                                
                                annotations = getattr(content_part, "annotations", [])
                                if annotations:
                                    yield {
                                        "type": "content",
                                        "content": text,
                                        "annotations": [
                                            {
                                                "type": ann.type,
                                                "index": getattr(ann, "index", None),
                                                "file_id": getattr(ann, "file_id", None),
                                                "filename": getattr(ann, "filename", None),
                                            }
                                            for ann in annotations
                                        ]
                                    }
                                else:
                                    yield {"type": "content", "content": text}
                    
                    elif output_item.type == "function_call":
                        has_function_calls = True
                        tool_name = output_item.name
                        call_id = output_item.call_id
                        
                        # Skip web_search - OpenAI handles it
                        if tool_name == "web_search":
                            continue
                        
                        try:
                            args = json.loads(output_item.arguments)
                        except json.JSONDecodeError:
                            args = {}

                        yield {
                            "type": "tool_call",
                            "tool_name": tool_name,
                            "tool_call_id": call_id,
                            "arguments": args,
                        }

                        result = self.tool_executor.execute(tool_name, args)

                        for incremental_event in self.tool_executor.get_pending_events():
                            yield {
                                "type": incremental_event["type"],
                                **incremental_event["data"],
                            }

                        yield {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "tool_call_id": call_id,
                            "result": result,
                        }
                        
                        # Build function output for next turn
                        function_call_outputs.append({
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result)
                        })
                
                # If no function calls, we're done
                if not has_function_calls:
                    if collected_content:
                        self.store.add_message(self.workspace_id, "assistant", content=collected_content)
                        self.store.create_event(
                            workspace_id=self.workspace_id,
                            event_type="chat_assistant_message",
                            payload={"content": collected_content},
                        )
                    yield {"type": "done", "content": collected_content}
                    break
                
                # Continue with next turn using previous_response_id
                # Responses API automatically includes function outputs

        except Exception as e:
            yield {"type": "error", "content": f"Error: {str(e)}"}
            yield {"type": "thinking_end", "content": ""}

    async def explain_node_stream(
        self,
        artifact_id: str,
        node_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream explanation of a specific node in a graph."""
        try:
            # Get the graph artifact
            artifact = self.store.get_artifact(artifact_id)
            if not artifact:
                yield {"type": "error", "content": f"Artifact not found: {artifact_id}"}
                return
            
            # Parse graph data
            import json as json_module
            graph_data = json_module.loads(artifact["content"])
            
            # Find the node
            node = None
            for n in graph_data.get("nodes", []):
                if n["id"] == node_id:
                    node = n
                    break
            
            if not node:
                yield {"type": "error", "content": f"Node not found: {node_id}"}
                return
            
            # Find connected edges
            edges = graph_data.get("edges", [])
            incoming = [e for e in edges if e["target"] == node_id]
            outgoing = [e for e in edges if e["source"] == node_id]
            
            # Build context prompt
            prompt = f"""Explain this node from a {graph_data.get('graph_type', 'graph')}:

Node: {node['label']} (ID: {node_id}, Level: {node.get('level', 'unknown')})

Connected nodes:
- {len(incoming)} incoming connections: {', '.join([e['source'] for e in incoming[:5]])}
- {len(outgoing)} outgoing connections: {', '.join([e['target'] for e in outgoing[:5]])}

Provide a clear, concise explanation (2-3 sentences) of:
1. What this node represents
2. Its role in the overall structure
3. Key relationships with other nodes"""

            yield {"type": "thinking_start", "content": ""}
            
            # Call OpenAI for explanation
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant explaining graph structures."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            
            yield {"type": "thinking_end", "content": ""}
            
            full_content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {"type": "content", "content": content}
            
            yield {"type": "done", "content": full_content}
            
        except Exception as e:
            yield {"type": "error", "content": f"Error: {str(e)}"}

    async def explain_edge_stream(
        self,
        artifact_id: str,
        source_id: str,
        target_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream explanation of a specific edge/relationship in a graph."""
        try:
            # Get the graph artifact
            artifact = self.store.get_artifact(artifact_id)
            if not artifact:
                yield {"type": "error", "content": f"Artifact not found: {artifact_id}"}
                return
            
            # Parse graph data
            import json as json_module
            graph_data = json_module.loads(artifact["content"])
            
            # Find source and target nodes
            nodes = graph_data.get("nodes", [])
            source_node = next((n for n in nodes if n["id"] == source_id), None)
            target_node = next((n for n in nodes if n["id"] == target_id), None)
            
            if not source_node:
                yield {"type": "error", "content": f"Source node not found: {source_id}"}
                return
            if not target_node:
                yield {"type": "error", "content": f"Target node not found: {target_id}"}
                return
            
            # Find the edge
            edges = graph_data.get("edges", [])
            edge = next((e for e in edges if e["source"] == source_id and e["target"] == target_id), None)
            
            if not edge:
                yield {"type": "error", "content": f"Edge not found between {source_id} and {target_id}"}
                return
            
            # Build context prompt
            prompt = f"""Explain this relationship in a {graph_data.get('graph_type', 'graph')}:

Relationship: {source_node['label']} (L{source_node.get('level')}) → {target_node['label']} (L{target_node.get('level')})
Type: {edge.get('relationship_type', 'unknown')}

Provide a clear, concise explanation (2-3 sentences) of:
1. What this relationship represents
2. How the source affects or relates to the target
3. Why this connection is important in the graph structure"""

            yield {"type": "thinking_start", "content": ""}
            
            # Call OpenAI for explanation
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant explaining graph relationships."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            
            yield {"type": "thinking_end", "content": ""}
            
            full_content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {"type": "content", "content": content}
            
            yield {"type": "done", "content": full_content}
            
        except Exception as e:
            yield {"type": "error", "content": f"Error: {str(e)}"}


def format_chat_sse(event: Dict[str, Any]) -> str:
    event_type = event.get("type", "message")
    payload = json.dumps(event)
    return f"event: {event_type}\ndata: {payload}\n\n"
