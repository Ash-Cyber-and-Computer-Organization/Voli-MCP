# Voli

MCP server providing forex session volatility analysis and trading guidance.

## Features

- Real-time session volatility analysis (Asian, London, NY)
- Historical pattern matching without database
- Confidence scoring based on market conditions
- Economic calendar integration
- Pure API-based implementation

## Installation

1. Clone the repository
2. Install dependencies:
```bash
   pip install -e .
```

3. Configure environment:
```bash
   cp .env.example .env
   # Edit .env and add your Twelve Data API key
```

## Usage

Run the MCP server:
```bash
python -m src.server
```

## API Tool

### `analyze_forex_session`

**Inputs:**
- `pair` (string, required): Currency pair (e.g., "EUR/USD")
- `target_session` (string, optional): "asian", "london", "ny", or "auto"

**Output:**
```json
{
  "pair": "EURUSD",
  "session": "London Open",
  "time_window_minutes": 90,
  "volatility_expectation": "High",
  "expected_deviation_pips": 38,
  "confidence": 0.74,
  "drivers": [...],
  "historical_context": {...},
  "agent_guidance": "..."
}
```

## Requirements

- Python 3.10+
- Twelve Data API key (free tier: 800 requests/day)

## License

MIT