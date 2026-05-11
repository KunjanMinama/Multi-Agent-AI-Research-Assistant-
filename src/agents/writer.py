"""
Writer Agent — Component 4
============================
Creates a polished, professional markdown report from the synthesized analysis.

DESIGN PHILOSOPHY:
- Final consumer of the workflow — quality matters most here
- Uses metadata from state (iterations, error count, source count)
- Temperature 0.5: balanced between structure and readability
- Enriches the combined_report rather than just reformatting it

FLOW:
  combined_report → LLM formatting → professional markdown → state["final_report"]
                 → set next_agent = None (end of workflow)
"""

from datetime import datetime
from typing import Dict, Any
from loguru import logger

from .base_v2 import BaseAgent


class WriterAgent(BaseAgent):
    """
    Creates the final professional markdown report.

    Key design decisions:
    - Adds metadata footer (timestamp, agent iterations, source count)
    - Uses strong markdown structure (H1, H2, H3, tables, bold)
    - Asks LLM to ENRICH content, not just reformat it
    - Falls back to structured concatenation if LLM fails
    """

    def __init__(self):
        super().__init__(
            name="Writer",
            model="llama-3.3-70b-versatile",
            temperature=0.5,  # Balanced: structured yet readable
        )

    def get_system_prompt(self) -> str:
        return """You are a professional technical writer who creates clear, compelling reports.

Your role:
- Transform analytical content into polished, professional documents
- Use clear markdown formatting (headers, bullets, bold emphasis)
- Create an engaging narrative that flows naturally
- Maintain factual accuracy — never fabricate or embellish facts
- Structure content for maximum scannability and comprehension

Formatting standards:
- Use # for title, ## for main sections, ### for subsections
- Bold (**text**) for key terms and important numbers
- Bullet lists for multiple related items
- Keep paragraphs concise (3-5 sentences max)
- Professional but accessible language (no unnecessary jargon)"""

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the final professional markdown report.

        Steps:
        1. Extract combined_report and metadata from state
        2. Use LLM to format and enrich into professional markdown
        3. Append metadata footer
        4. Set next_agent = None (workflow ends)

        Args:
            state: Current workflow state

        Returns:
            State updated with final_report, next_agent = None
        """
        logger.info("[Writer] Generating final report")

        query = state["query"]
        combined_report = state.get("combined_report") or ""
        research_findings = state.get("research_findings") or ""
        analysis_insights = state.get("analysis_insights") or ""
        iterations = state.get("iterations", 0)
        errors = state.get("errors", [])
        search_results = state.get("search_results", [])

        # Count sources for metadata
        source_count = len(search_results)
        has_data = bool(state.get("data_summary"))

        # Use combined_report if available, else fall back to what exists
        content_to_format = combined_report or research_findings or analysis_insights or \
                            "No content was generated."

        # ── Build writing prompt ──────────────────────────────────────────────
        writing_prompt = f"""Transform this analytical content into a professional markdown report.

Query: "{query}"

Content to format:
{content_to_format}

Create a well-structured report with these sections:
1. # [Descriptive Title based on the query]
2. ## Executive Summary (2-3 sentences capturing the key message)
3. ## Key Findings (3-5 bullet points with the most important discoveries)
4. ## Detailed Analysis (expand on findings with evidence and context)
5. ## Conclusions (what we can confidently conclude)
6. ## Recommendations (actionable next steps or implications)

