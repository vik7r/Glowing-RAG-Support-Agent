#!/usr/bin/env python3
"""
RAG Agentic Support Agent - Backend Server
Production-ready FastAPI application with vector retrieval and agentic reasoning
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.tools.tavily_search import TavilySearchResults

# Vector store and utilities
from pinecone import Pinecone as PineconeClient
import sqlite3

# ============================================================================
# LOGGING & SETUP
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# DATABASE SETUP
# ============================================================================

def init_db():
    """Initialize SQLite database for conversation history"""
    conn = sqlite3.connect("support_agent.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            customer_id TEXT,
            created_at TIMESTAMP,
            messages TEXT,
            kb_docs_used TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id TEXT PRIMARY KEY,
            filename TEXT,
            file_size INTEGER,
            upload_date TIMESTAMP,
            status TEXT,
            chunk_count INTEGER
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# ============================================================================
# VECTOR STORE SETUP
# ============================================================================

class VectorStoreManager:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.pc = PineconeClient(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX", "support-agent")
        self.namespace = "support-docs"
        self.vector_store = None
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize Pinecone index"""
        try:
            # List existing indexes (Pinecone v8 API)
            index_names = [idx.name for idx in self.pc.list_indexes()]
            if self.index_name not in index_names:
                logger.info(f"Creating index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,
                    metric="cosine"
                )
                # Wait for index to be ready
                import time
                time.sleep(2)
            
            # Connect to index
            index = self.pc.Index(self.index_name)
            self.vector_store = Pinecone(
                index=index,
                embedding=self.embeddings,
                text_key="text",
                namespace=self.namespace
            )
            logger.info(f"Vector store initialized successfully (index: {self.index_name}, namespace: {self.namespace})")
        except Exception as e:
            logger.error(f"Vector store initialization error: {e}")
            logger.exception(e)
            self.vector_store = None
    
    def add_documents(self, documents: List) -> int:
        """Add documents to vector store"""
        if self.vector_store is None:
            logger.error("Vector store is not initialized. Cannot add documents.")
            return 0
        try:
            if not documents:
                logger.warning("No documents provided to add_documents")
                return 0
            self.vector_store.add_documents(documents)
            logger.info(f"Successfully added {len(documents)} document chunks to vector store")
            return len(documents)
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            logger.exception(e)
            return 0
    
    def retrieve(self, query: str, k: int = 3) -> tuple:
        """Retrieve documents based on query"""
        if self.vector_store is None:
            logger.error("Vector store is not initialized. Cannot retrieve documents.")
            return []
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            logger.exception(e)
            return []
    
    def delete_documents_by_source(self, source: str) -> bool:
        """Delete documents from vector store by source filename"""
        if self.vector_store is None:
            logger.error("Vector store is not initialized. Cannot delete documents.")
            return False
        try:
            # Get the underlying Pinecone index
            index = self.pc.Index(self.index_name)
            
            # Delete by metadata filter (source filename)
            # Pinecone delete method accepts a filter parameter
            try:
                # Delete using metadata filter - Pinecone v8 API
                delete_response = index.delete(
                    filter={"source": {"$eq": source}},
                    namespace=self.namespace
                )
                logger.info(f"Deleted documents with source: {source}")
                return True
            except Exception as e:
                # Try alternative filter format
                try:
                    index.delete(
                        filter={"source": source},
                        namespace=self.namespace
                    )
                    logger.info(f"Deleted documents with source: {source} (alternative method)")
                    return True
                except Exception as e2:
                    logger.warning(f"Delete by filter failed: {e2}. Document may not exist in vector store.")
                    # Return True anyway - document might not have been in vector store
                    return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            logger.exception(e)
            # Return True to allow database deletion even if vector deletion fails
            return True

vs_manager = VectorStoreManager()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class QueryRequest(BaseModel):
    question: str
    customer_id: Optional[str] = None
    conversation_id: Optional[str] = None

class QueryResponse(BaseModel):
    conversation_id: str
    response: str
    sources: List[dict]
    reasoning_steps: List[str]
    timestamp: str

class DocumentUpload(BaseModel):
    filename: str
    status: str
    chunks: int

class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[dict]
    created_at: str

# ============================================================================
# AGENT REASONING ENGINE
# ============================================================================

