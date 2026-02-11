## Developer Guide

Complete step-by-step guide for development and testing.

---

## 📋 Table of Contents

1. [Initial Setup](#initial-setup)
2. [Environment Configuration](#environment-configuration)
3. [Running Tests](#running-tests)
4. [Running the API Wrapper](#running-the-api-wrapper)
5. [Running the MCP Server](#running-the-mcp-server)
6. [Troubleshooting](#troubleshooting)

---

## 🚀 Initial Setup

### Step 1: Open Project in VSCode
```bash
# Navigate to project directory
cd /path/to/Voli~MCP

# Open in VSCode
code .
```

### Step 2: Create and Activate Virtual Environment

**On Linux/Mac:**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Your terminal should now show (venv) at the start
```

**On Windows:**
```cmd
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Your terminal should now show (venv) at the start
```

**Verify activation:**
```bash
# Should show path inside venv folder
which python    # Linux/Mac
where python    # Windows
```

### Step 3: Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -e .

# OR if that fails:
pip install -r requirements.txt

# Verify installation
pip list
```

You should see:
- mcp
- pandas
- numpy
- requests
- fastapi
- uvicorn
- etc.

---

## ⚙️ Environment Configuration

### Step 1: Create .env File
```bash
# Copy example
cp .env.example .env

# Edit .env file
nano .env    # or use VSCode
```

### Step 2: Add Your API Key

Edit `.env` file:
```bash
# Twelve Data API Configuration
TWELVE_DATA_API_KEY=your_actual_api_key_here

# Optional: Rate Limiting
MAX_REQUESTS_PER_DAY=800
REQUEST_DELAY_SECONDS=1

# Logging
LOG_LEVEL=INFO
```

**Get API Key:**
1. Go to https://twelvedata.com/
2. Sign up for free account
3. Copy your API key
4. Paste into `.env` file

### Step 3: Verify Environment
```bash
# Check .env exists
cat .env

# Should show your API key (not "your_actual_api_key_here")
```

---

## 🧪 Running Tests

### Option 1: Run All Tests at Once
```bash
# Make sure you're in project root
pwd
# Should show: /path/to/forex-session-mcp

# Make sure venv is activated
# Terminal should show (venv)

# Run all tests
python test_utils.py && \
python test_data_clients.py && \
python test_analysis.py && \
python test_full_system.py
```

### Option 2: Run Tests Individually

#### Test 1: Utility Functions
```bash
python test_utils.py
```

**Expected Output:**
```
=== Testing Sessions ===
Current session: london
Is weekend: False
Next session: ny at 2025-02-09 13:00:00+00:00
...
✅ All utilities working!
```

#### Test 2: Data Clients (Requires API Key)
```bash
python test_data_clients.py
```

**Expected Output:**
```
=== Testing Twelve Data Client ===
✅ EUR/USD Quote: 1.08523
✅ Intraday data: 10 candles
✅ Historical data: 8640 candles over ~30 days
📊 Rate Limits: 3/800 used (0.4%)
...
✅ Data clients ready!
```

**If you see errors:**
- Check your API key in `.env`
- Check internet connection
- Verify API key is valid at twelvedata.com

#### Test 3: Analysis Modules
```bash
python test_analysis.py
```

**Expected Output:**
```
=== Testing Range Calculator ===
✅ Full range: 42.3 pips
✅ Pre-session range: 18.7 pips
...
✅ All analysis modules working!
```

#### Test 4: Full System Integration
```bash
python test_full_system.py
```

**Expected Output:**
```
============================================================
FOREX SESSION MCP - FULL SYSTEM TEST
============================================================

[Test 1] EUR/USD - Auto Session Detection
------------------------------------------------------------
{
  "pair": "EUR/USD",
  "session": "London Session",
  ...
}
✅ Test 1 PASSED
...
SYSTEM TEST COMPLETE
```

### Option 3: Interactive Testing
```bash
# Test any pair interactively
python test_any_pair.py "EUR/USD" "london"

# Or run interactive mode
python interactive_test.py
```

### Option 4: Batch Testing
```bash
# Test multiple pairs at once
python batch_test.py

# Results saved to: batch_test_results.json
cat batch_test_results.json
```

---

## 🌐 Running the API Wrapper (HTTP/Postman Testing)

### Step 1: Start the Server

**Method 1 - Direct Python (Recommended):**
```bash
# Make sure venv is activated
# Make sure you're in project root

python api_wrapper.py
```

**Method 2 - Using Uvicorn:**
```bash
uvicorn api_wrapper:app --reload --host 0.0.0.0 --port 8000
```

**Method 3 - Simplified Version:**
```bash
python simple_api.py
```

### Step 2: Verify Server is Running

You should see:
```
======================================================================
FOREX SESSION MCP - HTTP API WRAPPER
======================================================================

🚀 Starting server...

📍 Endpoints:
   • http://localhost:8000           - API info
   • http://localhost:8000/docs      - Interactive docs (Swagger)
   • http://localhost:8000/health    - Health check
...
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 3: Test the API

**In Browser:**
```
# Open in browser
http://localhost:8000/docs
```

**With cURL:**
```bash
# Health check
curl http://localhost:8000/health

# Analyze pair
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"pair": "EUR/USD", "target_session": "london"}'
```

**With Postman:**
```
POST http://localhost:8000/analyze
Content-Type: application/json

Body:
{
  "pair": "EUR/USD",
  "target_session": "london"
}
```

### Step 4: Stop the Server

Press `CTRL+C` in the terminal:
```
^C
INFO:     Shutting down
```

---

## 🔧 Running the MCP Server (Production)

### Step 1: Start MCP Server
```bash
python -m src.server
```

### Step 2: Test with MCP Inspector
```bash
# Install MCP Inspector (one-time)
npm install -g @modelcontextprotocol/inspector

# Run with inspector
npx @modelcontextprotocol/inspector python -m src.server
```

Opens web UI at: `http://localhost:5173`

### Step 3: Use with Claude Desktop

Edit `claude_desktop_config.json`:

**On Mac:**
```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**On Windows:**
```cmd
notepad %APPDATA%\Claude\claude_desktop_config.json
```

**Add this configuration:**
```json
{
  "mcpServers": {
    "forex-session": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/full/path/to/forex-session-mcp",
      "env": {
        "TWELVE_DATA_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Restart Claude Desktop**

---

## 🐛 Troubleshooting

### Issue: Tests Not Running

**Symptom:** `ModuleNotFoundError` or `ImportError`

**Solution:**
```bash
# 1. Verify you're in project root
pwd
# Should end with: forex-session-mcp

# 2. Verify venv is activated
which python
# Should show: /path/to/forex-session-mcp/venv/bin/python

# 3. Reinstall dependencies
pip install -e .

# 4. Try running test again
python test_utils.py
```

### Issue: API Key Not Found

**Symptom:** `TWELVE_DATA_API_KEY not found in environment`

**Solution:**
```bash
# 1. Check .env file exists
ls -la .env

# 2. Check it has your key
cat .env

# 3. If missing, add it
echo "TWELVE_DATA_API_KEY=your_key_here" > .env

# 4. Try again
python test_data_clients.py
```

### Issue: Import Errors After VSCode Reload

**Symptom:** Tests worked before, now getting import errors

**Solution:**
```bash
# 1. Close all Python terminals in VSCode

# 2. Open new terminal (Terminal → New Terminal)

# 3. Activate venv again
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# 4. Verify activation
which python

# 5. Run tests
python test_utils.py
```

### Issue: "Could not import module api_wrapper"

**Symptom:** Uvicorn can't find api_wrapper

**Solution:**
```bash
# 1. Check file exists
ls -la api_wrapper.py

# 2. Run with Python directly
python api_wrapper.py

# 3. If that fails, check you're in right directory
pwd
ls *.py
```

### Issue: Port Already in Use

**Symptom:** `Address already in use` when starting API

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000          # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>          # Mac/Linux
taskkill /PID <PID> /F # Windows

# Or use different port
python api_wrapper.py --port 8001
```

### Issue: VSCode Python Interpreter Wrong

**Symptom:** Tests fail but work in terminal

**Solution:**
1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows)
2. Type: "Python: Select Interpreter"
3. Choose: `./venv/bin/python`
4. Reload window

---

## 📝 Quick Reference Commands

### Every Time You Start Development:
```bash
# 1. Navigate to project
cd forex-session-mcp

# 2. Activate venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Verify activation
which python

# Now you can run tests/servers
```

### Testing Commands:
```bash
# Quick test
python test_utils.py

# Full test suite
python test_full_system.py

# Test specific pair
python test_any_pair.py "EUR/USD" "london"

# Interactive testing
python interactive_test.py
```

### Server Commands:
```bash
# HTTP API (for Postman)
python api_wrapper.py

# MCP Server (for Claude)
python -m src.server

# MCP Inspector (visual testing)
npx @modelcontextprotocol/inspector python -m src.server
```

### Cleanup Commands:
```bash
# Deactivate venv
deactivate

# Remove cache
find . -type d -name __pycache__ -exec rm -rf {} +

# Reset and reinstall
pip uninstall -y -r <(pip freeze)
pip install -e .
```

---

## 📂 Project Structure
```
forex-session-mcp/
├── .env                      # Your API keys (DO NOT COMMIT)
├── .env.example              # Template for .env
├── api_wrapper.py            # HTTP API for testing
├── test_utils.py             # Test utilities
├── test_data_clients.py      # Test API clients
├── test_analysis.py          # Test analysis modules
├── test_full_system.py       # Integration tests
├── test_any_pair.py          # Quick pair testing
├── interactive_test.py       # Interactive testing
├── batch_test.py             # Batch testing
├── venv/                     # Virtual environment (DO NOT COMMIT)
└── src/
    ├── server.py             # MCP server
    ├── tools/
    │   └── session_analyzer.py
    ├── data/
    │   ├── twelve_data_client.py
    │   └── calendar_client.py
    ├── analysis/
    │   ├── range_calculator.py
    │   ├── pattern_matcher.py
    │   └── confidence_scorer.py
    └── utils/
        ├── sessions.py
        └── formatters.py
```

---

## ✅ Checklist Before Testing

- [ ] Virtual environment activated (`(venv)` shows in terminal)
- [ ] In correct directory (run `pwd` to verify)
- [ ] `.env` file exists with valid API key
- [ ] Dependencies installed (`pip list` shows packages)
- [ ] No import errors when running `python -c "from src.tools.session_analyzer import analyze_forex_session"`

---

## 🆘 Still Having Issues?

Run this diagnostic script:
```bash
python -c "
import sys, os
print('Python:', sys.executable)
print('Directory:', os.getcwd())
print('Files:', [f for f in os.listdir('.') if f.endswith('.py')][:5])
try:
    from src.tools.session_analyzer import analyze_forex_session
    print('✅ Imports working')
except Exception as e:
    print('❌ Import error:', e)
"
```

Share the output for further debugging.

---
## How to run the MCP on MCP INSPECTOR

## Activate your .venv
### install the NPM package (using terminal):
- sudo npm install -g @modelcontextprotocol/inspector
### Confirm its installed using:
 - npm list -g @modelcontextprotocol/inspector
 ### it should show a result like this 
 - usr/local/lib
└── @modelcontextprotocol/inspector@0.20.0
### Run your Server by first locating the server file ()
- npx @modelcontextprotocol/inspector python -m src.server
### It will open a web page on your browser and you can interact with your MCP using the terminal.