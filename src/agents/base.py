from abc import ABC, abstractmethod
from typing import Dict, Any
import os
from datetime import datetime

# We'll import these when we install them
# from langchain_community.chat_models import ChatOllama
# from langchain_core.messages import HumanMessage, SystemMessage


class BaseAgent(ABC):
    """
    Abstract Base Class for all agents.
    
    ABC = Abstract Base Class (from Python's abc module)
    Why ABC? Forces child classes to implement required methods.
    
    If a child class doesn't implement execute(), Python will error!
    This ensures all agents follow the same pattern.
    """
    
    def __init__(
        self,
        name: str,
        model: str = "llama3.1:8b",
        temperature: float = 0.7
    ):
        """
        Initialize the agent.
        
        Args:
            name: Agent name (e.g., "Planner", "Researcher")
            model: LLM model to use (default: Llama 3.1 8B)
            temperature: How creative (0=deterministic, 1=creative)
        
        TEMPERATURE EXPLAINED:
        ---------------------
        - 0.0 = Always gives same answer (good for math, planning)
        - 0.5 = Balanced (good default)
        - 1.0 = Very creative (good for writing, brainstorming)
        """
        self.name = name
        self.model = model
        self.temperature = temperature
        
        # Initialize LLM connection
        self.llm = self._setup_llm()
        
        # Statistics tracking
        self.call_count = 0
        self.total_time = 0.0
        self.error_count = 0
        
        print(f"✅ {self.name} agent initialized with {self.model}")
    
    def _setup_llm(self):
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        from dotenv import load_dotenv
        load_dotenv(override=True)

        llm = HuggingFaceEndpoint(
        repo_id="meta-llama/Llama-3.1-8B-Instruct",
        task="chat-completion",
        max_new_tokens=256,
        huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_TOKEN")
    )
        model = ChatHuggingFace(llm=llm)
    # Pass llm to ChatHuggingFace
        return model
      
        return None  # Placeholder for now
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Return the system prompt for this agent.
        
        @abstractmethod EXPLAINED:
        --------------------------
        This decorator means: "Child classes MUST implement this method"
        
        Why? Each agent needs different instructions:
        - Planner: "You are a planning expert..."
        - Researcher: "You are a research expert..."
        - etc.
        
        If you create a child class and forget to add get_system_prompt(),
        Python will raise an error. This prevents bugs!
        
        EXAMPLE USAGE IN CHILD:
        -----------------------
        class PlannerAgent(BaseAgent):
            def get_system_prompt(self):
                return "You are an expert planner. Create detailed plans..."
        """
        pass
    
    @abstractmethod
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main task.
        
        This is the CORE method every agent must implement.
        
        Args:
            state: The shared state (our whiteboard from Step 1!)
        
        Returns:
            Updated state with this agent's contributions
        
        WORKFLOW:
        ---------
        1. Agent receives state
        2. Reads what it needs from state (query, plan, etc.)
        3. Does its work (call LLM, search web, analyze data)
        4. Updates state with results
        5. Returns updated state
        
        EXAMPLE:
        --------
        def execute(self, state):
            query = state["query"]  # Read from state
            result = self.do_work(query)  # Do work
            state["my_result"] = result  # Write to state
            return state  # Return updated state
        """
        pass
    
    def call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """
        Call the LLM with a prompt.
        
        This is a HELPER METHOD that all child agents can use.
        
        Args:
            prompt: The user message/question
            system_prompt: Optional system instructions (uses get_system_prompt() if not provided)
        
        Returns:
            LLM's response as string
        
        HOW THIS WORKS:
        ---------------
        1. Prepare messages (system + user)
        2. Call Ollama API
        3. Get response
        4. Track statistics
        5. Handle errors
        
        EXAMPLE USAGE IN CHILD:
        -----------------------
        class PlannerAgent(BaseAgent):
            def execute(self, state):
                query = state["query"]
                plan = self.call_llm(f"Create a plan for: {query}")
                state["plan"] = plan
                return state
        """
        
        # For now, return a placeholder
        # We'll implement real LLM calling in Step 3
        
        print(f"[{self.name}] Would call LLM with prompt: {prompt[:50]}...")
        
        self.call_count += 1
        
        return f"[Placeholder response from {self.name}]"
    
    def log(self, message: str, level: str = "INFO"):
        """
        Simple logging method.
        
        Later we'll use proper logging library (loguru),
        but this works for now.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.name}] {level}: {message}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Return statistics about this agent's execution.
        
        Useful for:
        - Monitoring performance
        - Debugging
        - Cost tracking
        - Optimization
        """
        return {
            "agent": self.name,
            "calls": self.call_count,
            "total_time": self.total_time,
            "errors": self.error_count,
            "avg_time": self.total_time / max(self.call_count, 1)
        }


# ============= TESTING =============

# Let's create a SIMPLE test agent to verify our base class works

class TestAgent(BaseAgent):
    """
    A simple test agent to verify BaseAgent works.
    
    This implements the required abstract methods.
    """
    
    def get_system_prompt(self) -> str:
        return "You are a test agent."
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Executing test agent")
        
        query = state.get("query", "")
        
        # Simulate calling LLM
        response = self.call_llm(f"Process: {query}")
        
        # Update state
        state["test_result"] = response
        state["iterations"] = state.get("iterations", 0) + 1
        
        self.log("Test execution complete")
        
        return state


# Test if it works
if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING BASE AGENT")
    print("="*60 + "\n")
    
    # Create test agent
    agent = TestAgent(name="TestAgent", model="llama3.1:8b")
    
    # Create test state
    test_state = {
        "query": "Test query",
        "iterations": 0
    }
    
    print("\nInitial state:")
    print(f"  Query: {test_state['query']}")
    print(f"  Iterations: {test_state['iterations']}")
    
    # Execute agent
    print("\nExecuting agent...")
    result_state = agent.execute(test_state)
    
    print("\nFinal state:")
    print(f"  Query: {result_state['query']}")
    print(f"  Test Result: {result_state['test_result']}")
    print(f"  Iterations: {result_state['iterations']}")
    
    # Show stats
    print("\nAgent Statistics:")
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Base Agent works correctly!")