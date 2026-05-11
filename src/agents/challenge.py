from base import BaseAgent

class summarizer(BaseAgent):
    def __init__(self):

        super().__init__(
            name="str",
            model="llama-3.3-70b-versatile",
            temperature=0.5
        )

    def get_system_prompt(self) -> str:
        return """You are a professional summarizer.
 
Your job:
- Read the provided text carefully
- Extract the most important points
- Create a concise summary (3-5 sentences)
- Keep it clear and easy to understand
 
Format: Just return the summary, no extra commentary."""

    def execute(self, state: dict) -> dict:
        self.log("Starting Summerization")

        text = state.get("text","")

        prompt = f"""Summarize the following text:
 
{text}
 
Provide a concise 3-5 sentence summary."""
        
        summary = self.call_llm(prompt)

        state["summary"] = summary
       # state["iteration"]=state.get["iteration", 0] + 1
        self.log("summaerization complete")

        return state

def test_summarizer():
    """Test the summarizer agent."""
    
    print("\n" + "="*60)
    print("TESTING SUMMARIZER AGENT")
    print("="*60 + "\n")
    
    # Create the agent
    agent = summarizer()
    
    # Create test state with long text
    test_state = {
        "text": """
        Artificial Intelligence (AI) has revolutionized numerous industries 
        in recent years. From healthcare to finance, AI systems are being 
        deployed to automate tasks, make predictions, and assist human 
        decision-making. Machine learning, a subset of AI, enables computers 
        to learn from data without being explicitly programmed. Deep learning, 
        which uses neural networks with many layers, has been particularly 
        successful in areas like image recognition and natural language 
        processing. However, the rapid advancement of AI also raises important 
        ethical questions about privacy, bias, and the future of work. As AI 
        continues to evolve, it's crucial that we develop it responsibly 
        and ensure it benefits all of humanity.
        """,
        "iterations": 0
    }
    
    print("Original text:")
    print(test_state["text"][:200] + "...\n")
    
    print("Executing summarizer...\n")
    
    # Execute the agent
    result_state = agent.execute(test_state)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60 + "\n")
    
    print("Summary:")
    print(result_state["summary"])
    
    print(f"\nIterations: {result_state['iterations']}")
    
    # Show agent stats
    print("\nAgent Statistics:")
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Summarizer Agent works!")
 
 
if __name__ == "__main__":
    test_summarizer()