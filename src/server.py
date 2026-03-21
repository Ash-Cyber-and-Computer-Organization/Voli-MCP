"""
MCP server for forex session analysis.
Exposes the analyze_forex_session tool via SSE transport for web hosting.
"""
import json
import os
from uuid import UUID
from typing import Any
from ctxprotocol import ContextError, is_protected_mcp_method, verify_context_request
from mcp.server import Server
from mcp.server.sse import SseServerTransport, ServerMessageMetadata, SessionMessage, types
from mcp.types import CallToolResult, ErrorData, JSONRPCError, Tool, TextContent
from pydantic import ValidationError
from tools.session_analyzer import analyze_forex_session
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
import uvicorn

# Initialize MCP server
app = Server("forex-session-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_forex_session",
            description=(
                "Analyze forex session volatility and generate trading guidance for a given currency pair. "
                "Provides expected deviation in pips, a confidence score (0-1), market drivers, "
                "historical pattern context, and agent-specific trading recommendations based on "
                "historical pattern matching and current market conditions. "
                "Returns a JSON object with fields: pair (string), session (string), "
                "time_window_minutes (integer), volatility_expectation (Low/Medium/High/None), "
                "expected_deviation_pips (number), confidence (0-1 number), "
                "drivers (array of strings), historical_context (object with "
                "similar_conditions_occurrences and expansion_rate), macro_events (array of named events), "
                "primary_macro_event (nearest named event or null), and agent_guidance (string). "
                "On weekends, returns session='Market Closed' with volatility_expectation='None'. "
                "Supported pairs: EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, NZD/USD, "
                "EUR/GBP, EUR/JPY, GBP/JPY and other major/minor pairs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Currency pair to analyze. Use slash-separated format e.g. 'EUR/USD', 'GBP/USD', 'USD/JPY', 'GBP/JPY', 'AUD/USD'.",
                        "examples": ["EUR/USD", "GBP/JPY", "AUD/USD"]
                    },
                    "target_session": {
                        "type": "string",
                        "description": "Trading session to analyze. Use 'asian' for Asian session (00:00-08:00 UTC), 'london' for London session (07:00-16:00 UTC), 'ny' for New York session (12:00-21:00 UTC), or 'auto' to automatically detect the current or next upcoming session.",
                        "enum": ["asian", "london", "ny", "auto"],
                        "default": "auto"
                    }
                },
                "required": ["pair"]
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "description": "Currency pair analyzed, e.g. EUR/USD"},
                    "session": {"type": "string", "description": "Session name, e.g. 'London Session' or 'Market Closed'"},
                    "time_window_minutes": {"type": "integer", "description": "Minutes analyzed in the pre-session window"},
                    "volatility_expectation": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High", "None"],
                        "description": "Expected volatility level for the session"
                    },
                    "expected_deviation_pips": {"type": "number", "description": "Projected pip movement for the session"},
                    "confidence": {"type": "number", "description": "Confidence score from 0.0 to 1.0"},
                    "drivers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of market drivers explaining the analysis"
                    },
                    "historical_context": {
                        "type": "object",
                        "properties": {
                            "similar_conditions_occurrences": {"type": "integer"},
                            "expansion_rate": {"type": "number"}
                        },
                        "required": ["similar_conditions_occurrences", "expansion_rate"]
                    },
                    "macro_events": {
                        "type": "array",
                        "description": "Named high-impact macro events relevant to the pair within the analysis window",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "event_type": {"type": ["string", "null"]},
                                "currency": {"type": ["string", "null"]},
                                "country": {"type": ["string", "null"]},
                                "impact": {"type": ["string", "null"]},
                                "datetime": {"type": "string"},
                                "minutes_until": {"type": ["integer", "null"]},
                                "source": {"type": ["string", "null"]}
                            },
                            "required": ["name", "datetime"]
                        }
                    },
                    "primary_macro_event": {
                        "type": ["object", "null"],
                        "description": "Nearest named high-impact macro event, if any",
                        "properties": {
                            "name": {"type": "string"},
                            "event_type": {"type": ["string", "null"]},
                            "currency": {"type": ["string", "null"]},
                            "country": {"type": ["string", "null"]},
                            "impact": {"type": ["string", "null"]},
                            "datetime": {"type": "string"},
                            "minutes_until": {"type": ["integer", "null"]},
                            "source": {"type": ["string", "null"]}
                        }
                    },
                    "agent_guidance": {"type": "string", "description": "Plain-English trading guidance for the agent"}
                },
                "required": [
                    "pair", "session", "time_window_minutes", "volatility_expectation",
                    "expected_deviation_pips", "confidence", "drivers",
                    "historical_context", "macro_events", "primary_macro_event", "agent_guidance"
                ]
            },
            # Context Protocol marketplace metadata (passed as extra fields via kwargs)
            **{
                "_meta": {
                    "surface": "answer",
                    "queryEligible": True,
                    "latencyClass": "fast",
                    "pricing": {
                        "queryUsd": "0.005"
                    },
                    "rateLimit": {
                        "maxRequestsPerMinute": 20,
                        "maxConcurrency": 5,
                        "cooldownMs": 500,
                        "supportsBulk": False,
                        "notes": "Rate limited by upstream Twelve Data API plan"
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any):
    if name != "analyze_forex_session":
        raise ValueError(f"Unknown tool: {name}")

    pair = arguments.get("pair")
    if not pair:
        raise ValueError("Missing required argument: pair")

    target_session = arguments.get("target_session", "auto")

    try:
        result = await analyze_forex_session(pair, target_session)
        # Return TextContent for legacy clients AND structuredContent for Context Protocol
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            structuredContent=result,
            isError=False,
        )
    except Exception as e:
        error_response = {
            "success": False,
            "error": str(e),
            "pair": pair,
            "target_session": target_session
        }
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(error_response, indent=2))],
            structuredContent=error_response,
            isError=True,
        )


