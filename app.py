from fastapi import FastAPI, HTTPException
from src.engine import build_intel

app = FastAPI(title="FX Intelligence Service")


@app.get("/intel/{pair}")
async def intel(pair: str):
    pair = pair.upper().strip()
    if len(pair) != 6 or not pair.isalpha():
        raise HTTPException(status_code=400, detail="Pair must be a 6-letter code like EURUSD")
    return build_intel(pair)
