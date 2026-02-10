# Quick Start Guide

## Installation (5 minutes)

```bash
# Navigate to project
cd Voli-MCP

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

## Run the API Server

```bash
ulicorn app:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at: `http://localhost:8000`

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Test the Engine

### Via API (curl)
```bash
# Basic EURUSD intelligence
curl "http://localhost:8000/intel/EURUSD"

# With macro events and debug mode
curl "http://localhost:8000/intel/GBPUSD?events=BoE%20Decision,UK%20Inflation&debug=true"

# Multiple events
curl "http://localhost:8000/intel/USDJPY?events=Fed%20Decision,US%20NFP"
```

### Programmatically
```python
from src.engine import build_intel

# Simple usage
result = build_intel("EURUSD")
print(result["volatility_expectation"])  # "Low", "Normal", or "High"
print(result["confidence"])              # 0.0 - 1.0
print(result["expected_deviation_pips"]) # Expected movement in pips
print(result["drivers"])                 # List of causal factors
print(result["agent_guidance"])          # Strategy recommendations

# With macro events
result = build_intel(
    pair="EURUSD",
    macro_events=["ECB Rate Decision", "Eurozone GDP"],
    debug=True  # Include debug fields
)

# Debug fields show how the calculation was made
print(f"Last 24h range: {result['last_24h_range_pips']} pips")
print(f"7-day average:  {result['avg_7day_range_pips']} pips")
print(f"Compression:    {result['compression_ratio']}")
```

## Sample Output

```json
{
  "pair": "EURUSD",
  "session": "London",
  "time_window_minutes": 90,
  "volatility_expectation": "High",
  "expected_deviation_pips": 54,
  "confidence": 0.78,
  "drivers": [
    "Range expansion detected (expansion ratio: 1.35)",
    "London session historically increases participation and volatility",
    "Macro event: ECB Rate Decision scheduled during window"
  ],
  "historical_context": {
    "similar_conditions_occurrences": 150,
    "expansion_rate": 0.92
  },
  "agent_guidance": "Range expansion indicates elevated volatility; favor breakout strategies with wider stops and careful position management.",
  "last_24h_range_pips": 67,
  "avg_7day_range_pips": 50,
  "compression_ratio": 1.34
}
```

## Supported Pairs

### FX Pairs (10,000 pips multiplier)
- EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD
- EURGBP, EURJPY, EURCHF, EURAUD
- GBPJPY, etc.

### Yen Pairs (100 pips multiplier)
- USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY

### Crypto (1 pips multiplier - native units)
- BTCUSD, ETHUSD

### Adding New Pairs
Edit `src/data_fetcher.py` - `get_symbol()` method

## Macro Events

Common high-impact events:
- `ECB Rate Decision` - ECB interest rate announcement
- `Fed Decision` - Federal Reserve announcement
- `US NFP` - Non-Farm Payroll (US employment)
- `US CPI` - Consumer Price Index
- `Eurozone GDP` - Eurozone economic growth
- `UK Inflation` - UK Consumer Price Index
- `BoE Rate Decision` - Bank of England decision
- `RBA Decision` - Reserve Bank of Australia decision

Events are customizable - any event string works, with impact multipliers defined in `src/volatility.py`.

## Configuration

Edit `src/config.py` to customize:

```python
# Change volatility classification thresholds
VOLATILITY_THRESHOLDS.low_compression = 0.70   # Below = Low vol
VOLATILITY_THRESHOLDS.high_expansion = 1.30    # Above = High vol

# Change market session hours (UTC)
SESSION_CONFIG.london_start = 7
SESSION_CONFIG.london_end = 12

# Adjust data fetching
DATA_CONFIG.yfinance_period = "10d"  # Longer history
DATA_CONFIG.yfinance_interval = "1h" # Or "1d", "1wk"
```

## Run Tests

```bash
# All tests
python -m pytest tests/test_intelligence.py -v

# Specific test class
python -m pytest tests/test_intelligence.py::SessionDetectionTests -v

# With coverage report
python -m pytest tests/test_intelligence.py --cov=src --cov-report=html
```

## Troubleshooting

### "No module named 'pandas'"
```bash
pip install -r requirements.txt
```

### Data not available
The engine gracefully falls back to session baseline with reduced confidence. Check internet connection if persistent.

### Wrong session detected
Ensure your system time/timezone is correct. The engine uses UTC.

### API not starting
Check if port 8000 is already in use:
```bash
# Try different port
uvicorn app:app --port 8001
```

## Project Structure

```
Voli-MCP/
├── src/
│   ├── __init__.py           # Package init
│   ├── config.py             # Configuration dataclasses
│   ├── models.py             # Pydantic validation schemas
│   ├── data_fetcher.py       # Data fetching + range calc
│   ├── session.py            # Session detection logic
│   ├── volatility.py         # Volatility intelligence
│   └── engine.py             # Core orchestration
│
├── tests/
│   └── test_intelligence.py  # 25+ unit tests
│
├── app.py                    # FastAPI application
├── requirements.txt          # Python dependencies
├── README.md                 # Full documentation
├── IMPROVEMENTS.md           # What was improved
├── QUICKSTART.md             # This file
├── validate.py               # Quick validation
└── test_imports.py           # Import sanity check
```

## Next: Integration

The engine is ready to integrate with:
- **Trading bots**: Call `build_intel()` to get volatility expectations
- **Risk managers**: Use confidence scores to scale position sizing
- **AI agents**: Leverage drivers and guidance for decision making
- **Signal generators**: Combine with your own technical analysis

## Support

For issues or questions:
1. Check README.md for detailed documentation
2. Review IMPROVEMENTS.md for architecture details
3. Check test suite for usage examples
4. Review docstrings in each module

Happy trading! 📈
