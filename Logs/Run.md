- Virtualenv + install:
```bash
python -m venv .venv # create a venv
source .venv/bin/activate
pip install "mcp[cli]" # This is for the MCP server for venv
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
# How to ADD local MCP
 -python -m venv .venv # create a venv
- source .venv/bin/activate
- pip install "mcp[cli]" # This is for the MCP server for venv
- Ctrl+Shift+P 
- MCP: Add Server.
- Choose the stdio
- find the path to your python executable by running which python or where python ("<full path to venv\Scripts\python.exe> <full path to your_project_folder\server.py>")
- Give your MCP server a descriptive name.
- Choose whether to save the configuration globally or at the Workspace level 
- Ctrl+Shift+P, then search for "Reload Window"
---
- Go to the Extensions tab and look for the MCP Servers Installed section. Your server should be listed here. You can - start/stop it from the inline menu in the mcp.json file.
- Open the GitHub Copilot Chat window.
- Ensure Agent mode is selected at the bottom of the chat panel.
- Select the Tools icon (two wrenches) and verify that your new MCP server's tools are enabled.
- You can now interact with your server via Copilot Chat by referencing your tools or resources using prompts or the # syntax. 