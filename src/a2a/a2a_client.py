"""
A2A Client Example
==================
Demonstrates how to discover and communicate with our A2A Server.
"""
import requests
import json
import uuid
from loguru import logger

A2A_SERVER_URL = "http://localhost:8000"

def discover_agent():
    """Fetch the Agent Card from the well-known discovery endpoint."""
    logger.info("Discovering Agent...")
    try:
        response = requests.get(f"{A2A_SERVER_URL}/.well-known/agent.json")
        response.raise_for_status()
        card = response.json()
        logger.info(f"Agent Found: {card['name']} (v{card['version']})")
        logger.info(f"Capabilities: {json.dumps(card['capabilities'])}")
        return card
    except Exception as e:
        logger.error(f"Failed to discover agent: {e}")
        return None

def send_task(query: str, data_path: str = None):
    """Send a task to the A2A agent using JSON-RPC."""
    logger.info(f"Sending Task: '{query}'")
    
    request_payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/send",
        "params": {
            "query": query,
            "data_path": data_path
        }
    }
    
    try:
        response = requests.post(f"{A2A_SERVER_URL}/a2a/tasks/send", json=request_payload)
        response.raise_for_status()
        data = response.json()
        
        if "error" in data:
            logger.error(f"Task Error: {data['error']['message']}")
            return
            
        result = data["result"]
        logger.info(f"Task Completed (Iterations: {result['result']['iterations']})")
        
        if result['result']['errors']:
            logger.warning(f"Workflow Warnings: {result['result']['errors']}")
            
        print("\n--- FINAL REPORT ---")
        print(result['result']['final_report'])
        print("--------------------\n")
        
    except Exception as e:
        logger.error(f"Failed to send task: {e}")

if __name__ == "__main__":
    card = discover_agent()
    if card:
        print("\n" + "="*50)
        # Test Query
        send_task("What are the latest breakthroughs in AI?")
