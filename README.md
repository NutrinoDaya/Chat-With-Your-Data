# Chat With Your Data

A production-ready data analytics assistant that combines SQL analytics with semantic search capabilities. Built with FastAPI, React, and modern AI technologies.

## Overview

This system transforms how you interact with your data by providing natural language querying capabilities across multiple data sources. It automatically detects query intent, applies time filtering, and presents results in the most appropriate format - whether that's text, tables, or interactive charts.

### Key Features

- **Query Processing**: Automatically detects whether you need SQL analytics or semantic search
- **Time Filtering**: Supports precise time ranges (past X seconds/minutes/hours/days)
- ** Conversation Memory**: Maintains context across multiple questions for natural follow-ups
- ** Multi-Format Responses**: Returns data as text, tables, or charts based on your query
- ** Auto Source Detection**: Automatically routes queries to the right data source
- **Caching**: Context-aware caching with pattern learning for performance
- ** Real-time Data**: Live data ingestion for up-to-date analytics

## Architecture

### Core Components

**Backend (FastAPI)**
- Query processing with conversation memory
- Hybrid RAG + SQL execution engine
- Schema-aware SQL generation
- Real-time chart generation
- Context-aware caching system

**Frontend (React + TypeScript)**
- Clean, responsive chat interface
- Real-time chart and table rendering
- Session-based conversation tracking
- Auto-detection of query types

**Data Layer**
- **DuckDB**: High-performance analytics database
- **Qdrant**: Vector database for semantic search
- **Redis**: Caching and session management

**AI Services**
- **TinyLlama**: Local LLM for query processing
- **BGE Embeddings**: Semantic understanding
- **LMCache**: Query pattern optimization

## Quick Start

### Prerequisites
- **Docker & Docker Compose** (required)
- 8GB+ RAM recommended  
- Modern web browser

> **Note**: This project only supports Docker deployment. All services are containerized for consistent deployment across environments.

### Launch the System

```bash
# 1. Clone the repository
git clone https://github.com/NutrinoDaya/Chat-With-Your-Data.git
cd Chat-With-Your-Data

# 2. Start all services with Docker Compose
docker-compose up --build

# 3. Wait for all services to initialize (may take 2-3 minutes for first run)
# Services will be available at:
# • Frontend: http://localhost:5173
# • Backend API: http://localhost:8001  
# • Qdrant Vector DB: http://localhost:6333
```

### Verify Installation

Once all containers are running, visit `http://localhost:5173` and try these sample queries:

```
"How many orders did we receive today?"
"Show me revenue by customer as a chart"  
"What devices are currently active?"
```

### Optional: Generate Additional Sample Data

```bash
# Run from your host machine (not inside containers)
python data_generators/financial_generator.py
python data_generators/devices_generator.py
```

## Usage Examples

### Financial Analytics

**Basic Queries:**
```
"How many orders did we receive today?"
→ Count: 1,084

"What's our total revenue today?"
→ Total: $2,743,773.71

"Show me revenue breakdown by customer as a chart"
→ [Interactive bar chart displayed]
```

**Time-Specific Queries:**
```
"How many orders in the past 1 minute?"
→ Count: 0

"Revenue for the past hour?"
→ Total: $45,230.50

"Orders in the past 30 seconds?"
→ Count: 0
```

**Conversation Flow:**
```
User: "How many orders today?"
Assistant: "Count: 1,084"

User: "What about the past hour?"
Assistant: "Count: 23" (understands context from previous question)

User: "Show that as a chart"
Assistant: [Generates and displays chart]
```

### Device Analytics

```
"How many devices are online?"
"Device status breakdown"
"Average uptime by location"
"Show device metrics as a table"
```

### Core Features

**Multi-format Responses:**
- Text responses for counts and simple metrics
- Tables for detailed breakdowns
- Charts for visual analytics
- SQL query display for transparency

**Caching:**
- Conversation-aware cache keys
- Pattern learning from query history
- Sub-second response times for repeated queries

## API Reference

### Core Endpoint

```http
POST /chat/ask
Content-Type: application/json

{
  "message": "How many orders today?",
  "source": "auto",  // "auto", "financial", "devices"
  "mode": "auto",    // "auto", "text", "table", "chart"
  "session_id": "optional_session_id"
}
```

**Response Types:**

```json
// Text Response
{
  "mode": "text",
  "text": "Count: 1,084",
  "query_sql": "SELECT COUNT(*) FROM financial_orders WHERE..."
}

// Chart Response
{
  "mode": "chart", 
  "chart_path": "chart_123456.png",
  "query_sql": "SELECT customer, SUM(amount)..."
}

// Table Response
{
  "mode": "table",
  "table": {
    "columns": ["customer", "revenue"],
    "rows": [["TechCorp", 50000], ["DataSys", 35000]]
  },
  "query_sql": "SELECT customer, SUM(amount)..."
}
```

