# 🤖 RAG AGENTIC SUPPORT AGENT - COMPLETE SYSTEM

**Production-Ready AI Support Agent with Retrieval-Augmented Generation, Multi-Agent Reasoning, and Real-time Web Interface**

---

## ⚡ Quick Start (3 Steps)

### Step 1: Clone & Setup

```bash
# Create project folder
mkdir rag-support-agent && cd rag-support-agent

# Copy all files from this package:
# - backend.py
# - requirements.txt
# - .env.example
# - test_agent.py
# - index.html (web interface)
# - SETUP_GUIDE.md

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Keys

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your keys:
# - OPENAI_API_KEY: https://platform.openai.com/api-keys
# - PINECONE_API_KEY: https://www.pinecone.io
# - TAVILY_API_KEY: https://tavily.com
```

### Step 3: Run & Test

```bash
# Test your setup
python test_agent.py

# Start the backend server
python backend.py

# In another terminal, open the web interface
# Open index.html in your browser
```

Done! 🎉 Start chatting with your AI support agent!

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB INTERFACE                            │
│         (HTML/JS Dashboard with Real-time Chat)            │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                  FASTAPI BACKEND                            │
│  (REST API with LangChain & Agentic Reasoning)             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          AGENTIC REASONING ENGINE                    │  │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐   │  │
│  │  │ Query      │→ │ Route to   │→ │ Execute      │   │  │
│  │  │ Router     │  │ Tools      │  │ Selected     │   │  │
│  │  └────────────┘  └────────────┘  │ Tool         │   │  │
│  │                                   └──────┬───────┘   │  │
│  └────────────────────────────────────────┬─────────────┘  │
│                                           ↓                 │
│  ┌───────────────────┬────────────────────────────┐        │
│  │                   ↓                            ↓        │
│  ▼              ▼                           ▼             │
│ ┌─────────┐ ┌──────────────┐ ┌──────────────────┐ ┌────┐ │
│ │Knowledge│ │Web Search    │ │Customer Database │ │...│ │
│ │Base     │ │(Tavily)      │ │(Mock/Real)       │ │ToolS│ │
│ │Retriever│ │              │ │                  │ │    │ │
│ └────┬────┘ └──────────────┘ └──────────────────┘ └────┘ │
│      │                                                      │
│  ┌───▼──────────────────────────────────────────────────┐ │
│  │    DOCUMENT GRADING & RELEVANCE CHECK               │ │
│  │    (Validates retrieved context quality)            │ │
│  └────────┬─────────────────────────────────────────────┘ │
│           │                                                 │
│  ┌────────▼──────────────────────────────────────────────┐ │
│  │        LLM RESPONSE GENERATION                        │ │
│  │   (Context-Augmented Answer with Citations)          │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                    ↑
                    │
    ┌───────────────┴────────────────┬──────────────────┐
    ↓                                ↓                  ↓
┌──────────────┐          ┌──────────────────┐   ┌──────────┐
│ Pinecone     │          │ SQLite           │   │ OpenAI   │
│ Vector DB    │          │ Conversation DB  │   │ LLM      │
└──────────────┘          └──────────────────┘   └──────────┘
```

---

## 📁 Project Files

```
rag-support-agent/
├── backend.py                 # Main FastAPI server (700+ lines)
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── test_agent.py             # Test & validation script
├── index.html                # Web dashboard UI
├── SETUP_GUIDE.md           # Detailed setup instructions
├── README.md                # This file
├── Dockerfile               # Container image
├── docker-compose.yml       # Multi-container setup
├── docs/                    # Your knowledge base files
│   ├── support_guide.pdf
│   ├── faq.txt
│   └── ...
├── support_agent.db         # SQLite database (auto-created)
└── temp/                    # Temporary file storage
```

---

## 🎯 Core Features

### 1. **Retrieval-Augmented Generation (RAG)**
- Semantic search over your documents using vector embeddings
- Automatic chunking of PDFs and text files
- Pinecone vector database for fast, scalable retrieval
- Multiple documents simultaneously supported

### 2. **Agentic Reasoning**
- **Query Routing**: Decides between KB search, web search, or direct answer
- **Document Grading**: Validates retrieved docs are relevant before using
- **Query Rewriting**: Improves retrieval if initial results insufficient
- **Multi-turn Conversations**: Maintains context across queries
- **Reasoning Transparency**: Shows all thinking steps to user

### 3. **Multi-Tool Orchestration**
- **Knowledge Base Retrieval**: Your uploaded documents
- **Web Search**: Real-time information via Tavily API
- **Customer Database**: Access account/order data (can integrate)
- **Custom Tools**: Extensible for your specific needs

### 4. **Web Interface**
- Real-time chat with streaming responses
- Document upload with drag-and-drop
- Source attribution and relevance scoring
- Conversation history tracking
- Dark theme optimized for long sessions

### 5. **Production Ready**
- Conversation persistence (SQLite)
- Error handling and logging
- API documentation (Swagger/OpenAPI)
- CORS enabled for web integration
- Docker deployment support

---

## 🔧 API Endpoints

### Ask a Question
```bash
POST /query
Content-Type: application/json

