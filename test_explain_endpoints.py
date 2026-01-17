#!/usr/bin/env python3
"""Test node and edge explanation endpoints."""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def create_workspace():
    response = requests.post(f"{BASE_URL}/workspaces", json={"title": "Explain Test"})
    return response.json()['id']

def create_test_graph(workspace_id):
    """Create a sample graph for testing explanations."""
    graph_data = {
        "type": "application/vnd.graph+json",
        "title": "AI Technology Map",
        "content": json.dumps({
            "graph_type": "mind_map",
            "nodes": [
                {"id": "central_ai", "label": "Artificial Intelligence", "level": 0},
                {"id": "core_ml", "label": "Machine Learning", "level": 1},
                {"id": "core_nlp", "label": "Natural Language Processing", "level": 1},
                {"id": "branch_deep_learning", "label": "Deep Learning", "level": 2},
                {"id": "branch_transformers", "label": "Transformers", "level": 2},
                {"id": "detail_gpt", "label": "GPT Models", "level": 3},
            ],
            "edges": [
                {"id": "e1", "source": "central_ai", "target": "core_ml", "relationship_type": "contains"},
                {"id": "e2", "source": "central_ai", "target": "core_nlp", "relationship_type": "contains"},
                {"id": "e3", "source": "core_ml", "target": "branch_deep_learning", "relationship_type": "contains"},
                {"id": "e4", "source": "core_nlp", "target": "branch_transformers", "relationship_type": "contains"},
                {"id": "e5", "source": "branch_transformers", "target": "detail_gpt", "relationship_type": "contains"},
                {"id": "e6", "source": "branch_deep_learning", "target": "branch_transformers", "relationship_type": "influences"},
            ],
            "metadata": {"created_by": "test"}
        })
    }
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/artifacts",
        json=graph_data
    )
    return response.json()

def explain_node(workspace_id, artifact_id, node_id):
    """Request explanation for a node."""
    print(f"\n{'=' * 80}")
    print(f"🔍 EXPLAINING NODE: {node_id}")
    print(f"{'=' * 80}")
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/artifacts/{artifact_id}/explain-node",
        json={
            "artifact_id": artifact_id,
            "node_id": node_id
        },
        stream=True
    )
    
    print("\n📥 Streaming explanation:")
    print("-" * 80)
    
    full_content = ""
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                data_str = line_str.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    if event_type == 'thinking_start':
                        print("🤔 AI is thinking...")
                    elif event_type == 'thinking_end':
                        print("✅ Thinking complete\n")
                    elif event_type == 'content':
                        content = data.get('content', '')
                        full_content += content
                        print(content, end='', flush=True)
                    elif event_type == 'done':
                        print("\n\n✅ Explanation complete")
                    elif event_type == 'error':
                        print(f"\n❌ Error: {data.get('content')}")
                except json.JSONDecodeError:
                    pass
    
    print("-" * 80)
    return full_content

def explain_edge(workspace_id, artifact_id, source_id, target_id):
    """Request explanation for an edge."""
    print(f"\n{'=' * 80}")
    print(f"🔗 EXPLAINING EDGE: {source_id} → {target_id}")
    print(f"{'=' * 80}")
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/artifacts/{artifact_id}/explain-edge",
        json={
            "artifact_id": artifact_id,
            "source_id": source_id,
            "target_id": target_id
        },
        stream=True
    )
    
    print("\n📥 Streaming explanation:")
    print("-" * 80)
    
    full_content = ""
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                data_str = line_str.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    if event_type == 'thinking_start':
                        print("🤔 AI is thinking...")
                    elif event_type == 'thinking_end':
                        print("✅ Thinking complete\n")
                    elif event_type == 'content':
                        content = data.get('content', '')
                        full_content += content
                        print(content, end='', flush=True)
                    elif event_type == 'done':
                        print("\n\n✅ Explanation complete")
                    elif event_type == 'error':
                        print(f"\n❌ Error: {data.get('content')}")
                except json.JSONDecodeError:
                    pass
    
    print("-" * 80)
    return full_content

def main():
    print("=" * 80)
    print("🧪 NODE & EDGE EXPLANATION TEST")
    print("=" * 80)
    
    workspace_id = create_workspace()
    print(f"\n✅ Created workspace: {workspace_id}")
    
    artifact = create_test_graph(workspace_id)
    artifact_id = artifact['id']
    print(f"✅ Created artifact: {artifact_id}")
    
    time.sleep(1)
    
    # Test node explanation
    node_explanation = explain_node(workspace_id, artifact_id, "branch_transformers")
    
    time.sleep(1)
    
    # Test edge explanation (cross-level connection)
    edge_explanation = explain_edge(workspace_id, artifact_id, "branch_deep_learning", "branch_transformers")
    
    print(f"\n{'=' * 80}")
    print("📊 TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"✅ Node explanation generated: {len(node_explanation)} characters")
    print(f"✅ Edge explanation generated: {len(edge_explanation)} characters")
    print(f"\n{'=' * 80}")
    print("✅ EXPLANATION ENDPOINTS TEST COMPLETE")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
