"""
Synthesizer Agent — Component 3
=================================
Combines research findings and data analysis into unified, coherent insights.

DESIGN PHILOSOPHY:
- Works even if only ONE source is available (research-only or data-only)
- The "integration layer" — finds connections research + data
- Sets stage for the Writer by providing structured combined_report
- Temperature 0.6: needs some creativity to find non-obvious connections

FLOW:
  research_findings + analysis_insights → LLM synthesis
                                        → combined_report → route to writer
"""

from typing import Dict, Any
from loguru import logger

from .base_v2 import BaseAgent


class SynthesizerAgent(BaseAgent):
    """
    Integrates research findings and data analysis into a unified insight report.

    Key design decisions:
    - Handles all three scenarios gracefully:
      * Research only (no data)
      * Data only (no research)
      * Both research AND data
    - Finds non-obvious connections between research and data
    - Structures output for the Writer agent to format
    """

    def __init__(self):
        super().__init__(
            name="Synthesizer",
            model="llama-3.3-70b-versatile",
            temperature=0.6,  # Moderate creativity for synthesis
        )

    def get_system_prompt(self) -> str:
        return """You are an expert analytical synthesizer who integrates multiple information sources.

Your role:
- Combine research findings with data analysis into unified insights
- Identify connections, alignments, and contradictions between sources
- Extract the most important integrated conclusions
- Present a holistic view that is greater than the sum of its parts

Quality standards:
- Every claim should be traceable to at least one source (research or data)
- Highlight where research confirms data patterns (and vice versa)
- Be explicit when sources conflict or when evidence is weak
- Focus on insights that would not be obvious from either source alone
- Write for a professional audience who wants actionable conclusions"""

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize research findings and/or data analysis into a combined report.

        Handles all scenarios:
        - research_findings only → summarize and structure
        - analysis_insights only → structure and contextualize
        - both → find connections and create integrated view

        Args:
            state: Current workflow state

        Returns:
            State updated with combined_report, next_agent set to "writer"
        """
        logger.info("[Synthesizer] Starting synthesis")

        query = state["query"]
        research_findings = state.get("research_findings") or ""
        analysis_insights = state.get("analysis_insights") or ""

        # ── Determine what sources are available ──────────────────────────────
        has_research = bool(research_findings.strip())
        has_data = bool(analysis_insights.strip()) and \
                   analysis_insights != "No data file provided — analysis skipped."

        logger.info(
            f"[Synthesizer] Sources available: "
            f"research={has_research}, data={has_data}"
        )

        # ── Build synthesis prompt based on available sources ─────────────────
        synthesis_prompt = self._build_synthesis_prompt(
            query=query,
            research_findings=research_findings if has_research else None,
            analysis_insights=analysis_insights if has_data else None,
        )

        # ── Call LLM ──────────────────────────────────────────────────────────
        try:
            combined_report = self.call_llm(synthesis_prompt)
            logger.info(f"[Synthesizer] Synthesis complete ({len(combined_report)} chars)")
        except Exception as e:
            logger.error(f"[Synthesizer] LLM synthesis failed: {e}")
            state["errors"].append(f"Synthesizer error: {str(e)}")
            # Fallback: concatenate available sources
            combined_report = self._fallback_synthesis(
                query, research_findings, analysis_insights
            )

        # ── Update state ──────────────────────────────────────────────────────
        state["combined_report"] = combined_report
        state["next_agent"] = "writer"
        state["iterations"] += 1

        logger.info("[Synthesizer] Done → routing to writer")
        return state

    # ── Private Helper Methods ────────────────────────────────────────────────

    def _build_synthesis_prompt(
        self,
        query: str,
        research_findings: str,
        analysis_insights: str,
    ) -> str:
        """
        Build a tailored synthesis prompt based on available sources.

        Three modes:
        1. Both sources: Full integration synthesis
        2. Research only: Structure and enrich findings
        3. Data only: Contextualize and interpret data
        """
        has_research = research_findings is not None
        has_data = analysis_insights is not None

        if has_research and has_data:
            return f"""Query: {query}

Research Findings:
{research_findings}

Data Analysis:
{analysis_insights}

Synthesize these two sources into a cohesive integrated analysis:

1. Executive Summary (2-3 sentences capturing the complete picture)
2. How Research Aligns With or Contradicts the Data
   - Points of agreement (with specific evidence from each source)
   - Points of conflict or tension (and possible explanations)
3. Key Integrated Insights (insights only possible by combining both sources)
4. Main Conclusions (what we know with confidence)
5. Recommendations (actionable next steps based on the full analysis)

Be specific. Reference actual findings from both sources."""

        elif has_research:
            return f"""Query: {query}

Research Findings:
{research_findings}

Structure these research findings into a comprehensive synthesis:

1. Executive Summary (2-3 sentences)
2. Core Findings (most important discoveries, with evidence)
3. Supporting Evidence and Sources
4. Uncertainties or Knowledge Gaps
5. Conclusions and Implications

Note: No data file was analyzed — this synthesis is based entirely on research."""

        else:
            return f"""Query: {query}

Data Analysis Results:
{analysis_insights}

Contextualize this data analysis into meaningful insights:

1. Executive Summary (2-3 sentences)
2. Key Data Patterns (what the numbers tell us)
3. Statistical Significance (which findings are most reliable)
4. Business/Practical Implications
5. Recommendations Based on the Data

Note: No web research was conducted — this synthesis is based entirely on the provided data."""

    def _fallback_synthesis(
        self, query: str, research: str, data: str
    ) -> str:
        """
        Simple fallback when LLM synthesis fails.
        Concatenates available sources with clear section headers.
        """
        parts = [f"# Synthesis for: {query}\n"]

        if research:
            parts.append("## Research Findings\n")
            parts.append(research[:1000] + ("..." if len(research) > 1000 else ""))
            parts.append("\n")

        if data:
            parts.append("## Data Analysis\n")
            parts.append(data[:1000] + ("..." if len(data) > 1000 else ""))

        if not research and not data:
            parts.append("*No findings available to synthesize.*")

        return "\n".join(parts)


# ── Standalone Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")

    from src.graph.state import create_initial_state

    print("\n" + "="*60)
    print("TESTING SYNTHESIZER AGENT")
    print("="*60)

    agent = SynthesizerAgent()
    state = create_initial_state(query="AI adoption trends in enterprise")

    # Simulate previous agents' outputs
    state["research_findings"] = """
1. Key Findings: AI adoption in enterprises grew 35% in 2023.
   Major drivers: automation, cost reduction, competitive pressure.
2. Supporting Evidence: Gartner report (2024) shows 67% of Fortune 500
   companies have deployed at least one AI solution.
3. Uncertainties: ROI measurement remains inconsistent across industries.
4. Conclusion: AI adoption is mainstream but implementation quality varies widely.
    """

    state["analysis_insights"] = """
1. Dataset shows 120 enterprise clients over 2 years.
2. Average AI project spend: $2.3M with 18-month payback period.
3. Strong correlation between company size and AI ROI (r=0.72).
4. Technology sector leads with 89% adoption; manufacturing at 45%.
    """

    result = agent.execute(state)

    print(f"\nCombined Report:\n{result['combined_report'][:600]}...")
    print(f"\nNext Agent: {result['next_agent']}")
    print("\n✅ Synthesizer Agent works!")
