"""
MCP Web Search Server
=====================
Exposes DuckDuckGo web search as an MCP tool using FastMCP.
"""
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS
from loguru import logger

# Initialize the MCP Server
mcp = FastMCP("WebSearchServer")

@mcp.tool()
def search_web(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search the web using DuckDuckGo.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to fetch
        
    Returns:
        List of dictionaries containing title, body, and href.
    """
    try:
        results = DDGS().text(query, max_results=max_results)
        results_list = list(results) if results else []
        logger.info(f"Searched '{query}', found {len(results_list)} results.")
        return results_list
    except Exception as e:
        logger.error(f"Search failed for '{query}': {e}")
        return [{"error": str(e)}]

if __name__ == "__main__":
    # Start the FastMCP server with stdio transport
    logger.info("Starting Web Search MCP Server (stdio)...")
    mcp.run()