Requirements:
- Use proper markdown (# ## ### for headers, **bold** for key terms)
- Include specific numbers and evidence from the content
- Make it scannable with clear bullet points
- Professional tone, clear language
- Do NOT add a metadata footer (it will be added automatically)
- Length: 400-700 words total"""

        try:
            formatted_report = self.call_llm(writing_prompt)
            logger.info(f"[Writer] Report generated ({len(formatted_report)} chars)")
        except Exception as e:
            logger.error(f"[Writer] LLM formatting failed: {e}")
            state["errors"].append(f"Writer LLM error: {str(e)}")
            # Fallback: basic structure
            formatted_report = self._create_fallback_report(query, content_to_format)

        # ── Append metadata footer ────────────────────────────────────────────
        metadata_footer = self._build_metadata_footer(
            query=query,
            iterations=iterations,
            source_count=source_count,
            has_data=has_data,
            error_count=len(errors),
        )

        final_report = formatted_report.strip() + "\n\n" + metadata_footer

        # ── Update state ──────────────────────────────────────────────────────
        state["final_report"] = final_report
        state["next_agent"] = None  # Signals end of workflow
        state["iterations"] += 1

        logger.info(f"[Writer] Final report ready ({len(final_report)} chars) → END")
        return state

    # ── Private Helper Methods ────────────────────────────────────────────────

    def _build_metadata_footer(
        self,
        query: str,
        iterations: int,
        source_count: int,
        has_data: bool,
        error_count: int,
    ) -> str:
        """
        Generate a professional metadata footer for the report.

        Includes generation timestamp, agent pipeline info, and quality note.
        This provides traceability for audit purposes.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sources_used = []
        if source_count > 0:
            sources_used.append(f"{source_count} web sources")
        if has_data:
            sources_used.append("uploaded data file")
        sources_str = " + ".join(sources_used) if sources_used else "LLM knowledge base"

        error_note = f" | ⚠️ {error_count} error(s) logged" if error_count > 0 else ""

        return (
            "---\n"
            "*🤖 Generated by Multi-Agent AI Research System*\n\n"
            f"| Field | Value |\n"
            f"|-------|-------|\n"
            f"| **Generated** | {timestamp} |\n"
            f"| **Query** | {query[:80]}{'...' if len(query) > 80 else ''} |\n"
            f"| **Agent Pipeline** | Planner → Researcher → Data Analyst → Synthesizer → Writer |\n"
            f"| **Sources Used** | {sources_str} |\n"
            f"| **Agent Iterations** | {iterations} |\n"
            f"| **Model** | Llama 3 8B (via Groq){error_note} |\n"
        )

    def _create_fallback_report(self, query: str, content: str) -> str:
        """
        Minimal markdown report when LLM formatting fails.
        Preserves content with basic structure.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        return f"""# Analysis Report: {query}

*Generated: {timestamp}*

## Summary

This report addresses the query: **"{query}"**

## Findings

{content[:2000]}

## Notes

*Report was generated using fallback formatting due to an LLM error.*
"""


# ── Standalone Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")

    from src.graph.state import create_initial_state

    print("\n" + "="*60)
    print("TESTING WRITER AGENT")
    print("="*60)

    agent = WriterAgent()
    state = create_initial_state(query="AI trends in healthcare 2024")

    # Simulate previous agents' work
    state["combined_report"] = """
Executive Summary: AI is transforming healthcare significantly in 2024.

Research shows: 
- AI diagnostics accuracy reached 94% for radiology (Nature Medicine, 2024)
- 67% of hospitals now use AI-assisted triage
- Global AI healthcare market: $45B, growing at 37% CAGR

Data Analysis:
- Our dataset: 500 hospitals, 2020-2024
- Hospitals using AI showed 23% reduction in diagnostic errors
- Average implementation cost: $1.2M, ROI achieved in 18 months
- Strong correlation between AI adoption and patient satisfaction (r=0.68)

Key insight: Hospitals that combined AI diagnostics with staff training
outperformed AI-only adoption by 31%.
    """
    state["search_results"] = [{"title": "Source 1"}, {"title": "Source 2"}, {"title": "Source 3"}]
    state["data_summary"] = {"shape": {"rows": 500, "columns": 12}}
    state["iterations"] = 3

    result = agent.execute(state)

    print("\nFinal Report:")
    print("="*60)
    print(result["final_report"])
    print(f"\nNext Agent: {result['next_agent']}")
    print("\n✅ Writer Agent works!")
