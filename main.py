import os
import sys
import time
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
load_dotenv() # Load env vars for LangSmith Observability

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.graph.workflow import ResearchWorkflow
from src.graph.state import create_initial_state

app = FastAPI(title="Multi-Agent AI Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize workflow
workflow = ResearchWorkflow()

# Active websocket connections
active_connections: List[WebSocket] = []

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection open, wait for messages (not expected from frontend, but just in case)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_ws_message(message: dict):
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to websocket: {e}")

class ResearchRequest(BaseModel):
    query: str

async def run_workflow_and_broadcast(query: str, data_path: str = None):
    start_time = time.time()
    
    # We will simulate stream updates while running the actual workflow
    # because workflow.run is synchronous in its current implementation
    # Wait, workflow.stream() is async!
    # Let's use workflow.stream() to get chunks!
    
    iteration = 1
    final_state = None
    
    try:
        async for chunk in workflow.stream(query, data_path):
            node_name = list(chunk.keys())[0] if chunk else "unknown"
            node_state = chunk[node_name]
            
            # Map node name to agent ID
            agent_id = node_name
            
            if "errors" in node_state and node_state["errors"]:
                status = "error"
                message = node_state["errors"][-1]
            else:
                status = "complete"
                message = f"Completed step"
                
            await broadcast_ws_message({
                "type": "agent_update",
                "agent": agent_id,
                "status": status,
                "message": message,
                "iteration": node_state.get("iterations", iteration),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
            final_state = node_state
            iteration = node_state.get("iterations", iteration)
            
    except Exception as e:
        logger.error(f"Workflow stream error: {e}")
        await broadcast_ws_message({
            "type": "error",
            "message": str(e)
        })
        raise e
        
    elapsed = time.time() - start_time
    
    if final_state is None:
        final_state = {}
        
    metadata = {
        "iterations": final_state.get("iterations", iteration),
        "quality_score": 0.95, # Mock score
        "total_time": f"{elapsed:.1f}s",
        "agents_used": ["planner", "researcher", "data_analyst", "synthesizer", "fact_checker", "writer"]
    }
    
    result = {
        "success": True,
        "final_report": final_state.get("final_report", "No report generated."),
        "metadata": metadata,
        "errors": final_state.get("errors", [])
    }
    
    await broadcast_ws_message({
        "type": "complete",
        "final_report": result["final_report"],
        "metadata": metadata
    })
    
    return result

@app.post("/research")
async def research(req: ResearchRequest):
    return await run_workflow_and_broadcast(req.query)

@app.post("/research-with-data")
async def research_with_data(query: str = Form(...), file: UploadFile = File(...)):
    # Save file temporarily
    os.makedirs("data/uploads", exist_ok=True)
    file_path = f"data/uploads/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    return await run_workflow_and_broadcast(query, file_path)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/.well-known/agent.json")
async def agent_json():
    from src.a2a.agent_card import get_agent_card
    return get_agent_card()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting REST API Server on http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
