"""
Agent Card for Agentic AI System
================================
Provides the discovery metadata for this agent via A2A protocol.
"""
from typing import Dict, Any

def get_agent_card() -> Dict[str, Any]:
    return {
        "name": "Multi-Agent Research & Analysis System",
        "description": "An agent that performs comprehensive research, data analysis, and synthesis using specialized sub-agents via LangGraph.",
        "url": "http://localhost:8000/a2a",
        "version": "1.0.0",
        "capabilities": {
            "web_search": True,
            "data_analysis": True,
            "markdown_reports": True
        },
        "supported_content_types": ["text/plain", "application/json"],
        "authors": ["Antigravity"]
    }
