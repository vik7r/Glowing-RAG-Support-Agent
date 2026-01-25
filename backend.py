#!/usr/bin/env python3
"""
RAG Agentic Support Agent - Backend Server
Production-ready FastAPI application with vector retrieval and agentic reasoning
Enhanced with feedback system, analytics, caching, and sentiment analysis
"""

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from contextlib import asynccontextmanager
import hashlib
from collections import defaultdict

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
# SENTIMENT ANALYZER
# ============================================================================

class SentimentAnalyzer:
    """Analyzes sentiment of queries and responses"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=100)
    
    def analyze(self, text: str) -> tuple:
        """Analyze sentiment and return (sentiment_label, score)"""
        try:
            prompt = f"""
            Analyze the sentiment of this text and respond with exactly:
            SENTIMENT|SCORE
            
            Where SENTIMENT is one of: positive, negative, neutral
            And SCORE is a number from -1.0 (most negative) to 1.0 (most positive)
            
            Text: {text}
            """
            response = self.llm.invoke(prompt)
            parts = response.content.strip().split("|")
            if len(parts) == 2:
                sentiment = parts[0].strip().lower()
                score = float(parts[1].strip())
                return sentiment, score
        except Exception as e:
            logger.warning(f"Sentiment analysis error: {e}")
        return "neutral", 0.0

sentiment_analyzer = SentimentAnalyzer()

# ============================================================================
# RESPONSE CACHE MANAGER
# ============================================================================

class CacheManager:
    """Manages response caching to reduce redundant API calls"""
    
    def __init__(self, ttl_hours: int = 24):
        self.ttl_hours = ttl_hours
        self.memory_cache = {}
    
    def _hash_query(self, query: str) -> str:
        """Generate hash of query for caching"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def get(self, query: str) -> Optional[Dict]:
        """Get cached response if available and not expired"""
        try:
            query_hash = self._hash_query(query)
            
            # Check memory cache first (faster)
            if query_hash in self.memory_cache:
                cached_time = self.memory_cache[query_hash]['timestamp']
                if datetime.now() - cached_time < timedelta(hours=self.ttl_hours):
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    return self.memory_cache[query_hash]['data']
                else:
                    del self.memory_cache[query_hash]
            
            # Check database cache
            conn = sqlite3.connect("support_agent.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT response, sources FROM response_cache 
                WHERE query_hash = ? AND datetime(created_at) > datetime('now', '-24 hours')
            """, (query_hash,))
            
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE response_cache 
                    SET hit_count = hit_count + 1, last_accessed = ?
                    WHERE query_hash = ?
                """, (datetime.now().isoformat(), query_hash))
                conn.commit()
                conn.close()
                
                return {
                    "response": row[0],
                    "sources": json.loads(row[1]),
                    "from_cache": True
                }
            conn.close()
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        return None
    
    def set(self, query: str, response: str, sources: List[dict]):
        """Cache a response"""
        try:
            query_hash = self._hash_query(query)
            
            # Store in memory cache
            self.memory_cache[query_hash] = {
                'data': {"response": response, "sources": sources, "from_cache": False},
                'timestamp': datetime.now()
            }
            
            # Store in database
            conn = sqlite3.connect("support_agent.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO response_cache 
                (query_hash, query, response, sources, created_at, hit_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (query_hash, query, response, json.dumps(sources), datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            
            logger.info(f"Cached response for query: {query[:50]}...")
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")

cache_manager = CacheManager()

# ============================================================================
# FOLLOW-UP QUESTION GENERATOR
# ============================================================================

class FollowUpGenerator:
    """Generates relevant follow-up questions"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=300)
    
    def generate(self, question: str, response: str) -> List[str]:
        """Generate 2-3 relevant follow-up questions"""
        try:
            prompt = f"""
            Based on this support conversation, generate 2-3 helpful follow-up questions 
            that the customer might want to ask next.
            
            Original Question: {question}
            Response: {response}
            
            Format your response as a JSON array of strings, like:
            ["Question 1?", "Question 2?", "Question 3?"]
            
            Only include the JSON array, nothing else.
            """
            response_text = self.llm.invoke(prompt)
            try:
                questions = json.loads(response_text.content)
                if isinstance(questions, list):
                    return questions[:3]
            except json.JSONDecodeError:
                logger.warning("Could not parse follow-up questions as JSON")
        except Exception as e:
            logger.warning(f"Follow-up generation error: {e}")
        
        return []

followup_generator = FollowUpGenerator()

# ============================================================================
# LANGUAGE DETECTOR
# ============================================================================

class LanguageDetector:
    """Detects and translates text"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=200)
    
    def detect_language(self, text: str) -> str:
        """Detect language of text"""
        try:
            prompt = f"""
            Detect the language of this text and respond with ONLY the language code 
            (e.g., 'en', 'es', 'fr', 'de', 'ja', 'zh', etc.):
            
            Text: {text}
            """
            response = self.llm.invoke(prompt)
            lang_code = response.content.strip().lower()[:2]
            return lang_code if lang_code.isalpha() else "en"
        except Exception as e:
            logger.warning(f"Language detection error: {e}")
            return "en"
    
    def translate(self, text: str, target_language: str) -> str:
        """Translate text to target language"""
        try:
            prompt = f"""
            Translate the following text to {target_language}.
            Respond with ONLY the translated text, nothing else.
            
            Text: {text}
            """
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.warning(f"Translation error: {e}")
            return text

language_detector = LanguageDetector()

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
    
    # New table for user feedback/ratings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            query TEXT,
            response TEXT,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)
    
    # New table for response caching
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS response_cache (
            query_hash TEXT PRIMARY KEY,
            query TEXT,
            response TEXT,
            sources TEXT,
            created_at TIMESTAMP,
            hit_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP
        )
    """)
    
    # New table for analytics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id TEXT PRIMARY KEY,
            query TEXT,
            response_time_ms REAL,
            tokens_used INTEGER,
            documents_retrieved INTEGER,
            rating INTEGER,
            created_at TIMESTAMP
        )
    """)
    
    # New table for sentiment analysis
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sentiment_log (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            query_sentiment TEXT,
            query_score REAL,
            response_sentiment TEXT,
            response_score REAL,
            created_at TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
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
    from_cache: bool = False
    suggested_questions: List[str] = []
    sentiment: Optional[str] = None

class DocumentUpload(BaseModel):
    filename: str
    status: str
    chunks: int

class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[dict]
    created_at: str

class FeedbackRequest(BaseModel):
    conversation_id: str
    query: str
    response: str
    rating: int  # 1-5 stars
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    feedback_id: str
    status: str
    timestamp: str

class TranslationRequest(BaseModel):
    text: str
    target_language: str

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
# ANALYTICS HELPER
# ============================================================================

def _log_analytics(query: str, response_time_ms: float, tokens: int, docs_retrieved: int, rating: Optional[int]):
    """Log query analytics to database"""
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        analytics_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO analytics 
            (id, query, response_time_ms, tokens_used, documents_retrieved, rating, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (analytics_id, query, response_time_ms, tokens, docs_retrieved, rating, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Analytics logging error: {e}")

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
    1. Checks cache for similar queries
    2. Routes the query to appropriate tool
    3. Retrieves relevant documents
    4. Grades document relevance
    5. Generates response with context
    6. Analyzes sentiment
    7. Generates follow-up questions
    """
    
    conversation_id = request.conversation_id or str(uuid.uuid4())
    agent.reasoning_steps = []
    sources = []
    from_cache = False
    suggested_questions = []
    sentiment = None
    
    try:
        # Step 0: Check cache
        cached_result = cache_manager.get(request.question)
        if cached_result:
            agent.reasoning_steps.append("Retrieved from cache")
            
            # Log analytics
            _log_analytics(request.question, 5.0, 0, len(cached_result["sources"]), None)
            
            return QueryResponse(
                conversation_id=conversation_id,
                response=cached_result["response"],
                sources=cached_result["sources"],
                reasoning_steps=agent.reasoning_steps,
                timestamp=datetime.now().isoformat(),
                from_cache=True,
                suggested_questions=followup_generator.generate(request.question, cached_result["response"]),
                sentiment=None
            )
        
        # Step 0.5: Detect language and sentiment
        detected_lang = language_detector.detect_language(request.question)
        query_sentiment, query_score = sentiment_analyzer.analyze(request.question)
        agent.reasoning_steps.append(f"Language: {detected_lang}, Sentiment: {query_sentiment} ({query_score:.2f})")
        
        # Step 1: Route the query
        tool = agent.route_query(request.question)
        
        # Step 2: Retrieve from knowledge base
        retrieved_count = 0
        if tool in ["knowledge_base", "direct_answer"]:
            logger.info(f"Retrieving documents for query: {request.question}")
            retrieved = vs_manager.retrieve(request.question, k=3)
            retrieved_count = len(retrieved)
            
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
                        retrieved_count = len(retrieved)
            else:
                logger.warning(f"No documents retrieved for query: {request.question}")
                context = ""
        else:
            logger.info(f"Query routed to {tool}, skipping knowledge base retrieval")
            context = ""
        
        # Step 4: Generate response
        import time
        start_time = time.time()
        response_text = agent.generate_response(request.question, context)
        response_time_ms = (time.time() - start_time) * 1000
        
        # Analyze response sentiment
        response_sentiment, response_score = sentiment_analyzer.analyze(response_text)
        sentiment = f"{response_sentiment} ({response_score:.2f})"
        
        # Step 5: Generate follow-up questions
        suggested_questions = followup_generator.generate(request.question, response_text)
        agent.reasoning_steps.append(f"Generated {len(suggested_questions)} follow-up questions")
        
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
        
        # Save sentiment log
        sentiment_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO sentiment_log
            (id, conversation_id, query_sentiment, query_score, response_sentiment, response_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sentiment_id, conversation_id, query_sentiment, query_score, response_sentiment, response_score, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Cache the response
        cache_manager.set(request.question, response_text, sources)
        
        # Log analytics
        _log_analytics(request.question, response_time_ms, 0, retrieved_count, None)
        
        return QueryResponse(
            conversation_id=conversation_id,
            response=response_text,
            sources=sources,
            reasoning_steps=agent.reasoning_steps,
            timestamp=datetime.now().isoformat(),
            from_cache=False,
            suggested_questions=suggested_questions,
            sentiment=sentiment
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
# NEW FEATURE ENDPOINTS
# ============================================================================

@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback and rating for a response"""
    
    try:
        feedback_id = str(uuid.uuid4())
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feedback 
            (id, conversation_id, query, response, rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (feedback_id, request.conversation_id, request.query, request.response, 
              request.rating, request.comment, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Feedback received: {request.rating} stars for conversation {request.conversation_id}")
        
        return FeedbackResponse(
            feedback_id=feedback_id,
            status="recorded",
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/summary")
async def get_analytics_summary():
    """Get analytics summary and metrics"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_queries,
                AVG(response_time_ms) as avg_response_time,
                AVG(documents_retrieved) as avg_docs_retrieved,
                AVG(rating) as avg_rating
            FROM analytics
            WHERE created_at > datetime('now', '-30 days')
        """)
        stats = cursor.fetchone()
        
        # Feedback stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_ratings,
                AVG(rating) as avg_rating,
                SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive_ratings
            FROM feedback
        """)
        feedback_stats = cursor.fetchone()
        
        # Top queries
        cursor.execute("""
            SELECT query, COUNT(*) as frequency
            FROM analytics
            WHERE created_at > datetime('now', '-30 days')
            GROUP BY query
            ORDER BY frequency DESC
            LIMIT 10
        """)
        top_queries = cursor.fetchall()
        
        # Cache performance
        cursor.execute("""
            SELECT 
                COUNT(*) as total_cached,
                SUM(hit_count) as total_hits
            FROM response_cache
        """)
        cache_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "period": "Last 30 days",
            "overall_metrics": {
                "total_queries": stats[0] or 0,
                "avg_response_time_ms": round(stats[1], 2) if stats[1] else 0,
                "avg_documents_retrieved": round(stats[2], 2) if stats[2] else 0,
                "avg_rating": round(stats[3], 2) if stats[3] else 0
            },
            "feedback_metrics": {
                "total_ratings": feedback_stats[0] or 0,
                "average_rating": round(feedback_stats[1], 2) if feedback_stats[1] else 0,
                "positive_ratings_count": feedback_stats[2] or 0
            },
            "cache_metrics": {
                "total_cached_responses": cache_stats[0] or 0,
                "total_cache_hits": cache_stats[1] or 0
            },
            "top_queries": [
                {"query": q[0], "frequency": q[1]}
                for q in top_queries
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/sentiment")
async def get_sentiment_analytics():
    """Get sentiment analysis trends"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        # Sentiment distribution
        cursor.execute("""
            SELECT response_sentiment, COUNT(*) as count, AVG(response_score) as avg_score
            FROM sentiment_log
            WHERE created_at > datetime('now', '-30 days')
            GROUP BY response_sentiment
        """)
        sentiment_dist = cursor.fetchall()
        
        # Trend over time (daily)
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                AVG(response_score) as avg_sentiment_score,
                COUNT(*) as interactions
            FROM sentiment_log
            WHERE created_at > datetime('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        sentiment_trend = cursor.fetchall()
        
        conn.close()
        
        return {
            "sentiment_distribution": [
                {
                    "sentiment": s[0],
                    "count": s[1],
                    "average_score": round(s[2], 3)
                }
                for s in sentiment_dist
            ],
            "sentiment_trend_7_days": [
                {
                    "date": t[0],
                    "average_score": round(t[1], 3),
                    "interactions": t[2]
                }
                for t in sentiment_trend
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Sentiment analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/feedback/summary")
async def get_feedback_summary():
    """Get feedback summary and ratings distribution"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        # Rating distribution
        cursor.execute("""
            SELECT rating, COUNT(*) as count
            FROM feedback
            GROUP BY rating
            ORDER BY rating DESC
        """)
        ratings_dist = cursor.fetchall()
        
        # Recent feedback
        cursor.execute("""
            SELECT id, conversation_id, rating, comment, created_at
            FROM feedback
            ORDER BY created_at DESC
            LIMIT 20
        """)
        recent_feedback = cursor.fetchall()
        
        conn.close()
        
        return {
            "rating_distribution": {
                str(r[0]): r[1] for r in ratings_dist
            },
            "recent_feedback": [
                {
                    "feedback_id": f[0],
                    "conversation_id": f[1],
                    "rating": f[2],
                    "comment": f[3],
                    "timestamp": f[4]
                }
                for f in recent_feedback
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Feedback summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/translate")
async def translate_text(request: TranslationRequest):
    """Translate text to target language"""
    
    try:
        translated = language_detector.translate(request.text, request.target_language)
        detected_lang = language_detector.detect_language(request.text)
        
        return {
            "original_text": request.text,
            "translated_text": translated,
            "source_language": detected_lang,
            "target_language": request.target_language,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache-status")
async def get_cache_status():
    """Get cache performance metrics"""
    
    try:
        conn = sqlite3.connect("support_agent.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_cached,
                SUM(hit_count) as total_hits,
                AVG(hit_count) as avg_hits,
                MAX(hit_count) as max_hits
            FROM response_cache
        """)
        cache_data = cursor.fetchone()
        
        cursor.execute("""
            SELECT query, hit_count, created_at, last_accessed
            FROM response_cache
            ORDER BY hit_count DESC
            LIMIT 10
        """)
        popular_queries = cursor.fetchall()
        
        conn.close()
        
        total_cached = cache_data[0] or 0
        total_hits = cache_data[1] or 0
        
        return {
            "cache_metrics": {
                "total_cached_responses": total_cached,
                "total_cache_hits": total_hits,
                "average_hits_per_query": round(cache_data[2], 2) if cache_data[2] else 0,
                "most_popular_hit_count": cache_data[3] or 0,
                "cache_hit_rate": round((total_hits / (total_hits + total_cached)) * 100, 2) if (total_hits + total_cached) > 0 else 0
            },
            "popular_queries": [
                {
                    "query": p[0][:100],
                    "hit_count": p[1],
                    "cached_at": p[2],
                    "last_accessed": p[3]
                }
                for p in popular_queries
            ],
            "memory_cache_size": len(cache_manager.memory_cache),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Cache status error: {e}")
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
