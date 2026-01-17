import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def create_workspace():
    print("📁 Creating workspace...")
    response = requests.post(
        f"{BASE_URL}/workspaces",
        json={"title": "URL Fetch Test Workspace"}
    )
    workspace = response.json()
    print(f"✅ Created workspace: {workspace['id']}")
    return workspace['id']

def chat_with_url(workspace_id, message, url):
    print(f"\n💬 Sending chat message with URL...")
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
    
    print("\n📥 Receiving response stream:")
    print("-" * 80)
    
    url_fetched = False
    full_content = ""
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                data_str = line_str.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    if event_type == 'url_fetching':
                        print(f"🌐 Fetching URL: {data.get('url')}")
                    elif event_type == 'url_fetched':
                        print(f"✅ URL fetched successfully!")
                        print(f"   Title: {data.get('title')}")
                        print(f"   Content length: {data.get('content_length')} characters")
                        url_fetched = True
                    elif event_type == 'url_fetch_error':
                        print(f"❌ Failed to fetch URL: {data.get('error')}")
                    elif event_type == 'thinking_start':
                        print("🤔 AI is thinking...")
                    elif event_type == 'thinking_end':
                        print("✅ Thinking complete")
                    elif event_type == 'content':
                        content = data.get('content', '')
                        full_content += content
                        print(content, end='', flush=True)
                    elif event_type == 'done':
                        print("\n\n✅ Response complete")
                except json.JSONDecodeError:
                    pass
    
    print("-" * 80)
    return url_fetched, full_content

def main():
    print("=" * 80)
    print("🧪 URL FETCH TEST")
    print("=" * 80)
    
    workspace_id = create_workspace()
    
    # Test with a real webpage
    test_cases = [
        {
            "message": "Summarize this page in 2-3 sentences.",
            "url": "https://platform.openai.com/docs/guides/prompt-engineering"
        },
        {
            "message": "What are the main topics covered on this page?",
            "url": "https://docs.python.org/3/tutorial/index.html"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}/{len(test_cases)}")
        print(f"{'=' * 80}")
        
        url_fetched, content = chat_with_url(
            workspace_id,
            test_case["message"],
            test_case["url"]
        )
        
        print(f"\n📊 Test Result:")
        print(f"   URL fetched: {'✅ Yes' if url_fetched else '❌ No'}")
        print(f"   Response length: {len(content)} characters")
        
        if i < len(test_cases):
            import time
            time.sleep(2)
    
    print(f"\n{'=' * 80}")
    print("✅ URL FETCH TEST COMPLETE")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
