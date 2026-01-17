#!/usr/bin/env python3
"""Test chat and artifacts endpoints."""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_workspace_creation():
    """Create a workspace for testing."""
    print("\n" + "=" * 80)
    print("📁 TEST: Create Workspace")
    print("=" * 80)
    
    response = requests.post(
        f"{BASE_URL}/workspaces",
        json={"title": "Test Workspace"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        workspace = response.json()
        print(f"✅ Workspace created: {workspace['id']}")
        return workspace
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_artifact_create(workspace_id: str):
    """Test creating an artifact."""
    print("\n" + "=" * 80)
    print("📄 TEST: Create Artifact (Graph)")
    print("=" * 80)
    
    graph_content = json.dumps({
        "graph_type": "mind_map",
        "nodes": [
            {"id": "central_test", "label": "Test Topic", "level": 0}
        ],
        "edges": [],
        "metadata": {"created_by": "test"}
    })
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/artifacts",
        json={
            "type": "application/vnd.graph+json",
            "title": "Test Mind Map",
            "content": graph_content
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        artifact = response.json()
        print(f"✅ Artifact created: {artifact['id']}")
        print(f"   Type: {artifact['type']}")
        print(f"   Title: {artifact['title']}")
        return artifact
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_artifact_list(workspace_id: str):
    """Test listing artifacts."""
    print("\n" + "=" * 80)
    print("📋 TEST: List Artifacts")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/workspaces/{workspace_id}/artifacts")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data['artifacts'])} artifacts")
        for a in data['artifacts']:
            print(f"   - {a['title']} ({a['id'][:8]}...)")
        return data['artifacts']
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_artifact_get(workspace_id: str, artifact_id: str):
    """Test getting a single artifact."""
    print("\n" + "=" * 80)
    print("🔍 TEST: Get Artifact")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/workspaces/{workspace_id}/artifacts/{artifact_id}")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        artifact = response.json()
        print(f"✅ Got artifact: {artifact['id']}")
        print(f"   Title: {artifact['title']}")
        content = json.loads(artifact['content'])
        print(f"   Nodes: {len(content.get('nodes', []))}")
        print(f"   Edges: {len(content.get('edges', []))}")
        return artifact
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_artifact_update(workspace_id: str, artifact_id: str):
    """Test updating an artifact."""
    print("\n" + "=" * 80)
    print("✏️ TEST: Update Artifact")
    print("=" * 80)
    
    updated_content = json.dumps({
        "graph_type": "mind_map",
        "nodes": [
            {"id": "central_test", "label": "Test Topic", "level": 0},
            {"id": "core_updated", "label": "Updated Node", "level": 1}
        ],
        "edges": [
            {"id": "e1", "source": "central_test", "target": "core_updated", "relationship_type": "contains"}
        ],
        "metadata": {"created_by": "test", "updated": True}
    })
    
    response = requests.put(
        f"{BASE_URL}/workspaces/{workspace_id}/artifacts/{artifact_id}",
        json={"content": updated_content}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        artifact = response.json()
        print(f"✅ Artifact updated: {artifact['id']}")
        content = json.loads(artifact['content'])
        print(f"   Nodes: {len(content.get('nodes', []))}")
        print(f"   Edges: {len(content.get('edges', []))}")
        return artifact
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_chat_stream(workspace_id: str):
    """Test chat streaming endpoint."""
    print("\n" + "=" * 80)
    print("💬 TEST: Chat Stream")
    print("=" * 80)
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/chat",
        json={"message": "Hello! What can you do?"},
        stream=True,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("📥 Streaming response:")
        print("-" * 40)
        
        events_received = 0
        content_chunks = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data:'):
                    try:
                        data = json.loads(line_str.split(':', 1)[1].strip())
                        event_type = data.get('type', 'unknown')
                        events_received += 1
                        
                        if event_type == 'thinking_start':
                            print("🤔 Thinking...")
                        elif event_type == 'thinking_end':
                            print("✅ Thinking complete")
                        elif event_type == 'content':
                            chunk = data.get('content', '')
                            content_chunks.append(chunk)
                            print(chunk, end='', flush=True)
                        elif event_type == 'done':
                            print("\n\n✅ Chat complete")
                        elif event_type == 'tool_call':
                            print(f"\n🔧 Tool call: {data.get('tool_name')}")
                        elif event_type == 'tool_result':
                            print(f"   Result received")
                    except json.JSONDecodeError:
                        pass
        
        print("-" * 40)
        print(f"✅ Received {events_received} events")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_messages_list(workspace_id: str):
    """Test listing chat messages."""
    print("\n" + "=" * 80)
    print("📝 TEST: List Messages")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/workspaces/{workspace_id}/messages")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data['messages'])} messages")
        for m in data['messages'][:5]:
            role = m['role']
            content = (m['content'] or '')[:50]
            print(f"   - [{role}] {content}...")
        return data['messages']
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_artifact_delete(workspace_id: str, artifact_id: str):
    """Test deleting an artifact."""
    print("\n" + "=" * 80)
    print("🗑️ TEST: Delete Artifact")
    print("=" * 80)
    
    response = requests.delete(f"{BASE_URL}/workspaces/{workspace_id}/artifacts/{artifact_id}")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 204:
        print(f"✅ Artifact deleted successfully")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def main():
    print("=" * 80)
    print("🧪 CHAT & ARTIFACTS TEST SUITE")
    print("=" * 80)
    
    # Create workspace
    workspace = test_workspace_creation()
    if not workspace:
        print("\n❌ Workspace creation failed, stopping tests")
        return
    
    workspace_id = workspace['id']
    
    # Test artifacts
    artifact = test_artifact_create(workspace_id)
    if artifact:
        artifact_id = artifact['id']
        test_artifact_list(workspace_id)
        test_artifact_get(workspace_id, artifact_id)
        test_artifact_update(workspace_id, artifact_id)
    
    # Test chat
    test_chat_stream(workspace_id)
    test_messages_list(workspace_id)
    
    # Cleanup - delete artifact
    if artifact:
        test_artifact_delete(workspace_id, artifact_id)
    
    print("\n" + "=" * 80)
    print("✅ ALL CHAT & ARTIFACTS TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
