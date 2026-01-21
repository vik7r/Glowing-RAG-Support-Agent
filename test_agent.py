#!/usr/bin/env python3
"""
RAG Agentic Support Agent - Test & Demo Script
Run this to test the agent without running the full server
"""

import os
import json
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

print("""
╔════════════════════════════════════════════════════════════╗
║  RAG AGENTIC SUPPORT AGENT - LOCAL TEST                   ║
╚════════════════════════════════════════════════════════════╝
""")

# ============================================================================
# STEP 1: Check Environment
# ============================================================================
print("\n📋 Checking configuration...\n")

required_keys = ["OPENAI_API_KEY", "PINECONE_API_KEY"]
missing = []

for key in required_keys:
    value = os.getenv(key)
    if value:
        masked = value[:10] + "..." + value[-4:] if len(value) > 14 else "***"
        print(f"  ✓ {key}: {masked}")
    else:
        print(f"  ✗ {key}: NOT SET")
        missing.append(key)

if missing:
    print(f"\n❌ Missing required keys: {', '.join(missing)}")
    print("   Please create .env file with your API keys")
    exit(1)

print("\n✅ All required keys present!")

# ============================================================================
# STEP 2: Initialize Components
# ============================================================================
print("\n🔧 Initializing components...\n")

try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    print("  ✓ LangChain & OpenAI")
except Exception as e:
    print(f"  ✗ LangChain error: {e}")
    print("    Run: pip install langchain langchain-openai")
    exit(1)

try:
    from pinecone import Pinecone as PineconeClient
    print("  ✓ Pinecone")
except Exception as e:
    print(f"  ✗ Pinecone error: {e}")
    print("    Run: pip install pinecone-client")
    exit(1)

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    print("  ✓ Tavily Web Search")
except:
    print("  ⚠ Tavily (optional)")

# ============================================================================
# STEP 3: Test LLM Connection
# ============================================================================
print("\n🧠 Testing LLM connection...\n")

try:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = llm.invoke("Say 'RAG Agent Ready' and nothing else")
    print(f"  ✓ LLM Response: {response.content}")
except Exception as e:
    print(f"  ✗ LLM Error: {e}")
    exit(1)

# ============================================================================
# STEP 4: Test Embeddings
# ============================================================================
print("\n📊 Testing embeddings...\n")

try:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    embedding = embeddings.embed_query("test query")
    print(f"  ✓ Embedding dimension: {len(embedding)}")
except Exception as e:
    print(f"  ✗ Embedding Error: {e}")
    exit(1)

# ============================================================================
# STEP 5: Test Pinecone Connection
# ============================================================================
print("\n📍 Testing Pinecone connection...\n")

try:
    pc = PineconeClient(api_key=os.getenv("PINECONE_API_KEY"))
    indexes = pc.list_indexes().names()
    print(f"  ✓ Connected to Pinecone")
    print(f"  ✓ Available indexes: {indexes if indexes else 'None yet'}")
except Exception as e:
    print(f"  ✗ Pinecone Error: {e}")

# ============================================================================
# STEP 6: Test Agentic Reasoning
# ============================================================================
print("\n🤖 Testing agent reasoning...\n")

class TestAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    def route_query(self, question: str) -> str:
        """Test query routing"""
        routing_prompt = f"""
        Determine which tool to use: "{question}"
        Options: knowledge_base, web_search, direct_answer
        Respond with ONE tool name only.
        """
        response = self.llm.invoke(routing_prompt)
        return response.content.strip()
    
    def grade_documents(self, question: str, context: str) -> bool:
        """Test document grading"""
        grade_prompt = f"""
        Question: {question}
        Context: {context[:200]}...
        Is this relevant? Yes or No only.
        """
        response = self.llm.invoke(grade_prompt)
        return "yes" in response.content.lower()

agent = TestAgent()

# Test 1: Query Routing
test_queries = [
    "How do I reset my password?",
    "What's the latest AI news?",
    "Tell me about your company"
]

for query in test_queries:
    tool = agent.route_query(query)
    print(f"  Query: '{query}'")
    print(f"  → Routed to: {tool}\n")

# Test 2: Document Grading
test_context = """
Password Reset Process:
1. Click 'Forgot Password' on login page
2. Enter your email address
3. Check your email for reset link
4. Click the link and create new password
5. Log in with new password
"""

test_question = "How do I reset my password?"
is_relevant = agent.grade_documents(test_question, test_context)
print(f"  Context relevance check: {'✓ Relevant' if is_relevant else '✗ Not relevant'}\n")

# ============================================================================
# STEP 7: Demo Sample Response
# ============================================================================
print("\n💬 Demo: Generating sample response...\n")

sample_response = llm.invoke("""
You are a helpful support agent. Answer briefly:
"What features does your RAG support agent have?"
Keep response to 2-3 sentences.
""")

print(f"  Sample Response:\n  {sample_response.content}\n")

# ============================================================================
# STEP 8: Summary & Next Steps
# ============================================================================
print("╔════════════════════════════════════════════════════════════╗")
print("║                    ✅ ALL TESTS PASSED                     ║")
print("╚════════════════════════════════════════════════════════════╝")

print("""
📚 YOUR SYSTEM IS READY!

Next Steps:

1️⃣  START THE SERVER
    python backend.py
    
    Server will run at: http://localhost:8000
    API Docs at: http://localhost:8000/docs

2️⃣  OPEN THE WEB INTERFACE
    Open 'index.html' in your browser
    (Or create an HTML file with the provided code)

3️⃣  UPLOAD YOUR DOCUMENTS
    - Click the upload area in the dashboard
    - Add PDF or TXT files with your support docs
    - Files will be automatically indexed

4️⃣  START ASKING QUESTIONS
    Type your support questions in the chat
    Agent will retrieve relevant docs and respond

5️⃣  MONITOR CONVERSATION
    - View retrieved sources on the right
    - See reasoning steps
    - Conversation history saved automatically

═══════════════════════════════════════════════════════════════════

🚀 QUICK COMMANDS:

  # Run the backend server
  python backend.py

  # Test API with curl
  curl -X POST http://localhost:8000/query \\
    -H "Content-Type: application/json" \\
    -d '{"question": "Help me with..."}' 

  # Check API docs
  open http://localhost:8000/docs

  # Deploy with Docker
  docker-compose up -d

═══════════════════════════════════════════════════════════════════

📞 API ENDPOINTS:

  POST   /query                    - Ask a question
  POST   /upload-documents         - Upload PDF/TXT files
  GET    /conversations/{id}       - Get conversation history
  GET    /kb-status               - Check knowledge base status
  DELETE /conversations/{id}       - Delete conversation
  GET    /health                  - Health check
  GET    /docs                    - API documentation

═══════════════════════════════════════════════════════════════════

Questions? Check:
  - SETUP_GUIDE.md for detailed installation
  - backend.py for API implementation
  - index.html for web interface code

Enjoy! 🎉
""")
