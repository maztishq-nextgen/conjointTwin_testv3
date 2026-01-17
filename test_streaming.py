#!/usr/bin/env python3
"""Test streaming implementation with OpenAI Responses API."""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def create_workspace():
    response = requests.post(f"{BASE_URL}/workspaces", json={"title": "Streaming Test"})
    return response.json()['id']

def test_streaming_chat(workspace_id, message):
    """Test streaming chat and measure time-to-first-token."""
    print(f"\n{'=' * 80}")
    print(f"💬 Message: {message}")
    print(f"{'=' * 80}")
    
    start_time = time.time()
    first_content_time = None
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/chat",
        json={"message": message},
        stream=True
    )
    
    print("\n📥 Streaming events:")
    print("-" * 80)
    
    event_counts = {}
    full_content = ""
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                data_str = line_str.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    # Count events
                    event_counts[event_type] = event_counts.get(event_type, 0) + 1
                    
                    if event_type == 'thinking_start':
                        print("🤔 Thinking started...")
                    elif event_type == 'thinking_end':
                        print("✅ Thinking complete")
                    elif event_type == 'content':
                        content = data.get('content', '')
                        if first_content_time is None:
                            first_content_time = time.time()
                            ttft = first_content_time - start_time
                            print(f"\n⚡ Time to first token: {ttft:.2f}s")
                            print("\n📝 Content streaming:")
                        full_content += content
                        print(content, end='', flush=True)
                    elif event_type == 'tool_call':
                        tool_name = data.get('tool_name')
                        print(f"\n🔧 Tool call: {tool_name}")
                    elif event_type == 'tool_result':
                        print(f"✅ Tool result received")
                    elif event_type == 'file_search_call':
                        status = data.get('status')
                        queries = data.get('queries', [])
                        print(f"📄 File search [{status}]: {queries}")
                    elif event_type == 'done':
                        print("\n\n✅ Stream complete")
                    elif event_type == 'error':
                        print(f"\n❌ Error: {data.get('content')}")
                except json.JSONDecodeError:
                    pass
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("-" * 80)
    print(f"\n📊 Streaming Statistics:")
    print(f"   Total time: {total_time:.2f}s")
    if first_content_time:
        print(f"   Time to first token: {first_content_time - start_time:.2f}s")
    print(f"   Content length: {len(full_content)} characters")
    print(f"   Event counts:")
    for evt, count in sorted(event_counts.items()):
        print(f"      {evt}: {count}")
    
    return full_content, event_counts

def main():
    print("=" * 80)
    print("🧪 STREAMING TEST")
    print("=" * 80)
    
    workspace_id = create_workspace()
    print(f"\n✅ Created workspace: {workspace_id}")
    
    # Test 1: Simple text response
    print("\n\n" + "=" * 80)
    print("TEST 1: Simple text response (should stream)")
    print("=" * 80)
    
    content1, events1 = test_streaming_chat(
        workspace_id,
        "What are 3 benefits of exercise? Keep it brief."
    )
    
    # Verify we got streaming events
    if events1.get('content', 0) > 1:
        print("\n✅ TEST 1 PASSED: Multiple content events received (true streaming)")
    else:
        print("\n⚠️ TEST 1: Single content event (may not be streaming)")
    
    time.sleep(2)
    
    # Test 2: Graph creation (tool calls + streaming)
    print("\n\n" + "=" * 80)
    print("TEST 2: Graph creation with tool calls")
    print("=" * 80)
    
    content2, events2 = test_streaming_chat(
        workspace_id,
        "Create a simple mind map about Python with 5 nodes"
    )
    
    # Verify we got tool calls
    if events2.get('tool_call', 0) > 0:
        print(f"\n✅ TEST 2 PASSED: {events2.get('tool_call', 0)} tool calls made")
    else:
        print("\n⚠️ TEST 2: No tool calls detected")
    
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"Test 1 - Text streaming: {'✅ PASS' if events1.get('content', 0) > 1 else '⚠️ CHECK'}")
    print(f"Test 2 - Tool calls: {'✅ PASS' if events2.get('tool_call', 0) > 0 else '⚠️ CHECK'}")
    print("\n" + "=" * 80)
    print("✅ STREAMING TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
