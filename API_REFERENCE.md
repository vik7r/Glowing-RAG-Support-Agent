# RAG Support Agent - Complete API Reference

## Base URL
```
http://localhost:8000
```

## Interactive Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🔵 Core Endpoints

### 1. POST `/query` - Process Support Query
Process a customer question through the RAG agent with all reasoning steps.

**Request:**
```json
{
  "question": "How do I reset my password?",
  "customer_id": "cust_12345",
  "conversation_id": "existing-conv-id"
}
```

**Response (200):**
```json
{
  "conversation_id": "uuid-conv-123",
  "response": "To reset your password, click on 'Forgot Password' on the login page...",
  "sources": [
    {
      "source": "FAQ.pdf",
      "relevance": 0.92,
      "preview": "Password reset instructions..."
    }
  ],
  "reasoning_steps": [
    "Language: en, Sentiment: neutral (0.1)",
    "Routed to: knowledge_base",
    "Retrieved 3 documents",
    "Documents relevant: ✓ Relevant",
    "Response generated successfully"
  ],
  "from_cache": false,
  "sentiment": "positive (0.65)",
  "suggested_questions": [
    "I didn't receive the reset email",
    "How long until password works?",
    "Can I set my own password?"
  ],
  "timestamp": "2026-01-25T10:30:00Z"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `500` - Server error

---

### 2. POST `/upload-documents` - Upload KB Documents
Upload PDF or TXT files to the knowledge base.

**Request (multipart/form-data):**
```
Files: [file1.pdf, file2.pdf, doc.txt]
```

**Response (200):**
```json
{
  "uploaded": 3,
  "documents": [
    {
      "file_id": "uuid-doc-1",
      "filename": "FAQ.pdf",
      "chunks": 45,
      "status": "success"
    },
    {
      "file_id": "uuid-doc-2",
      "filename": "Policies.pdf",
      "chunks": 28,
      "status": "success"
    },
    {
      "file_id": "uuid-doc-3",
      "filename": "Guide.txt",
      "chunks": 12,
      "status": "success"
    }
  ],
  "timestamp": "2026-01-25T10:30:00Z"
}
```

---

### 3. GET `/conversations/{conversation_id}` - Get Conversation History
Retrieve full history of a conversation.

**Response (200):**
```json
{
  "conversation_id": "uuid-conv-123",
  "created_at": "2026-01-25T09:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "How do I reset my password?"
    },
    {
      "role": "assistant",
      "content": "To reset your password..."
    },
    {
      "role": "user",
      "content": "I didn't receive the email"
    },
    {
      "role": "assistant",
      "content": "Let me help you with that..."
    }
  ],
  "sources_used": [
    {
      "source": "FAQ.pdf",
      "relevance": 0.92,
      "preview": "..."
    }
  ]
}
```

---

### 4. DELETE `/conversations/{conversation_id}` - Delete Conversation
Remove a conversation from history.

**Response (200):**
```json
{
  "status": "deleted",
  "conversation_id": "uuid-conv-123"
}
```

---

## 📊 Knowledge Base Endpoints

### 5. GET `/kb-status` - Knowledge Base Status
Get statistics about uploaded documents.

**Response (200):**
```json
{
  "total_documents": 5,
  "total_chunks": 150,
  "recent_documents": [
    {
      "filename": "FAQ.pdf",
      "date": "2026-01-25T14:30:00Z",
      "chunks": 45
    },
    {
      "filename": "Policies.pdf",
      "date": "2026-01-25T10:15:00Z",
      "chunks": 28
    }
  ]
}
```

---

### 6. GET `/kb-documents` - List All Documents
Get detailed list of all KB documents.

**Response (200):**
```json
{
  "documents": [
    {
      "id": "uuid-doc-1",
      "filename": "FAQ.pdf",
      "file_size": 256000,
      "upload_date": "2026-01-25T10:30:00Z",
      "status": "processed",
      "chunk_count": 45
    },
    {
      "id": "uuid-doc-2",
      "filename": "Policies.pdf",
      "file_size": 128000,
      "upload_date": "2026-01-25T10:15:00Z",
      "status": "processed",
      "chunk_count": 28
    }
  ]
}
```

---

### 7. DELETE `/kb-documents/{document_id}` - Delete Document
Remove a document from knowledge base.

**Response (200):**
```json
{
  "status": "deleted",
  "document_id": "uuid-doc-1",
  "filename": "FAQ.pdf",
  "vector_store_deleted": true
}
```

---

## 💬 Feedback & Rating Endpoints

### 8. POST `/feedback` - Submit Response Rating
User feedback on agent response quality.

**Request:**
```json
{
  "conversation_id": "uuid-conv-123",
  "query": "How do I reset my password?",
  "response": "To reset your password, click...",
  "rating": 5,
  "comment": "Very helpful and clear!"
}
```

**Response (200):**
```json
{
  "feedback_id": "uuid-feedback-1",
  "status": "recorded",
  "timestamp": "2026-01-25T10:30:00Z"
}
```

---

### 9. GET `/feedback/summary` - Feedback Analytics
Get feedback statistics and sentiment.

**Response (200):**
```json
{
  "rating_distribution": {
    "5": 180,
    "4": 95,
    "3": 45,
    "2": 15,
    "1": 5
  },
  "recent_feedback": [
    {
      "feedback_id": "uuid-1",
      "conversation_id": "uuid-conv-123",
      "rating": 5,
      "comment": "Excellent support",
      "timestamp": "2026-01-25T15:45:00Z"
    }
  ],
  "timestamp": "2026-01-25T16:00:00Z"
}
```

---

## 📈 Analytics Endpoints

### 10. GET `/analytics/summary` - Overall Metrics Dashboard
Comprehensive analytics for the last 30 days.

**Response (200):**
```json
{
  "period": "Last 30 days",
  "overall_metrics": {
    "total_queries": 2450,
    "avg_response_time_ms": 2350.45,
    "avg_documents_retrieved": 2.8,
    "avg_rating": 4.25
  },
  "feedback_metrics": {
    "total_ratings": 340,
    "average_rating": 4.2,
    "positive_ratings_count": 285
  },
  "cache_metrics": {
    "total_cached_responses": 450,
    "total_cache_hits": 2100
  },
  "top_queries": [
    {
      "query": "How do I reset my password?",
      "frequency": 85
    },
    {
      "query": "What's your refund policy?",
      "frequency": 72
    },
    {
      "query": "How do I contact support?",
      "frequency": 68
    }
  ],
  "timestamp": "2026-01-25T16:00:00Z"
}
```

---

### 11. GET `/analytics/sentiment` - Sentiment Trends
Sentiment analysis data and customer satisfaction trends.

**Response (200):**
```json
{
  "sentiment_distribution": [
    {
      "sentiment": "positive",
      "count": 1650,
      "average_score": 0.72
    },
    {
      "sentiment": "neutral",
      "count": 650,
      "average_score": 0.08
    },
    {
      "sentiment": "negative",
      "count": 150,
      "average_score": -0.65
    }
  ],
  "sentiment_trend_7_days": [
    {
      "date": "2026-01-25",
      "average_score": 0.68,
      "interactions": 280
    },
    {
      "date": "2026-01-24",
      "average_score": 0.70,
      "interactions": 265
    },
    {
      "date": "2026-01-23",
      "average_score": 0.65,
      "interactions": 250
    }
  ],
  "timestamp": "2026-01-25T16:00:00Z"
}
```

---

### 12. GET `/cache-status` - Cache Performance
Monitor response caching metrics.

**Response (200):**
```json
{
  "cache_metrics": {
    "total_cached_responses": 450,
    "total_cache_hits": 2100,
    "average_hits_per_query": 4.67,
    "most_popular_hit_count": 45,
    "cache_hit_rate": 82.35
  },
  "popular_queries": [
    {
      "query": "How do I reset my password?",
      "hit_count": 45,
      "cached_at": "2026-01-20T10:30:00Z",
      "last_accessed": "2026-01-25T15:00:00Z"
    },
    {
      "query": "What's your refund policy?",
      "hit_count": 38,
      "cached_at": "2026-01-21T14:20:00Z",
      "last_accessed": "2026-01-25T14:45:00Z"
    }
  ],
  "memory_cache_size": 45,
  "timestamp": "2026-01-25T16:00:00Z"
}
```

---

## 🌍 Language & Translation Endpoints

### 13. POST `/translate` - Translate Text
Translate text to a target language.

**Request:**
```json
{
  "text": "How do I reset my password?",
  "target_language": "Spanish"
}
```

**Response (200):**
```json
{
  "original_text": "How do I reset my password?",
  "translated_text": "¿Cómo restablezco mi contraseña?",
  "source_language": "en",
  "target_language": "es",
  "timestamp": "2026-01-25T10:30:00Z"
}
```

---

## 🏥 Health & System Endpoints

### 14. GET `/health` - Health Check
Check if the API is running.

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-25T10:30:00Z",
  "version": "1.0.0"
}
```

