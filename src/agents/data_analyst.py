"""
Data Analyst Agent — Component 2
==================================
Loads CSV/Excel files with pandas and generates LLM-powered insights.

DESIGN PHILOSOPHY:
- Pandas for all data operations (industry standard)
- Generates both structured stats AND narrative insights
- Handles missing files gracefully (skips, routes to synthesizer)
- Truncates large datasets to stay within LLM context limits

FLOW:
  data_path → load file → compute statistics → LLM analysis
           → store data_summary + analysis_insights → route to synthesizer
"""

import os
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np
from loguru import logger

from .base_v2 import BaseAgent
from src.mcp_client.tool_client import get_data_analysis_client, get_file_client

class DataAnalystAgent(BaseAgent):
    """
    Analyzes CSV/Excel data files and generates structured insights via LLM.

    Key design decisions:
    - Separates "structural summary" (pandas stats) from "narrative insights" (LLM)
    - Truncates long data for LLM to avoid context overflow
    - Continues gracefully if data file is missing (doesn't crash the workflow)
    """

    def __init__(self):
        super().__init__(
            name="DataAnalyst",
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            temperature=0.3,  # Low temperature = precise, consistent analysis
        )

    def get_system_prompt(self) -> str:
        return """You are an expert data analyst and statistician.

Your role:
- Analyze datasets and extract meaningful insights
- Identify patterns, trends, and anomalies
- Provide specific, quantitative observations
- Connect data findings to the user's query context
- Flag data quality issues (missing values, outliers, skewness)

Standards:
- Always cite specific numbers and values
- Distinguish correlation from causation
- Highlight actionable insights
- Use clear, professional language"""

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load data file and generate comprehensive analysis via MCP.
        Supports both tabular data (CSV/Excel) and text documents (PDF/Word/JSON/TXT/MD).
        """
        logger.info("[DataAnalyst] Starting data analysis via MCP")

        query = state["query"]
        data_path = state.get("data_path")

        # ── Guard: no data file ───────────────────────────────────────────────
        if not data_path:
            logger.info("[DataAnalyst] No data_path — skipping to synthesizer")
            state["data_summary"] = None
            state["analysis_insights"] = "No data file provided — analysis skipped."
            state["next_agent"] = "synthesizer"
            state["iterations"] += 1
            return state

        if not os.path.exists(data_path):
            logger.warning(f"[DataAnalyst] File not found: {data_path}")
            state["errors"].append(f"DataAnalyst: File not found — {data_path}")
            state["data_summary"] = None
            state["analysis_insights"] = f"Data file '{data_path}' was not found."
            state["next_agent"] = "synthesizer"
            state["iterations"] += 1
            return state

        ext = os.path.splitext(data_path)[1].lower()

        # ── Route based on file type ─────────────────────────────────────────
        if ext in (".pdf", ".docx", ".json", ".txt", ".md"):
            return self._execute_document_analysis(state, data_path, ext)
        else:
            return self._execute_tabular_analysis(state, data_path)

    def _execute_tabular_analysis(self, state: Dict[str, Any], data_path: str) -> Dict[str, Any]:
        """Existing pandas analysis flow for tabular datasets."""
        query = state["query"]
        summary = self._analyze_via_mcp(data_path)
        if summary is None:
            state["errors"].append(f"DataAnalyst: MCP analysis failed for {data_path}")
            state["next_agent"] = "synthesizer"
            state["iterations"] += 1
            return state

        state["data_summary"] = summary
        logger.info("[DataAnalyst] MCP Structural summary computed")

        # LLM analysis
        analysis_prompt = self._build_analysis_prompt(query, summary)

        try:
            insights = self.call_llm(analysis_prompt)
            logger.info(f"[DataAnalyst] Insights generated ({len(insights)} chars)")
        except Exception as e:
            logger.error(f"[DataAnalyst] LLM analysis failed: {e}")
            state["errors"].append(f"DataAnalyst LLM error: {str(e)}")
            # Fallback: use the structural summary as insights
            insights = self._summary_to_text(summary)

        # Update state
        state["analysis_insights"] = insights
        state["next_agent"] = "synthesizer"
        state["iterations"] += 1

        logger.info("[DataAnalyst] Tabular analysis done → routing to synthesizer")
        return state

    def _execute_document_analysis(self, state: Dict[str, Any], data_path: str, ext: str) -> Dict[str, Any]:
        """New document analysis flow for PDF, Word, JSON, and Text files."""
        query = state["query"]
        logger.info(f"[DataAnalyst] Starting document analysis via MCP File Server for {ext}")
        
        try:
            client = get_file_client()
            abs_path = os.path.abspath(data_path)
            result_content = client.call_tool("read_file", {"file_path": abs_path})
            
            if result_content and len(result_content) > 0:
                text_content = result_content[0].text
            else:
                text_content = ""
        except Exception as e:
            logger.error(f"[DataAnalyst] MCP File read failed: {e}")
            state["errors"].append(f"DataAnalyst: File read failed — {str(e)}")
            state["data_summary"] = {"file_type": ext, "error": str(e)}
            state["analysis_insights"] = f"Failed to read document file: {str(e)}"
            state["next_agent"] = "synthesizer"
            state["iterations"] += 1
            return state

        if not text_content or text_content.startswith("Error"):
            state["errors"].append(f"DataAnalyst File Reader: {text_content}")
            state["data_summary"] = {"file_type": ext, "error": text_content}
            state["analysis_insights"] = f"Failed to extract text from document: {text_content}"
            state["next_agent"] = "synthesizer"
            state["iterations"] += 1
            return state

        # Cap text at 12,000 characters to prevent prompt bloat while retaining high quality
        max_chars = 12000
        truncated = False
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + f"\n\n... [TRUNCATED - Content exceeded {max_chars} characters] ..."
            truncated = True

        state["data_summary"] = {
            "file_type": ext,
            "char_count": len(text_content),
            "is_truncated": truncated,
            "preview": text_content[:200] + "..."
        }

        # Build analysis prompt for document
        document_prompt = f"""Analyze the following document in context of the query: "{query}"

