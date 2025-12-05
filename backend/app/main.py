from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel

from app.db import insert_tickets, get_all_tickets, get_latest_analysis
from app.models import TicketCreate, Ticket, LatestAnalysisResponse
from app.agent import run_agent

app = FastAPI(title="Support Ticket Analyst API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateTicketsRequest(BaseModel):
    tickets: List[TicketCreate]


class AnalyzeRequest(BaseModel):
    ticket_ids: Optional[List[int]] = None


class AnalyzeResponse(BaseModel):
    run_id: int
    summary: str
    ticket_count: int


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
def root():
    return {"message": "Support Ticket Analyst API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/tickets", response_model=List[Ticket])
def create_tickets(request: CreateTicketsRequest):
    """
    Create one or more support tickets.
    """
    try:
        tickets = insert_tickets(request.tickets)
        return tickets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tickets", response_model=List[Ticket])
def list_tickets():
    """
    Get all support tickets.
    """
    try:
        tickets = get_all_tickets()
        return tickets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_tickets(request: AnalyzeRequest = AnalyzeRequest()):
    """
    Run the LangGraph agent to analyze tickets.
    
    If ticket_ids is provided, only those tickets are analyzed.
    Otherwise, all tickets are analyzed.
    """
    try:
        result = run_agent(ticket_ids=request.ticket_ids)
        return AnalyzeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/latest", response_model=Optional[LatestAnalysisResponse])
def get_latest_analysis_results():
    """
    Get the most recent analysis run with all ticket results.
    Returns null if no analysis has been run yet.
    """
    try:
        result = get_latest_analysis()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))