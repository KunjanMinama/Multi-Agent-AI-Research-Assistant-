"""
Researcher Agent — Component 1
================================
Performs multi-query web research using DuckDuckGo and synthesizes findings.

DESIGN PHILOSOPHY:
- DuckDuckGo search: no API key needed, privacy-friendly, free
- Multiple search queries: each from a different angle for better coverage
- LLM synthesis: raw results → coherent, cited summary
- Graceful degradation: if search fails, LLM still generates a general response

FLOW:
  query → generate 3-5 sub-queries → search each → collect results
       → LLM synthesis → store findings → set next_agent → return state
"""

from typing import Dict, Any, List
import os
import httpx

from loguru import logger

# Top-level import so tests can patch 'src.agents.researcher.DDGS'
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None  # type: ignore[assignment]

SEARCH_VERSION = "tavily-v3"  # bump this to force cache-bust


from .base_v2 import BaseAgent


class ResearcherAgent(BaseAgent):
    """
    Conducts web research using DuckDuckGo and synthesizes findings via LLM.

    Key design decisions:
    - Multiple search queries per topic: covers different angles
    - Results deduplicated by URL to avoid repetition
    - LLM synthesis prompt is carefully structured for citation quality
    - Falls back to LLM-only response if all searches fail
    """

    def __init__(self):
        super().__init__(
            name="Researcher",
            model="llama-3.3-70b-versatile",
            temperature=0.5,  # Balanced: factual but not robotic
        )

    def get_system_prompt(self) -> str:
        return """You are an expert research analyst with deep knowledge across all domains.

Your role:
- Synthesize information from multiple web sources
- Identify key facts, trends, and insights
- Present findings in a clear, well-structured format
- Always cite sources by title and URL
- Flag conflicts, uncertainties, or gaps in available information

Quality standards:
- Be factual and evidence-based
- Prioritize recent and authoritative sources
- Distinguish between facts and opinions
- Note source credibility where relevant"""

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform web research and synthesize findings.

        Steps:
        1. Generate multiple search queries from the main query
        2. Execute DuckDuckGo searches for each sub-query
        3. Collect and deduplicate results
        4. Use LLM to synthesize findings into a coherent report
        5. Update state and set routing

        Args:
            state: Current workflow state

        Returns:
            State updated with search_results, research_findings, next_agent
        """
        logger.info(f"[Researcher] Starting research for: '{state['query'][:60]}'")

        query = state["query"]
        data_path = state.get("data_path")

        # ── Step 1: Generate diverse search queries ──────────────────────────
        search_queries = self._generate_search_queries(query)
        logger.info(f"[Researcher] Generated {len(search_queries)} search queries")

        # ── Step 2: Execute searches ──────────────────────────────────────────
        all_results = []
        seen_urls = set()
        import time as _time
        import random

        for i, sq in enumerate(search_queries, 1):
            # Add small delay between queries (less needed with Tavily API)
            if i > 1:
                _time.sleep(1)

            logger.info(f"[Researcher] Searching ({i}/{len(search_queries)}): '{sq}'")
            results = self._search(sq, max_results=5)

            # Deduplicate by URL
            for r in results:
                if isinstance(r, dict):
                    url = r.get("href", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)

        logger.info(f"[Researcher] Collected {len(all_results)} unique results")

        # Store raw results in state
        state["search_results"] = all_results[:30]  # Cap at 30 to keep state manageable

        # ── Step 3: Synthesize with LLM ──────────────────────────────────────
        if all_results:
            formatted = self._format_results_for_llm(all_results[:20])  # Top 20 for context
        else:
            # No results — inform LLM so it can still provide general knowledge
            formatted = "No web search results were available. Use your knowledge base."
            logger.warning("[Researcher] No search results — using LLM knowledge only")

        synthesis_prompt = f"""Based on these search results, synthesize findings for: {query}

Search Results:
{formatted}

Provide a comprehensive research synthesis with:
1. Key findings (3-5 main points with specific details)
2. Supporting evidence from sources (cite titles and URLs)
3. Any conflicts or uncertainties between sources
4. Notable trends or patterns
5. Brief conclusion

Format your response clearly with numbered sections.
Be factual and cite sources using [Title](URL) format."""

        try:
            synthesis = self.call_llm(synthesis_prompt)
            logger.info(f"[Researcher] Synthesis complete ({len(synthesis)} chars)")
        except Exception as e:
            logger.error(f"[Researcher] Synthesis LLM failed: {e}")
            state["errors"].append(f"Researcher synthesis error: {str(e)}")
            synthesis = f"Research synthesis failed. Raw search found {len(all_results)} results about '{query}'."

        # ── Step 4: Update state ──────────────────────────────────────────────
        state["research_findings"] = synthesis
        state["iterations"] += 1

        # Routing: if we also have data to analyze, go to data_analyst; else synthesizer
        if data_path:
            state["next_agent"] = "data_analyst"
            logger.info("[Researcher] → routing to data_analyst (data file present)")
        else:
            state["next_agent"] = "synthesizer"
            logger.info("[Researcher] → routing to synthesizer (no data file)")

        return state

    # ── Private Helper Methods ────────────────────────────────────────────────

    def _generate_search_queries(self, query: str) -> List[str]:
        """
        Generate 3 diverse search queries from the main query.

        Using an LLM here gives much better sub-queries than simple string manipulation.
        Falls back to rule-based queries if LLM fails.
        """
        prompt = f"""Generate exactly 3 diverse search queries to research: "{query}"

Rules:
- Each query from a DIFFERENT angle (overview, recent news, expert opinions)
- Keep each query under 8 words
- Format: Return ONLY the queries, one per line, no numbers or bullets