Document Type: {ext.upper()}
Character Count: {len(text_content)}

Document Content:
\"\"\"
{text_content}
\"\"\"

Provide a comprehensive, high-quality document analysis containing:
1. Detailed Summary: A summary of the document's main topics and overall thesis.
2. Key Insights & Findings: Extract specific data points, quotes, facts, or statistics relevant to the query.
3. Analysis & Relevance: Explain how this document helps answer the user's research query: "{query}".
4. Quality & Context: Note the tone, target audience, credibility, and any limitations or conflicts within the text.

Format your analysis clearly in markdown, referencing specific sections if available in the text. Be precise and objective."""

        try:
            insights = self.call_llm(document_prompt)
            logger.info(f"[DataAnalyst] Document insights generated ({len(insights)} chars)")
        except Exception as e:
            logger.error(f"[DataAnalyst] LLM document analysis failed: {e}")
            state["errors"].append(f"DataAnalyst LLM document error: {str(e)}")
            insights = f"Successfully read {ext.upper()} document but LLM analysis failed: {str(e)}\n\nPreview:\n{text_content[:1000]}..."

        state["analysis_insights"] = insights
        state["next_agent"] = "synthesizer"
        state["iterations"] += 1
        
        logger.info("[DataAnalyst] Document analysis complete → routing to synthesizer")
        return state

    # ── Private Helper Methods ────────────────────────────────────────────────

    def _analyze_via_mcp(self, data_path: str) -> Optional[Dict[str, Any]]:
        """
        Use the MCP Data Analysis Server to load and analyze the dataset.
        """
        try:
            client = get_data_analysis_client()
            
            abs_path = os.path.abspath(data_path)
            result_content = client.call_tool("analyze_dataset", {"file_path": abs_path})
            
            import json
            if result_content and len(result_content) > 0:
                text_result = result_content[0].text
                if isinstance(text_result, str):
                    text_result = text_result.replace("'", '"')
                    try:
                        summary = json.loads(text_result)
                    except json.JSONDecodeError:
                        import ast
                        summary = ast.literal_eval(text_result)
                else:
                    summary = text_result
                    
                if "error" in summary:
                    logger.error(f"[DataAnalyst] MCP Error: {summary['error']}")
                    return None
                    
                # Format for prompt compatibility
                if "column_names" not in summary and "columns" in summary:
                    summary["column_names"] = summary["columns"]
                if "duplicate_rows" not in summary:
                    summary["duplicate_rows"] = 0
                if "correlations" not in summary:
                    summary["correlations"] = {}
                if "categorical_columns" not in summary:
                    summary["categorical_columns"] = []
                    
                return summary
            return None

        except Exception as e:
            logger.error(f"[DataAnalyst] MCP Analysis failed for '{data_path}': {e}")
            return None
    def _build_analysis_prompt(
        self, query: str, summary: Dict[str, Any]
    ) -> str:
        """
        Build a detailed prompt for LLM analysis.

        Includes:
        - Query context (so LLM can give relevant insights)
        - Structural summary (shape, columns, stats)
        - Sample data rows (first 5, for concrete examples)
        """
        shape = summary["shape"]
        numeric_stats = summary["numeric_stats"]
        missing = summary["missing_values"]
        correlations = summary["correlations"]

        # Format numeric stats compactly
        stats_lines = []
        for col, stats in list(numeric_stats.items())[:8]:  # Top 8 columns
            stats_lines.append(
                f"  {col}: mean={stats['mean']}, std={stats['std']}, "
                f"min={stats['min']}, max={stats['max']}"
            )
        stats_summary = "\n".join(stats_lines) or "No numeric columns"

        # Format missing values
        missing_summary = (
            ", ".join(f"{col}: {n} missing" for col, n in list(missing.items())[:5])
            or "No missing values"
        )

        # Sample data (first 5 rows)
        sample_data = summary.get("sample", [])
        if sample_data:
            import json
            sample = json.dumps(sample_data, indent=2)
        else:
            sample = "No sample data available."

        # Format correlations
        corr_text = (
            ", ".join(f"{pair}: r={r}" for pair, r in correlations.items())
            or "No strong correlations found"
        )

        return f"""Analyze this dataset in context of the query: "{query}"

