import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import openai

from config import OPENAI_API_KEY, OPENAI_MODEL
from cost_tracker import cost_tracker
from llm_tools import TOOL_DEFINITIONS, ToolExecutor
from workspace_store import WorkspaceStore

SYSTEM_PROMPT = """You create topic exploration mind maps with hierarchical levels.

<task>
Build a hierarchical tree: L0 (central topic) → L1 (core concepts) → L2 (branches) → L3 (details) → L4+ (deeper).
If the user asks about current events or unfamiliar topics, use web_search to gather accurate information first.
</task>

<thinking_guidance>
Before taking action:
1. Think through the topic structure (2-3 sentences max)
2. Identify: central concept (L0), main pillars (L1), key branches (L2)
3. If information is needed, search first, then plan the structure
</thinking_guidance>

<tools>
**web_search(query)** - Search the web for current information
- Use when: user asks about recent events, unfamiliar topics, or current data
- Before calling: state why you need to search
- Example: "I need current information about this topic, so I'll search the web."

**create_graph(title, graph_type)** - Initialize a new mind map
- Call this FIRST to get artifact_id
- Before calling: explain the structure you'll build

**add_node(artifact_id, id, label, level)** - Add a single node
- Levels: 0=central, 1=core, 2=branch, 3=detail, 4+=deeper
- IDs: descriptive with level prefix (e.g., 'central_ai', 'core_nlp', 'branch_transformers')
- Parallelize multiple add_node calls

**add_edge(artifact_id, source, target, relationship_type)** - Connect nodes
- Call after nodes exist
- Parallelize multiple add_edge calls
- Relationships: 'contains' for hierarchies

**finish_graph(artifact_id)** - Finalize the graph
- Call last after all nodes and edges are added

**list_graphs()** - Find existing graphs for edits
</tools>

<workflow>
1. If needed: web_search → analyze results
2. Plan structure (≤3 sentences): identify L0, L1, L2 nodes
3. create_graph → get artifact_id
4. Batch add_node: L0 first, then L1, then L2, then L3 (parallel calls)
5. Batch add_edge: connect parent→child (parallel calls)
6. finish_graph
</workflow>

<levels>
- L0: Central node (1 node) - the main topic
- L1: Core concepts (2-4 nodes) - primary pillars
- L2: Branches (3-6 nodes) - subtopics under L1
- L3: Details (4-8 nodes) - specifics under L2
- L4+: Deeper details (optional)
</levels>

<constraints>
- Total nodes: 10-20
- Node labels: 2-5 words
- For follow-ups: edit existing graph, don't create new
- Before each tool call: briefly explain why (1 sentence)
</constraints>"""


class ChatAgent:
    """Agent that handles chat with tool-use loop."""

    def __init__(self, store: WorkspaceStore, workspace_id: str):
        self.store = store
        self.workspace_id = workspace_id
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.tool_executor = ToolExecutor(store, workspace_id)

    def _build_messages(self, user_message: str) -> List[Dict[str, Any]]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        history = self.store.list_messages(self.workspace_id, limit=50)
        
        # Build a map of tool_call_id to tool response for validation
        tool_responses = {}
        for msg in history:
            if msg["role"] == "tool" and msg.get("tool_call_id"):
                tool_responses[msg["tool_call_id"]] = msg
        
        i = 0
        while i < len(history):
            msg = history[i]
            
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg.get("content", "")})
            
            elif msg["role"] == "assistant":
                if msg.get("tool_calls"):
                    # Check if all tool_calls have responses
                    all_have_responses = all(
                        tc.get("id") in tool_responses 
                        for tc in msg["tool_calls"]
                    )
                    
                    if all_have_responses:
                        # Include assistant message with tool_calls
                        entry = {"role": "assistant"}
                        if msg.get("content"):
                            entry["content"] = msg["content"]
                        entry["tool_calls"] = msg["tool_calls"]
                        messages.append(entry)
                        
                        # Include corresponding tool responses
                        for tc in msg["tool_calls"]:
                            tool_msg = tool_responses[tc["id"]]
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": tool_msg.get("content", "{}"),
                            })
                    else:
                        # Skip tool_calls without responses, just include content as summary
                        if msg.get("content"):
                            messages.append({"role": "assistant", "content": msg["content"]})
                else:
                    # Regular assistant message without tool calls
                    if msg.get("content"):
                        messages.append({"role": "assistant", "content": msg["content"]})
            
            i += 1
        
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat_stream(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        self.store.add_message(self.workspace_id, "user", content=user_message)
        
        self.store.create_event(
            workspace_id=self.workspace_id,
            event_type="chat_user_message",
            payload={"content": user_message},
        )

        messages = self._build_messages(user_message)
        
        while True:
            yield {"type": "thinking_start", "content": ""}
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                stream=True,
            )

            collected_content = ""
            collected_tool_calls: List[Dict[str, Any]] = []
            current_tool_call: Optional[Dict[str, Any]] = None
            finish_reason = None

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

                if delta and delta.content:
                    collected_content += delta.content
                    yield {"type": "content", "content": delta.content}

                if delta and delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index is not None:
                            while len(collected_tool_calls) <= tc.index:
                                collected_tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            current_tool_call = collected_tool_calls[tc.index]
                        
                        if current_tool_call:
                            if tc.id:
                                current_tool_call["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    current_tool_call["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    current_tool_call["function"]["arguments"] += tc.function.arguments

            yield {"type": "thinking_end", "content": ""}

            if collected_tool_calls:
                self.store.add_message(
                    self.workspace_id,
                    "assistant",
                    content=collected_content if collected_content else None,
                    tool_calls=collected_tool_calls,
                )

                # Add assistant message with tool_calls ONCE
                messages.append({
                    "role": "assistant",
                    "content": collected_content if collected_content else None,
                    "tool_calls": collected_tool_calls,
                })

                # Process each tool call and collect results
                tool_results = []
                for tool_call in collected_tool_calls:
                    tool_name = tool_call["function"]["name"]
                    try:
                        args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    yield {
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "tool_call_id": tool_call["id"],
                        "arguments": args,
                    }

                    result = self.tool_executor.execute(tool_name, args)

                    # Stream incremental events (nodes/edges added one by one)
                    for incremental_event in self.tool_executor.get_pending_events():
                        yield {
                            "type": incremental_event["type"],
                            **incremental_event["data"],
                        }

                    yield {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "tool_call_id": tool_call["id"],
                        "result": result,
                    }

                    self.store.add_message(
                        self.workspace_id,
                        "tool",
                        content=json.dumps(result),
                        tool_call_id=tool_call["id"],
                    )

                    # Add tool response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result),
                    })

            else:
                if collected_content:
                    self.store.add_message(self.workspace_id, "assistant", content=collected_content)
                    self.store.create_event(
                        workspace_id=self.workspace_id,
                        event_type="chat_assistant_message",
                        payload={"content": collected_content},
                    )
                yield {"type": "done", "content": collected_content}
                break

            if finish_reason == "stop":
                yield {"type": "done", "content": collected_content}
                break


def format_chat_sse(event: Dict[str, Any]) -> str:
    event_type = event.get("type", "message")
    payload = json.dumps(event)
    return f"event: {event_type}\ndata: {payload}\n\n"
