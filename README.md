# Support Ticket Analyst

An AI-powered support ticket analysis system that automatically categorizes and prioritizes customer support tickets using LangGraph and OpenAI GPT-4.

## 🚀 Quickstart

### Prerequisites

- Docker & Docker Compose
- OpenAI API key

### Running the Application

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ticket-analyst-agent
   ```

2. **Set up environment variables**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env and add your OPENAI_API_KEY
   ```

3. **Start all services**
   ```bash
   docker compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

The database will automatically initialize with sample tickets on first run.

## 📋 Configuration

### Environment Variables

Create a `backend/.env` file with:

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/support_tickets
OPENAI_API_KEY=sk-proj-your-key-here
```

### Default Ports

- **PostgreSQL**: 5432
- **Backend (FastAPI)**: 8000
- **Frontend (React)**: 3000

## 🏗️ Architecture

### Tech Stack

**Backend:**
- Python 3.12
- FastAPI (REST API)
- LangGraph (Agent orchestration)
- OpenAI GPT-4o-mini (Classification)
- PostgreSQL + psycopg2 (Database)
- Pydantic (Data validation)

**Frontend:**
- React 18 + TypeScript
- Vite (Build tool)
- Nginx (Production server)

**Infrastructure:**
- Docker & Docker Compose
- Multi-stage builds for optimization

### Database Schema

```sql
tickets
├─ id (SERIAL PRIMARY KEY)
├─ title (TEXT)
├─ description (TEXT)
└─ created_at (TIMESTAMP)

analysis_runs
├─ id (SERIAL PRIMARY KEY)
├─ created_at (TIMESTAMP)
└─ summary (TEXT)

ticket_analysis
├─ id (SERIAL PRIMARY KEY)
├─ analysis_run_id (FK → analysis_runs)
├─ ticket_id (FK → tickets)
├─ category (TEXT)
├─ priority (TEXT)
└─ notes (TEXT)
```

### LangGraph Agent Flow

The agent uses a 3-node linear workflow:

```
┌─────────────────┐
│ fetch_tickets   │ ← Fetch tickets from DB (all or filtered)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ analyze_tickets │ ← Classify each ticket using OpenAI
└────────┬────────┘   - Category: billing, bug, feature_request, general
         │            - Priority: high, medium, low
         │            - Reasoning: Brief explanation
         ▼
┌─────────────────┐
│ save_results    │ ← Create analysis_run + bulk insert results
└────────┬────────┘
         │
         ▼
        END
```

**State Management:**
```python
AgentState:
  - ticket_ids: Optional[List[int]]  # Filter specific tickets
  - tickets: List[Ticket]            # Fetched tickets
  - run_id: int                      # Created analysis run ID
  - summary: str                     # Overall summary
  - analyses: List[TicketAnalysisCreate]  # Individual results
```

### OpenAI Integration

The agent uses **GPT-4o-mini** with **structured outputs** (JSON schema enforcement):

```python
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "ticket_classification",
        "schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": [...]},
                "priority": {"type": "string", "enum": [...]},
                "reasoning": {"type": "string"}
            },
            "required": ["category", "priority", "reasoning"]
        }
    }
}
```

This ensures reliable, parseable responses with no fallback logic needed.

## 🔌 API Endpoints

### POST `/api/tickets`

Create one or more support tickets.

**Request:**
```json
{
  "tickets": [
    {
      "title": "Cannot login to account",
      "description": "Getting password error for past hour"
    }
  ]
}
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "title": "Cannot login to account",
    "description": "Getting password error for past hour",
    "created_at": "2024-12-04T23:30:00Z"
  }
]
```

### GET `/api/tickets`

List all support tickets.

**Response:** `200 OK` - Array of tickets

### POST `/api/analyze`

Run the LangGraph agent to analyze tickets.

**Request (optional):**
```json
{
  "ticket_ids": [1, 2, 3]  // Optional: analyze specific tickets
}
```

