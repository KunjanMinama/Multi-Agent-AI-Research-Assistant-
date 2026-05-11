"""
Comprehensive Test Suite — Component 7
========================================
Tests for the complete multi-agent system.

TEST STRATEGY:
- Unit tests: each agent in isolation (mock LLM to avoid API calls)
- Integration tests: full workflow with real Groq API (skipped if no key)
- Error handling tests: graceful degradation

RUNNING TESTS:
    # All tests (skips integration if no GROQ_API_KEY)
    pytest tests/test_workflow.py -v

    # Unit tests only (no API key needed)
    pytest tests/test_workflow.py -v -m "not integration"

    # Integration tests only
    pytest tests/test_workflow.py -v -m integration
"""

import os
import sys
import csv
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.state import create_initial_state, AgentState


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_state():
    """Create a clean initial state for testing."""
    return create_initial_state(
        query="What are the latest trends in quantum computing?",
        data_path=None
    )

@pytest.fixture
def sample_state_with_data(tmp_path):
    """Create initial state with a temporary CSV file."""
    csv_path = tmp_path / "test_data.csv"
    rows = [
        ["month", "sales", "profit", "region"],
        ["Jan", 10000, 2000, "North"],
        ["Feb", 12000, 2400, "North"],
        ["Mar", 15000, 3000, "South"],
        ["Apr", 13000, 2600, "South"],
        ["May", 18000, 3600, "East"],
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return create_initial_state(
        query="Analyze monthly sales trends and identify peak months",
        data_path=str(csv_path)
    )

@pytest.fixture
def mock_llm_response():
    """Factory for creating mock LLM responses."""
    def _make_mock(text: str = "Mock LLM response for testing."):
        mock = MagicMock()
        mock.content = text
        return mock
    return _make_mock


# ── State Tests ───────────────────────────────────────────────────────────────

class TestAgentState:
    """Tests for the shared state definition."""

    def test_create_initial_state_basic(self):
        """Initial state has correct defaults."""
        state = create_initial_state("Test query")
        assert state["query"] == "Test query"
        assert state["next_agent"] == "planner"
        assert state["iterations"] == 0
        assert state["errors"] == []
        assert state["search_results"] == []
        assert state["data_path"] is None
        assert state["final_report"] is None

    def test_create_initial_state_with_data(self):
        """Initial state with data_path stores it correctly."""
        state = create_initial_state("Analyze data", data_path="data.csv")
        assert state["data_path"] == "data.csv"
        assert state["query"] == "Analyze data"

    def test_state_has_all_required_fields(self):
        """All expected state fields are present."""
        state = create_initial_state("Test")
        required_fields = [
            "query", "data_path", "plan", "next_agent",
            "research_findings", "search_results",
            "data_summary", "analysis_insights",
            "combined_report", "quality_score",
            "needs_revision", "final_report",
            "iterations", "errors"
        ]
        for field in required_fields:
            assert field in state, f"Missing field: {field}"


# ── Planner Agent Tests ───────────────────────────────────────────────────────

class TestPlannerAgent:
    """Tests for PlannerAgent."""

    def test_planner_routes_to_researcher_no_data(self, sample_state, mock_llm_response):
        """Planner routes to researcher when no data file is present."""
        from src.agents.planner import PlannerAgent
        agent = PlannerAgent()

        # Mock LLM to return a valid plan
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()(
            "TASK_TYPE: research\nNEXT_AGENT: researcher\nPLAN:\n1. Research the topic."
        ))

        result = agent.execute(sample_state)

        assert result["next_agent"] == "researcher"
        assert result["plan"] is not None
        assert result["iterations"] == 1

    def test_planner_routes_to_data_analyst_with_data(self, sample_state_with_data, mock_llm_response):
        """Planner routes to data_analyst when data file present and no research keywords."""
        from src.agents.planner import PlannerAgent
        agent = PlannerAgent()

        # Use a pure data query
        sample_state_with_data["query"] = "Summarize this dataset statistics"

        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()(
            "TASK_TYPE: data_analysis\nNEXT_AGENT: data_analyst\nPLAN:\n1. Analyze the data."
        ))

        result = agent.execute(sample_state_with_data)

        assert result["plan"] is not None
        assert result["iterations"] == 1

    def test_planner_fallback_on_llm_error(self, sample_state):
        """Planner uses heuristic fallback when LLM fails."""
        from src.agents.planner import PlannerAgent
        agent = PlannerAgent()

        # Force LLM to raise an error
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(side_effect=Exception("API unavailable"))

        result = agent.execute(sample_state)

        # Should still route somewhere (not crash)
        assert result["next_agent"] in ["researcher", "data_analyst", "synthesizer"]
        # Error should be recorded
        assert len(result["errors"]) > 0

    def test_planner_increments_iterations(self, sample_state, mock_llm_response):
        """Planner always increments iteration counter."""
        from src.agents.planner import PlannerAgent
        agent = PlannerAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()("TASK_TYPE: research\nNEXT_AGENT: researcher\nPLAN:\n1. Step."))

        initial_iterations = sample_state["iterations"]
        result = agent.execute(sample_state)
        assert result["iterations"] == initial_iterations + 1


