import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from server import web_app
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(web_app, host="0.0.0.0", port=port)