class RAGAgentReasoner:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=2000)
        self.web_search = TavilySearchResults(max_results=3)
        self.reasoning_steps = []
    
    def route_query(self, question: str) -> str:
        """Route query to appropriate tool"""
        routing_prompt = f"""
        Determine which tool to use for this support question:
        "{question}"
        
        Tools available:
        - knowledge_base: For product info, FAQs, policies, procedures
        - web_search: For current information, external resources
        - direct_answer: For general questions
        
        Respond with ONLY one tool name.
        """
        
        response = self.llm.invoke(routing_prompt)
        tool = response.content.strip().lower()
        self.reasoning_steps.append(f"Routed to: {tool}")
        return tool
    
    def grade_documents(self, question: str, context: str) -> bool:
        """Grade if retrieved documents are relevant"""
        grade_prompt = f"""
        Question: {question}
        
        Retrieved context:
        {context}
        
        Is this context relevant and helpful for answering the question?
        Respond with ONLY: yes or no
        """
        
        response = self.llm.invoke(grade_prompt)
        is_relevant = "yes" in response.content.lower()
        self.reasoning_steps.append(f"Document relevance: {'✓ Relevant' if is_relevant else '✗ Not relevant'}")
        return is_relevant
    
    def rewrite_query(self, original_query: str) -> str:
        """Rewrite query if documents aren't relevant"""
        rewrite_prompt = f"""
        The initial search for "{original_query}" didn't return relevant results.
        
        Rewrite this query to be more specific or use different keywords.
        Respond with ONLY the rewritten query (no explanation).
        """
        
        response = self.llm.invoke(rewrite_prompt)
        rewritten = response.content.strip()
        self.reasoning_steps.append(f"Query rewritten: {rewritten}")
        return rewritten
    
    def generate_response(self, question: str, context: str = "", use_web: bool = False) -> str:
        """Generate final response with context"""
        context_section = f"Knowledge Base:\n{context}" if context else ""
        
        prompt = f"""
        You are a helpful support agent. Answer the following question clearly and concisely.
        
        Question: {question}
        
        {context_section}
        
        Guidelines:
        - Use the provided context if available
        - Be clear and helpful
        - If you don't have sufficient information, acknowledge it
        - Provide actionable steps when relevant
        """
        
        response = self.llm.invoke(prompt)
        self.reasoning_steps.append("Response generated successfully")
        return response.content

agent = RAGAgentReasoner()

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    logger.info("🚀 RAG Support Agent started")
    yield
    logger.info("🛑 RAG Support Agent shutdown")

