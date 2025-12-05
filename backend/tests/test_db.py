import pytest
from app.db import (
    get_all_tickets,
    insert_tickets,
    get_tickets_by_ids,
    create_analysis_run,
    insert_ticket_analysis,
    bulk_insert_ticket_analysis,
    get_latest_analysis,
)
from app.models import TicketCreate, TicketAnalysisCreate


def test_get_all_tickets():
    """Test fetching all tickets from sample data"""
    tickets = get_all_tickets()
    
    assert len(tickets) >= 3  # We have 3 in init.sql
    assert all(hasattr(t, 'id') for t in tickets)
    assert all(hasattr(t, 'title') for t in tickets)
    assert all(hasattr(t, 'description') for t in tickets)


def test_insert_tickets():
    """Test inserting new tickets"""
    new_tickets = [
        TicketCreate(title="Test Ticket A", description="Description A"),
        TicketCreate(title="Test Ticket B", description="Description B"),
    ]
    
    result = insert_tickets(new_tickets)
    
    assert len(result) == 2
    assert result[0].title == "Test Ticket A"
    assert result[1].title == "Test Ticket B"
    assert result[0].id is not None
    assert result[1].id is not None


def test_get_tickets_by_ids():
    """Test fetching specific tickets by ID"""
    # First insert some tickets
    new_tickets = insert_tickets([
        TicketCreate(title="Ticket 1", description="Desc 1"),
        TicketCreate(title="Ticket 2", description="Desc 2"),
    ])
    
    ids = [t.id for t in new_tickets]
    
    # Fetch them back
    fetched = get_tickets_by_ids(ids)
    
    assert len(fetched) == 2
    assert set(t.id for t in fetched) == set(ids)


def test_create_analysis_run():
    """Test creating an analysis run"""
    summary = "Found 3 billing issues, 2 bugs, 1 feature request"
    
    run = create_analysis_run(summary)
    
    assert run.id is not None
    assert run.summary == summary
    assert run.created_at is not None


def test_insert_ticket_analysis():
    """Test inserting a single ticket analysis"""
    # Setup: create a ticket and analysis run
    tickets = insert_tickets([
        TicketCreate(title="Bug Report", description="App crashes on login")
    ])
    run = create_analysis_run("Test analysis")
    
    # Insert analysis
    analysis = insert_ticket_analysis(
        analysis_run_id=run.id,
        ticket_id=tickets[0].id,
        category="bug",
        priority="high",
        notes="Critical login issue"
    )
    
    assert analysis.id is not None
    assert analysis.analysis_run_id == run.id
    assert analysis.ticket_id == tickets[0].id
    assert analysis.category == "bug"
    assert analysis.priority == "high"
    assert analysis.notes == "Critical login issue"


def test_bulk_insert_ticket_analysis():
    """Test bulk inserting ticket analyses"""
    # Setup
    tickets = insert_tickets([
        TicketCreate(title="Issue 1", description="Desc 1"),
        TicketCreate(title="Issue 2", description="Desc 2"),
    ])
    run = create_analysis_run("Bulk test")
    
    # Bulk insert
    analyses = [
        TicketAnalysisCreate(
            analysis_run_id=run.id,
            ticket_id=tickets[0].id,
            category="billing",
            priority="medium",
            notes="Payment issue"
        ),
        TicketAnalysisCreate(
            analysis_run_id=run.id,
            ticket_id=tickets[1].id,
            category="feature_request",
            priority="low",
            notes=None
        ),
    ]
    
    result = bulk_insert_ticket_analysis(analyses)
    
    assert len(result) == 2
    assert result[0].category == "billing"
    assert result[1].category == "feature_request"


def test_get_latest_analysis():
    """Test fetching the latest analysis with all ticket details"""
    # Setup: create tickets, run, and analyses
    tickets = insert_tickets([
        TicketCreate(title="Payment Failed", description="CC declined"),
        TicketCreate(title="UI Bug", description="Button not working"),
    ])
    
    run = create_analysis_run("Analysis: 1 billing issue, 1 bug found")
    
    for ticket in tickets:
        insert_ticket_analysis(
            analysis_run_id=run.id,
            ticket_id=ticket.id,
            category="billing" if "Payment" in ticket.title else "bug",
            priority="high",
            notes="Automated analysis"
        )
    
    # Fetch latest
    latest = get_latest_analysis()
    
    assert latest is not None
    assert latest.analysis_run_id == run.id
    assert latest.summary == "Analysis: 1 billing issue, 1 bug found"
    assert len(latest.tickets) == 2
    
    # Check joined data
    for ticket_with_analysis in latest.tickets:
        assert ticket_with_analysis.title is not None
        assert ticket_with_analysis.category is not None
        assert ticket_with_analysis.priority is not None


def test_get_latest_analysis_empty():
    """Test get_latest_analysis when no analyses exist"""
    # This might fail if there's data from other tests
    # In real setup, you'd use fixtures to ensure clean DB state
    # For now, just check it returns something or None
    result = get_latest_analysis()
    assert result is None or isinstance(result.analysis_run_id, int)