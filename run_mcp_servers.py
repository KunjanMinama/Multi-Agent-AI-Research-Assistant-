"""
Run all MCP Tool Servers concurrently.
(For demonstration purposes in a single terminal).
"""
import subprocess
import sys
import time

def start_server(script_path: str):
    print(f"Starting {script_path}...")
    return subprocess.Popen(
        [sys.executable, script_path],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

if __name__ == "__main__":
    servers = []
    try:
        # Start Web Search MCP Server
        servers.append(start_server("src/mcp_servers/web_search_server.py"))
        
        # Start Data Analysis MCP Server
        servers.append(start_server("src/mcp_servers/data_analysis_server.py"))
        
        # Start File MCP Server
        servers.append(start_server("src/mcp_servers/file_server.py"))
        
        print("\nAll MCP Servers running on stdio transport...")
        print("Press Ctrl+C to stop.")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down MCP servers...")
        for p in servers:
            p.terminate()
        for p in servers:
            p.wait()
        print("Shutdown complete.")
