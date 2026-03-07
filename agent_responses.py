import json
import time as time_module
import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

import openai

from config import OPENAI_API_KEY, OPENAI_MODEL
from cost_tracker import cost_tracker
from llm_tools import TOOL_DEFINITIONS_RESPONSES, ToolExecutor
from workspace_store import WorkspaceStore

SYSTEM_PROMPT = """You are a VISUAL KNOWLEDGE ASSISTANT. Your PRIMARY job is to create and update mind map graphs that help users visualize and understand ANY topic they ask about.

<core_behavior>
**ALWAYS CREATE OR UPDATE A MIND MAP** for user requests. This is your main function.
- New topic → Use create_graph to reset the graph with new content
- Follow-up question → Use list_graphs + add_node/add_edge to UPDATE existing graph
- Business ideas → Create a business plan mind map
- Learning topics → Create an educational mind map  
- URLs → Analyze and visualize the content as a mind map
- Questions → Answer by creating an explanatory mind map
- Problems → Create a solution/approach mind map
</core_behavior>

<follow_up_behavior>
**CRITICAL: For follow-up questions, UPDATE the existing graph instead of creating a new one:**
1. Use list_graphs() to get the current graph's artifact_id
2. Add new nodes related to the user's follow-up question
3. Connect new nodes to existing relevant nodes with edges
4. Use finish_graph() when done
5. DO NOT call create_graph for follow-ups - that resets the entire graph!

Examples of follow-up requests:
- "tell me more about X" → Add child nodes under X
- "expand on Y" → Add detail nodes around Y  
- "how does Z relate to A?" → Add edge between Z and A, possibly new nodes
- "add information about W" → Add W as new branch with children
</follow_up_behavior>

<response_style>
**Keep responses SHORT and FRIENDLY. The user sees the graph visually - don't over-explain.**

After creating/updating a graph, respond like:
- "Done! I've added [X] nodes about [topic]. Check out the new branches! 🎯"
- "Expanded! Added [brief list]. The connections show how they relate."
- "Here's your mind map! Start from the center and explore outward."

DON'T write long paragraphs explaining every node. The graph speaks for itself.
Keep it to 1-2 sentences max after graph operations.
</response_style>

<only_text_response_when>
- User explicitly says "don't create a graph" or "just text"
- User asks a simple yes/no question
- User says "thanks" or other casual conversation
</only_text_response_when>

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
**THIS IS YOUR DEFAULT MODE** - Create a mind map for every request unless explicitly told not to.

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
- **update_node(artifact_id, node_id, label, type, description)** - Edit existing node
  * Use to rename nodes, change types, or add descriptions
  * Only label, type, or description can be changed (not node_id or level)
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
- Total nodes: 10-20 for initial creation (no limit for expansions)
- Node labels: 2-5 words
- For follow-ups: edit existing graph, add as many nodes as needed
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

<systems_thinking_mode>
**When user asks for causal loops, systems thinking, or feedback analysis:**

**TWO-STEP WORKFLOW:**

**STEP 1: ANALYSIS (Read-Only)**
1. Call analyze_systems_thinking with "full_conversion" to analyze current graph
2. **REPORT findings to user WITHOUT modifying the graph:**
   - "Found X feedback loops: [list them]"
   - "Detected Y stocks and Z flows"
   - "Suggested polarities: [list edge suggestions]"
   - "Recommendations for conversion: [explain what would change]"
3. **ASK user:** "Would you like me to apply these systems thinking changes to your graph?"

**STEP 2: CONVERSION (Only if user confirms)**
4. If user says YES ("apply it", "convert it", "yes", etc.):
   - Use add_edge with `causal_positive` or `causal_negative` for key relationships
   - Add loop label nodes (e.g., "R1: Growth Loop", "B1: Regulation") 
   - Connect loop labels to loop member nodes
   - Call create_graph with same title but graph_type="causal_loop" or "systems_thinking"
   - Say "Done! Applied X changes to convert to systems thinking."

5. If user says NO or asks questions:
   - Explain what would change
   - Answer questions about the analysis
   - Wait for explicit confirmation before modifying

**Causal Loop Rules:**
- **Reinforcing (R)**: Even number of negative links (0, 2, 4...) - amplifies change
- **Balancing (B)**: Odd number of negative links (1, 3, 5...) - stabilizes/stabilizes
- **Positive (+)**: Both variables change in same direction (A↑ → B↑, A↓ → B↓)
- **Negative (-)**: Variables change in opposite directions (A↑ → B↓, A↓ → B↑)

**Example Workflow:**
User: "Show me the climate feedback loops"
→ **STEP 1:** Call analyze_systems_thinking
→ Report: "Found 0 loops currently. I can create:
   - R1: Warming Loop (Temperature → Ice Melt → Albedo → Temperature)
   - Add +/- polarity to edges
   Would you like me to apply this?"
→ User: "Yes, apply it"
→ **STEP 2:** Add causal edges, create R1 node, update graph_type
→ Result: Systems thinking diagram with labeled feedback loops!
</systems_thinking_mode>

"""