{
  "question": "How do I reset my password?",
  "customer_id": "CUST123",
  "conversation_id": "conv-456"
}

Response:
{
  "conversation_id": "conv-456",
  "response": "To reset your password...",
  "sources": [
    {
      "source": "support_guide.pdf",
      "relevance": 0.92,
      "preview": "..."
    }
  ],
  "reasoning_steps": [
    "Routed to: knowledge_base",
    "Document relevance: ✓ Relevant",
    "Response generated successfully"
  ],
  "timestamp": "2026-01-20T17:25:30.123456"
}
```

### Upload Documents
```bash
POST /upload-documents
Content-Type: multipart/form-data

Files: support_guide.pdf, faq.txt

Response:
{
  "uploaded": 2,
  "documents": [
    {
      "file_id": "uuid",
      "filename": "support_guide.pdf",
      "chunks": 42,
      "status": "success"
    }
  ],
  "timestamp": "2026-01-20T17:25:30.123456"
}
```

### Get Conversation History
```bash
GET /conversations/{conversation_id}

Response:
{
  "conversation_id": "conv-456",
  "created_at": "2026-01-20T17:20:00.000000",
  "messages": [
    {"role": "user", "content": "Help with..."},
    {"role": "assistant", "content": "Sure! ..."}
  ],
  "sources_used": [...]
}
```

### Check Knowledge Base Status
```bash
GET /kb-status

Response:
{
  "total_documents": 5,
  "total_chunks": 342,
  "recent_documents": [
    {
      "filename": "support_guide.pdf",
      "date": "2026-01-20T16:00:00",
      "chunks": 42
    }
  ]
}
```

### Full Endpoint List
- `GET /health` - Health check
- `POST /query` - Process question (agentic)
- `POST /upload-documents` - Upload KB files
- `GET /conversations/{id}` - Get history
- `DELETE /conversations/{id}` - Delete conversation
- `GET /kb-status` - KB statistics
- `GET /docs` - Interactive API documentation

---

## 🚀 Deployment Options

### Option 1: Local Development
```bash
python backend.py
# http://localhost:8000
```

### Option 2: Docker
```bash
docker-compose up -d
# http://localhost:8000
```

### Option 3: Cloud Deployment

**AWS EC2:**
```bash
# 1. Create EC2 instance (Ubuntu 22.04)
# 2. SSH into instance
# 3. Clone repo & setup

git clone <repo>
cd rag-support-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Create systemd service
sudo nano /etc/systemd/system/support-agent.service

[Unit]
Description=RAG Support Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/rag-support-agent
Environment="PATH=/home/ubuntu/rag-support-agent/venv/bin"
ExecStart=/home/ubuntu/rag-support-agent/venv/bin/python backend.py
Restart=always

[Install]
WantedBy=multi-user.target

# 5. Start service
sudo systemctl start support-agent
sudo systemctl enable support-agent
```

**Heroku:**
```bash
# Create Procfile
web: uvicorn backend:app --host 0.0.0.0 --port $PORT

# Deploy
git push heroku main
```

**Google Cloud Run:**
```bash
# Build & deploy
gcloud run deploy support-agent --source . --platform managed
```

---

## 🔐 Security Considerations

### Best Practices
1. **Never commit API keys** - Use .env file (in .gitignore)
2. **HTTPS in production** - Use reverse proxy (Nginx, Cloudflare)
3. **Rate limiting** - Protect against abuse (FastAPI middleware)
4. **Authentication** - Add JWT/API key validation if needed
5. **Data privacy** - Encrypt sensitive data, follow GDPR/CCPA
6. **Input validation** - Sanitize user inputs (Pydantic does this)
7. **Monitoring** - Log all queries for compliance

### Adding Authentication
```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

