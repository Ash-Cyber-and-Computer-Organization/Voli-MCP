- Virtualenv + install:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
- CLI demo:
```bash
python -m src.mcp.cli generate --csv examples/data/sample_eurusd.csv --pair EURUSD --session "London Open" --event ECB --out out/sample.json
```
- Run API:
```bash
uvicorn src.mcp.api:app --reload --port 8000
```
- Run tests:
```bash
pytest -q
```