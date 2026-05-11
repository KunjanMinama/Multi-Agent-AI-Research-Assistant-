"""
Fact Checker Agent — Component QA
=================================
Validates the synthesized report against raw research findings and data analysis insights.
"""

from typing import Dict, Any
from loguru import logger

from .base_v2 import BaseAgent

class FactCheckerAgent(BaseAgent):
    """
    Acts as a strict QA reviewer.
    It reads the combined report from the Synthesizer and checks for hallucinations.
    """

    def __init__(self):
        super().__init__(
            name="FactChecker",
            model="llama-3.3-70b-versatile",
            temperature=0.1,  # Very low temperature for strict QA
        )

    def get_system_prompt(self) -> str:
        return """You are a strict QA Fact-Checker for an enterprise research team.

Your job is to compare a Synthesized Report against the raw Source Material (Research Findings and Data Analysis Insights).
You must determine if the report contains any "hallucinations" (claims not supported by the sources) or logical errors.

OUTPUT FORMAT:
You must return exactly two lines:
Line 1: SCORE: <float between 0.0 and 1.0> (1.0 = perfect accuracy, 0.0 = completely fabricated)
Line 2: FEEDBACK: <a brief explanation of what is wrong, or "Looks good">
"""

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the report and set quality_score and needs_revision.
        """
        logger.info("[FactChecker] Starting QA review...")

        report = state.get("combined_report", "")
        if not report:
            logger.warning("[FactChecker] No report to check. Skipping.")
            state["quality_score"] = 0.0
            state["needs_revision"] = False
            state["next_agent"] = "writer"
            return state

        sources = f"""
        [RESEARCH FINDINGS]
        {state.get('research_findings', 'None')}

        [DATA ANALYSIS INSIGHTS]
        {state.get('analysis_insights', 'None')}
        """

        prompt = f"""Review this report against the sources:
        
SOURCES:
{sources}

SYNTHESIZED REPORT:
{report}

Is the report fully supported by the sources? Do not be overly pedantic about minor wording changes, but flag any fake statistics, wrong facts, or major unsupported claims.
Remember to output EXACTLY two lines: SCORE: <value> and FEEDBACK: <message>
"""

        try:
            response = self.call_llm(prompt)
            lines = response.strip().split("\n")
            score = 1.0
            feedback = "Looks good"
            
            for line in lines:
                if line.startswith("SCORE:"):
                    try:
                        score = float(line.replace("SCORE:", "").strip())
                    except ValueError:
                        score = 1.0
                elif line.startswith("FEEDBACK:"):
                    feedback = line.replace("FEEDBACK:", "").strip()

            state["quality_score"] = score
            logger.info(f"[FactChecker] Score: {score} | Feedback: {feedback}")

            if score < 0.7:
                logger.warning("[FactChecker] Quality score too low. Requesting revision.")
                state["needs_revision"] = True
                state["errors"].append(f"QA Failed (Score {score}): {feedback}")
                state["next_agent"] = "synthesizer" # Send back to synthesizer to rewrite
            else:
                state["needs_revision"] = False
                state["next_agent"] = "writer"

        except Exception as e:
            logger.error(f"[FactChecker] QA failed: {e}")
            state["errors"].append(f"FactChecker LLM Error: {e}")
            state["next_agent"] = "writer" # Fail gracefully and let writer finish

        state["iterations"] += 1
        return state
