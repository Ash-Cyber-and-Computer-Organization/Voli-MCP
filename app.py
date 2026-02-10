"""FastAPI application for FX Volatility Intelligence Service."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import ValidationError

from src.engine import build_intel
from src.models import VolatilityIntelligence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FX Volatility Intelligence Service",
    description="AI-powered FX volatility expectations and reasoning",
    version="1.0.0",
)


@app.get(
    "/intel/{pair}",
    response_model=VolatilityIntelligence,
    summary="Get volatility intelligence for a FX pair",
    tags=["Intelligence"],
)
async def get_intel(
    pair: str = Query(..., description="FX pair code (e.g., EURUSD)", min_length=6, max_length=6),
    events: Optional[str] = Query(
        None,
        description="Comma-separated macro events (e.g., 'ECB Rate Decision,US NFP')"
    ),
    debug: bool = Query(False, description="Include debug fields in response"),
):
    """Get volatility intelligence for a currency pair.
    
    Returns structured volatility expectations with drivers and agent guidance.
    """
    try:
        # Parse events
        macro_events = None
        if events:
            macro_events = [e.strip() for e in events.split(",")]
            logger.info(f"Macro events: {macro_events}")
        
        # Build intelligence
        intel = build_intel(pair, macro_events=macro_events, debug=debug)
        
        # Validate against schema
        validated = VolatilityIntelligence(**intel)
        logger.info(f"Successfully generated intelligence for {pair}")
        return validated
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        logger.error(f"Schema validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health", summary="Health check", tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
