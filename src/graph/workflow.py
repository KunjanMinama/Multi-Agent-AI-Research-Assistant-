"""
LangGraph Workflow — Component 5
==================================
Orchestrates the complete multi-agent pipeline using LangGraph StateGraph.

ARCHITECTURE:
                    ┌──────────┐
                    │  START   │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ PLANNER  │  ← Always runs first
                    └────┬─────┘
                         │ _router()
           ┌─────────────┼──────────────┐
           │             │              │
    ┌──────▼───┐  ┌──────▼──────┐  ┌───▼──────┐
    │RESEARCHER│  │DATA_ANALYST │  │SYNTHESIZER│
    └──────┬───┘  └──────┬──────┘  └───┬──────┘
           │              │             │
           └──────────────┴─────────────┘
                         │ _router()
                    ┌────▼─────┐
                    │  WRITER  │
                    └────┬─────┘
                         │
                      ┌──▼──┐
                      │ END │
                      └─────┘

ROUTING LOGIC:
- Planner → researcher (if research needed) or data_analyst (if data only)
- Researcher → data_analyst (if data file exists) or synthesizer
- Data_analyst → synthesizer (always)
- Synthesizer → writer (always)
- Writer → END (always)
- Any node → END if iterations > 10 (safety circuit breaker)

WHY LANGGRAPH?
- Type-safe state management (no shared mutable state bugs)
- Conditional routing built-in
- Automatic state merging (Annotated[int, add] for counters)
- Easy visualization and debugging
- Async streaming support
"""

import time
from typing import Dict, Any, Literal, Optional, AsyncGenerator

from loguru import logger
from langgraph.graph import StateGraph, END

from .state import AgentState, create_initial_state
from ..agents.planner import PlannerAgent
from ..agents.researcher import ResearcherAgent
from ..agents.data_analyst import DataAnalystAgent
from ..agents.synthesizer import SynthesizerAgent
from ..agents.fact_checker import FactCheckerAgent
from ..agents.writer import WriterAgent