Example output:
AI trends in healthcare 2024
latest artificial intelligence medical breakthroughs
experts opinion AI replacing doctors"""

        try:
            response = self.call_llm(prompt)
            # Parse queries — one per non-empty line
            raw_queries = [line.strip() for line in response.strip().split("\n") if line.strip()]
            # Filter out any accidental headers/labels
            queries = [q for q in raw_queries if not q.endswith(":") and len(q) > 3][:3]

            if len(queries) >= 2:
                logger.debug(f"[Researcher] Sub-queries: {queries}")
                return queries
        except Exception as e:
            logger.warning(f"[Researcher] Sub-query generation failed: {e} — using fallbacks")

        # Rule-based fallback queries
        return [
            query,
            f"{query} latest news",
            f"{query} trends analysis",
        ]

    def _search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Execute a web search using Tavily, SerpAPI, or DuckDuckGo.

        Checks environment variables for API keys first for production-grade reliability,
        falling back to DuckDuckGo search if no key is configured.
        """
        # 1. Try Tavily Search API if TAVILY_API_KEY is configured
        tavily_key = os.getenv("TAVILY_API_KEY")
        logger.info(f"[Researcher] SEARCH_VERSION={SEARCH_VERSION} | Tavily key present={bool(tavily_key)}")
        if tavily_key:
            logger.info(f"[Researcher] Tavily key found, querying for: '{query}'")
            try:
                # Use Authorization header (Tavily v2 format)
                resp = httpx.post(
                    "https://api.tavily.com/search",
                    headers={"Authorization": f"Bearer {tavily_key}"},
                    json={
                        "query": query,
                        "search_depth": "basic",
                        "max_results": max_results
                    },
                    timeout=15
                )
                logger.info(f"[Researcher] Tavily HTTP status: {resp.status_code}")
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    # Map Tavily format to standard format (title, href, body)
                    mapped = []
                    for r in results:
                        mapped.append({
                            "title": r.get("title", ""),
                            "href": r.get("url", ""),
                            "body": r.get("content", "")
                        })
                    logger.info(f"[Researcher] Tavily search succeeded with {len(mapped)} results")
                    return mapped
                else:
                    logger.warning(f"[Researcher] Tavily failed ({resp.status_code}): {resp.text[:300]}")
            except Exception as e:
                logger.error(f"[Researcher] Tavily exception: {type(e).__name__}: {e}")

        # 2. Try SerpAPI if SERPAPI_API_KEY is configured
        serpapi_key = os.getenv("SERPAPI_API_KEY")
        if serpapi_key:
            try:
                logger.info(f"[Researcher] Querying SerpAPI for: '{query}'")
                resp = httpx.get(
                    "https://serpapi.com/search.json",
                    params={
                        "q": query,
                        "api_key": serpapi_key,
                        "engine": "google",
                        "num": max_results
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    organic = resp.json().get("organic_results", [])
                    mapped = []
                    for r in organic:
                        mapped.append({
                            "title": r.get("title", ""),
                            "href": r.get("link", ""),
                            "body": r.get("snippet", "")
                        })
                    logger.info(f"[Researcher] SerpAPI search succeeded with {len(mapped)} results")
                    return mapped
                else:
                    logger.warning(f"[Researcher] SerpAPI returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"[Researcher] SerpAPI search failed: {e}")

        # 3. Fall back to free DuckDuckGo search
        if DDGS is None:
            logger.warning("[Researcher] duckduckgo_search not installed — skipping search")
            return []

        import time as _time
        import random

        logger.info(f"[Researcher] Using DuckDuckGo Search (no API key configured)")
        for attempt in range(1, 4):  # 3 attempts
            try:
                with DDGS() as searcher:
                    results = searcher.text(query, max_results=max_results)
                    results_list = list(results) if results else []
                logger.info(f"[Researcher] DDG Search '{query}' → {len(results_list)} results")
                return results_list
            except Exception as e:
                wait = random.uniform(5, 10) * attempt
                logger.warning(
                    f"[Researcher] DDG Search failed (attempt {attempt}/3): {e}"
                    f" | retrying in {wait:.0f}s..."
                )
                if attempt < 3:
                    _time.sleep(wait)

        return []

    def _format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        """
        Format search results into clean text for LLM synthesis.

        Truncates long snippets to stay within context limits.
        Includes title, snippet, and URL for proper citation.
        """
        if not results:
            return "No results available."

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            body = r.get("body", "")[:300]  # Truncate to 300 chars per result
            url = r.get("href", "No URL")

            lines.append(f"[{i}] {title}")
            lines.append(f"    {body}")
            lines.append(f"    URL: {url}")
            lines.append("")

        return "\n".join(lines)


# ── Standalone Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")  # Allow running from project root

    from src.graph.state import create_initial_state

    print("\n" + "="*60)
    print("TESTING RESEARCHER AGENT")
    print("="*60)

    # Create agent and initial state
    agent = ResearcherAgent()
    state = create_initial_state(
        query="What are the latest trends in quantum computing?",
        data_path=None
    )

    print(f"\nQuery: {state['query']}")
    print("Running researcher...\n")

    result = agent.execute(state)

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"\nSearch Results Count: {len(result['search_results'])}")
    print(f"\nResearch Findings:\n{result['research_findings'][:500]}...")
    print(f"\nNext Agent: {result['next_agent']}")
    print(f"Iterations: {result['iterations']}")

    stats = agent.get_stats()
    print(f"\nAgent Stats: {stats}")
    print("\n[OK] Researcher Agent works!")