---

## 📋 Error Responses

All endpoints return standard HTTP status codes:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid input)
- `404` - Not Found (resource doesn't exist)
- `500` - Server Error (internal error)

---

## 🔌 Integration Examples

### Python - Using Requests
```python
import requests

# Submit a query
response = requests.post(
    "http://localhost:8000/query",
    json={
        "question": "How do I reset my password?",
        "customer_id": "cust_12345"
    }
)

result = response.json()
print(f"Answer: {result['response']}")
print(f"Suggested follow-ups: {result['suggested_questions']}")

# Submit feedback
requests.post(
    "http://localhost:8000/feedback",
    json={
        "conversation_id": result["conversation_id"],
        "query": "How do I reset my password?",
        "response": result["response"],
        "rating": 5,
        "comment": "Great help!"
    }
)
```

### JavaScript - Using Fetch
```javascript
// Submit a query
const response = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    question: "How do I reset my password?",
    customer_id: "cust_12345"
  })
});

const data = await response.json();
console.log("Answer:", data.response);
console.log("Suggestions:", data.suggested_questions);
```

### cURL
```bash
# Query endpoint
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How do I reset my password?"}'

# Analytics
curl http://localhost:8000/analytics/summary

# Upload documents
curl -X POST http://localhost:8000/upload-documents \
  -F "files=@FAQ.pdf"
```

---

## 📊 Rate Limiting & Performance

- **No rate limiting** on development server
- **Recommended**: Implement rate limiting in production
- **Cache TTL**: 24 hours (configurable)
- **Max file size**: Limited by server memory
- **Concurrent queries**: Limited by LLM API rate limits

---

## 🔐 Authentication

Currently no authentication required. For production, add:
- API key validation
- JWT tokens
- Rate limiting per key
- Request signing

---

## 📚 Documentation Files

- [NEW_FEATURES.md](NEW_FEATURES.md) - Detailed feature documentation
- [README.md](README.md) - Project overview
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Installation and deployment

---

## 🚀 Getting Started

1. **Start the server:**
   ```bash
   python backend.py
   ```

2. **Test the API:**
   ```bash
   python test_agent.py
   ```

3. **View Swagger UI:**
   ```
   http://localhost:8000/docs
   ```

4. **Make your first query:**
   ```bash
   curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question":"How can I help you?"}'
   ```

---

## 📞 Support

For issues or questions:
1. Check error messages in logs
2. Review [SETUP_GUIDE.md](SETUP_GUIDE.md)
3. Test with `test_agent.py`
4. Check API health with `/health` endpoint

---

**API Version: 1.0.0**  
**Last Updated: January 25, 2026**