class ResearchWorkflow:
    """
    Orchestrates the complete multi-agent research and analysis pipeline.

    Usage:
    ------
    workflow = ResearchWorkflow()

    # Synchronous run
    result = workflow.run("What are AI trends in healthcare?")
    print(result["final_report"])

    # With data
    result = workflow.run("Analyze sales", data_path="sales.csv")

    # Async streaming
    async for chunk in workflow.stream("Analyze AI trends"):
        print(chunk)
    """

    def __init__(self):
        """
        Initialize all agent instances and build the LangGraph state machine.

        Agent initialization is eager (done at startup) to fail fast if
        credentials are missing, rather than failing mid-workflow.
        """
        logger.info("Initializing ResearchWorkflow...")

        # ── Instantiate all agents ────────────────────────────────────────────
        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.data_analyst = DataAnalystAgent()
        self.synthesizer = SynthesizerAgent()
        self.fact_checker = FactCheckerAgent()
        self.writer = WriterAgent()

        # ── Build and compile the LangGraph workflow ──────────────────────────
        self.app = self._build_graph()

        logger.info("✅ ResearchWorkflow ready")

    def _build_graph(self):
        """
        Construct the LangGraph StateGraph with all nodes and edges.

        Design decisions:
        - All edges from planner, researcher, data_analyst use _router()
        - Writer always ends (no routing needed)
        - Conditional edges map string → node_name for LangGraph compatibility
        """
        workflow = StateGraph(AgentState)

        # ── Add all agent nodes ───────────────────────────────────────────────
        workflow.add_node("planner", self._run_planner)
        workflow.add_node("researcher", self._run_researcher)
        workflow.add_node("data_analyst", self._run_data_analyst)
        workflow.add_node("synthesizer", self._run_synthesizer)
        workflow.add_node("fact_checker", self._run_fact_checker)
        workflow.add_node("writer", self._run_writer)

        # ── Set entry point ───────────────────────────────────────────────────
        workflow.set_entry_point("planner")

        # ── Define all routing edges ──────────────────────────────────────────
        # Each routing map must list ALL possible outputs of _router()
        routing_map = {
            "researcher": "researcher",
            "data_analyst": "data_analyst",
            "synthesizer": "synthesizer",
            "fact_checker": "fact_checker",
            "writer": "writer",
            "end": END,
        }

        # Planner can route to any agent
        workflow.add_conditional_edges("planner", self._router, routing_map)

        # Researcher → data_analyst or synthesizer
        workflow.add_conditional_edges("researcher", self._router, routing_map)

        # Data analyst → always synthesizer (but router handles the dispatch)
        workflow.add_conditional_edges("data_analyst", self._router, routing_map)

        # Synthesizer → always fact_checker
        workflow.add_edge("synthesizer", "fact_checker")
        
        # FactChecker → writer (if passed) or synthesizer (if failed)
        workflow.add_conditional_edges("fact_checker", self._router, routing_map)

        # Writer → always END (no conditional needed)
        workflow.add_edge("writer", END)

        return workflow.compile()

    # ── Router ────────────────────────────────────────────────────────────────

    def _router(self, state: AgentState) -> Literal[
        "researcher", "data_analyst", "synthesizer", "fact_checker", "writer", "end"
    ]:
        """
        Route the workflow based on state["next_agent"].

        Safety features:
        - Iteration limit (>10 = force end) prevents infinite loops
        - None/unknown next_agent = safe END
        - All valid routes explicitly listed for LangGraph type checking

        This is a pure routing function — it NEVER modifies state.
        """
        # Safety: circuit breaker to prevent infinite loops
        if state.get("iterations", 0) > 10:
            logger.warning(
                f"[Router] Iteration limit exceeded ({state['iterations']}) → forcing END"
            )
            return "end"

        next_agent = state.get("next_agent")

        if next_agent == "researcher":
            logger.info("[Router] → researcher")
            return "researcher"
        elif next_agent == "data_analyst":
            logger.info("[Router] → data_analyst")
            return "data_analyst"
        elif next_agent == "synthesizer":
            logger.info("[Router] → synthesizer")
            return "synthesizer"
        elif next_agent == "fact_checker":
            logger.info("[Router] → fact_checker")
            return "fact_checker"
        elif next_agent == "writer":
            logger.info("[Router] → writer")
            return "writer"
        else:
            logger.info(f"[Router] next_agent='{next_agent}' → end")
            return "end"

    # ── Agent Wrapper Methods ─────────────────────────────────────────────────
    # These wrappers provide:
    # 1. Logging with EXECUTING banner
    # 2. Error isolation (caught exceptions don't crash the whole workflow)
    # 3. Error tracking in state["errors"]

    def _run_planner(self, state: AgentState) -> AgentState:
        """Execute planner with error isolation."""
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("EXECUTING: Planner")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        try:
            return self.planner.execute(state)
        except Exception as e:
            logger.error(f"Planner failed: {e}")
            state["errors"].append(f"Planner: {str(e)}")
            # Fallback routing — try research if planner fails
            state["next_agent"] = "researcher"
            return state

    def _run_researcher(self, state: AgentState) -> AgentState:
        """Execute researcher with error isolation."""
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("EXECUTING: Researcher")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        try:
            return self.researcher.execute(state)
        except Exception as e:
            logger.error(f"Researcher failed: {e}")
            state["errors"].append(f"Researcher: {str(e)}")
            # Skip to appropriate next step
            state["next_agent"] = "data_analyst" if state.get("data_path") else "synthesizer"
            return state

    def _run_data_analyst(self, state: AgentState) -> AgentState:
        """Execute data analyst with error isolation."""
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("EXECUTING: Data Analyst")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        try:
            return self.data_analyst.execute(state)
        except Exception as e:
            logger.error(f"DataAnalyst failed: {e}")
            state["errors"].append(f"DataAnalyst: {str(e)}")
            state["next_agent"] = "synthesizer"
            return state

    def _run_synthesizer(self, state: AgentState) -> AgentState:
        """Execute synthesizer with error isolation."""
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("EXECUTING: Synthesizer")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        try:
            return self.synthesizer.execute(state)
        except Exception as e:
            logger.error(f"Synthesizer failed: {e}")
            state["errors"].append(f"Synthesizer: {str(e)}")
            state["combined_report"] = (
                state.get("research_findings", "") + "\n" +
                state.get("analysis_insights", "")
            )
            state["next_agent"] = "fact_checker"
            return state

    def _run_fact_checker(self, state: AgentState) -> AgentState:
        """Execute fact checker with error isolation."""
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("EXECUTING: Fact Checker")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        try:
            return self.fact_checker.execute(state)
        except Exception as e:
            logger.error(f"FactChecker failed: {e}")
            state["errors"].append(f"FactChecker: {str(e)}")
            state["next_agent"] = "writer"
            return state

    def _run_writer(self, state: AgentState) -> AgentState:
        """Execute writer with error isolation."""
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("EXECUTING: Writer")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        try:
            return self.writer.execute(state)
        except Exception as e:
            logger.error(f"Writer failed: {e}")
            state["errors"].append(f"Writer: {str(e)}")
            # Minimal report as fallback
            state["final_report"] = (
                f"# Report: {state['query']}\n\n"
                + (state.get("combined_report") or state.get("research_findings") or
                   "Analysis could not be completed.")
            )
            state["next_agent"] = None
            return state

    # ── Public Interface ──────────────────────────────────────────────────────

    def run(self, query: str, data_path: Optional[str] = None) -> AgentState:
        """
        Run the complete multi-agent workflow synchronously.

        This is the primary entry point for the CLI and tests.

        Args:
            query: The research question or analysis task
            data_path: Optional path to CSV/Excel file for data analysis

        Returns:
            Final AgentState with all results populated:
            - state["final_report"]: The polished markdown report
            - state["research_findings"]: Raw research findings
            - state["analysis_insights"]: Data analysis insights
            - state["errors"]: Any errors encountered
            - state["iterations"]: Total agent calls made
        """
        logger.info("=" * 60)
        logger.info(f"WORKFLOW START: '{query[:50]}'")
        logger.info("=" * 60)

        start_time = time.time()

        # Create initial state
        initial_state = create_initial_state(query, data_path)

        # Run the LangGraph workflow
        try:
            final_state = self.app.invoke(initial_state)
        except Exception as e:
            logger.error(f"Workflow crashed: {e}")
            # Return partial state with error
            initial_state["errors"].append(f"Workflow crash: {str(e)}")
            initial_state["final_report"] = (
                f"# Workflow Error\n\nThe workflow encountered an error: {e}"
            )
            return initial_state

        elapsed = time.time() - start_time

        logger.info("=" * 60)
        logger.info(f"WORKFLOW COMPLETE in {elapsed:.1f}s")
        logger.info(f"  Iterations: {final_state.get('iterations', 0)}")
        logger.info(f"  Errors: {len(final_state.get('errors', []))}")
        logger.info("=" * 60)

        return final_state

    async def stream(
        self, query: str, data_path: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream workflow execution for real-time updates.

        Each yielded chunk contains the node name and partial state.
        Useful for WebSocket / streaming API endpoints.

        Usage:
        ------
        async for chunk in workflow.stream("AI trends"):
            node_name = list(chunk.keys())[0]
            node_state = chunk[node_name]
            print(f"Completed: {node_name}")

        Args:
            query: Research question
            data_path: Optional data file path

        Yields:
            Dict with node_name → partial_state for each completed node
        """
        logger.info(f"STREAM START: '{query[:50]}'")
        initial_state = create_initial_state(query, data_path)

        async for chunk in self.app.astream(initial_state):
            node_name = list(chunk.keys())[0] if chunk else "unknown"
            logger.info(f"STREAM chunk: {node_name}")
            yield chunk

    def get_agent_stats(self) -> Dict[str, Any]:
        """
        Return performance statistics for all agents.

        Useful for monitoring agent performance across a session.
        """
        return {
            "planner": self.planner.get_stats(),
            "researcher": self.researcher.get_stats(),
            "data_analyst": self.data_analyst.get_stats(),
            "synthesizer": self.synthesizer.get_stats(),
            "fact_checker": self.fact_checker.get_stats(),
            "writer": self.writer.get_stats(),
        }


# ── Standalone Integration Test ───────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")

    print("\n" + "="*60)
    print("INTEGRATION TEST: Full Workflow")
    print("="*60)

    workflow = ResearchWorkflow()

    # Test 1: Research-only
    print("\n[Test 1] Research-only query...")
    result = workflow.run("What are the key trends in quantum computing?")

    print(f"\nFinal Report (first 400 chars):")
    print(result["final_report"][:400])
    print(f"\nIterations: {result['iterations']}")
    print(f"Errors: {result['errors']}")

    print("\n✅ Workflow integration test complete!")
