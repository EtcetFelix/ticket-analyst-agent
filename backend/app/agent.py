from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from openai import OpenAI
from pydantic import BaseModel

from app.models import Ticket, TicketAnalysisCreate
from app.db import (
    get_tickets_by_ids,
    get_all_tickets,
    create_analysis_run,
    bulk_insert_ticket_analysis,
)
from app.config import settings


# ============================================================================
# OpenAI Client Setup
# ============================================================================

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ============================================================================
# Structured Output Schemas for LLM
# ============================================================================

class TicketClassification(BaseModel):
    """Structured output from LLM for a single ticket"""
    category: str  # billing, bug, feature_request, or general
    priority: str  # high, medium, or low
    reasoning: str  # Brief explanation of the classification


# ============================================================================
# Agent State Definition
# ============================================================================

class AgentState(TypedDict):
    """State passed between nodes in the analysis graph"""
    ticket_ids: Optional[List[int]]
    tickets: List[Ticket]
    run_id: Optional[int]
    summary: str
    analyses: List[TicketAnalysisCreate]


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


def classify_ticket_with_llm(ticket: Ticket) -> TicketClassification:
    """
    Use OpenAI to classify a single ticket with structured outputs.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Fast and cheap for this task
        messages=[
            {
                "role": "system",
                "content": """You are a support ticket classifier. Analyze the ticket and provide:
1. Category: Choose one of: billing, bug, feature_request, general
2. Priority: Choose one of: high, medium, low
3. Reasoning: Brief explanation (1-2 sentences)

Guidelines:
- billing: payment, subscription, refund issues
- bug: errors, crashes, things not working
- feature_request: new features, enhancements
- general: everything else

- high: urgent issues affecting production/revenue
- medium: important but not urgent
- low: minor issues, nice-to-haves"""
            },
            {
                "role": "user",
                "content": f"Title: {ticket.title}\n\nDescription: {ticket.description}"
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ticket_classification",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["billing", "bug", "feature_request", "general"]
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"]
                        },
                        "reasoning": {
                            "type": "string"
                        }
                    },
                    "required": ["category", "priority", "reasoning"],
                    "additionalProperties": False
                }
            }
        },
        temperature=0.3,
    )
    
    # Parse the structured response
    import json
    result = response.choices[0].message.content
    classification_dict = json.loads(result)
    return TicketClassification(**classification_dict)


def analyze_tickets_node(state: AgentState) -> AgentState:
    """
    Node 2: Analyze each ticket using OpenAI LLM with structured outputs.
    """
    tickets = state["tickets"]
    analyses = []
    
    for ticket in tickets:
        # Classify using LLM
        classification = classify_ticket_with_llm(ticket)
        
        analyses.append(
            TicketAnalysisCreate(
                analysis_run_id=0,  # Will be updated in save_results_node
                ticket_id=ticket.id,
                category=classification.category,
                priority=classification.priority,
                notes=classification.reasoning,
            )
        )
    
    # Generate overall summary
    total = len(tickets)
    high_priority = sum(1 for a in analyses if a.priority == "high")
    medium_priority = sum(1 for a in analyses if a.priority == "medium")
    low_priority = sum(1 for a in analyses if a.priority == "low")
    
    categories = {}
    for a in analyses:
        categories[a.category] = categories.get(a.category, 0) + 1
    
    category_summary = ", ".join(f"{count} {cat}" for cat, count in sorted(categories.items()))
    
    summary = (
        f"Analyzed {total} ticket(s). "
        f"Priority breakdown: {high_priority} high, {medium_priority} medium, {low_priority} low. "
        f"Categories: {category_summary}."
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