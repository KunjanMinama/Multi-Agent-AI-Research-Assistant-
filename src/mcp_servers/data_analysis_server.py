"""
MCP Data Analysis Server
========================
Exposes pandas data analysis functions as MCP tools.
"""
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from loguru import logger

mcp = FastMCP("DataAnalysisServer")

@mcp.tool()
def analyze_dataset(file_path: str) -> Dict[str, Any]:
    """
    Load a CSV or Excel dataset and return summary statistics.
    
    Args:
        file_path: Absolute path to the data file.
        
    Returns:
        Dictionary containing shape, columns, stats, and a sample of the data.
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
        
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path) # Try CSV by default
    except Exception as e:
        return {"error": f"Failed to load dataset: {str(e)}"}

    rows, cols = df.shape
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    missing_info = {col: int(count) for col, count in df.isnull().sum().items() if count > 0}
    
    numeric_stats = {}
    if numeric_cols:
        desc = df[numeric_cols].describe()
        for col in numeric_cols:
            numeric_stats[col] = {
                "mean": round(float(desc.loc["mean", col]), 4),
                "std": round(float(desc.loc["std", col]), 4),
                "min": round(float(desc.loc["min", col]), 4),
                "max": round(float(desc.loc["max", col]), 4),
            }

    sample_data = df.head(5).to_dict(orient="records")

    logger.info(f"Analyzed {file_path}: {rows}x{cols}")
    return {
        "shape": {"rows": rows, "columns": cols},
        "columns": df.columns.tolist(),
        "numeric_columns": numeric_cols,
        "missing_values": missing_info,
        "numeric_stats": numeric_stats,
        "sample": sample_data
    }

if __name__ == "__main__":
    logger.info("Starting Data Analysis MCP Server (stdio)...")
    mcp.run()
