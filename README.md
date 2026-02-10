# Voli-MCP: FX Volatility Intelligence Engine

**Voli-MCP** is a production-ready FX volatility intelligence platform designed for AI agents and quantitative trading systems.

## Features

### ✅ Volatility Intelligence Generation
- **Session-aware analysis**: Detects current trading session (Asia, London, New York, Off-session)
- **Range compression metrics**: Calculates compression ratios against 7-day historical averages
- **Macro event integration**: Incorporates scheduled economic events for impact quantification
- **Confidence scoring**: Provides confidence (0-1) based on data extremeness and sample size

### ✅ Causal Reasoning
- **Multi-factor drivers**: Range compression, session participation, macro events, liquidity
- **Historical context**: Similar-conditions occurrence counts and expansion probabilities
- **Agent guidance**: Strategy recommendations tailored to volatility expectations

### ✅ Structured Output
All responses follow this JSON schema:
```json
{
  "pair": "EURUSD",
  "session": "London",
  "time_window_minutes": 90,
  "volatility_expectation": "High",
  "expected_deviation_pips": 45,
  "confidence": 0.78,
  "drivers": [
    "Range expansion detected (expansion ratio: 1.35)",
    "London session historically increases participation and volatility"
  ],
  "historical_context": {
    "similar_conditions_occurrences": 150,
    "expansion_rate": 0.92
  },
  "agent_guidance": "Range expansion indicates elevated volatility; favor breakout strategies with wider stops..."
}
```

## Project Structure

```
Voli-MCP/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration and thresholds
│   ├── models.py           # Pydantic validation schemas
│   ├── data_fetcher.py     # Market data and range calculations
│   ├── session.py          # Trading session detection
│   ├── volatility.py       # Volatility classification logic
│   └── engine.py           # Core intelligence generation
├── tests/
│   └── test_intelligence.py # Comprehensive unit tests
├── app.py                  # FastAPI application
├── requirements.txt        # Dependencies
└── README.md
```

## Installation

### Prerequisites
- Python 3.8+
- pip or conda

### Setup
```bash
# Clone/download the project
cd Voli-MCP

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### API Server
```bash
# Start the FastAPI server
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Test in browser or with curl
curl "http://localhost:8000/intel/EURUSD?events=ECB%20Rate%20Decision&debug=true"

# Access API docs
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Programmatic Usage
```python
from src.engine import build_intel

# Get volatility intelligence
intel = build_intel(
    pair="EURUSD",
    macro_events=["ECB Rate Decision", "US NFP"],
    debug=True
)

print(f"Expectation: {intel['volatility_expectation']}")
print(f"Confidence: {intel['confidence']}")
print(f"Drivers: {intel['drivers']}")
print(f"Guidance: {intel['agent_guidance']}")
```

## Key Components

### Configuration (`src/config.py`)
- **PipConfig**: Pair-specific pip multipliers
- **VolatilityThresholds**: Compression ratios for classification
- **SessionConfig**: UTC market session hours
- **DataConfig**: Data fetching parameters

### Models (`src/models.py`)
- **VolatilityIntelligence**: Response schema with validation
- **HistoricalContext**: Historical condition statistics

### Session Detection (`src/session.py`)
- `detect_session()`: Current session name
- `detect_session_detailed()`: Detailed session info with progress
- `is_high_impact_session()`: Check if session typically drives volatility

### Data Fetching (`src/data_fetcher.py`)
- **DataFetcher**: Manages yfinance downloads with caching
- **RangeCalculator**: Calculates ranges and compression metrics
- Pip multiplier logic for all pair types

### Volatility Intelligence (`src/volatility.py`)
- `classify_volatility_expectation()`: Low/Normal/High classification
- `get_confidence_for_expectation()`: Confidence scoring
- `get_session_volatility_multiplier()`: Session impact factors
- `get_macro_event_impact()`: Event multiplier calculation
- `volatility_for_session()`: Full intelligence calculation

### Engine (`src/engine.py`)
- `build_intel()`: Main entry point for intelligence generation
- Fallback intelligence for missing data
- Agent guidance generation
- Debug mode for detailed diagnostics

## Volatility Classification Logic

### Low Volatility
- **Compression Ratio**: < 0.75
- **Characteristics**: Range compression, mean-reverting conditions
- **Agent Guidance**: Tight stops, reduced position sizing, mean reversion strategies

### Normal Volatility
- **Compression Ratio**: 0.75 - 1.25
- **Characteristics**: Range within historical norms
- **Agent Guidance**: Standard risk management and position sizing

### High Volatility
- **Compression Ratio**: > 1.25
- **Characteristics**: Range expansion, potential breakout conditions
- **Agent Guidance**: Wider stops, breakout strategies, careful position management

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test class
python -m pytest tests/test_intelligence.py::SessionDetectionTests

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run tests with unittest directly
python -m unittest tests.test_intelligence
```

## API Endpoints

### GET `/intel/{pair}`
Get volatility intelligence for a specific FX pair.

**Parameters:**
- `pair` (path, required): 6-letter FX pair code (e.g., EURUSD)
- `events` (query, optional): Comma-separated macro events
- `debug` (query, optional): Include debug fields (default: false)

**Response:** VolatilityIntelligence JSON object

**Example:**
```bash
curl "http://localhost:8000/intel/GBPUSD?events=BoE%20Decision&debug=true"
```

### GET `/health`
Simple health check endpoint.

**Response:**
```json
{"status": "healthy"}
```

## Configuration

Edit `src/config.py` to customize:
- Session hours (UTC)
- Pip multipliers by pair type
- Volatility classification thresholds
- Data fetching parameters (period, interval, user agent)

## Historical Data Sources

Currently supports:
- **FX Pairs**: EURUSD, GBPUSD, USDJPY (via yfinance)
- **Crypto**: BTCUSD, ETHUSD (via yfinance)
- **Extensible**: Easy to add support for additional symbols

## Error Handling

- Invalid pair format: Returns 400 Bad Request
- Data fetch failures: Returns fallback intelligence with reduced confidence
- Schema validation: Returns 422 Unprocessable Entity
- Unexpected errors: Returns 500 Internal Server Error

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.115.8 | Web framework |
| uvicorn | 0.30.6 | ASGI server |
| pydantic | 2.7.1 | Data validation |
| yfinance | ≥0.2.40 | Market data fetching |
| pandas | ≥1.3.0 | Data analysis |
| requests | ≥2.31.0 | HTTP requests |
| python-dotenv | 1.0.0 | Environment management |

## Performance Considerations

- **Caching**: DataFetcher caches market data to reduce API calls
- **Non-blocking**: Data fetch failures gracefully fall back to session baseline
- **Confidence**: Reduced for fallback scenarios to alert agents
- **Session detection**: O(1) time complexity
- **Range calculation**: O(n) where n = number of candles (typically 168 for 7 days @ 1h)

## Future Enhancements

- [ ] Real-time event feed integration
- [ ] Multi-timeframe analysis (5m, 15m, 1h, 4h, 1d)
- [ ] Volatility term structure
- [ ] Correlation-adjusted expectations
- [ ] Machine learning confidence scoring
- [ ] Historical event impact database
- [ ] Alternative data sources (IB, Bloomberg, etc.)

## License

Proprietary - Built for quantitative trading agents

## Support

For issues or questions, please create an issue or contact the development team.