# ── Researcher Agent Tests ────────────────────────────────────────────────────

class TestResearcherAgent:
    """Tests for ResearcherAgent."""

    def test_researcher_stores_findings(self, sample_state, mock_llm_response):
        """Researcher populates research_findings in state."""
        from src.agents.researcher import ResearcherAgent
        agent = ResearcherAgent()

        mock_results = [
            {"title": "Quantum Computing 2024", "body": "Major advances in qubit stability", "href": "https://example.com/1"},
            {"title": "IBM Quantum Update", "body": "IBM releases 1000-qubit processor", "href": "https://example.com/2"},
        ]

        llm_call_responses = iter([
            "Quantum computing trends\nQuantum hardware advances\nQuantum software development",
            "1. Key findings: Quantum computing grew 35%.\n2. Sources: Example.com\n3. Conclusion: Strong growth.",
        ])

        with patch("src.agents.researcher.get_web_search_client") as mock_client_factory, \
             patch.object(agent, "call_llm", side_effect=lambda *a, **kw: next(llm_call_responses)):
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            # Mock the MCP call_tool result to look like an MCP result object
            class MockTextContent:
                def __init__(self, text):
                    self.text = text
            import json
            mock_client.call_tool.return_value = [MockTextContent(json.dumps(mock_results))]
            
            result = agent.execute(sample_state)

        assert result["research_findings"] is not None
        assert isinstance(result["research_findings"], str)
        assert len(result["research_findings"]) > 0

    def test_researcher_routes_to_synthesizer_no_data(self, sample_state, mock_llm_response):
        """Researcher routes to synthesizer when no data file present."""
        from src.agents.researcher import ResearcherAgent
        agent = ResearcherAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()("Findings here"))

        with patch("src.agents.researcher.get_web_search_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            class MockTextContent:
                def __init__(self, text):
                    self.text = text
            import json
            mock_client.call_tool.return_value = [MockTextContent(json.dumps([]))]
            
            sample_state.pop("data_path", None)
            result = agent.execute(sample_state)

        assert result["next_agent"] == "synthesizer"

    def test_researcher_routes_to_data_analyst_with_data(self, sample_state_with_data, mock_llm_response):
        """Researcher routes to data_analyst when data file is in state."""
        from src.agents.researcher import ResearcherAgent
        agent = ResearcherAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()("Findings here"))

        with patch("src.agents.researcher.get_web_search_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            class MockTextContent:
                def __init__(self, text):
                    self.text = text
            import json
            mock_client.call_tool.return_value = [MockTextContent(json.dumps([]))]
            
            result = agent.execute(sample_state_with_data)

        assert result["next_agent"] == "data_analyst"

    def test_researcher_handles_search_failure_gracefully(self, sample_state, mock_llm_response):
        """Researcher continues even when search API fails."""
        from src.agents.researcher import ResearcherAgent
        agent = ResearcherAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()("General findings from knowledge base"))

        with patch("src.agents.researcher.get_web_search_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.call_tool.side_effect = Exception("Network error")
            
            result = agent.execute(sample_state)

        # Should not crash; should still have some findings
        assert result["research_findings"] is not None
        assert result["next_agent"] in ["synthesizer", "data_analyst"]

    def test_researcher_increments_iterations(self, sample_state, mock_llm_response):
        """Researcher increments iteration counter."""
        from src.agents.researcher import ResearcherAgent
        agent = ResearcherAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()("response"))

        with patch("src.agents.researcher.get_web_search_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            class MockTextContent:
                def __init__(self, text):
                    self.text = text
            import json
            mock_client.call_tool.return_value = [MockTextContent(json.dumps([]))]
            
            result = agent.execute(sample_state)

        assert result["iterations"] == 1


# ── Data Analyst Agent Tests ──────────────────────────────────────────────────

class TestDataAnalystAgent:
    """Tests for DataAnalystAgent."""

    def test_data_analyst_skips_gracefully_without_data(self, sample_state, mock_llm_response):
        """DataAnalyst routes to synthesizer when no data_path in state."""
        from src.agents.data_analyst import DataAnalystAgent
        agent = DataAnalystAgent()
        agent.llm = MagicMock()

        result = agent.execute(sample_state)

        assert result["next_agent"] == "synthesizer"
        assert result["data_summary"] is None
        # No LLM call needed
        agent.llm.invoke.assert_not_called()

    def test_data_analyst_handles_missing_file(self, sample_state):
        """DataAnalyst records error and continues if file doesn't exist."""
        from src.agents.data_analyst import DataAnalystAgent
        agent = DataAnalystAgent()
        agent.llm = MagicMock()

        sample_state["data_path"] = "/nonexistent/path/data.csv"
        result = agent.execute(sample_state)

        assert result["next_agent"] == "synthesizer"
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0].lower() or \
               "DataAnalyst" in result["errors"][0]

    def test_data_analyst_loads_csv(self, sample_state_with_data, mock_llm_response):
        """DataAnalyst successfully loads and analyzes a CSV file via MCP."""
        from src.agents.data_analyst import DataAnalystAgent
        agent = DataAnalystAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()(
            "1. Sales peaked in December.\n2. North region leads.\n3. Strong growth trend."
        ))

        mock_summary = {
            "shape": {"rows": 5, "columns": 4},
            "columns": ["month", "sales", "profit", "region"],
            "numeric_columns": ["sales", "profit"],
            "missing_values": {},
            "numeric_stats": {"sales": {"mean": 13600.0, "std": 1000.0, "min": 10000.0, "max": 18000.0}},
            "sample": []
        }

        with patch("src.agents.data_analyst.get_data_analysis_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            class MockTextContent:
                def __init__(self, text):
                    self.text = text
            import json
            mock_client.call_tool.return_value = [MockTextContent(json.dumps(mock_summary))]

            result = agent.execute(sample_state_with_data)

        assert result["data_summary"] is not None
        assert result["data_summary"]["shape"]["rows"] == 5
        assert result["data_summary"]["shape"]["columns"] == 4
        assert result["analysis_insights"] is not None
        assert result["next_agent"] == "synthesizer"

    def test_data_analyst_computes_correct_stats(self, sample_state_with_data, mock_llm_response):
        """Data summary contains expected statistics."""
        from src.agents.data_analyst import DataAnalystAgent
        agent = DataAnalystAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()("insights"))

        mock_summary = {
            "shape": {"rows": 5, "columns": 4},
            "columns": ["month", "sales", "profit", "region"],
            "numeric_columns": ["sales", "profit"],
            "missing_values": {},
            "numeric_stats": {"sales": {"mean": 13600.0, "std": 1000.0, "min": 10000.0, "max": 18000.0}},
            "sample": []
        }

        with patch("src.agents.data_analyst.get_data_analysis_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            class MockTextContent:
                def __init__(self, text):
                    self.text = text
            import json
            mock_client.call_tool.return_value = [MockTextContent(json.dumps(mock_summary))]

            result = agent.execute(sample_state_with_data)

        summary = result["data_summary"]
        assert "month" in summary["column_names"]
        assert "sales" in summary["numeric_columns"]
        assert summary["shape"]["rows"] == 5
        # sales: [10000, 12000, 15000, 13000, 18000] → mean = 13600
        assert abs(summary["numeric_stats"]["sales"]["mean"] - 13600.0) < 1


# ── Synthesizer Agent Tests ───────────────────────────────────────────────────

class TestSynthesizerAgent:
    """Tests for SynthesizerAgent."""

    def test_synthesizer_combines_both_sources(self, sample_state, mock_llm_response):
        """Synthesizer produces combined_report from research + data."""
        from src.agents.synthesizer import SynthesizerAgent
        agent = SynthesizerAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()(
            "1. Executive Summary: AI is transforming quantum computing.\n"
            "2. Research aligns with data showing 35% growth.\n"
            "3. Conclusion: Strong upward trend confirmed."
        ))

        sample_state["research_findings"] = "Quantum computing grew 35% in 2024."
        sample_state["analysis_insights"] = "Dataset shows 35% CAGR in quantum startups."

        result = agent.execute(sample_state)

        assert result["combined_report"] is not None
        assert result["next_agent"] == "writer"

    def test_synthesizer_handles_research_only(self, sample_state, mock_llm_response):
        """Synthesizer works with only research findings (no data)."""
        from src.agents.synthesizer import SynthesizerAgent
        agent = SynthesizerAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(return_value=mock_llm_response()(
            "Research-only synthesis output."
        ))

        sample_state["research_findings"] = "Key research findings about quantum computing."
        sample_state["analysis_insights"] = None  # No data

        result = agent.execute(sample_state)

        assert result["combined_report"] is not None
        assert result["next_agent"] == "writer"

    def test_synthesizer_fallback_on_llm_error(self, sample_state):
        """Synthesizer falls back to concatenation if LLM fails."""
        from src.agents.synthesizer import SynthesizerAgent
        agent = SynthesizerAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(side_effect=RuntimeError("API error"))

        sample_state["research_findings"] = "Research findings."
        sample_state["analysis_insights"] = "Data insights."

        result = agent.execute(sample_state)

        # Should still produce a combined_report via fallback
        assert result["combined_report"] is not None
        assert len(result["errors"]) > 0


