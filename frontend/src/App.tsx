import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = ''

interface Ticket {
  id: number
  title: string
  description: string
  created_at: string
}

interface TicketWithAnalysis extends Ticket {
  category: string
  priority: string
  notes?: string
}

interface Analysis {
  analysis_run_id: number
  created_at: string
  summary: string
  tickets: TicketWithAnalysis[]
}

function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [newTicket, setNewTicket] = useState({ title: '', description: '' })

  useEffect(() => {
    fetchTickets()
    fetchLatestAnalysis()
  }, [])

  const fetchTickets = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tickets`)
      const data = await res.json()
      setTickets(data)
    } catch (err) {
      console.error('Failed to fetch tickets:', err)
    }
  }

  const fetchLatestAnalysis = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/analysis/latest`)
      const data = await res.json()
      setAnalysis(data)
    } catch (err) {
      console.error('Failed to fetch analysis:', err)
    }
  }

  const handleAddTicket = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTicket.title || !newTicket.description) return

    try {
      const res = await fetch(`${API_BASE}/api/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickets: [newTicket] })
      })
      
      if (res.ok) {
        setNewTicket({ title: '', description: '' })
        fetchTickets()
      }
    } catch (err) {
      console.error('Failed to add ticket:', err)
    }
  }

  const handleAnalyze = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
      
      if (res.ok) {
        await fetchLatestAnalysis()
      }
    } catch (err) {
      console.error('Failed to analyze:', err)
    } finally {
      setLoading(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      high: '#ff4444',
      medium: '#ffaa00',
      low: '#44ff44'
    }
    return colors[priority] || '#999'
  }

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      bug: '#ff6b6b',
      billing: '#4ecdc4',
      feature_request: '#95e1d3',
      general: '#aaa'
    }
    return colors[category] || '#aaa'
  }

  return (
    <div className="app">
      <h1>🎫 Support Ticket Analyst</h1>
      
      {/* Add Ticket Form */}
      <div className="section">
        <h2>Add New Ticket</h2>
        <form onSubmit={handleAddTicket} className="ticket-form">
          <input
            type="text"
            placeholder="Ticket title"
            value={newTicket.title}
            onChange={(e) => setNewTicket({ ...newTicket, title: e.target.value })}
          />
          <textarea
            placeholder="Description"
            value={newTicket.description}
            onChange={(e) => setNewTicket({ ...newTicket, description: e.target.value })}
          />
          <button type="submit">Add Ticket</button>
        </form>
      </div>

      {/* Ticket List */}
      <div className="section">
        <h2>All Tickets ({tickets.length})</h2>
        <div className="ticket-list">
          {tickets.map((ticket) => (
            <div key={ticket.id} className="ticket-card">
              <h3>{ticket.title}</h3>
              <p>{ticket.description}</p>
              <small>ID: {ticket.id}</small>
            </div>
          ))}
        </div>
      </div>

      {/* Analyze Button */}
      <div className="section">
        <button 
          onClick={handleAnalyze} 
          disabled={loading}
          className="analyze-button"
        >
          {loading ? 'Analyzing...' : '🤖 Analyze All Tickets'}
        </button>
      </div>

      {/* Analysis Results */}
      {analysis && (
        <div className="section">
          <h2>Latest Analysis</h2>
          <div className="analysis-summary">
            <p><strong>Summary:</strong> {analysis.summary}</p>
            <p><small>Run ID: {analysis.analysis_run_id} | {new Date(analysis.created_at).toLocaleString()}</small></p>
          </div>

          <div className="analyzed-tickets">
            {analysis.tickets.map((ticket) => (
              <div key={ticket.id} className="analyzed-ticket-card">
                <h3>{ticket.title}</h3>
                <p>{ticket.description}</p>
                <div className="tags">
                  <span 
                    className="tag category"
                    style={{ backgroundColor: getCategoryColor(ticket.category) }}
                  >
                    {ticket.category}
                  </span>
                  <span 
                    className="tag priority"
                    style={{ backgroundColor: getPriorityColor(ticket.priority) }}
                  >
                    {ticket.priority}
                  </span>
                </div>
                {ticket.notes && <small className="notes">{ticket.notes}</small>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default App