### Additional Endpoints

```http
GET /chat/stats                    # System performance metrics
GET /chat/history/{session_id}     # Conversation history
DELETE /chat/history/{session_id}  # Clear conversation
GET /static/charts/{filename}      # Chart image access
```

## Technical Details

### Data Processing Pipeline

1. **Schema Ingestion**: Table schemas and query patterns stored in vector database
2. **Query Analysis**: Intent detection using conversation context and schema awareness
3. **SQL Generation**: Context-aware SQL generation with proper time filtering
4. **Execution**: Query execution with error handling and fallbacks
5. **Response Formatting**: Response formatting based on data and query type

### Time Filtering Engine

Supports natural language time expressions:
- "today", "yesterday"
- "past X seconds/minutes/hours/days/weeks"
- "last X minutes/hours"
- Automatic SQL generation: `ts >= '2025-08-16 23:15:30'`

### Conversation Memory

- Session-based conversation tracking
- Context-aware response generation
- Support for follow-up questions
- Cache invalidation based on conversation flow

### Performance Optimizations

- **Query Caching**: Context-aware with 1-hour TTL
- **Pattern Learning**: Automatic optimization of common query types
- **Connection Pooling**: Efficient database connections
- **Static File Serving**: Optimized chart delivery

## Deployment Options

### Local Development (Full Features)
- Uses local LLM via vLLM for zero API costs
- Complete functionality including AI-generated responses
- Recommended for development and testing

### Demo/Cloud Deployment (No LLM Required)
- Set `DEMO_MODE=true` for realistic hardcoded responses
- Perfect for portfolio demonstrations and resume showcasing
- No API keys or expensive GPU instances required
- Deploys easily on platforms like Railway, Render, or Vercel

### Production Deployment

> **All deployments use Docker Compose** - no manual installation of Python, Node.js, or other dependencies required.

#### Option 1: Full Local Deployment (Recommended)
```bash
# Complete system with local LLM (zero API costs)
docker-compose up --build -d

# View logs
docker-compose logs -f
```

#### Option 2: Cloud Deployment with External LLM
```bash
# Modify docker-compose.yml to use external APIs
# Set environment variables:
export PROVIDER=openai
export OPENAI_API_KEY=your_key_here

docker-compose up --build -d
```

#### Option 3: Demo Mode (Portfolio/Showcase)
```bash
# No LLM required - uses realistic demo responses
export DEMO_MODE=true
export PROVIDER=demo

docker-compose up --build -d
```

## Configuration

### Environment Variables

```bash
# Core Configuration
BACKEND_PORT=8001
FRONTEND_PORT=5173
QDRANT_URL=http://qdrant:6333
DUCKDB_PATH=/app/data/analytics.duckdb

# AI Configuration  
VLLM_URL=http://vllm:8000
MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Optional
HF_TOKEN=your_huggingface_token
REDIS_URL=redis://redis:6379
```

### Docker Compose Production

```yaml
# Key production settings included:
# - Health checks for all services
# - Proper dependency management
# - Volume persistence
# - Resource limits
# - Restart policies
```

### Monitoring

Access built-in metrics:
- Cache hit rates and performance
- Query pattern analysis
- Conversation statistics
- System health status

## Development

### Project Structure

```
├── backend/
│   ├── src/app/
│   │   ├── routes/          # API endpoints
│   │   ├── services/        # Core business logic
│   │   ├── providers/       # AI service integrations
│   │   └── utils/           # Helper functions
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/          # Page components
│   │   ├── lib/            # API client
│   │   └── styles/         # SCSS styling
│   └── package.json
└── docker-compose.yml
```

### Key Technologies

- **Backend**: FastAPI, SQLAlchemy, Pydantic, DuckDB
- **Frontend**: React 19, TypeScript, Vite, SCSS
- **AI/ML**: Transformers, Sentence-Transformers, vLLM
- **Databases**: DuckDB (analytics), Qdrant (vectors), Redis (cache)
- **Infrastructure**: Docker, Docker Compose

## Troubleshooting

### Common Docker Issues

**Services not starting:**
```bash
# Check Docker is running
docker --version
docker-compose --version

# Check container logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs vllm
```

**Port conflicts:**
```bash
# Stop existing services
docker-compose down

# Check ports in use
netstat -tulpn | grep :5173
netstat -tulpn | grep :8001
```

**Out of memory errors:**
```bash
# Increase Docker memory limit to 8GB+
# Docker Desktop -> Settings -> Resources -> Memory

# Or reduce services
docker-compose up frontend backend qdrant redis
```

**LLM download issues:**
```bash
# Check internet connection and retry
docker-compose pull vllm
docker-compose up vllm --build
```

### Reset Everything

```bash
# Complete reset (removes all data)
docker-compose down -v
docker system prune -f
docker-compose up --build
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built for production use** - Combines the precision of SQL with the flexibility of natural language processing.