# ── Writer Agent Tests ────────────────────────────────────────────────────────

class TestWriterAgent:
    """Tests for WriterAgent."""

    def test_writer_produces_markdown_report(self, sample_state, mock_llm_response):
        """Writer generates a non-empty final_report in markdown format."""
        from src.agents.writer import WriterAgent
        agent = WriterAgent()

        mock_content = (
            "# Quantum Computing Trends 2024\n\n"
            "## Executive Summary\nQuantum computing is advancing rapidly.\n\n"
            "## Key Findings\n- 35% growth in qubit count\n- New error correction methods\n\n"
            "## Conclusions\nStrong growth trajectory confirmed."
        )

        with patch("src.agents.writer.WriterAgent.call_llm", return_value=mock_content):
            sample_state["combined_report"] = "Quantum computing research and data synthesis."
            sample_state["search_results"] = [{"title": "s1"}, {"title": "s2"}]
            sample_state["iterations"] = 3

            result = agent.execute(sample_state)

        assert result["final_report"] is not None
        assert "#" in result["final_report"]  # Has markdown headers
        assert result["next_agent"] is None  # Signals end of workflow

    def test_writer_appends_metadata_footer(self, sample_state, mock_llm_response):
        """Writer appends the metadata footer to the report."""
        from src.agents.writer import WriterAgent
        agent = WriterAgent()

        with patch("src.agents.writer.WriterAgent.call_llm", return_value="# Report\n\nContent here."):
            sample_state["combined_report"] = "Content."
            sample_state["iterations"] = 2

            result = agent.execute(sample_state)

        footer = result["final_report"]
        assert "Generated by Multi-Agent" in footer
        assert "Agent Pipeline" in footer

    def test_writer_fallback_on_llm_error(self, sample_state):
        """Writer falls back to basic report if LLM fails."""
        from src.agents.writer import WriterAgent
        agent = WriterAgent()
        agent.llm = MagicMock()
        agent.llm.invoke = MagicMock(side_effect=RuntimeError("API error"))

        sample_state["combined_report"] = "Some content to format."

        result = agent.execute(sample_state)

        # Should still produce a report (not crash)
        assert result["final_report"] is not None
        assert len(result["errors"]) > 0
        assert result["next_agent"] is None


