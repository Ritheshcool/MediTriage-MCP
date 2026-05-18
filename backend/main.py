"""
MediTriage — FastAPI Backend
Serves the chat UI and handles WebSocket connections for real-time AI interactions.
"""

import os
import sys
import json
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.mcp_client.hub import MCPClientHub
from backend.agent.orchestrator import MediTriageAgent

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("meditriage")

# Global instances
hub = MCPClientHub()
agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect all MCP servers. Shutdown: disconnect."""
    global agent

    logger.info("Starting MediTriage — connecting to 6 MCP servers...")
    await hub.connect_all()
    agent = MediTriageAgent(hub)

    # Log server status
    status = hub.get_server_status()
    for name, info in status.items():
        icon = "✅" if info["connected"] else "❌"
        logger.info(f"  {icon} {name}: {len(info['tools'])} tools — {info['description']}")

    logger.info(f"MediTriage ready — {len(hub.all_tools)} tools across {len(hub.sessions)} servers")
    yield

    logger.info("Shutting down MediTriage...")
    await hub.disconnect_all()


app = FastAPI(title="MediTriage", lifespan=lifespan)

# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


# ── Routes ──────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    """Serve the chat UI."""
    return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/api/status")
async def server_status():
    """Return the connection status of all 6 MCP servers."""
    return JSONResponse(hub.get_server_status())


# ── WebSocket Chat ──────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Real-time chat over WebSocket."""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info(f"[WS] New session: {session_id}")

    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message.strip():
                continue

            logger.info(f"[WS] User: {user_message[:100]}")

            # Send "thinking" status
            await websocket.send_json({
                "type": "status",
                "message": "Analyzing your symptoms..."
            })

            # Process through the agent
            result = await agent.process_message(session_id, user_message)

            # Send tool calls info (for the UI to show which servers were called)
            if result["tool_calls_made"]:
                await websocket.send_json({
                    "type": "tool_calls",
                    "calls": [
                        {
                            "server": tc["server"],
                            "tool": tc["tool"],
                        }
                        for tc in result["tool_calls_made"]
                    ]
                })

            # Send the AI response
            await websocket.send_json({
                "type": "response",
                "message": result["response"],
                "tool_calls_count": len(result["tool_calls_made"]),
            })

            # Send slot data if available (clickable buttons in UI)
            if result.get("slots") and result["slots"].get("slots"):
                await websocket.send_json({
                    "type": "slots",
                    "doctor": result["slots"].get("doctor", ""),
                    "slots": result["slots"]["slots"],
                })

            # Send doctor data if available (doctor cards in UI)
            if result.get("doctors") and result["doctors"].get("doctors"):
                await websocket.send_json({
                    "type": "doctors",
                    "specialty": result["doctors"].get("specialty", ""),
                    "doctors": result["doctors"]["doctors"],
                })

            logger.info(f"[WS] AI response sent ({len(result['tool_calls_made'])} tool calls)")

    except WebSocketDisconnect:
        logger.info(f"[WS] Session {session_id} disconnected")
        agent.clear_session(session_id)
    except Exception as e:
        logger.error(f"[WS] Error in session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Something went wrong: {str(e)}"
            })
        except:
            pass


# ── Init files ──────────────────────────────────────────────────────
# Create __init__.py files for package imports
for path in [
    os.path.join(os.path.dirname(__file__), "__init__.py"),
    os.path.join(os.path.dirname(__file__), "agent", "__init__.py"),
    os.path.join(os.path.dirname(__file__), "mcp_client", "__init__.py"),
]:
    if not os.path.exists(path):
        with open(path, "w") as f:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