**Response:** `200 OK`
```json
{
  "run_id": 5,
  "summary": "Analyzed 3 ticket(s). Priority breakdown: 1 high, 2 medium, 0 low. Categories: 2 bug, 1 billing.",
  "ticket_count": 3
}
```

### GET `/api/analysis/latest`

Get the most recent analysis run with full results.

**Response:** `200 OK`
```json
{
  "analysis_run_id": 5,
  "created_at": "2024-12-04T23:35:00Z",
  "summary": "Analyzed 3 ticket(s)...",
  "tickets": [
    {
      "id": 1,
      "title": "Cannot login to account",
      "description": "...",
      "created_at": "2024-12-04T23:30:00Z",
      "category": "bug",
      "priority": "high",
      "notes": "Authentication failure affecting user access, requires immediate attention."
    }
  ]
}
```

## 📂 Project Structure

```
ticket-analyst-agent/
├── backend/
│   ├── app/
│   │   ├── agent.py       # LangGraph workflow definition
│   │   ├── config.py      # Settings & environment
│   │   ├── db.py          # Database CRUD operations
│   │   ├── main.py        # FastAPI app & endpoints
│   │   └── models.py      # Pydantic schemas
│   ├── tests/             # Test suite
│   ├── Dockerfile
│   └── pyproject.toml     # Poetry dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx        # Main React component
│   │   ├── App.css        # Styling
│   │   └── main.tsx       # Entry point
│   ├── Dockerfile
│   ├── nginx.conf         # Nginx configuration
│   └── package.json
├── db/
│   └── init.sql           # Database schema & seed data
├── docker-compose.yml
└── README.md
```

## ⚖️ Design Tradeoffs & Shortcuts

Due to the 3-hour time constraint, the following pragmatic decisions were made:

### What Was Prioritized

✅ **Real AI Integration**: Used actual OpenAI GPT-4o-mini instead of stubbing with keyword matching  
✅ **Production-Grade LangGraph**: Clean 3-node workflow with proper state management  
✅ **Structured Database**: Proper foreign keys, indexes, and normalized schema  
✅ **Type Safety**: Full Pydantic models and TypeScript throughout  
✅ **Containerization**: Everything runs in Docker with proper service isolation  

### Known Limitations

⚠️ **No Authentication**: User management would be added with JWT tokens  
⚠️ **Minimal Error Handling**: Production would need retry logic, circuit breakers, and graceful degradation  
⚠️ **No Tests for Agent**: Unit tests exist for CRUD, but LangGraph workflow needs integration tests  
⚠️ **Basic Styling**: Functional UI prioritized over polished design  
⚠️ **Synchronous Analysis**: Long-running analyses block the API (would use Celery/background tasks)  
⚠️ **No Rate Limiting**: OpenAI calls are unbounded (would add token bucket or leaky bucket)  
⚠️ **Hardcoded OpenAI Model**: Should be configurable via environment  
⚠️ **No Migrations Tool**: Using raw SQL (would use Alembic in production)  
⚠️ **No Logging/Monitoring**: Would add structured logging (loguru), metrics (Prometheus), and tracing (Jaeger)  

### Architecture Decisions

**Why LangGraph?**  
- Explicit state management makes the analysis flow debuggable
- Easy to extend with conditional branching or human-in-the-loop nodes
- Built-in checkpointing for reliability (not used here but available)

**Why FastAPI?**  
- Automatic OpenAPI docs (interactive at `/docs`)
- Native async support for future scalability
- Excellent type checking with Pydantic

**Why PostgreSQL over SQLite?**  
- Needed for production Docker environment
- Better concurrency handling
- Rich indexing capabilities

**Why Separate Frontend Container?**  
- Cleaner separation of concerns
- Easier to scale independently
- Nginx provides production-grade static file serving

## 📝 Notes

- The OpenAI API key in `.env` is **required** for the agent to work
- Database persists in a Docker volume (`postgres_data`)
- Frontend makes direct API calls to `http://localhost:8000` (configurable via `API_BASE`)
- Sample tickets are automatically loaded on first database initialization

---
