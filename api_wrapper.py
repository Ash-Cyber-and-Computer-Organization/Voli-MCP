"""
Optional HTTP wrapper for Postman testing.
NOT part of standard MCP - just for debugging.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.tools.session_analyzer import analyze_forex_session
import uvicorn

app = FastAPI(title="Forex Session API (Debug Only)")

class AnalysisRequest(BaseModel):
    pair: str
    target_session: str = "auto"

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    """Analyze forex session - Postman compatible endpoint."""
    try:
        result = analyze_forex_session(
            request.pair,
            request.target_session
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "forex-session-mcp"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)