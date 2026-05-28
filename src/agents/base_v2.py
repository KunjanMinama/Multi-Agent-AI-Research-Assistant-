"""
BaseAgent v2 - Production-Grade Abstract Base Class
====================================================

Uses Groq API (free, fast) as the LLM backend.
Groq runs open-source models (Llama 3, Mixtral) at incredible speed.

WHY GROQ OVER OLLAMA?
- No local GPU needed — works on any machine
- 500+ tokens/sec (10x faster than typical Ollama setup)
- Free tier: 14,400 requests/day
- Same open-source models (Llama 3.1 8B, Mixtral 8x7B)

PATTERN:
- All agents inherit from this class
- They MUST implement: get_system_prompt(), execute()
- They GET for free: call_llm(), retry logic, logging, stats
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from loguru import logger
from dotenv import load_dotenv
load_dotenv(override=True)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system.

    Design Decisions:
    -----------------
    1. ABC enforces contract: every agent MUST implement execute() and get_system_prompt()
    2. call_llm() is shared — no code duplication across agents
    3. Retry logic lives here so agents don't need to handle it
    4. Statistics tracking for monitoring & debugging

    Usage:
    ------
    class MyAgent(BaseAgent):
        def get_system_prompt(self) -> str:
            return "You are an expert at..."

        def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
            result = self.call_llm("Do something with " + state["query"])
            state["my_result"] = result
            return state
    """

    def __init__(
        self,
        name: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_retries: int = 3,
    ):
        """
        Initialize the agent with Groq LLM connection.

        Args:
            name: Human-readable agent name (e.g., "Researcher")
            model: Groq model ID. Options:
                   - "llama3-8b-8192"        → Fast, good quality
                   - "llama3-70b-8192"       → Slower, higher quality
                   - "mixtral-8x7b-32768"    → Best for long contexts
                   - "gemma2-9b-it"          → Google's model
            temperature: Creativity level (0.0=deterministic, 1.0=creative)
            max_retries: Number of retry attempts on LLM failure
        """
        self.name = name
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries

        # Performance tracking
        self.call_count = 0
        self.total_time = 0.0
        self.error_count = 0

        # Setup LLM connection
        self.llm = self._setup_llm()

        logger.info(f"✅ {self.name} initialized | model={self.model} | temp={self.temperature}")

    def _setup_llm(self):
        """
        Configure the Groq LLM client.

        Why Groq? Free, fast, and supports Llama/Mixtral (open-source models).
        The API is compatible with OpenAI's format, making it easy to swap.

        Returns:
            Configured ChatGroq instance
        """
        from langchain_groq import ChatGroq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set — LLM calls will fail!")

        return ChatGroq(
            model=self.model,
            temperature=self.temperature,
            groq_api_key=api_key,
        )

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Return the system-level instructions for this agent.

        Each agent has a different role/persona:
        - PlannerAgent: "You are an expert planner..."
        - ResearcherAgent: "You are an expert researcher..."

        This method is @abstractmethod, meaning child classes MUST implement it.
        """
        pass

    @abstractmethod
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's core task.

        This is the main method every agent implements. The pattern is:
        1. Read inputs from state
        2. Do work (LLM calls, API calls, data processing)
        3. Write results back to state
        4. Set state["next_agent"] to route the workflow
        5. Return updated state

        Args:
            state: Shared state dict (AgentState TypedDict)

        Returns:
            Updated state with agent's contributions added
        """
        pass

    def call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Call the LLM with automatic retry logic.

        This centralizes LLM communication so all agents benefit from:
        - Retry on failure (exponential backoff)
        - Performance tracking
        - Consistent error handling

        Args:
            prompt: The user message / task description
            system_prompt: Override system instructions (uses get_system_prompt() if None)

        Returns:
            LLM response as a string

        Raises:
            RuntimeError: If all retries are exhausted
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        sys_prompt = system_prompt or self.get_system_prompt()
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=prompt),
        ]

        # Retry loop with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()
            try:
                logger.debug(f"[{self.name}] LLM call attempt {attempt}/{self.max_retries}")

                response = self.llm.invoke(messages)
                content = response.content

                # Track successful call
                elapsed = time.time() - start_time
                self.call_count += 1
                self.total_time += elapsed

                logger.debug(f"[{self.name}] LLM responded in {elapsed:.2f}s | {len(content)} chars")
                return content

            except Exception as e:
                self.error_count += 1
                elapsed = time.time() - start_time

                # Check for rate limit or 429
                err_msg = str(e).lower()
                is_rate_limit = "rate_limit" in err_msg or "429" in err_msg or "rate limit" in err_msg

                if is_rate_limit:
                    fallback_model = None
                    if self.model == "llama-3.3-70b-versatile":
                        fallback_model = "llama-3.1-8b-instant"

                    if fallback_model:
                        logger.warning(
                            f"[{self.name}] ⚠️ Groq 429 Rate Limit hit for '{self.model}'. "
                            f"Automatically falling back to '{fallback_model}'..."
                        )
                        self.model = fallback_model
                        self.llm = self._setup_llm()
                        time.sleep(1)
                        # Re-instantiate LLM messages references
                        messages = [
                            SystemMessage(content=sys_prompt),
                            HumanMessage(content=prompt),
                        ]
                        continue

                if attempt < self.max_retries:
                    wait = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    logger.warning(
                        f"[{self.name}] LLM call failed (attempt {attempt}): {e} "
                        f"| Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"[{self.name}] All {self.max_retries} retries exhausted: {e}")
                    raise RuntimeError(f"{self.name} LLM call failed after {self.max_retries} retries: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Return performance statistics for monitoring.

        Useful for:
        - Identifying slow agents
        - Tracking error rates
        - Cost estimation (calls × avg_tokens)
        """
        avg_time = self.total_time / max(self.call_count, 1)
        return {
            "agent": self.name,
            "model": self.model,
            "llm_calls": self.call_count,
            "total_time_sec": round(self.total_time, 2),
            "avg_time_sec": round(avg_time, 2),
            "errors": self.error_count,
        }