@app.post("/query")
async def process_query(
    request: QueryRequest,
    credentials: HTTPAuthCredentials = Depends(security)
):
    # Validate credentials
    if credentials.credentials != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid key")
    # ... rest of code
```

---

## 📊 Performance Optimization

### Caching
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def retrieve_cached(query: str):
    return vs_manager.retrieve(query)
```

### Async Processing
```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def process_query_async(request: QueryRequest):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process, request)
    return result
```

### Database Optimization
```sql
-- Add indexes
CREATE INDEX idx_conversations_customer ON conversations(customer_id);
CREATE INDEX idx_conversations_date ON conversations(created_at);
```

---

## 🐛 Troubleshooting

### Issue: "API Key not found"
```bash
# Solution: Create .env file with keys
cp .env.example .env
# Edit .env with your actual keys
```

### Issue: "Pinecone connection failed"
```bash
# Solution: Verify API key and environment
# Check: https://app.pinecone.io/organizations/default/projects/default/indexes
# Ensure PINECONE_ENVIRONMENT matches your index
```

### Issue: "CORS error in browser"
```python
# Already enabled in backend.py
# If still issues, add specific origins:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
)
```

### Issue: "Document upload timeout"
```python
# Increase timeout in backend
# For large files, use chunked upload:
# Split files <50MB, upload separately
```

### Issue: "Slow retrieval"
```python
# Solutions:
# 1. Reduce chunk_overlap: 50 instead of 200
# 2. Use text-embedding-3-small (cheaper)
# 3. Add database indexes
# 4. Implement query caching
```

---

## 📚 Testing

### Unit Tests
```bash
pytest tests/ -v
```

### Integration Tests
```bash
# Test full flow
python test_agent.py

# Manual API test
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host http://localhost:8000
```

---

## 🎓 Advanced Usage

### Custom Tools
```python
@tool
def your_custom_tool(input_data: str) -> str:
    """Your custom tool description"""
    # Implement your logic
    return result

agent.tools.append(your_custom_tool)
```

### Multi-Tenant Setup
```python
# Separate namespaces per tenant
class MultiTenantVectorStore:
    def retrieve(self, query: str, tenant_id: str):
        return self.vector_store.similarity_search(
            query,
            filter={"tenant_id": tenant_id}
        )
```

### Custom LLM
```python
from langchain_anthropic import ChatAnthropic

# Use Claude instead of GPT
agent.llm = ChatAnthropic(model="claude-3-sonnet-20240229")
```

---

## 📈 Monitoring & Analytics

### Key Metrics
- **Query latency**: Average response time
- **Hit rate**: % queries with retrieved docs
- **User satisfaction**: Relevance ratings
- **Cost tracking**: API usage (OpenAI, Pinecone)

### Dashboard Query
```python
@app.get("/analytics")
async def get_analytics(days: int = 7):
    cursor.execute("""
        SELECT 
            COUNT(*) as total_queries,
            AVG(response_time) as avg_latency,
            COUNT(DISTINCT customer_id) as unique_users
        FROM conversations
        WHERE created_at > datetime('now', '-' || ? || ' days')
    """, (days,))
    return cursor.fetchone()
```

---

## 🤝 Contributing

Want to extend this agent? Ideas:
1. **Multi-language support** - Add translation layer
2. **Sentiment analysis** - Detect customer emotion
3. **Auto-categorization** - Classify query types
4. **Knowledge gap detection** - Find missing docs
5. **Conversation summarization** - Extract insights
6. **A/B testing** - Test different prompts
7. **Fine-tuning** - Custom LLM models
8. **Integration** - Slack, Teams, Discord bots

---

## 📞 Support

### Documentation
- `SETUP_GUIDE.md` - Installation details
- API docs: `http://localhost:8000/docs`
- Code comments - Inline documentation

### Resources
- OpenAI Docs: https://platform.openai.com/docs
- LangChain: https://python.langchain.com
- Pinecone: https://docs.pinecone.io
- FastAPI: https://fastapi.tiangolo.com

---

## 📄 License

This project is provided as-is for educational and commercial use.

---

## 🎉 Summary

You now have a **production-ready RAG Agentic Support Agent** with:

✅ Semantic search over documents  
✅ Intelligent query routing  
✅ Document relevance grading  
✅ Multi-tool orchestration  
✅ Real-time web interface  
✅ Conversation persistence  
✅ Easy deployment  
✅ Full API documentation  

**Start building better support experiences!** 🚀

---

**Made with ❤️ for AI builders**

*Last updated: January 2026*
