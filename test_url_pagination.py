import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def create_workspace():
    print("📁 Creating workspace...")
    response = requests.post(
        f"{BASE_URL}/workspaces",
        json={"title": "URL Pagination Test"}
    )
    workspace = response.json()
    print(f"✅ Created workspace: {workspace['id']}")
    return workspace['id']

def chat_with_url(workspace_id, message, url):
    print(f"\n💬 Sending chat message...")
    print(f"   Message: {message}")
    print(f"   URL: {url}")
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/chat",
        json={
            "message": message,
            "url": url,
            "enable_file_search": False,
            "force_web_search": False
        },
        stream=True
    )
    
    print("\n📥 Response stream:")
    print("-" * 80)
    
    chunk_info = []
    tool_calls = []
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                data_str = line_str.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    if event_type == 'url_fetched':
                        print(f"📄 Initial fetch complete")
                        print(f"   Title: {data.get('title')}")
                        total_len = data.get('total_length')
                        if total_len:
                            print(f"   Total length: {total_len:,} chars")
                    elif event_type == 'url_chunk_retrieved':
                        chunk_idx = data.get('chunk_index')
                        chunk_sz = data.get('chunk_size')
                        print(f"📑 Retrieved chunk {chunk_idx} ({chunk_sz:,} chars)")
                    elif event_type == 'tool_call':
                        tool = data.get('tool_name')
                        args = data.get('arguments', {})
                        print(f"🔧 Tool call: {tool}")
                        if args:
                            print(f"   Args: {json.dumps(args, indent=6)}")
                        tool_calls.append({"tool": tool, "args": args})
                    elif event_type == 'tool_result':
                        result = data.get('result', {})
                        if result.get('success'):
                            info = {
                                'chunk_index': result.get('chunk_index', 0),
                                'chunk_size': result.get('chunk_size', 0),
                                'total_chunks': result.get('total_chunks', 0),
                                'has_more': result.get('has_more', False),
                            }
                            chunk_info.append(info)
                            print(f"✅ Tool result:")
                            print(f"   Chunk {info['chunk_index']}/{info['total_chunks']-1}")
                            print(f"   Size: {info['chunk_size']:,} chars")
                            print(f"   Has more: {info['has_more']}")
                    elif event_type == 'content':
                        content = data.get('content', '')
                        print(content, end='', flush=True)
                    elif event_type == 'done':
                        print("\n\n✅ Complete")
                except json.JSONDecodeError:
                    pass
    
    print("-" * 80)
    return chunk_info, tool_calls

def main():
    print("=" * 80)
    print("🧪 URL PAGINATION TEST")
    print("=" * 80)
    
    workspace_id = create_workspace()
    
    # Test with a long page (Python docs index has lots of content)
    print(f"\n{'=' * 80}")
    print("TEST: Fetching large webpage with pagination")
    print(f"{'=' * 80}")
    
    chunk_info, tool_calls = chat_with_url(
        workspace_id,
        "This page is probably long. Can you tell me about the main sections? "
        "If the page has multiple chunks, fetch them to get complete information.",
        "https://en.wikipedia.org/wiki/Artificial_intelligence"
    )
    
    print(f"\n{'=' * 80}")
    print("📊 TEST RESULTS")
    print(f"{'=' * 80}")
    print(f"Total tool calls: {len(tool_calls)}")
    print(f"Chunks retrieved: {len(chunk_info)}")
    
    if chunk_info:
        first_chunk = chunk_info[0]
        print(f"\nFirst chunk info:")
        print(f"  Total chunks available: {first_chunk['total_chunks']}")
        print(f"  Chunk size: {first_chunk['chunk_size']:,} chars")
        print(f"  Has more: {first_chunk['has_more']}")
        
        if len(chunk_info) > 1:
            print(f"\n✅ AI successfully fetched {len(chunk_info)} chunks!")
            for i, info in enumerate(chunk_info):
                print(f"  Chunk {i}: {info['chunk_size']:,} chars")
        else:
            if first_chunk['has_more']:
                print(f"\n⚠️  Page has {first_chunk['total_chunks']} chunks but AI only fetched 1")
                print(f"    AI should call fetch_url again with chunk_index=1,2,etc.")
            else:
                print(f"\n✅ Single chunk page - no pagination needed")
    
    print(f"\n{'=' * 80}")
    print("✅ PAGINATION TEST COMPLETE")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
