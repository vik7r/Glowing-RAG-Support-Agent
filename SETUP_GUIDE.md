# RAG Agentic Support Agent - Installation & Deployment Guide

## 📋 Quick Start (5 minutes)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install fastapi uvicorn langchain langchain-openai langchain-community
pip install pinecone-client python-dotenv tavily-python pydantic
pip install python-multipart  # For file uploads
```

### 2. Setup Environment Variables

Create `.env` file in your project root:

```
OPENAI_API_KEY=sk-your-key-here
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX=support-agent
TAVILY_API_KEY=your-tavily-key
```

Get free keys:
- **OpenAI**: https://platform.openai.com/api-keys
- **Pinecone**: https://www.pinecone.io (free tier: 1M vectors)
- **Tavily**: https://tavily.com (free for development)

### 3. Run the Backend Server

```bash
python backend.py
```

Server starts at `http://localhost:8000`

Access API docs: `http://localhost:8000/docs` (Swagger UI)

---

## 🎯 API Usage Examples

### Example 1: Upload Documents

```bash
curl -X POST "http://localhost:8000/upload-documents" \
  -F "files=@support_guide.pdf" \
  -F "files=@faq.txt"
```

### Example 2: Ask a Question

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I reset my password?",
    "customer_id": "CUST123",
    "conversation_id": "conv-456"
  }'