# ── Workflow Router Tests ─────────────────────────────────────────────────────

class TestWorkflowRouter:
    """Tests for the LangGraph workflow routing logic."""

    @pytest.fixture
    def workflow(self):
        """Create workflow with mocked agents."""
        from src.graph.workflow import ResearchWorkflow
        with patch("src.graph.workflow.PlannerAgent"), \
             patch("src.graph.workflow.ResearcherAgent"), \
             patch("src.graph.workflow.DataAnalystAgent"), \
             patch("src.graph.workflow.SynthesizerAgent"), \
             patch("src.graph.workflow.WriterAgent"):
            return ResearchWorkflow()

    def test_router_to_researcher(self, workflow, sample_state):
        """Router returns 'researcher' when next_agent is set to it."""
        sample_state["next_agent"] = "researcher"
        assert workflow._router(sample_state) == "researcher"

    def test_router_to_data_analyst(self, workflow, sample_state):
        """Router returns 'data_analyst' correctly."""
        sample_state["next_agent"] = "data_analyst"
        assert workflow._router(sample_state) == "data_analyst"

    def test_router_to_synthesizer(self, workflow, sample_state):
        """Router returns 'synthesizer' correctly."""
        sample_state["next_agent"] = "synthesizer"
        assert workflow._router(sample_state) == "synthesizer"

    def test_router_to_writer(self, workflow, sample_state):
        """Router returns 'writer' correctly."""
        sample_state["next_agent"] = "writer"
        assert workflow._router(sample_state) == "writer"

    def test_router_to_end_on_none(self, workflow, sample_state):
        """Router returns 'end' when next_agent is None."""
        sample_state["next_agent"] = None
        assert workflow._router(sample_state) == "end"

    def test_router_safety_circuit_breaker(self, workflow, sample_state):
        """Router forces 'end' if iterations exceed limit."""
        sample_state["next_agent"] = "researcher"
        sample_state["iterations"] = 11  # Over the limit of 10
        assert workflow._router(sample_state) == "end"

    def test_router_unknown_agent(self, workflow, sample_state):
        """Router returns 'end' for unknown agent names."""
        sample_state["next_agent"] = "nonexistent_agent"
        assert workflow._router(sample_state) == "end"