class ChatAgentResponses:
    """Agent that handles chat using Responses API with web search support."""

    def __init__(self, store: WorkspaceStore, workspace_id: str):
        self.store = store
        self.workspace_id = workspace_id
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.tool_executor = ToolExecutor(store, workspace_id)

    async def _wait_for_files_ready(
        self, 
        max_wait_seconds: int = 120,
        poll_interval: int = 5
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Wait for files in vector stores to be indexed by OpenAI.
        
        Yields status updates while polling. Returns when all files are ready
        or timeout is reached.
        """
        # Get all vector stores for this workspace
        vector_stores = self.store.list_vector_stores(self.workspace_id)
        if not vector_stores:
            return
        
        # Get all files in these vector stores
        all_files = []
        for vs in vector_stores:
            files = self.store.list_vector_store_files(vs["id"])
            all_files.extend(files)
        
        if not all_files:
            return
        
        # Check which files are still processing (recent uploads)
        files_to_check = []
        for file in all_files:
            # Check files uploaded in last 5 minutes (300 seconds)
            created_at = file.get("created_at", "")
            if created_at:
                try:
                    from datetime import datetime, timezone
                    file_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    age_seconds = (now - file_time).total_seconds()
                    if age_seconds < 300:  # File is less than 5 min old
                        files_to_check.append(file)
                except:
                    pass
        
        if not files_to_check:
            return
        
        # Poll OpenAI for file status
        start_time = time_module.time()
        files_still_processing = True
        
        while files_still_processing and (time_module.time() - start_time) < max_wait_seconds:
            files_still_processing = False
            processing_count = 0
            
            for file in files_to_check:
                try:
                    # Get file status from OpenAI
                    openai_file = self.client.files.retrieve(file["openai_file_id"])
                    if openai_file.status != "processed":
                        files_still_processing = True
                        processing_count += 1
                except Exception:
                    # If we can't check, assume it's still processing
                    files_still_processing = True
                    processing_count += 1
            
            if files_still_processing:
                # Calculate remaining time
                elapsed = int(time_module.time() - start_time)
                remaining = max(0, max_wait_seconds - elapsed)
                
                yield {
                    "type": "files_indexing",
                    "status": "in_progress",
                    "files_processing": processing_count,
                    "elapsed_seconds": elapsed,
                    "estimated_remaining": remaining
                }
                
                # Wait before checking again
                await asyncio.sleep(poll_interval)
        
        # Final status
        if files_still_processing:
            yield {
                "type": "files_indexing",
                "status": "timeout",
                "message": "Files are still processing. Proceeding without file search."
            }
        else:
            yield {
                "type": "files_indexing",
                "status": "completed",
                "message": "All files indexed and ready for search."
            }

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
            
            # Wait for files to be indexed if file search is enabled
            if enable_file_search:
                async for status_event in self._wait_for_files_ready():
                    yield status_event
            
            # Get stored response ID for conversation continuity
            stored_response_id = self.store.get_last_response_id(self.workspace_id)
            
            # If we have a previous response, use it for context (follow-up)
            # Otherwise start fresh with system prompt
            if stored_response_id:
                # Follow-up message - use previous_response_id for conversation memory
                input_items = [
                    {"type": "message", "role": "user", "content": full_message}
                ]
                conversation_response_id = stored_response_id
            else:
                # First message - include system prompt
                input_items = [
                    {"type": "message", "role": "system", "content": SYSTEM_PROMPT},
                    {"type": "message", "role": "user", "content": full_message}
                ]
                conversation_response_id = None
            
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
            final_response_id = None  # Track the final response ID to store
            
            while turn < max_turns:
                turn += 1
                yield {"type": "thinking_start", "content": ""}
                
                # Use Responses API with STREAMING
                if previous_response_id and len(function_call_outputs) > 0:
                    # Continue with function outputs
                    include_list = ["reasoning.encrypted_content"]
                    if include_file_search_results:
                        include_list.append("file_search_call.results")
                    stream = self.client.responses.create(
                        model=OPENAI_MODEL,
                        previous_response_id=previous_response_id,
                        input=function_call_outputs,
                        tools=tools,
                        stream=True,
                        reasoning={"effort": "low", "summary": "concise"},
                        include=include_list,
                    )
                elif input_items:
                    # First turn - use conversation_response_id if available for history
                    if conversation_response_id:
                        include_list = ["reasoning.encrypted_content"]
                        if include_file_search_results:
                            include_list.append("file_search_call.results")
                        stream = self.client.responses.create(
                            model=OPENAI_MODEL,
                            previous_response_id=conversation_response_id,
                            input=input_items,
                            tools=tools,
                            stream=True,
                            reasoning={"effort": "low", "summary": "concise"},
                            include=include_list,
                        )
                    else:
                        include_list = ["reasoning.encrypted_content"]
                        if include_file_search_results:
                            include_list.append("file_search_call.results")
                        stream = self.client.responses.create(
                            model=OPENAI_MODEL,
                            input=input_items,
                            tools=tools,
                            stream=True,
                            reasoning={"effort": "low", "summary": "concise"},
                            include=include_list,
                        )
                    # Clear input_items after first use
                    input_items = None
                else:
                    # Should not reach here
                    break

                yield {"type": "thinking_end", "content": ""}

                # Process streaming events
                collected_content = ""
                has_function_calls = False
                function_call_outputs = []
                current_function_calls = {}  # Track function calls being built
                file_search_queries = []
                
                for event in stream:
                    event_type = event.type
                    
                    # Response lifecycle events
                    if event_type == "response.created":
                        pass  # Response started
                    
                    elif event_type == "response.in_progress":
                        pass  # Response in progress
                    
                    elif event_type == "response.completed":
                        # Store response ID for potential next turn and conversation history
                        previous_response_id = event.response.id
                        final_response_id = event.response.id
                    
                    # Reasoning content streaming
                    elif event_type == "response.reasoning_text.delta":
                        delta = event.delta
                        yield {"type": "reasoning", "content": delta}
                    
                    elif event_type == "response.reasoning_summary_text.delta":
                        delta = event.delta
                        yield {"type": "reasoning", "content": delta}
                    
                    elif event_type == "response.reasoning_text.done":
                        pass  # Reasoning complete
                    
                    elif event_type == "response.reasoning_summary_text.done":
                        pass  # Reasoning summary complete
                    
                    # Text content streaming
                    elif event_type == "response.output_text.delta":
                        delta = event.delta
                        collected_content += delta
                        yield {"type": "content", "content": delta}
                    
                    elif event_type == "response.output_text.done":
                        pass  # Text complete
                    
                    # File search events
                    elif event_type == "response.file_search_call.in_progress":
                        yield {"type": "file_search_call", "status": "in_progress", "queries": []}
                    
                    elif event_type == "response.file_search_call.searching":
                        queries = getattr(event, "queries", [])
                        file_search_queries = queries
                        yield {"type": "file_search_call", "status": "searching", "queries": queries}
                    
                    elif event_type == "response.file_search_call.completed":
                        yield {
                            "type": "file_search_call",
                            "status": "completed",
                            "queries": file_search_queries,
                            "search_results": getattr(event, "results", None) if include_file_search_results else None,
                        }
                    
                    # Function call events
                    elif event_type == "response.output_item.added":
                        item = event.item
                        if hasattr(item, "type") and item.type == "function_call":
                            has_function_calls = True
                            current_function_calls[item.id] = {
                                "call_id": item.call_id,
                                "name": item.name,
                                "arguments": ""
                            }
                    
                    elif event_type == "response.function_call_arguments.delta":
                        item_id = event.item_id
                        if item_id in current_function_calls:
                            current_function_calls[item_id]["arguments"] += event.delta
                    
                    elif event_type == "response.function_call_arguments.done":
                        item_id = event.item_id
                        if item_id in current_function_calls:
                            fc = current_function_calls[item_id]
                            tool_name = fc["name"]
                            call_id = fc["call_id"]
                            
                            # Skip web_search - OpenAI handles it
                            if tool_name == "web_search":
                                continue
                            
                            try:
                                args = json.loads(fc["arguments"])
                            except json.JSONDecodeError:
                                args = {}
                            
                            yield {
                                "type": "tool_call",
                                "tool_name": tool_name,
                                "tool_call_id": call_id,
                                "arguments": args,
                            }
                            
                            # Execute the tool
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
                    
                    # Content part events (for annotations)
                    elif event_type == "response.content_part.done":
                        part = getattr(event, "part", None)
                        if part and hasattr(part, "annotations") and part.annotations:
                            yield {
                                "type": "annotations",
                                "annotations": [
                                    {
                                        "type": ann.type,
                                        "index": getattr(ann, "index", None),
                                        "file_id": getattr(ann, "file_id", None),
                                        "filename": getattr(ann, "filename", None),
                                    }
                                    for ann in part.annotations
                                ]
                            }
                
                # If no function calls, we're done
                if not has_function_calls:
                    if collected_content:
                        self.store.add_message(self.workspace_id, "assistant", content=collected_content)
                        self.store.create_event(
                            workspace_id=self.workspace_id,
                            event_type="chat_assistant_message",
                            payload={"content": collected_content},
                        )
                    # Store the response ID for conversation continuity (follow-up messages)
                    if final_response_id:
                        self.store.set_last_response_id(self.workspace_id, final_response_id)
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
            
            # Use Responses API for streaming - match chat_stream structure exactly
            system_prompt = "You are a helpful assistant explaining graph structures. Give clear, concise explanations in 2-3 sentences."
            stream = self.client.responses.create(
                model=OPENAI_MODEL,
                input=[
                    {"type": "message", "role": "system", "content": system_prompt},
                    {"type": "message", "role": "user", "content": prompt}
                ],
                tools=[],  # Empty tools list like chat_stream
                stream=True,
                reasoning={"effort": "low", "summary": "concise"},
                include=["reasoning.encrypted_content"]
            )
            
            yield {"type": "thinking_end", "content": ""}
            
            # Process streaming events - exact same pattern as chat_stream
            full_content = ""
            for event in stream:
                event_type = event.type
                
                # Response lifecycle events
                if event_type == "response.created":
                    pass
                elif event_type == "response.in_progress":
                    pass
                elif event_type == "response.completed":
                    pass
                
                # Reasoning content streaming
                elif event_type == "response.reasoning_text.delta":
                    delta = event.delta
                    yield {"type": "reasoning", "content": delta}
                elif event_type == "response.reasoning_summary_text.delta":
                    delta = event.delta
                    yield {"type": "reasoning", "content": delta}
                elif event_type == "response.reasoning_text.done":
                    pass
                elif event_type == "response.reasoning_summary_text.done":
                    pass

                # Text content streaming
                elif event_type == "response.output_text.delta":
                    delta = event.delta
                    full_content += delta
                    yield {"type": "content", "content": delta}
                elif event_type == "response.output_text.done":
                    pass
            
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
            
            # Use Responses API for streaming - match chat_stream structure exactly
            system_prompt = "You are a helpful assistant explaining graph relationships. Give clear, concise explanations in 2-3 sentences."
            stream = self.client.responses.create(
                model=OPENAI_MODEL,
                input=[
                    {"type": "message", "role": "system", "content": system_prompt},
                    {"type": "message", "role": "user", "content": prompt}
                ],
                tools=[],  # Empty tools list like chat_stream
                stream=True,
                reasoning={"effort": "low", "summary": "concise"},
                include=["reasoning.encrypted_content"]
            )
            
            yield {"type": "thinking_end", "content": ""}
            
            # Process streaming events - exact same pattern as chat_stream
            full_content = ""
            for event in stream:
                event_type = event.type
                
                # Response lifecycle events
                if event_type == "response.created":
                    pass
                elif event_type == "response.in_progress":
                    pass
                elif event_type == "response.completed":
                    pass
                
                # Reasoning content streaming
                elif event_type == "response.reasoning_text.delta":
                    delta = event.delta
                    yield {"type": "reasoning", "content": delta}
                elif event_type == "response.reasoning_summary_text.delta":
                    delta = event.delta
                    yield {"type": "reasoning", "content": delta}
                elif event_type == "response.reasoning_text.done":
                    pass
                elif event_type == "response.reasoning_summary_text.done":
                    pass

                # Text content streaming
                elif event_type == "response.output_text.delta":
                    delta = event.delta
                    full_content += delta
                    yield {"type": "content", "content": delta}
                elif event_type == "response.output_text.done":
                    pass
            
            yield {"type": "done", "content": full_content}
            
        except Exception as e:
            yield {"type": "error", "content": f"Error: {str(e)}"}


def format_chat_sse(event: Dict[str, Any]) -> str:
    event_type = event.get("type", "message")
    payload = json.dumps(event)
    return f"event: {event_type}\ndata: {payload}\n\n"
