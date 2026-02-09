"""
MCP server for forex session analysis.
Exposes the analyze_forex_session tool via stdio transport.
"""

import asyncio
import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.tools.session_analyzer import analyze_forex_session
from src.utils.formatters import get_supported_pairs


# Initialize MCP server
app = Server("forex-session-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available MCP tools.
    
    Returns:
        List of tool definitions
    """
    return [
        Tool(
            name="analyze_forex_session",
            description=(
                "Analyze forex session volatility and generate trading guidance. "
                "Provides expected deviation, confidence score, market drivers, "
                "and agent-specific trading recommendations based on historical "
                "pattern matching and current market conditions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": (
                            "Currency pair to analyze (e.g., 'EUR/USD', 'GBP/USD', 'USD/JPY'). "
                            "Supports majors, minors, and select exotics."
                        ),
                        "examples": ["EUR/USD", "GBP/JPY", "AUD/USD"]
                    },
                    "target_session": {
                        "type": "string",
                        "description": (
                            "Trading session to analyze: 'asian', 'london', 'ny', or 'auto' "
                            "for automatic detection of next session."
                        ),
                        "enum": ["asian", "london", "ny", "auto"],
                        "default": "auto"
                    }
                },
                "required": ["pair"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool calls from MCP clients.
    
    Args:
        name: Tool name
        arguments: Tool arguments
        
    Returns:
        Tool response as TextContent
        
    Raises:
        ValueError: If tool not found or arguments invalid
    """
    if name != "analyze_forex_session":
        raise ValueError(f"Unknown tool: {name}")
    
    # Extract arguments
    pair = arguments.get("pair")
    if not pair:
        raise ValueError("Missing required argument: pair")
    
    target_session = arguments.get("target_session", "auto")
    
    try:
        # Run analysis
        result = analyze_forex_session(pair, target_session)
        
        # Format as JSON
        result_json = json.dumps(result, indent=2)
        
        return [
            TextContent(
                type="text",
                text=result_json
            )
        ]
        
    except Exception as e:
        # Return error as JSON
        error_response = {
            "error": str(e),
            "pair": pair,
            "target_session": target_session
        }
        
        return [
            TextContent(
                type="text",
                text=json.dumps(error_response, indent=2)
            )
        ]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def run():
    """Entry point for the server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()