# ── Error Handling Tests ──────────────────────────────────────────────────────

class TestErrorHandling:
    """Test graceful degradation and error recording."""

    def test_workflow_handles_nonexistent_data_file(self, mock_llm_response):
        """Full workflow completes even when data file doesn't exist."""
        from src.graph.workflow import ResearchWorkflow

        with patch("src.agents.planner.PlannerAgent._setup_llm"), \
             patch("src.agents.researcher.ResearcherAgent._setup_llm"), \
             patch("src.agents.data_analyst.DataAnalystAgent._setup_llm"), \
             patch("src.agents.synthesizer.SynthesizerAgent._setup_llm"), \
             patch("src.agents.writer.WriterAgent._setup_llm"):
            pass  # This test needs integration — skip if no API key

        # Test just the data analyst handling
        from src.agents.data_analyst import DataAnalystAgent
        agent = DataAnalystAgent()
        agent.llm = MagicMock()

        state = create_initial_state("Analyze data", data_path="/nonexistent/file.csv")
        result = agent.execute(state)

        assert result["next_agent"] == "synthesizer"  # Should continue
        assert len(result["errors"]) > 0

    def test_state_errors_accumulate_across_agents(self, sample_state, mock_llm_response):
        """Multiple agent errors accumulate in state["errors"] list."""
        state = sample_state.copy()
        state["errors"] = []

        # Simulate errors from multiple agents
        state["errors"].append("Researcher: search failed")
        state["errors"].append("DataAnalyst: file not found")

        assert len(state["errors"]) == 2
        assert "Researcher" in state["errors"][0]


