"""
MCP Tool Client
===============
Provides a synchronous wrapper to connect to MCP stdio servers and call tools.

Our LangGraph agents are currently synchronous, so we need a helper to run the 
async MCP client code.
"""
import sys
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Get project root to resolve absolute paths
PROJECT_ROOT = Path(__file__).parent.parent.parent

class MCPToolClient:
    """
    Client to connect to a local MCP tool server over stdio.
    """
    def __init__(self, server_script_path: str):
        self.server_script_path = str(PROJECT_ROOT / server_script_path)
        
    async def _call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Asynchronously connect, initialize, and call the tool."""
        server_params = StdioServerParameters(
            command=sys.executable,  # Uses the current Python interpreter
            args=[self.server_script_path],
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.debug(f"[MCP Client] Calling tool '{tool_name}' with args {arguments}")
                result = await session.call_tool(tool_name, arguments=arguments)
                return result.content
                
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Synchronously call an MCP tool.
        
        Args:
            tool_name: The name of the tool (e.g., "search_web")
            arguments: Dict of arguments for the tool
            
        Returns:
            The tool's result content.
        """
        try:
            # Check if we are already in an event loop (e.g. FastAPI/A2A server)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We can't use run_until_complete if loop is running
                import threading
                
                result_container = {}
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result_container["res"] = new_loop.run_until_complete(
                        self._call_tool_async(tool_name, arguments)
                    )
                    new_loop.close()
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                return result_container["res"]
            else:
                return asyncio.run(self._call_tool_async(tool_name, arguments))
        except Exception as e:
            logger.error(f"[MCP Client] Tool call failed: {e}")
            raise

# Helper singletons for agents to use
def get_web_search_client():
    return MCPToolClient("src/mcp_servers/web_search_server.py")

def get_data_analysis_client():
    return MCPToolClient("src/mcp_servers/data_analysis_server.py")
