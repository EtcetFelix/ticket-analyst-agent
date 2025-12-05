from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ============================================================================
# Ticket Schemas
# ============================================================================

class TicketCreate(BaseModel):
    title: str
    description: str


class Ticket(BaseModel):
    id: int
    title: str
    description: str
    created_at: datetime


# ============================================================================
# Analysis Run Schemas
# ============================================================================

class AnalysisRun(BaseModel):
    id: int
    created_at: datetime
    summary: str


# ============================================================================
# Ticket Analysis Schemas
# ============================================================================

class TicketAnalysisCreate(BaseModel):
    analysis_run_id: int
    ticket_id: int
    category: str
    priority: str
    notes: Optional[str] = None


class TicketAnalysis(BaseModel):
    id: int
    analysis_run_id: int
    ticket_id: int
    category: str
    priority: str
    notes: Optional[str] = None


# ============================================================================
# Combined Response Schemas
# ============================================================================

class TicketWithAnalysis(BaseModel):
    """Ticket with its analysis results"""
    id: int
    title: str
    description: str
    created_at: datetime
    category: str
    priority: str
    notes: Optional[str] = None


class LatestAnalysisResponse(BaseModel):
    """Complete analysis run with all ticket results"""
    analysis_run_id: int
    created_at: datetime
    summary: str
    tickets: List[TicketWithAnalysis]