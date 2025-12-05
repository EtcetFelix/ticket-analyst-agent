import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.config import settings
from app.models import (
    Ticket,
    TicketCreate,
    AnalysisRun,
    TicketAnalysis,
    TicketAnalysisCreate,
    TicketWithAnalysis,
    LatestAnalysisResponse,
)


def get_db_connection():
    """Create a new database connection"""
    return psycopg2.connect(
        settings.DATABASE_URL,
        cursor_factory=RealDictCursor  # Returns rows as dicts
    )


# ============================================================================
# Ticket Operations
# ============================================================================

def insert_tickets(tickets: List[TicketCreate]) -> List[Ticket]:
    """Insert multiple tickets and return them with IDs"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    inserted = []
    try:
        for ticket in tickets:
            cur.execute(
                """
                INSERT INTO tickets (title, description, created_at)
                VALUES (%s, %s, NOW())
                RETURNING id, title, description, created_at
                """,
                (ticket.title, ticket.description)
            )
            row = cur.fetchone()
            inserted.append(Ticket(**row))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
    
    return inserted


def get_all_tickets() -> List[Ticket]:
    """Fetch all tickets from the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            "SELECT id, title, description, created_at FROM tickets ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
        return [Ticket(**row) for row in rows]
    finally:
        cur.close()
        conn.close()


def get_tickets_by_ids(ticket_ids: List[int]) -> List[Ticket]:
    """Fetch specific tickets by their IDs"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            SELECT id, title, description, created_at 
            FROM tickets 
            WHERE id = ANY(%s)
            ORDER BY created_at DESC
            """,
            (ticket_ids,)
        )
        rows = cur.fetchall()
        return [Ticket(**row) for row in rows]
    finally:
        cur.close()
        conn.close()


# ============================================================================
# Analysis Run Operations
# ============================================================================

def create_analysis_run(summary: str) -> AnalysisRun:
    """Create a new analysis run and return it"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO analysis_runs (summary, created_at)
            VALUES (%s, NOW())
            RETURNING id, created_at, summary
            """,
            (summary,)
        )
        row = cur.fetchone()
        conn.commit()
        return AnalysisRun(**row)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


# ============================================================================
# Ticket Analysis Operations
# ============================================================================

def insert_ticket_analysis(
    analysis_run_id: int,
    ticket_id: int,
    category: str,
    priority: str,
    notes: Optional[str] = None
) -> TicketAnalysis:
    """Insert a ticket analysis result"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO ticket_analysis (analysis_run_id, ticket_id, category, priority, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, analysis_run_id, ticket_id, category, priority, notes
            """,
            (analysis_run_id, ticket_id, category, priority, notes)
        )
        row = cur.fetchone()
        conn.commit()
        return TicketAnalysis(**row)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def bulk_insert_ticket_analysis(analyses: List[TicketAnalysisCreate]) -> List[TicketAnalysis]:
    """Insert multiple ticket analyses in a single transaction"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    inserted = []
    try:
        for analysis in analyses:
            cur.execute(
                """
                INSERT INTO ticket_analysis (analysis_run_id, ticket_id, category, priority, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, analysis_run_id, ticket_id, category, priority, notes
                """,
                (
                    analysis.analysis_run_id,
                    analysis.ticket_id,
                    analysis.category,
                    analysis.priority,
                    analysis.notes,
                )
            )
            row = cur.fetchone()
            inserted.append(TicketAnalysis(**row))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
    
    return inserted


# ============================================================================
# Combined Query Operations
# ============================================================================

def get_latest_analysis() -> Optional[LatestAnalysisResponse]:
    """
    Get the most recent analysis run with all its ticket analyses.
    Returns None if no analysis runs exist.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # First, get the latest analysis run
        cur.execute(
            """
            SELECT id, created_at, summary
            FROM analysis_runs
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        run_row = cur.fetchone()
        
        if not run_row:
            return None
        
        analysis_run = AnalysisRun(**run_row)
        
        # Then get all ticket analyses for this run with ticket details
        cur.execute(
            """
            SELECT 
                t.id,
                t.title,
                t.description,
                t.created_at,
                ta.category,
                ta.priority,
                ta.notes
            FROM ticket_analysis ta
            JOIN tickets t ON ta.ticket_id = t.id
            WHERE ta.analysis_run_id = %s
            ORDER BY t.created_at DESC
            """,
            (analysis_run.id,)
        )
        ticket_rows = cur.fetchall()
        
        tickets = [TicketWithAnalysis(**row) for row in ticket_rows]
        
        return LatestAnalysisResponse(
            analysis_run_id=analysis_run.id,
            created_at=analysis_run.created_at,
            summary=analysis_run.summary,
            tickets=tickets,
        )
    finally:
        cur.close()
        conn.close()