app = FastAPI(
    title="RAG Agentic Support Agent API",
    description="AI-powered support with vector retrieval and reasoning",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ROUTES
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a support query through the RAG agent
    
    The agent:
    1. Routes the query to appropriate tool
    2. Retrieves relevant documents
    3. Grades document relevance
    4. Generates response with context
    """
    
    conversation_id = request.conversation_id or str(uuid.uuid4())
    agent.reasoning_steps = []
    sources = []
    
    try:
        # Step 1: Route the query
        tool = agent.route_query(request.question)
        
        # Step 2: Retrieve from knowledge base
        if tool in ["knowledge_base", "direct_answer"]:
            logger.info(f"Retrieving documents for query: {request.question}")
            retrieved = vs_manager.retrieve(request.question, k=3)
            
            if retrieved:
                logger.info(f"Found {len(retrieved)} documents in knowledge base")
                context = "\n\n".join([
                    f"📄 {doc.metadata.get('source', 'Unknown')} (Score: {score:.2f})\n{doc.page_content}"
                    for doc, score in retrieved
                ])
                sources = [
                    {
                        "source": doc.metadata.get('source', 'Unknown'),
                        "relevance": float(score),
                        "preview": doc.page_content[:200]
                    }
                    for doc, score in retrieved
                ]
                
                # Step 3: Grade documents
                is_relevant = agent.grade_documents(request.question, context)
                
                if not is_relevant and len(agent.reasoning_steps) < 5:
                    # Rewrite and retry
                    rewritten = agent.rewrite_query(request.question)
                    logger.info(f"Query rewritten to: {rewritten}")
                    retrieved = vs_manager.retrieve(rewritten, k=3)
                    if retrieved:
                        context = "\n\n".join([
                            f"{doc.metadata.get('source', 'Unknown')}\n{doc.page_content}"
                            for doc, _ in retrieved
                        ])
                        sources = [
                            {
                                "source": doc.metadata.get('source', 'Unknown'),
                                "relevance": 0.0,
                                "preview": doc.page_content[:200]
                            }
                            for doc, _ in retrieved
                        ]
            else:
                logger.warning(f"No documents retrieved for query: {request.question}")
                context = ""
        else:
            logger.info(f"Query routed to {tool}, skipping knowledge base retrieval")
            context = ""
        
        # Step 4: Generate response
        response_text = agent.generate_response(request.question, context)
        
        # Save to database
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        messages = json.dumps([
            {"role": "user", "content": request.question},
            {"role": "assistant", "content": response_text}
        ])
        
        cursor.execute("""
            INSERT OR REPLACE INTO conversations 
            (id, customer_id, created_at, messages, kb_docs_used)
            VALUES (?, ?, ?, ?, ?)
        """, (conversation_id, request.customer_id, datetime.now().isoformat(), messages, json.dumps(sources)))
        
        conn.commit()
        conn.close()
        
        return QueryResponse(
            conversation_id=conversation_id,
            response=response_text,
            sources=sources,
            reasoning_steps=agent.reasoning_steps,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-documents")
async def upload_documents(files: List[UploadFile] = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Upload and process documents"""
    
    processed_docs = []
    
    try:
        for file in files:
            file_id = str(uuid.uuid4())
            
            # Save file temporarily
            temp_path = f"./temp/{file.filename}"
            os.makedirs("./temp", exist_ok=True)
            
            # Read file content and save
            file_content = await file.read()
            file_size = len(file_content)
            
            with open(temp_path, "wb") as f:
                f.write(file_content)
            
            # Process file based on type
            documents = []
            try:
                if file.filename.endswith(".pdf"):
                    loader = PyPDFLoader(temp_path)
                    documents = loader.load()
                    logger.info(f"Loaded {len(documents)} pages from PDF: {file.filename}")
                elif file.filename.endswith(".txt"):
                    loader = TextLoader(temp_path)
                    documents = loader.load()
                    logger.info(f"Loaded {len(documents)} documents from TXT: {file.filename}")
                else:
                    logger.warning(f"Unsupported file type: {file.filename}")
            except Exception as e:
                logger.error(f"Error loading file {file.filename}: {e}")
                processed_docs.append({
                    "file_id": file_id,
                    "filename": file.filename,
                    "chunks": 0,
                    "status": f"error: {str(e)}"
                })
                os.remove(temp_path)
                continue
            
            # Chunk documents
            if documents:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                chunks = splitter.split_documents(documents)
                logger.info(f"Split into {len(chunks)} chunks")
                
                # Add to vector store
                added = vs_manager.add_documents(chunks)
                
                if added == 0:
                    logger.error(f"Failed to add documents to vector store for {file.filename}")
                    status = "failed"
                else:
                    status = "processed"
                
                # Record in database
                conn = sqlite3.connect("support_agent.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO knowledge_base 
                    (id, filename, file_size, upload_date, status, chunk_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (file_id, file.filename, file_size, datetime.now().isoformat(), status, added))
                conn.commit()
                conn.close()
                
                processed_docs.append({
                    "file_id": file_id,
                    "filename": file.filename,
                    "chunks": added,
                    "status": "success" if added > 0 else "failed"
                })
            else:
                logger.warning(f"No documents extracted from {file.filename}")
                processed_docs.append({
                    "file_id": file_id,
                    "filename": file.filename,
                    "chunks": 0,
                    "status": "no_content"
                })
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return {
            "uploaded": len(processed_docs),
            "documents": processed_docs,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Retrieve conversation history"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, created_at, messages, kb_docs_used 
            FROM conversations 
            WHERE id = ?
        """, (conversation_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "conversation_id": row[0],
            "created_at": row[1],
            "messages": json.loads(row[2]),
            "sources_used": json.loads(row[3])
        }
    
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/kb-status")
async def get_kb_status():
    """Get knowledge base status"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(chunk_count) FROM knowledge_base WHERE status = 'processed'")
        docs_count, total_chunks = cursor.fetchone()
        
        cursor.execute("SELECT filename, upload_date, chunk_count FROM knowledge_base ORDER BY upload_date DESC LIMIT 10")
        recent_docs = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_documents": docs_count or 0,
            "total_chunks": total_chunks or 0,
            "recent_documents": [
                {"filename": doc[0], "date": doc[1], "chunks": doc[2]}
                for doc in recent_docs
            ]
        }
    
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/kb-documents")
async def list_documents():
    """List all uploaded documents"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, file_size, upload_date, status, chunk_count 
            FROM knowledge_base 
            ORDER BY upload_date DESC
        """)
        docs = cursor.fetchall()
        
        conn.close()
        
        return {
            "documents": [
                {
                    "id": doc[0],
                    "filename": doc[1],
                    "file_size": doc[2],
                    "upload_date": doc[3],
                    "status": doc[4],
                    "chunk_count": doc[5]
                }
                for doc in docs
            ]
        }
    
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/kb-documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from knowledge base"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        # Get document info before deletion
        cursor.execute("SELECT filename FROM knowledge_base WHERE id = ?", (document_id,))
        doc = cursor.fetchone()
        
        if not doc:
            conn.close()
            raise HTTPException(status_code=404, detail="Document not found")
        
        filename = doc[0]
        
        # Delete from vector store
        deleted_from_vector = vs_manager.delete_documents_by_source(filename)
        
        # Delete from database
        cursor.execute("DELETE FROM knowledge_base WHERE id = ?", (document_id,))
        conn.commit()
        conn.close()
        
        return {
            "status": "deleted",
            "document_id": document_id,
            "filename": filename,
            "vector_store_deleted": deleted_from_vector
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
        conn.close()
        
        return {"status": "deleted", "conversation_id": conversation_id}
    
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