# SSE transport
sse = SseServerTransport("/messages")


def _get_context_audience() -> str | None:
    return (
        os.environ.get("CTXPROTOCOL_AUDIENCE")
        or os.environ.get("CONTEXT_PROTOCOL_AUDIENCE")
        or os.environ.get("CONTEXT_AUDIENCE")
    )


def _jsonrpc_auth_error(message_id: str | int | None, error: ContextError) -> JSONResponse:
    if message_id is None:
        return JSONResponse(
            {
                "error": "Unauthorized",
                "details": error.message,
                "code": error.code or "unauthorized",
            },
            status_code=error.status_code or 401,
        )

    response = JSONRPCError(
        jsonrpc="2.0",
        id=message_id,
        error=ErrorData(
            code=-32001,
            message="Unauthorized",
            data={
                "details": error.message,
                "code": error.code or "unauthorized",
            },
        ),
    )
    return JSONResponse(
        response.model_dump(mode="json"),
        status_code=error.status_code or 401,
    )


async def handle_sse(request: Request) -> Response:
    """
    SSE endpoint — keeps the long-lived connection open for the full MCP session.
    Returns an empty Response() after the session ends so Starlette doesn't crash
    trying to call the None return value as an ASGI app.
    """
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())
    return Response()


async def handle_messages(request: Request) -> Response:
    security_error = await sse._security.validate_request(request, is_post=True)
    if security_error:
        return security_error

    session_id_param = request.query_params.get("session_id")
    if session_id_param is None:
        return Response("session_id is required", status_code=400)

    try:
        session_id = UUID(hex=session_id_param)
    except ValueError:
        return Response("Invalid session ID", status_code=400)

    writer = sse._read_stream_writers.get(session_id)
    if not writer:
        return Response("Could not find session", status_code=404)

    body = await request.body()
    try:
        message = types.JSONRPCMessage.model_validate_json(body)
    except ValidationError as err:
        captured_status = 400
        captured_headers: dict[str, str] = {}
        captured_body = b""

        async def parsing_error_send(asgi_message: dict) -> None:
            nonlocal captured_status, captured_headers, captured_body
            if asgi_message["type"] == "http.response.start":
                captured_status = asgi_message.get("status", 400)
                captured_headers = {
                    k.decode("latin-1"): v.decode("latin-1")
                    for k, v in asgi_message.get("headers", [])
                }
            elif asgi_message["type"] == "http.response.body":
                captured_body = asgi_message.get("body", b"")

        error_response = Response("Could not parse message", status_code=400)
        await error_response(request.scope, request.receive, parsing_error_send)
        await writer.send(err)
        return Response(
            content=captured_body,
            status_code=captured_status,
            headers=captured_headers,
        )

    method = getattr(message.root, "method", None)
    if method and is_protected_mcp_method(method):
        try:
            request.state.context_protocol = await verify_context_request(
                authorization_header=request.headers.get("authorization"),
                audience=_get_context_audience(),
            )
        except ContextError as err:
            return _jsonrpc_auth_error(getattr(message.root, "id", None), err)

    captured_status = 202
    captured_headers: dict[str, str] = {}
    captured_body = b""

    async def capturing_send(message: dict) -> None:
        nonlocal captured_status, captured_headers, captured_body
        if message["type"] == "http.response.start":
            captured_status = message.get("status", 202)
            # ASGI headers are list of [bytes, bytes] pairs
            captured_headers = {
                k.decode("latin-1"): v.decode("latin-1")
                for k, v in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            captured_body = message.get("body", b"")

    metadata = ServerMessageMetadata(request_context=request)
    session_message = SessionMessage(message, metadata=metadata)

    response = Response("Accepted", status_code=202)
    await response(request.scope, request.receive, capturing_send)
    await writer.send(session_message)

    return Response(
        content=captured_body,
        status_code=captured_status,
        headers=captured_headers,
    )


# Starlette web app
web_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(web_app, host="0.0.0.0", port=port)