Dataset Summary:
- Shape: {shape['rows']} rows × {shape['columns']} columns
- Columns: {', '.join(summary['column_names'][:15])}
- Numeric columns: {', '.join(summary['numeric_columns'][:8])}
- Categorical columns: {', '.join(summary['categorical_columns'][:5])}

Numeric Statistics:
{stats_summary}

Missing Values: {missing_summary}
Duplicate Rows: {summary['duplicate_rows']}
Strong Correlations: {corr_text}

Sample Data (first 5 rows):
{sample}

Provide a comprehensive data analysis with:
1. Key characteristics of this dataset
2. Notable patterns and trends (with specific numbers)
3. Interesting correlations or relationships
4. Data quality observations (missing values, outliers, anomalies)
5. Insights specifically relevant to: "{query}"

Be specific with numbers. Reference actual column names and values."""

    def _summary_to_text(self, summary: Dict[str, Any]) -> str:
        """
        Convert structured summary to readable text (used as LLM fallback).
        """
        shape = summary["shape"]
        return (
            f"Dataset contains {shape['rows']} rows and {shape['columns']} columns. "
            f"Columns: {', '.join(summary['column_names'][:10])}. "
            f"Numeric columns: {', '.join(summary['numeric_columns'][:5])}. "
            f"Missing values in: {list(summary['missing_values'].keys())[:5]}. "
            f"Duplicate rows: {summary['duplicate_rows']}."
        )


# ── Standalone Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import csv
    import tempfile
    import os

    # Create a test CSV file
    test_data = [
        ["month", "sales", "profit", "region"],
        ["Jan", 10000, 2000, "North"],
        ["Feb", 12000, 2400, "North"],
        ["Mar", 15000, 3000, "South"],
        ["Apr", 13000, 2600, "South"],
        ["May", 18000, 3600, "East"],
        ["Jun", 20000, 4000, "East"],
    ]

    # Write to temp CSV
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="")
    writer = csv.writer(tmp)
    writer.writerows(test_data)
    tmp.close()

    print("\n" + "="*60)
    print("TESTING DATA ANALYST AGENT")
    print("="*60)

    sys.path.insert(0, ".")
    from src.graph.state import create_initial_state

    agent = DataAnalystAgent()
    state = create_initial_state(
        query="Analyze monthly sales trends and identify peak months",
        data_path=tmp.name
    )

    result = agent.execute(state)

    print(f"\nData Summary: {result['data_summary']['shape']}")
    print(f"\nAnalysis Insights:\n{result['analysis_insights'][:500]}...")
    print(f"\nNext Agent: {result['next_agent']}")

    os.unlink(tmp.name)  # Cleanup
    print("\n✅ Data Analyst Agent works!")