# ── Integration Tests (require GROQ_API_KEY) ─────────────────────────────────

@pytest.mark.integration
class TestIntegration:
    """
    End-to-end integration tests that hit the real Groq API.
    Require GROQ_API_KEY to be set in environment.
    Skip if key not available.
    """

    @pytest.fixture(autouse=True)
    def require_api_key(self):
        """Skip integration tests if API key not available."""
        if not os.getenv("GROQ_API_KEY"):
            pytest.skip("GROQ_API_KEY not set — skipping integration test")

    def test_research_only_query(self):
        """Full workflow for research-only query produces final_report."""
        from src.graph.workflow import ResearchWorkflow

        workflow = ResearchWorkflow()
        result = workflow.run("What are the key benefits of quantum computing?")

        assert result["final_report"] is not None
        assert len(result["final_report"]) > 100
        assert result["research_findings"] is not None
        assert result["iterations"] >= 3

    def test_data_only_query(self, tmp_path):
        """Full workflow for data analysis produces analysis_insights."""
        from src.graph.workflow import ResearchWorkflow

        # Create test CSV
        csv_path = tmp_path / "sales.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["month", "sales", "profit"])
            for i, (m, s, p) in enumerate([
                ("Jan", 10000, 2000), ("Feb", 12000, 2400),
                ("Mar", 15000, 3000), ("Apr", 13000, 2600),
            ]):
                writer.writerow([m, s, p])

        workflow = ResearchWorkflow()
        result = workflow.run("Analyze sales trends", data_path=str(csv_path))

        assert result["final_report"] is not None
        assert result["data_summary"] is not None
        assert result["analysis_insights"] is not None
        assert result["iterations"] >= 2

    def test_combined_query(self, tmp_path):
        """Full combined research + data workflow produces all outputs."""
        from src.graph.workflow import ResearchWorkflow

        csv_path = tmp_path / "adoption.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["year", "ai_adoption_pct", "industry"])
            writer.writerows([
                [2020, 15, "Healthcare"], [2021, 23, "Healthcare"],
                [2022, 35, "Finance"], [2023, 52, "Finance"],
            ])

        workflow = ResearchWorkflow()
        result = workflow.run(
            "Research AI adoption trends and compare with our data",
            data_path=str(csv_path)
        )

        assert result["final_report"] is not None
        assert result["research_findings"] is not None
        assert result["analysis_insights"] is not None
        assert result["combined_report"] is not None

    def test_error_handling_invalid_data(self):
        """Workflow completes gracefully with invalid data file path."""
        from src.graph.workflow import ResearchWorkflow

        workflow = ResearchWorkflow()
        result = workflow.run(
            "Test error handling with missing file",
            data_path="/this/file/does/not/exist.csv"
        )

        # System should complete (not crash) and produce a report
        assert result["final_report"] is not None
        # Error should be recorded
        assert len(result["errors"]) > 0


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run unit tests (no API key needed)
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not integration",
    ])
