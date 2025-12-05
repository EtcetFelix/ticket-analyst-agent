-- db/init.sql
-- Support Ticket Analyst Database Schema

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS ticket_analysis (
    id SERIAL PRIMARY KEY,
    analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    category TEXT,
    priority TEXT,
    notes TEXT
);

-- Create indexes for better query performance
CREATE INDEX idx_ticket_analysis_run ON ticket_analysis(analysis_run_id);
CREATE INDEX idx_ticket_analysis_ticket ON ticket_analysis(ticket_id);

-- Insert some sample tickets for testing
INSERT INTO tickets (title, description) VALUES
    ('Cannot login to account', 'I have been trying to login for the past hour but keep getting an error message saying my password is incorrect.'),
    ('Billing question about invoice', 'I was charged twice for my subscription this month. Can you please refund one of the charges?'),
    ('Feature request: dark mode', 'It would be great if you could add a dark mode option to the app. My eyes get tired using it at night.'),
    ('App crashes on startup', 'Every time I open the app it crashes immediately. I am using iPhone 12 with iOS 16.'),
    ('How to export my data?', 'I need to export all my data before my trial ends. Where is the export button?');