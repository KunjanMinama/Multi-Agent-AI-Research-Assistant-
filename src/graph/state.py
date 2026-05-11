"""
STATE DEFINITION - The Shared Memory of Our Multi-Agent System

WHAT IS STATE?
--------------
Think of State as a "shared whiteboard" that all agents can read and write to.
- Planner reads the query, writes the plan
- Researcher reads the plan, writes research results
- Data Analyst reads the query + data path, writes analysis
- And so on...

WHY DO WE NEED THIS?
--------------------
Without shared state:
  Agent1 → Agent2 → Agent3  (each has to pass everything manually)
  
With shared state:
  Agent1 ↓
         STATE (everyone reads/writes here)
  Agent2 ↓
  Agent3 ↓

This is MUCH cleaner and allows agents to run in any order.

LANGGRAPH'S MAGIC:
------------------
LangGraph automatically:
1. Passes this state to each agent
2. Merges updates from agents
3. Tracks the history
4. Handles the flow between agents
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from operator import add


class AgentState(TypedDict):
    """
    This is THE CORE of our system.
    Every piece of information flows through this state.
    
    TypedDict = Python dictionary with type hints (helps catch bugs)
    """
    
    # ============= INPUT (what user provides) =============
    query: str  # The question/task from user
    data_path: Optional[str]  # Path to CSV/Excel file (if any)
    
    # ============= PLANNING =============
    plan: Optional[str]  # The execution plan created by Planner
    next_agent: Optional[str]  # Which agent should run next?
    
    # ============= RESEARCH RESULTS =============
    research_findings: Optional[str]  # What the Researcher found
    search_results: List[Dict[str, Any]]  # Raw search results
    
    # ============= DATA ANALYSIS RESULTS =============
    data_summary: Optional[Dict[str, Any]]  # Statistics from data
    analysis_insights: Optional[str]  # LLM-generated insights
    
    # ============= SYNTHESIS =============
    combined_report: Optional[str]  # Research + Data combined
    
    # ============= QUALITY CONTROL =============
    quality_score: float  # 0.0 to 1.0, how good is the output?
    needs_revision: bool  # Should we loop back and improve?
    
    # ============= FINAL OUTPUT =============
    final_report: Optional[str]  # The polished final report
    
    # ============= TRACKING & METADATA =============
    # Annotated[int, add] means: when merging states, ADD the numbers
    # (otherwise LangGraph would just replace the value)
    iterations: int  # How many agent calls so far?
    errors: List[str]  # Any errors encountered
    
    # NOTE: We don't include "current_agent" in state because 
    # LangGraph tracks that automatically


# Helper function to create initial state
def create_initial_state(query: str, data_path: str = None) -> AgentState:
    """
    Creates a fresh state when user starts a new task.
    
    This is like setting up a blank whiteboard before the agents start working.
    """
    return AgentState(
        query=query,
        data_path=data_path,
        plan=None,
        next_agent="planner",  # Always start with Planner
        research_findings=None,
        search_results=[],
        data_summary=None,
        analysis_insights=None,
        combined_report=None,
        quality_score=0.0,
        needs_revision=False,
        final_report=None,
        iterations=0,
        errors=[]
    )


# Let's test this works
if __name__ == "__main__":
    # Create a test state
    test_state = create_initial_state(
        query="What are the latest trends in AI?",
        data_path=None
    )
    
    print("Initial State Created:")
    print(f"  Query: {test_state['query']}")
    print(f"  Next Agent: {test_state['next_agent']}")
    print(f"  Iterations: {test_state['iterations']}")
    print("\n✅ State definition works!")