"""
Run the A2A FastAPI Server.
"""
import uvicorn
from loguru import logger

if __name__ == "__main__":
    logger.info("Starting A2A Server on http://0.0.0.0:8000")
    logger.info("Discovery endpoint: http://localhost:8000/.well-known/agent.json")
    logger.info("Task endpoint: http://localhost:8000/a2a/tasks/send")
    
    uvicorn.run("src.a2a.a2a_server:app", host="0.0.0.0", port=8000, reload=True)
