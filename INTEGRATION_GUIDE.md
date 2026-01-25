# 🔌 Integration Guide - Using New Features

**For Frontend & Application Developers**

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Feature Integration Examples](#feature-integration-examples)
3. [Dashboard Implementation](#dashboard-implementation)
4. [Best Practices](#best-practices)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Basic Query with All Features

**JavaScript/Fetch:**
```javascript
async function askAgent(question) {
  const response = await fetch('http://localhost:8000/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: question,
      customer_id: 'user_123'
    })
  });
  
  const data = await response.json();
  
  return {
    answer: data.response,
    sources: data.sources,
    sentiment: data.sentiment,
    suggestions: data.suggested_questions,
    cached: data.from_cache,
    steps: data.reasoning_steps
  };
}
```

**Python/Requests:**
```python
import requests

def ask_agent(question, customer_id=None):
    response = requests.post('http://localhost:8000/query', json={
        'question': question,
        'customer_id': customer_id
    })
    
    data = response.json()
    return {
        'answer': data['response'],
        'sentiment': data['sentiment'],
        'suggestions': data['suggested_questions'],
        'sources': data['sources'],
        'cached': data['from_cache']
    }
```

---

## Feature Integration Examples

### 1. 💬 Adding Feedback System

#### Frontend (HTML/JS):
```html
<div id="response-area">
  <p id="answer"></p>
  
  <!-- Feedback Section -->
  <div class="feedback-section" style="margin-top: 20px; padding: 15px; border-top: 1px solid #ccc;">
    <p>Was this helpful?</p>
    <div class="rating-stars">
      <button class="star" onclick="submitFeedback(1)">⭐</button>
      <button class="star" onclick="submitFeedback(2)">⭐⭐</button>
      <button class="star" onclick="submitFeedback(3)">⭐⭐⭐</button>
      <button class="star" onclick="submitFeedback(4)">⭐⭐⭐⭐</button>
      <button class="star" onclick="submitFeedback(5)">⭐⭐⭐⭐⭐</button>
    </div>
    <textarea id="feedback-comment" placeholder="Additional comments (optional)"></textarea>
    <button onclick="submitFeedbackWithComment()">Submit Feedback</button>
  </div>
</div>

<script>
let currentConversationId = null;
let currentQuery = null;
let currentResponse = null;

async function submitFeedback(rating) {
  const response = await fetch('http://localhost:8000/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_id: currentConversationId,
      query: currentQuery,
      response: currentResponse,
      rating: rating,
      comment: null
    })
  });
  
  const data = await response.json();
  alert('Thank you for your feedback!');
}

async function submitFeedbackWithComment() {
  const comment = document.getElementById('feedback-comment').value;
  await submitFeedback(5); // Or get rating from UI
}
</script>
```

**Python Backend Integration:**
```python
from fastapi import FastAPI
import requests

@app.post("/api/submit-feedback")
def save_feedback(conversation_id: str, rating: int, comment: str):
    # Forward to main API
    response = requests.post(
        'http://localhost:8000/feedback',
        json={
            'conversation_id': conversation_id,
            'query': 'query_text',
            'response': 'response_text',
            'rating': rating,
            'comment': comment
        }
    )
    return response.json()
```

---

### 2. 🧠 Using Sentiment Analysis

#### Frontend:
```javascript
async function displayResponseWithSentiment(data) {
  const answerDiv = document.getElementById('answer');
  answerDiv.innerHTML = `
    <p>${data.response}</p>
    <div style="margin-top: 10px; padding: 10px; background: rgba(0,0,0,0.1); border-radius: 5px;">
      <small>
        <strong>Sentiment:</strong> ${data.sentiment}
      </small>
    </div>
  `;
  
  // Show different UI based on sentiment
  if (data.sentiment.includes('negative')) {
    answerDiv.style.borderLeft = '4px solid red';
  } else if (data.sentiment.includes('positive')) {
    answerDiv.style.borderLeft = '4px solid green';
  }
}
```

#### Analytics Dashboard:
```javascript
async function loadSentimentDashboard() {
  const response = await fetch('http://localhost:8000/analytics/sentiment');
  const data = await response.json();
  
  // Show sentiment distribution
  const chart = {
    labels: data.sentiment_distribution.map(s => s.sentiment),
    values: data.sentiment_distribution.map(s => s.count)
  };
  
  // Render with Chart.js, Plotly, or similar
  renderChart(chart);
  
  // Show trend
  const trend = data.sentiment_trend_7_days;
  console.log('7-day sentiment trend:', trend);
}
```

---

### 3. ⚡ Leveraging Response Caching

#### Frontend:
```javascript
async function askWithCacheIndicator(question) {
  const data = await askAgent(question);
  
  const badge = document.createElement('span');
  if (data.cached) {
    badge.innerHTML = '⚡ From Cache (instant response)';
    badge.style.color = 'green';
  } else {
    badge.innerHTML = '🔄 Fresh Response';
    badge.style.color = 'blue';
  }
  
  document.getElementById('status').appendChild(badge);
  
  return data;
}
```

#### Performance Monitoring:
```javascript
async function checkCachePerformance() {
  const response = await fetch('http://localhost:8000/cache-status');
  const data = await response.json();
  
  console.log(`Cache Hit Rate: ${data.cache_metrics.cache_hit_rate}%`);
  console.log(`Cached Responses: ${data.cache_metrics.total_cached_responses}`);
  console.log(`Total Hits: ${data.cache_metrics.total_cache_hits}`);
  
  // Display to admins
  updateAdminDashboard({
    cacheHitRate: data.cache_metrics.cache_hit_rate,
    responsesServed: data.cache_metrics.total_cached_responses
  });
}
```

---

### 4. 💡 Displaying Suggested Questions

#### Frontend:
```html
<div id="suggestions">
  <h4>Suggested Follow-up Questions:</h4>
  <div id="suggestions-list"></div>
</div>

<script>
async function displaySuggestions(data) {
  const list = document.getElementById('suggestions-list');
  list.innerHTML = '';
  
  data.suggested_questions.forEach(question => {
    const button = document.createElement('button');
    button.className = 'suggestion-button';
    button.textContent = question;
    button.onclick = () => askAgent(question);
    button.style.cssText = `
      display: block;
      width: 100%;
      padding: 10px;
      margin: 8px 0;
      background: #f0f0f0;
      border: 1px solid #ddd;
      border-radius: 5px;
      cursor: pointer;
      text-align: left;
    `;
    
    list.appendChild(button);
  });
}

// After getting response:
async function processResponse(question) {
  const data = await askAgent(question);
  displayAnswer(data.answer);
  displaySuggestions(data);
}
```

---

### 5. 🌍 Multi-Language Support

#### Frontend:
```javascript
async function translateResponse(text, language) {
  const response = await fetch('http://localhost:8000/translate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: text,
      target_language: language
    })
  });
  
  const data = await response.json();
  return data.translated_text;
}

// Language selector
async function changeResponseLanguage(language) {
  const originalResponse = document.getElementById('answer').textContent;
  const translated = await translateResponse(originalResponse, language);
  
  document.getElementById('answer').innerHTML = `
    <p>${translated}</p>
    <small style="color: gray;">Translated to ${language}</small>
  `;
}
```

#### Auto-Detection:
```javascript
async function getAutoDetectedLanguage(text) {
  // Language is auto-detected on backend
  // Just use the sentiment sentiment.query_sentiment field
  // which is logged during /query call
  
  // Or call analytics to see detected languages
  const analytics = await fetch('http://localhost:8000/analytics/sentiment');
  const data = await analytics.json();
  
  // Backend processes in user's detected language
  return data;
}
```

---

## Dashboard Implementation

### Complete Analytics Dashboard

```html
<!DOCTYPE html>
<html>
<head>
  <title>Support Agent Analytics</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>

<h1>Support Agent Analytics Dashboard</h1>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px;">
  
  <!-- Overall Metrics -->
  <div class="metric-card">
    <h3>Overall Metrics</h3>
    <div id="overall-metrics"></div>
  </div>
  
  <!-- Sentiment Trend -->
  <div class="metric-card">
    <h3>Sentiment Trend (7 Days)</h3>
    <canvas id="sentiment-chart"></canvas>
  </div>
  
  <!-- Rating Distribution -->
  <div class="metric-card">
    <h3>Rating Distribution</h3>
    <canvas id="rating-chart"></canvas>
  </div>
  
  <!-- Cache Performance -->
  <div class="metric-card">
    <h3>Cache Performance</h3>
    <div id="cache-metrics"></div>
  </div>
  
</div>

<script>
async function loadDashboard() {
  // Load overall metrics
  const overall = await fetch('http://localhost:8000/analytics/summary').then(r => r.json());
  displayOverallMetrics(overall);
  
  // Load sentiment trends
  const sentiment = await fetch('http://localhost:8000/analytics/sentiment').then(r => r.json());
  displaySentimentChart(sentiment);
  
  // Load feedback
  const feedback = await fetch('http://localhost:8000/feedback/summary').then(r => r.json());
  displayRatingChart(feedback);
  
  // Load cache status
  const cache = await fetch('http://localhost:8000/cache-status').then(r => r.json());
  displayCacheMetrics(cache);
}

function displayOverallMetrics(data) {
  const html = `
    <p><strong>Total Queries:</strong> ${data.overall_metrics.total_queries}</p>
    <p><strong>Avg Response Time:</strong> ${data.overall_metrics.avg_response_time_ms.toFixed(0)}ms</p>
    <p><strong>Avg Rating:</strong> ${data.overall_metrics.avg_rating.toFixed(1)}/5.0</p>
    <p><strong>Cache Hit Rate:</strong> ${((data.cache_metrics.total_cache_hits / (data.cache_metrics.total_cached_responses + data.cache_metrics.total_cache_hits)) * 100).toFixed(1)}%</p>
  `;
  document.getElementById('overall-metrics').innerHTML = html;
}

function displaySentimentChart(data) {
  const labels = data.sentiment_trend_7_days.map(d => d.date);
  const scores = data.sentiment_trend_7_days.map(d => d.average_score);
  
  new Chart(document.getElementById('sentiment-chart'), {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Avg Sentiment Score',
        data: scores,
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1
      }]
    }
  });
}

function displayRatingChart(data) {
  const labels = Object.keys(data.rating_distribution);
  const values = Object.values(data.rating_distribution);
  
  new Chart(document.getElementById('rating-chart'), {
    type: 'bar',
    data: {
      labels: labels.map(l => l + ' ⭐'),
      datasets: [{
        label: 'Rating Count',
        data: values,
        backgroundColor: 'rgba(99, 102, 241, 0.5)'
      }]
    }
  });
}

function displayCacheMetrics(data) {
  const html = `
    <p><strong>Cache Hit Rate:</strong> ${data.cache_metrics.cache_hit_rate.toFixed(1)}%</p>
    <p><strong>Cached Responses:</strong> ${data.cache_metrics.total_cached_responses}</p>
    <p><strong>Cache Hits:</strong> ${data.cache_metrics.total_cache_hits}</p>
    <p><strong>Avg Hits/Query:</strong> ${data.cache_metrics.average_hits_per_query.toFixed(1)}</p>
  `;
  document.getElementById('cache-metrics').innerHTML = html;
}

// Load dashboard on page load
window.addEventListener('load', loadDashboard);

// Refresh every 30 seconds
setInterval(loadDashboard, 30000);
</script>

<style>
  body { font-family: Arial; margin: 20px; }
  .metric-card { border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9; }
  h3 { margin-top: 0; color: #333; }
</style>

</body>
</html>
```

---

## Best Practices

### 1. Error Handling
```javascript
async function askAgentSafely(question) {
  try {
    const response = await askAgent(question);
    return response;
  } catch (error) {
    console.error('Agent error:', error);
    
    // Fallback options
    if (error.response?.status === 500) {
      alert('Backend error. Please try again.');
    } else if (error.response?.status === 400) {
      alert('Invalid question format.');
    } else {
      alert('Network error. Please check your connection.');
    }
    
    return null;
  }
}
```

### 2. Rate Limiting (Client-side)
```javascript
let lastQueryTime = 0;
const MIN_QUERY_INTERVAL = 1000; // 1 second

async function askAgentRateLimited(question) {
  const now = Date.now();
  if (now - lastQueryTime < MIN_QUERY_INTERVAL) {
    console.warn('Too many requests. Please wait.');
    return null;
  }
  
  lastQueryTime = now;
  return askAgent(question);
}
```

### 3. Caching Strategy
```javascript
const responseCache = {};

async function askAgentWithCache(question) {
  const key = question.toLowerCase().trim();
  
  if (key in responseCache) {
    return { ...responseCache[key], from_local_cache: true };
  }
  
  const data = await askAgent(question);
  responseCache[key] = data;
  return data;
}
```

### 4. Analytics Batching
```javascript
const analyticsBatch = [];

function trackEvent(eventType, data) {
  analyticsBatch.push({ type: eventType, data, timestamp: Date.now() });
}

async function flushAnalytics() {
  if (analyticsBatch.length === 0) return;
  
  // Send all at once
  await fetch('/api/analytics/batch', {
    method: 'POST',
    body: JSON.stringify(analyticsBatch)
  });
  
  analyticsBatch.length = 0;
}

// Flush every 5 minutes or when batch reaches 50 items
setInterval(flushAnalytics, 300000);
```

---

## Troubleshooting

### Issue: Cache not working
**Solution:**
```javascript
// Debug cache status
async function debugCache() {
  const status = await fetch('http://localhost:8000/cache-status').then(r => r.json());
  console.log('Cache status:', status);
  
  if (status.cache_metrics.total_cached_responses === 0) {
    console.warn('Cache is empty. Submit some queries first.');
  }
}

debugCache();
```

### Issue: Sentiment always "neutral"
**Solution:**
```javascript
// Check backend health
async function checkBackend() {
  const health = await fetch('http://localhost:8000/health').then(r => r.json());
  console.log('Backend status:', health);
  
  // Check OpenAI key
  const test = await fetch('http://localhost:8000/query', {
    method: 'POST',
    body: JSON.stringify({ question: 'test' })
  }).then(r => r.json());
  
  if (test.sentiment === 'neutral (0)') {
    console.warn('Sentiment analysis may not be working. Check OpenAI key.');
  }
}
```

### Issue: Suggestions not showing
**Solution:**
```javascript
// Verify suggestions are in response
const response = await askAgent('question');
if (response.suggested_questions?.length === 0) {
  console.warn('No suggestions generated. Response may be too short.');
}
```

---

## Complete Example App

```javascript
class SupportAgentUI {
  constructor() {
    this.conversationId = null;
    this.init();
  }
  
  async init() {
    document.getElementById('ask-button').addEventListener('click', () => this.handleQuery());
    document.getElementById('clear-button').addEventListener('click', () => this.clearChat());
  }
  
  async handleQuery() {
    const question = document.getElementById('question-input').value;
    if (!question) return;
    
    // Show loading
    this.showLoading(true);
    
    const response = await askAgent(question);
    this.conversationId = response.conversation_id;
    
    // Display response
    this.displayResponse(response);
    
    // Display suggestions
    this.displaySuggestions(response.suggested_questions);
    
    // Clear input
    document.getElementById('question-input').value = '';
    
    this.showLoading(false);
  }
  
  displayResponse(response) {
    const html = `
      <div class="message assistant">
        <p>${response.response}</p>
        <small style="color: gray;">
          ${response.from_cache ? '⚡ Cached' : '🔄 Fresh'} |
          ${response.sentiment}
        </small>
      </div>
    `;
    document.getElementById('chat').innerHTML += html;
  }
  
  displaySuggestions(suggestions) {
    if (suggestions.length === 0) return;
    
    let html = '<div class="suggestions"><p>Follow-up questions:</p>';
    suggestions.forEach(q => {
      html += `<button onclick="askQuestion('${q}')">${q}</button>`;
    });
    html += '</div>';
    
    document.getElementById('chat').innerHTML += html;
  }
  
  async submitFeedback(rating) {
    if (!this.conversationId) return;
    
    await fetch('http://localhost:8000/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: this.conversationId,
        query: this.lastQuery,
        response: this.lastResponse,
        rating: rating
      })
    });
    
    alert('Thank you for your feedback!');
  }
  
  showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
  }
  
  clearChat() {
    document.getElementById('chat').innerHTML = '';
  }
}

// Initialize
const agent = new SupportAgentUI();
```

---

## Summary

The new features are designed to be easily integrated:

1. **Feedback** - Add ratings buttons after responses
2. **Sentiment** - Show sentiment badges or use in logic
3. **Caching** - Show "cached" indicator to users
4. **Analytics** - Build dashboards with `/analytics/*` endpoints
5. **Languages** - Add language selector with `/translate`
6. **Suggestions** - Display as clickable buttons
7. **Metrics** - Real-time monitoring for admins

All features are **backward compatible** and work together seamlessly!

---

**Happy integrating! 🚀**
