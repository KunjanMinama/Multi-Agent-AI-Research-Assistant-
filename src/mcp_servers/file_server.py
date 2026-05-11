"""
MCP File Server
===============
Exposes basic file reading as an MCP tool.
"""
import os
from mcp.server.fastmcp import FastMCP
from loguru import logger

mcp = FastMCP("FileServer")

@mcp.tool()
def read_file(file_path: str) -> str:
    """
    Read the contents of a file.
    
    Args:
        file_path: Absolute path to the file.
        
    Returns:
        String content of the file.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Read file: {file_path}")
        return content
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return f"Error reading file: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting File MCP Server (stdio)...")
    mcp.run()
