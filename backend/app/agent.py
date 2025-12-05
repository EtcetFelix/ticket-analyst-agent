# backend/app/agent.py
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator

from app.models import Ticket, TicketAnalysisCreate
from app.db import (
    get_tickets_by_ids,
    get_all_tickets,
    create_analysis_run,
    bulk_insert_ticket_analysis,
)


# ============================================================================
# Agent State Definition
# ============================================================================

class AgentState(TypedDict):
    """State passed between nodes in the analysis graph"""
    ticket_ids: Optional[List[int]]  # If None, analyze all tickets
    tickets: List[Ticket]  # Fetched tickets to analyze
    run_id: Optional[int]  # Created analysis run ID
    summary: str  # Overall summary of the analysis
    analyses: List[TicketAnalysisCreate]  # Per-ticket analysis results


# ============================================================================
# Node Functions
# ============================================================================

def fetch_tickets_node(state: AgentState) -> AgentState:
    """
    Node 1: Fetch tickets from the database.
    If ticket_ids is provided, fetch only those. Otherwise, fetch all.
    """
    ticket_ids = state.get("ticket_ids")
    
    if ticket_ids:
        tickets = get_tickets_by_ids(ticket_ids)
    else:
        tickets = get_all_tickets()
    
    return {
        **state,
        "tickets": tickets,
    }


def analyze_tickets_node(state: AgentState) -> AgentState:
    """
    Node 2: Analyze each ticket using keyword-based classification.
    
    NOTE: This uses simple keyword matching instead of a real LLM to avoid
    needing API keys for the take-home. In production, this would call
    Claude/GPT with a structured prompt.
    
    Category logic:
    - billing: "billing", "payment", "card", "charge", "invoice"
    - bug: "bug", "crash", "error", "broken", "not working"
    - feature_request: "feature", "request", "add", "want", "could you"
    
    Priority logic:
    - high: "urgent", "asap", "critical", "immediately", "production"
    - medium: everything else (default)
    - low: "minor", "eventually", "nice to have"
    """
    tickets = state["tickets"]
    analyses = []
    
    # Category and priority keywords
    category_keywords = {
        "billing": ["billing", "payment", "card", "charge", "invoice", "refund", "subscription"],
        "bug": ["bug", "crash", "error", "broken", "not working", "fails", "doesn't work"],
        "feature_request": ["feature", "request", "add", "want", "could you", "suggestion", "enhance"],
    }
    
    priority_keywords = {
        "high": ["urgent", "asap", "critical", "immediately", "production", "down", "outage"],
        "low": ["minor", "eventually", "nice to have", "sometime", "when possible"],
    }
    
    for ticket in tickets:
        # Combine title and description for analysis
        text = f"{ticket.title} {ticket.description}".lower()
        
        # Determine category
        category = "general"  # default
        for cat, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                category = cat
                break
        
        # Determine priority
        priority = "medium"  # default
        for pri, keywords in priority_keywords.items():
            if any(keyword in text for keyword in keywords):
                priority = pri
                break
        
        # Generate notes explaining the classification
        notes = f"Classified based on keywords. Category: {category}, Priority: {priority}."
        
        analyses.append(
            TicketAnalysisCreate(
                analysis_run_id=0,  # Will be updated in save_results_node
                ticket_id=ticket.id,
                category=category,
                priority=priority,
                notes=notes,
            )
        )
    
    # Generate overall summary
    total = len(tickets)
    high_priority = sum(1 for a in analyses if a.priority == "high")
    categories = {}
    for a in analyses:
        categories[a.category] = categories.get(a.category, 0) + 1
    
    category_summary = ", ".join(f"{count} {cat}" for cat, count in categories.items())
    summary = (
        f"Analyzed {total} ticket(s). "
        f"Found {high_priority} high-priority issue(s). "
        f"Breakdown: {category_summary}."
    )
    
    return {
        **state,
        "summary": summary,
        "analyses": analyses,
    }


def save_results_node(state: AgentState) -> AgentState:
    """
    Node 3: Save the analysis results to the database.
    Creates an analysis_run record and inserts all ticket analyses.
    """
    summary = state["summary"]
    analyses = state["analyses"]
    
    # Create the analysis run
    analysis_run = create_analysis_run(summary)
    
    # Update all analyses with the correct run_id
    for analysis in analyses:
        analysis.analysis_run_id = analysis_run.id
    
    # Bulk insert all ticket analyses
    bulk_insert_ticket_analysis(analyses)
    
    return {
        **state,
        "run_id": analysis_run.id,
    }


# ============================================================================
# Graph Definition
# ============================================================================

def create_analysis_graph():
    """
    Build the LangGraph state graph for ticket analysis.
    
    Flow: fetch_tickets -> analyze_tickets -> save_results -> END
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("fetch_tickets", fetch_tickets_node)
    workflow.add_node("analyze_tickets", analyze_tickets_node)
    workflow.add_node("save_results", save_results_node)
    
    # Define edges (linear flow)
    workflow.set_entry_point("fetch_tickets")
    workflow.add_edge("fetch_tickets", "analyze_tickets")
    workflow.add_edge("analyze_tickets", "save_results")
    workflow.add_edge("save_results", END)
    
    return workflow.compile()


# ============================================================================
# Public API
# ============================================================================

# Create the compiled graph once at module load
analysis_graph = create_analysis_graph()


def run_agent(ticket_ids: Optional[List[int]] = None) -> dict:
    """
    Run the ticket analysis agent.
    
    Args:
        ticket_ids: Optional list of specific ticket IDs to analyze.
                   If None, analyzes all tickets.
    
    Returns:
        dict with:
            - run_id: The created analysis_run ID
            - summary: Overall summary text
            - ticket_count: Number of tickets analyzed
    """
    # Initialize state
    initial_state: AgentState = {
        "ticket_ids": ticket_ids,
        "tickets": [],
        "run_id": None,
        "summary": "",
        "analyses": [],
    }
    
    # Run the graph
    final_state = analysis_graph.invoke(initial_state)
    
    return {
        "run_id": final_state["run_id"],
        "summary": final_state["summary"],
        "ticket_count": len(final_state["tickets"]),
    }