```

**Response:**
```json
{
  "conversation_id": "conv-456",
  "response": "To reset your password: 1. Click 'Forgot Password'... ",
  "sources": [
    {
      "source": "support_guide.pdf",
      "relevance": 0.92,
      "preview": "Password reset instructions..."
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

### Example 3: Get Conversation History

```bash
curl "http://localhost:8000/conversations/conv-456"
```

### Example 4: Check Knowledge Base Status

```bash
curl "http://localhost:8000/kb-status"
```

---

## 🖥️ Web Interface (HTML + JavaScript)

Save this as `index.html` and open in browser:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG Support Agent Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f1f5f9;
            height: 100vh;
            overflow: hidden;
        }
        
        .container {
            display: grid;
            grid-template-columns: 300px 1fr;
            height: 100vh;
        }
        
        .sidebar {
            background: #020617;
            border-right: 1px solid #334155;
            padding: 20px;
            overflow-y: auto;
        }
        
        .sidebar h2 {
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 15px;
        }
        
        .nav-item {
            padding: 10px 12px;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 8px;
            transition: all 0.2s;
            font-size: 14px;
        }
        
        .nav-item:hover {
            background: #1e293b;
        }
        
        .nav-item.active {
            background: #0284c7;
            color: #fff;
        }
        
        .main {
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            background: #0f172a;
            border-bottom: 1px solid #334155;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 20px;
            font-weight: 600;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            padding: 6px 12px;
            background: #1e293b;
            border-radius: 20px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .content {
            flex: 1;
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 20px;
            padding: 20px;
            overflow: hidden;
        }
        
        .chat-container {
            background: #0f172a;
            border-radius: 8px;
            border: 1px solid #334155;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        
        .message {
            display: flex;
            gap: 12px;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-bubble {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 8px;
            word-wrap: break-word;
        }
        
        .message.user .message-bubble {
            background: #0284c7;
            color: #fff;
        }
        
        .message.assistant .message-bubble {
            background: #1e293b;
            color: #cbd5e1;
        }
        
        .thinking {
            padding: 12px 16px;
            background: #1e293b;
            border-radius: 8px;
            color: #94a3b8;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .thinking::before {
            content: '⚡';
        }
        
        .input-area {
            padding: 16px;
            border-top: 1px solid #334155;
            display: flex;
            gap: 12px;
        }
        
        .input-field {
            flex: 1;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 10px 14px;
            color: #f1f5f9;
            font-size: 14px;
        }
        
        .input-field:focus {
            outline: none;
            border-color: #0284c7;
            box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.1);
        }
        
        .send-btn {
            background: #0284c7;
            border: none;
            color: #fff;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
        }
        
        .send-btn:hover {
            background: #0369a1;
        }
        
        .send-btn:disabled {
            background: #334155;
            cursor: not-allowed;
        }
        
        .sidebar-panel {
            background: #0f172a;
            border-radius: 8px;
            border: 1px solid #334155;
            padding: 16px;
            overflow-y: auto;
        }
        
        .panel-title {
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 12px;
        }
        
        .source-item {
            background: #1e293b;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid #0284c7;
        }
        
        .source-filename {
            font-weight: 500;
            color: #0284c7;
            font-size: 13px;
        }
        
        .source-score {
            font-size: 12px;
            color: #94a3b8;
            margin-top: 4px;
        }
        
        .upload-area {
            border: 2px dashed #334155;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .upload-area:hover {
            border-color: #0284c7;
            background: rgba(2, 132, 199, 0.05);
        }
        
        .upload-area.dragover {
            border-color: #0284c7;
            background: rgba(2, 132, 199, 0.1);
        }
        
        .scrollbar::-webkit-scrollbar {
            width: 6px;
        }
        
        .scrollbar::-webkit-scrollbar-track {
            background: transparent;
        }
        
        .scrollbar::-webkit-scrollbar-thumb {
            background: #334155;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar scrollbar">
            <h2>📚 Knowledge Base</h2>
            <div id="kb-status" class="nav-item">
                <div class="status-badge">
                    <span class="status-dot"></span>
                    <span id="kb-docs">0 Documents</span>
                </div>
            </div>
            
            <div class="upload-area" id="upload-area">
                <div>📤 Drop files here or click</div>
                <input type="file" id="file-input" multiple style="display:none;" accept=".pdf,.txt">
            </div>
            
            <h2 style="margin-top: 20px;">💬 Recent Chats</h2>
            <div id="recent-chats"></div>
        </div>
        
        <div class="main">
            <div class="header">
                <h1>🤖 AI Support Agent</h1>
                <div class="status-badge">
                    <span class="status-dot"></span>
                    <span>API Connected</span>
                </div>
            </div>
            
            <div class="content">
                <div class="chat-container scrollbar">
                    <div class="messages" id="messages"></div>
                    <div class="input-area">
                        <input 
                            type="text" 
                            class="input-field" 
                            id="message-input" 
                            placeholder="Ask your question..."
                            autocomplete="off"
                        >
                        <button class="send-btn" id="send-btn">Send</button>
                    </div>
                </div>
                
                <div class="sidebar-panel scrollbar">
                    <div class="panel-title">📄 Sources</div>
                    <div id="sources"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const API_URL = 'http://localhost:8000';
        let conversationId = localStorage.getItem('conversationId') || null;
        let isLoading = false;
        
        const elements = {
            messagesContainer: document.getElementById('messages'),
            messageInput: document.getElementById('message-input'),
            sendBtn: document.getElementById('send-btn'),
            sourcesContainer: document.getElementById('sources'),
            uploadArea: document.getElementById('upload-area'),
            fileInput: document.getElementById('file-input'),
            kbStatus: document.getElementById('kb-docs')
        };
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadKBStatus();
            
            elements.sendBtn.addEventListener('click', sendMessage);
            elements.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !isLoading) sendMessage();
            });
            
            // File upload handlers
            elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
            elements.fileInput.addEventListener('change', handleFileUpload);
            elements.uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                elements.uploadArea.classList.add('dragover');
            });
            elements.uploadArea.addEventListener('dragleave', () => {
                elements.uploadArea.classList.remove('dragover');
            });
            elements.uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                elements.uploadArea.classList.remove('dragover');
                handleFileDrop(e);
            });
        });
        
        async function sendMessage() {
            const message = elements.messageInput.value.trim();
            if (!message || isLoading) return;
            
            isLoading = true;
            elements.messageInput.value = '';
            elements.sendBtn.disabled = true;
            
            // Add user message
            addMessage(message, 'user');
            
            // Show thinking indicator
            showThinking();
            
            try {
                const response = await fetch(`${API_URL}/query`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: message,
                        conversation_id: conversationId
                    })
                });
                
                if (!response.ok) throw new Error('API error');
                
                const data = await response.json();
                conversationId = data.conversation_id;
                localStorage.setItem('conversationId', conversationId);
                
                // Remove thinking indicator
                document.querySelectorAll('.thinking').forEach(el => el.remove());
                
                // Add agent response
                addMessage(data.response, 'assistant');
                
                // Display sources
                displaySources(data.sources);
                
            } catch (error) {
                document.querySelectorAll('.thinking').forEach(el => el.remove());
                addMessage('❌ Error: ' + error.message, 'error');
            } finally {
                isLoading = false;
                elements.sendBtn.disabled = false;
                elements.messageInput.focus();
            }
        }
        
        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = `message ${type}`;
            const bubble = document.createElement('div');
            bubble.className = 'message-bubble';
            bubble.textContent = text;
            div.appendChild(bubble);
            elements.messagesContainer.appendChild(div);
            elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
        }
        
        function showThinking() {
            const div = document.createElement('div');
            div.className = 'thinking';
            div.textContent = ' Processing your query...';
            elements.messagesContainer.appendChild(div);
            elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
        }
        
        function displaySources(sources) {
            elements.sourcesContainer.innerHTML = '';
            if (sources.length === 0) {
                elements.sourcesContainer.innerHTML = '<p style="color: #94a3b8; font-size: 13px;">No sources used</p>';
                return;
            }
            
            sources.forEach(source => {
                const div = document.createElement('div');
                div.className = 'source-item';
                div.innerHTML = `
                    <div class="source-filename">📄 ${source.source}</div>
                    <div class="source-score">Relevance: ${(source.relevance * 100).toFixed(0)}%</div>
                `;
                elements.sourcesContainer.appendChild(div);
            });
        }
        
        async function handleFileUpload() {
            const files = elements.fileInput.files;
            if (files.length === 0) return;
            
            const formData = new FormData();
            Array.from(files).forEach(file => formData.append('files', file));
            
            try {
                const response = await fetch(`${API_URL}/upload-documents`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) throw new Error('Upload failed');
                
                const data = await response.json();
                addMessage(`✅ Uploaded ${data.uploaded} file(s) with ${data.documents.reduce((a, d) => a + d.chunks, 0)} chunks`, 'system');
                
                loadKBStatus();
                elements.fileInput.value = '';
                
            } catch (error) {
                addMessage('❌ Upload error: ' + error.message, 'error');
            }
        }
        
        async function handleFileDrop(e) {
            const files = e.dataTransfer.files;
            elements.fileInput.files = files;
            await handleFileUpload();
        }
        
        async function loadKBStatus() {
            try {
                const response = await fetch(`${API_URL}/kb-status`);
                if (response.ok) {
                    const data = await response.json();
                    elements.kbStatus.textContent = `${data.total_documents || 0} Documents`;
                }
            } catch (error) {
                console.error('KB status error:', error);
            }
        }
    </script>
</body>
</html>
```

---

## 🚀 Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend.py .
COPY .env .

EXPOSE 8000

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  support-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
    volumes:
      - ./support_agent.db:/app/support_agent.db
      - ./docs:/app/docs
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d
```

---

## 📊 Features Built

✅ **RAG Query Processing** - Vector retrieval + LLM reasoning
✅ **Multi-turn Conversations** - Full history tracking
✅ **Document Upload** - PDF & Text file support
✅ **Relevance Grading** - Auto-validates retrieved docs
✅ **Query Rewriting** - Improves retrieval if docs not relevant
✅ **Web Interface** - Real-time chat dashboard
✅ **API Documentation** - Auto-generated Swagger UI
✅ **SQLite Persistence** - Conversation history saved
✅ **Production Ready** - Error handling, logging, CORS

---

## 🔧 Next Steps

1. **Get API Keys** → OpenAI, Pinecone, Tavily
2. **Create .env file** → Add your keys
3. **Run backend** → `python backend.py`
4. **Open index.html** → Start chatting
5. **Upload your docs** → PDF/Text files
6. **Deploy** → Docker to cloud (AWS, GCP, Azure)

Enjoy your AI Support Agent! 🎉
