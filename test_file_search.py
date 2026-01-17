import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def create_workspace():
    print("📁 Creating workspace...")
    response = requests.post(
        f"{BASE_URL}/workspaces",
        json={"title": "File Search Test Workspace"}
    )
    workspace = response.json()
    print(f"✅ Created workspace: {workspace['id']}")
    return workspace['id']

def create_vector_store(workspace_id):
    print(f"\n📚 Creating vector store for workspace {workspace_id}...")
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/vector-stores",
        json={"name": "Research Papers"}
    )
    vector_store = response.json()
    print(f"✅ Created vector store: {vector_store['id']}")
    print(f"   OpenAI Vector Store ID: {vector_store['openai_vector_store_id']}")
    return vector_store['id']

def upload_file(workspace_id, vector_store_id, file_path):
    print(f"\n📤 Uploading file: {file_path}...")
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/workspaces/{workspace_id}/vector-stores/{vector_store_id}/files",
            files={"file": f}
        )
    
    if response.status_code == 200:
        file_info = response.json()
        print(f"✅ Uploaded file: {file_info['filename']}")
        print(f"   File ID: {file_info['id']}")
        print(f"   OpenAI File ID: {file_info['openai_file_id']}")
        print(f"   Status: {file_info['status']}")
        return file_info
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.text)
        return None

def verify_file_indexed(openai_api_key, vector_store_id, file_id, max_wait=60):
    """Poll OpenAI API to verify file is fully indexed."""
    import openai
    client = openai.OpenAI(api_key=openai_api_key)
    
    print(f"\n⏳ Verifying file indexing status...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            files = client.vector_stores.files.list(vector_store_id=vector_store_id)
            for file in files.data:
                if file.id == file_id:
                    print(f"   Status: {file.status}", end='\r')
                    if file.status == "completed":
                        print(f"\n✅ File indexing complete! ({int(time.time() - start_time)}s)")
                        return True
                    elif file.status == "failed":
                        print(f"\n❌ File indexing failed!")
                        return False
        except Exception as e:
            print(f"\n⚠️  Error checking status: {e}")
        
        time.sleep(2)
    
    print(f"\n⚠️  Timeout waiting for indexing (waited {max_wait}s)")
    return False

def list_vector_stores(workspace_id):
    print(f"\n📋 Listing vector stores...")
    response = requests.get(f"{BASE_URL}/workspaces/{workspace_id}/vector-stores")
    stores = response.json()
    print(f"✅ Found {len(stores['vector_stores'])} vector store(s)")
    for store in stores['vector_stores']:
        print(f"   - {store['name']} (ID: {store['id']})")
    return stores

def chat_with_file_search(workspace_id, message):
    print(f"\n💬 Sending chat message with file search enabled...")
    print(f"   Message: {message}")
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/chat",
        json={
            "message": message,
            "enable_file_search": True,
            "include_file_search_results": True,
            "force_web_search": False
        },
        stream=True
    )
    
    print("\n📥 Receiving response stream:")
    print("-" * 80)
    
    full_content = ""
    annotations_found = []
    file_searches = []
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('event:'):
                event_type = line_str.split(':', 1)[1].strip()
            elif line_str.startswith('data:'):
                data_str = line_str.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    if event_type == 'thinking_start':
                        print("🤔 AI is thinking...")
                    elif event_type == 'thinking_end':
                        print("✅ Thinking complete")
                    elif event_type == 'file_search_call':
                        print(f"\n🔍 File Search Executed:")
                        print(f"   ID: {data.get('file_search_id')}")
                        print(f"   Status: {data.get('status')}")
                        print(f"   Queries: {data.get('queries')}")
                        if data.get('search_results'):
                            print(f"   Results: {len(data.get('search_results'))} found")
                        file_searches.append(data)
                    elif event_type == 'content':
                        content = data.get('content', '')
                        full_content += content
                        print(content, end='', flush=True)
                        
                        if data.get('annotations'):
                            annotations_found.extend(data['annotations'])
                    elif event_type == 'done':
                        print("\n\n✅ Response complete")
                except json.JSONDecodeError:
                    pass
    
    print("-" * 80)
    
    if annotations_found:
        print(f"\n📎 Citations found: {len(annotations_found)}")
        for i, ann in enumerate(annotations_found, 1):
            print(f"   {i}. Type: {ann.get('type')}")
            print(f"      File: {ann.get('filename')}")
            print(f"      Position: {ann.get('index')}")
    
    if file_searches:
        print(f"\n🔍 File searches performed: {len(file_searches)}")
    
    return full_content, annotations_found

def main():
    print("=" * 80)
    print("🧪 FILE SEARCH TEST")
    print("=" * 80)
    
    # Load OpenAI API key
    import os
    from dotenv import load_dotenv
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return
    
    workspace_id = create_workspace()
    
    vector_store_id = create_vector_store(workspace_id)
    
    print("\n⏳ Waiting 2 seconds for vector store to initialize...")
    time.sleep(2)
    
    file_path = "Christian-et-al-2010-PPsych-SJT.pdf"
    file_info = upload_file(workspace_id, vector_store_id, file_path)
    
    if not file_info:
        print("❌ Test failed: Could not upload file")
        return
    
    # Get the vector store's OpenAI ID
    stores = list_vector_stores(workspace_id)
    openai_vector_store_id = None
    for store in stores['vector_stores']:
        if store['id'] == vector_store_id:
            openai_vector_store_id = store['openai_vector_store_id']
            break
    
    if not openai_vector_store_id:
        print("❌ Could not find OpenAI vector store ID")
        return
    
    # Verify file is fully indexed (PDFs can take 2-5 minutes)
    indexed = verify_file_indexed(
        openai_api_key,
        openai_vector_store_id,
        file_info['openai_file_id'],
        max_wait=180  # 3 minutes for large PDFs
    )
    
    if not indexed:
        print("❌ File not indexed after timeout. Cannot proceed with test.")
        print("   This PDF may be too large or there's an API issue.")
        return
    
    list_vector_stores(workspace_id)
    
    test_questions = [
        "What is this research paper about? Provide a brief summary.",
        "What are the key findings or conclusions in this paper?",
        "Who are the authors of this paper?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'=' * 80}")
        print(f"QUESTION {i}/{len(test_questions)}")
        print(f"{'=' * 80}")
        content, annotations = chat_with_file_search(workspace_id, question)
        time.sleep(2)
    
    print(f"\n{'=' * 80}")
    print("✅ FILE SEARCH TEST COMPLETE")
    print(f"{'=' * 80}")
    print(f"\n📊 Test Summary:")
    print(f"   Workspace ID: {workspace_id}")
    print(f"   Vector Store ID: {vector_store_id}")
    print(f"   File: {file_path}")
    print(f"   Questions tested: {len(test_questions)}")

if __name__ == "__main__":
    main()
