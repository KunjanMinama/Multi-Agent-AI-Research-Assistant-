"""
Planner Agent
=============
The "brain" that decides HOW to answer the user's query.

ROLE:
- Reads the user query
- Creates a step-by-step execution plan
- Decides which agents to involve (researcher? data analyst? both?)
- Sets the routing path via state["next_agent"]

DECISION LOGIC:
- Has data file → include data analyst
- Research keywords (trends, latest, what, why, how) → include researcher
- Pure data → data analyst only
"""

from typing import Dict, Any
from loguru import logger
import os

from .base_v2 import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Analyzes the user query and creates a structured execution plan.

    This is always the FIRST agent to run. Its output shapes the
    entire workflow — which agents run, in what order, and why.
    """

    def __init__(self):
        super().__init__(
            name="Planner",
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            temperature=0.3,  # Low temperature = consistent, predictable plans
        )

    def get_system_prompt(self) -> str:
        return """You are an expert AI workflow planner.

Your job is to analyze user queries and create clear, structured execution plans.

You decide which agents to use:
- RESEARCHER: for questions needing web research (trends, news, facts, explanations)
- DATA_ANALYST: for analyzing uploaded data files and documents (CSV, Excel, PDF, Word .docx, JSON, plain text/markdown)
- BOTH: when the query involves both research AND data

Output format — always respond with exactly this structure:
TASK_TYPE: [research | data_analysis | combined]
NEXT_AGENT: [researcher | data_analyst]
PLAN:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Be concise and decisive. Do not add extra commentary."""

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze query and create execution plan.

        Routing logic:
        - query has data file + research keywords → combined → researcher first
        - query has data file only → data_analyst
        - query has no data file → researcher
        """
        logger.info(f"[Planner] Starting — query: '{state['query'][:60]}...'")

        query = state["query"]
        data_path = state.get("data_path")

        # Determine task type with heuristics before calling LLM
        has_data = bool(data_path)
        research_keywords = [
            "research", "find", "what", "why", "how", "trend", "latest",
            "news", "explain", "describe", "tell me", "search"
        ]
        needs_research = any(kw in query.lower() for kw in research_keywords) or not has_data

        # Build planning prompt
        prompt = f"""Create an execution plan for this query:

Query: {query}
Data File: {data_path if data_path else "None"}
Has Data: {has_data}
Needs Research: {needs_research}

Determine TASK_TYPE and NEXT_AGENT based on the query and available data."""

        try:
            plan_text = self.call_llm(prompt)
            logger.info(f"[Planner] Plan generated successfully")

            # Parse next_agent from LLM output (with fallback)
            next_agent = self._parse_next_agent(plan_text, has_data, needs_research)
            task_type = self._parse_task_type(plan_text, has_data, needs_research)

        except Exception as e:
            # Fallback planning when LLM fails
            logger.error(f"[Planner] LLM failed: {e} — using heuristic fallback")
            state["errors"].append(f"Planner LLM error: {str(e)}")

            if has_data and needs_research:
                task_type = "combined"
                next_agent = "researcher"
                plan_text = f"Fallback plan: Research query '{query}' then analyze {data_path}"
            elif has_data:
                task_type = "data_analysis"
                next_agent = "data_analyst"
                plan_text = f"Fallback plan: Analyze data file {data_path} for '{query}'"
            else:
                task_type = "research"
                next_agent = "researcher"
                plan_text = f"Fallback plan: Research '{query}' on the web"

        # Update state
        state["plan"] = plan_text
        state["task_type"] = task_type  # store for routing decisions
        state["next_agent"] = next_agent
        state["iterations"] += 1

        logger.info(f"[Planner] Done | task_type={task_type} | next_agent={next_agent}")
        return state

    def _parse_next_agent(self, plan_text: str, has_data: bool, needs_research: bool) -> str:
        """
        Extract NEXT_AGENT from LLM output, falling back to heuristics.

        LLM output is parsed first; if not found, heuristics decide.
        This makes the system resilient to LLM formatting variations.
        """
        text_lower = plan_text.lower()

        # Try to parse from LLM output
        if "next_agent: researcher" in text_lower or "next_agent:researcher" in text_lower:
            return "researcher"
        if "next_agent: data_analyst" in text_lower or "next_agent:data_analyst" in text_lower:
            return "data_analyst"

        # Fallback to heuristics
        if has_data and not needs_research:
            return "data_analyst"
        return "researcher"

    def _parse_task_type(self, plan_text: str, has_data: bool, needs_research: bool) -> str:
        """Extract TASK_TYPE from LLM output with heuristic fallback."""
        text_lower = plan_text.lower()

        if "task_type: combined" in text_lower:
            return "combined"
        if "task_type: data_analysis" in text_lower:
            return "data_analysis"
        if "task_type: research" in text_lower:
            return "research"

        # Heuristic fallback
        if has_data and needs_research:
            return "combined"
        elif has_data:
            return "data_analysis"
        return "research"
