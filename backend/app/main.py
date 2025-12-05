from fastapi import FastAPI

app = FastAPI(title="Support Ticket Analyst")

@app.get("/health")
def health_check():
    return {"status": "healthy"}