"""
A2A FastAPI Server
==================
Exposes the LangGraph multi-agent workflow as an A2A-compliant endpoint.
"""
import os
import sys
import uuid
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.a2a.agent_card import get_agent_card
from src.graph.workflow import ResearchWorkflow
from src.graph.state import create_initial_state

app = FastAPI(title="Agentic AI System A2A Server")

# Initialize the LangGraph workflow
workflow_runner = ResearchWorkflow()

class A2ATaskRequest(BaseModel):
    id: str
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]

@app.get("/.well-known/agent.json")
async def get_discovery_card():
    """A2A Discovery Endpoint: Returns the Agent Card."""
    return JSONResponse(content=get_agent_card())

@app.post("/a2a/tasks/send")
async def handle_task(request: A2ATaskRequest):
    """
    A2A Task Endpoint.
    Expects a JSON-RPC request.
    params should contain 'query' and optionally 'data_path'
    """
    if request.method != "tasks/send":
        return JSONResponse(status_code=400, content={
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {"code": -32601, "message": "Method not found"}
        })

    params = request.params
    query = params.get("query", "")
    data_path = params.get("data_path", None)

    if not query:
        return JSONResponse(status_code=400, content={
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {"code": -32602, "message": "Invalid params: 'query' is required"}
        })

    logger.info(f"[A2A Server] Received task request: query='{query}'")

    # Initialize LangGraph State
    initial_state = create_initial_state(query=query, data_path=data_path)

    try:
        # Run LangGraph workflow synchronously (could be async in a fully async rewrite)
        final_state = workflow_runner.run(initial_state)
        
        # Format the response back to the A2A client
        response_content = {
            "task_id": str(uuid.uuid4()),
            "status": "completed",
            "result": {
                "final_report": final_state.get("final_report"),
                "errors": final_state.get("errors", []),
                "iterations": final_state.get("iterations", 0)
            }
        }
        
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": request.id,
            "result": response_content
        })

    except Exception as e:
        logger.error(f"[A2A Server] Workflow execution failed: {e}")
        return JSONResponse(status_code=500, content={
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {"code": -32000, "message": str(e)}
        })

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting A2A Server on http://0.0.0.0:8000")
    uvicorn.run("src.a2a.a2a_server:app", host="0.0.0.0", port=8000, reload=True)
