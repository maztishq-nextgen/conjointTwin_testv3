#!/usr/bin/env python3
"""Test graph expansion - AI should add nodes when asked to elaborate."""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def create_workspace():
    response = requests.post(f"{BASE_URL}/workspaces", json={"title": "Graph Expansion Test"})
    return response.json()['id']

def chat_and_stream(workspace_id, message):
    """Send chat message and collect streaming response."""
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/chat",
        json={"message": message, "force_web_search": False},
        stream=True
    )
    
    print(f"\n💬 User: {message}")
    print("🤖 Assistant: ", end='', flush=True)
    
    full_content = ""
    tool_calls = []
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                data_str = line_str.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    if event_type == 'content':
                        content = data.get('content', '')
                        full_content += content
                        print(content, end='', flush=True)
                    elif event_type == 'tool_call':
                        tool_name = data.get('tool_name')
                        args = data.get('arguments', {})
                        tool_calls.append({'tool': tool_name, 'args': args})
                        print(f"\n  🔧 Tool: {tool_name}({json.dumps(args, indent=2)})")
                except json.JSONDecodeError:
                    pass
    
    print("\n")
    return full_content, tool_calls

def get_artifact(workspace_id, artifact_id):
    """Get artifact details."""
    response = requests.get(f"{BASE_URL}/workspaces/{workspace_id}/artifacts/{artifact_id}")
    return response.json()

def main():
    print("=" * 80)
    print("🧪 GRAPH EXPANSION TEST")
    print("=" * 80)
    
    workspace_id = create_workspace()
    print(f"\n✅ Created workspace: {workspace_id}")
    
    # Step 1: Create initial graph
    print("\n" + "=" * 80)
    print("STEP 1: Create initial climate change graph")
    print("=" * 80)
    
    content1, tools1 = chat_and_stream(
        workspace_id,
        "Create a mind map about climate change with main causes and effects"
    )
    
    # Find the artifact_id from tool calls
    artifact_id = None
    for tool_call in tools1:
        if tool_call['tool'] == 'create_graph':
            # The artifact_id is returned in the result, but we can also list artifacts
            pass
    
    # Get the graph artifact
    time.sleep(2)
    artifacts_response = requests.get(f"{BASE_URL}/workspaces/{workspace_id}/artifacts")
    artifacts = artifacts_response.json()['artifacts']
    
    if artifacts:
        artifact_id = artifacts[0]['id']
        print(f"\n✅ Created graph artifact: {artifact_id}")
        
        # Show initial graph structure
        artifact = get_artifact(workspace_id, artifact_id)
        graph_data = json.loads(artifact['content'])
        print(f"\n📊 Initial graph:")
        print(f"   Nodes: {len(graph_data['nodes'])}")
        print(f"   Edges: {len(graph_data['edges'])}")
        
        initial_node_count = len(graph_data['nodes'])
        initial_edge_count = len(graph_data['edges'])
        
        # Step 2: Ask to expand on a specific node
        print("\n" + "=" * 80)
        print("STEP 2: Ask to expand on 'agriculture' node")
        print("=" * 80)
        
        content2, tools2 = chat_and_stream(
            workspace_id,
            "Can you expand on agriculture? Add nodes for crop types, livestock systems, and soil management"
        )
        
        # Check if AI used graph tools
        used_graph_tools = any(
            tool['tool'] in ['add_node', 'add_edge', 'finish_graph'] 
            for tool in tools2
        )
        
        if used_graph_tools:
            print("\n✅ AI used graph tools to expand!")
            
            # Show updated graph structure
            time.sleep(2)
            artifact = get_artifact(workspace_id, artifact_id)
            graph_data = json.loads(artifact['content'])
            
            final_node_count = len(graph_data['nodes'])
            final_edge_count = len(graph_data['edges'])
            
            print(f"\n📊 Updated graph:")
            print(f"   Nodes: {final_node_count} (was {initial_node_count}, added {final_node_count - initial_node_count})")
            print(f"   Edges: {final_edge_count} (was {initial_edge_count}, added {final_edge_count - initial_edge_count})")
            
            print(f"\n📋 New nodes added:")
            for node in graph_data['nodes']:
                print(f"   - {node['label']} (L{node.get('level', '?')})")
            
        else:
            print("\n❌ AI did NOT use graph tools - only provided text explanation")
            print("\nTool calls made:")
            for tool in tools2:
                print(f"   - {tool['tool']}")
        
        print(f"\n{'=' * 80}")
        print("📊 TEST SUMMARY")
        print(f"{'=' * 80}")
        print(f"Workspace: {workspace_id}")
        print(f"Artifact: {artifact_id}")
        print(f"Graph expansion: {'✅ SUCCESS' if used_graph_tools else '❌ FAILED'}")
        
    else:
        print("\n❌ No graph artifact found")
    
    print(f"\n{'=' * 80}")
    print("✅ GRAPH EXPANSION TEST COMPLETE")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
