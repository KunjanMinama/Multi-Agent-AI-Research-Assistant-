# 🤖 Multi-Agent AI Research System — Complete Technical Guide
### Everything You Need to Know to Present, Explain, and Defend This Project

---

## 🗂️ TABLE OF CONTENTS

1. [What Is This Project? (The Elevator Pitch)](#1-what-is-this-project)
2. [Why Was It Built This Way? (Design Decisions)](#2-why-was-it-built-this-way)
3. [Full Tech Stack (Every Technology Explained)](#3-full-tech-stack)
4. [Complete System Architecture](#4-complete-system-architecture)
5. [Every File Explained (Line-by-Line Purpose)](#5-every-file-explained)
6. [Every Agent Explained (Role + Code + Why)](#6-every-agent-explained)
7. [MCP (Model Context Protocol) — Deep Dive](#7-mcp-model-context-protocol)
8. [A2A (Agent-to-Agent Protocol) — Deep Dive](#8-a2a-agent-to-agent-protocol)
9. [LangGraph — How the Workflow is Orchestrated](#9-langgraph-workflow-orchestration)
10. [End-to-End Request Trace (What Happens Step by Step)](#10-end-to-end-request-trace)
11. [Testing Strategy](#11-testing-strategy)
12. [How to Run the Project (All 3 Modes)](#12-how-to-run-the-project)
13. [Common Interview Questions & Answers](#13-common-interview-questions--answers)

---

## 1. What Is This Project?

### 🎤 Elevator Pitch (30 seconds)
> *"I built a production-grade Multi-Agent AI System where instead of one AI trying to answer everything, I have a team of 6 specialized AI agents that collaborate. A Planner routes the task, a Researcher searches the web, a Data Analyst processes CSV files, a Synthesizer merges both, a Fact-Checker audits for hallucinations, and a Writer formats the final report. The agents communicate using the Model Context Protocol (MCP) for tool execution and the Agent-to-Agent (A2A) protocol so this whole system can be called by any other software over a standard REST API."*

### 🎯 Core Use Cases
| Use Case | What Happens |
|----------|-------------|
| **"Research quantum computing trends"** | Planner → Researcher (web search via MCP) → Synthesizer → FactChecker → Writer → Professional Report |
| **"Analyze my sales.csv file"** | Planner → DataAnalyst (Pandas via MCP) → Synthesizer → FactChecker → Writer → Statistical Report |
| **"Research AI + analyze our data"** | Planner → Researcher → DataAnalyst → Synthesizer → FactChecker → Writer → Combined Intelligence Report |
| **External app calling this system** | HTTP POST to A2A server → LangGraph runs → JSON-RPC response returned |

---

## 2. Why Was It Built This Way?

### ❓ Why Multiple Agents Instead of One LLM?

| Single LLM Approach | Multi-Agent Approach |
|--------------------|---------------------|
| Has to do everything | Each agent is specialized |
| Context window fills up | Each agent gets a fresh, focused context |
| Hard to debug ("why did it fail?") | Easy to trace (which agent failed?) |
| Can't run tools without frameworks | MCP servers provide isolated, testable tools |
| Not interoperable | A2A makes it callable from anywhere |

### ❓ Why LangGraph Instead of Plain Python?

LangGraph is a **state machine** framework. It gives you:
- **Type-safe state**: Every field in `AgentState` is typed. If Researcher writes to the wrong field, Python catches it.
- **Conditional routing**: One function (`_router`) decides who runs next based on the current state.
- **Cyclic graphs**: The FactChecker can route *backward* to the Synthesizer to force rewrites. This is impossible in a simple linear pipeline.
- **Streaming**: You can `async for chunk in workflow.stream(...)` to get real-time updates.

### ❓ Why Groq Instead of Local Ollama?

| Groq | Ollama (Local) |
|------|----------------|
| 500+ tokens/sec on cloud | ~30-50 tokens/sec on CPU |
| No GPU needed | Requires 8GB+ GPU for good models |
| Same open-source models (Llama 3.3) | Same open-source models |
| Free tier: 14,400 requests/day | Unlimited local requests |
| Zero setup | Needs local installation |

### ❓ Why MCP Instead of Direct Library Calls?

Before MCP: `researcher.py` imported `duckduckgo_search` directly. To unit test it, you'd need actual internet access.

After MCP: `researcher.py` calls `get_web_search_client().call_tool(...)`. In tests, you just mock `get_web_search_client` and inject fake results. The tool runs in an **isolated subprocess**, so a crashed tool never crashes the agent.

---

## 3. Full Tech Stack

### 🧠 AI / LLM Layer
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Groq API** | `>=0.13.0` | Cloud inference for Llama 3.3 70B at 500+ tokens/sec |
| **Llama 3.3 70B** | Model: `llama-3.3-70b-versatile` | The open-source LLM powering every agent's reasoning |
| **LangChain** | `>=0.3.17` | Message formatting, prompts, ChatGroq integration |
| **LangChain-Groq** | `>=0.2.3` | Connects LangChain to Groq's API |

### 🕸️ Orchestration Layer
| Technology | Version | Purpose |
|-----------|---------|---------|
| **LangGraph** | `>=0.2.44` | State machine for multi-agent workflow. Manages routing and state. |
| **LangChain-Core** | `>=0.3.33` | Core message types (HumanMessage, AIMessage) used by agents |

### 🔧 Tool Execution Layer (MCP)
| Technology | Version | Purpose |
|-----------|---------|---------|
| **MCP (Model Context Protocol)** | `>=1.0.0` | Standard protocol for connecting agents to external tools via stdio |
| **FastMCP** | (part of `mcp`) | Decorator-based framework to build MCP servers quickly |
| **DuckDuckGo Search** | `==6.3.7` | Web search library used inside `web_search_server.py` |
| **Pandas** | `>=2.2.0` | DataFrame analysis used inside `data_analysis_server.py` |
| **NumPy** | `>=1.26.0,<2.0.0` | Numerical operations for data analysis |
| **OpenPyXL** | `>=3.1.5` | Reading `.xlsx` Excel files in the data analyst |

### 🌐 API / Microservice Layer (A2A)
| Technology | Version | Purpose |
|-----------|---------|---------|
| **FastAPI** | `>=0.115.0` | The REST API server exposing the A2A endpoint |
| **Uvicorn** | `>=0.32.0` | ASGI server that runs FastAPI |
| **WebSockets** | `>=13.1` | For future streaming support via WebSocket connections |
| **Python-Multipart** | `>=0.0.12` | For handling file uploads in the API |

### 🧰 Utilities
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Loguru** | `>=0.7.2` | Beautiful, structured logging with colors and file output |
| **Python-Dotenv** | `>=1.0.1` | Loads `GROQ_API_KEY` from the `.env` file |
| **HTTPX** | `>=0.27.0,<0.29.0` | HTTP client used by Groq SDK (pinned to avoid Python 3.13 bugs) |

### 🧪 Testing
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Pytest** | `>=8.3.0` | Test framework |
| **Pytest-Mock** | `>=3.15.0` | Provides `MagicMock` and `patch` for mocking agents & tools |
| **Pytest-AsyncIO** | `>=0.24.0` | Allows testing `async` functions (streaming endpoint) |

---

## 4. Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER / CLIENT                           │
│                    (CLI or A2A HTTP Client)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   main.py / a2a_server  │  ← Entry Point
              │   (CLI or FastAPI)       │
              └────────────┬────────────┘
                           │  creates AgentState{}
                           ▼
              ┌─────────────────────────┐
              │   LangGraph StateGraph  │  ← Orchestration Brain
              │   (workflow.py)         │
              └────────────┬────────────┘
                           │
         ┌─────────────────▼──────────────────┐
         │            PLANNER AGENT            │
         │  "Analyzes query → decides route"   │
         └──────────┬─────────┬───────────────┘
                    │         │
         ┌──────────▼──┐  ┌───▼──────────────┐
         │  RESEARCHER │  │   DATA ANALYST   │
         │   AGENT     │  │      AGENT       │
         │             │  │                  │
         │ ┌─────────┐ │  │  ┌────────────┐  │
         │ │MCP Call │ │  │  │ MCP Call   │  │
         │ │ ↓       │ │  │  │ ↓          │  │
         │ │web_     │ │  │  │data_       │  │
         │ │search_  │ │  │  │analysis_   │  │
         │ │server   │ │  │  │server      │  │
         │ └─────────┘ │  │  └────────────┘  │
         └──────┬──────┘  └──────┬───────────┘
                └────────┬───────┘
                         ▼
         ┌───────────────────────────────┐
         │       SYNTHESIZER AGENT       │
         │  "Merges findings into prose" │
         └──────────────┬────────────────┘
                        ▼
         ┌───────────────────────────────┐
         │      FACT-CHECKER AGENT       │
         │  "QA review, score 0.0-1.0"  │
         │  Score < 0.7 → Back to Synth  │◄──┐
         │  Score ≥ 0.7 → Forward        │   │ (cyclic loop)
         └──────────────┬────────────────┘   │
                        │                    │
                  [if needs revision] ───────┘
                        │
                  [if approved]
                        ▼
         ┌───────────────────────────────┐
         │         WRITER AGENT         │
         │  "Formats final Markdown"    │
         └──────────────┬───────────────┘
                        ▼
              📄 FINAL REPORT (Markdown)
```

### How the A2A Protocol Layers On Top

```
External App / Other AI System
         │
         │  HTTP POST /a2a/tasks/send
         │  {"jsonrpc":"2.0", "method":"tasks/send",
         │   "params":{"query":"...", "data_path":"..."}}
         │
         ▼
   FastAPI A2A Server (port 8000)
         │
         │  calls workflow_runner.run(query)
         │
         ▼
   [Full LangGraph Pipeline above]
         │
         ▼
   HTTP Response:
   {"jsonrpc":"2.0", "result":{"final_report":"..."}}
```

---

## 5. Every File Explained

```
Agentic AI System/
│
├── main.py                    ← CLI entry point. Run "python main.py 'your query'"
├── cli.py                     ← Advanced CLI with colors, progress bars, output saving
├── run_a2a_server.py          ← One-click script to start the FastAPI A2A server
├── run_mcp_servers.py         ← Script to test MCP servers standalone
├── requirements.txt           ← All Python dependencies (pip install -r requirements.txt)
├── .env                       ← Secrets file (GROQ_API_KEY=gsk_...)
│
├── src/
│   │
│   ├── agents/
│   │   ├── base_v2.py         ← Parent class ALL agents inherit. Connects to Groq, retry logic
│   │   ├── planner.py         ← AGENT 1: Reads query, creates plan, routes to correct agent
│   │   ├── researcher.py      ← AGENT 2: Web search via MCP, LLM synthesis of results
│   │   ├── data_analyst.py    ← AGENT 3: Pandas analysis via MCP, LLM business insights
│   │   ├── synthesizer.py     ← AGENT 4: Merges research + data into unified narrative
│   │   ├── fact_checker.py    ← AGENT 5: QA auditor, scores report, can force rewrites
│   │   └── writer.py          ← AGENT 6: Final Markdown formatter with metadata footer
│   │
│   ├── graph/
│   │   ├── state.py           ← AgentState TypedDict — the shared memory of all agents
│   │   └── workflow.py        ← LangGraph StateGraph — wires all agents + routing logic
│   │
│   ├── mcp_client/
│   │   └── tool_client.py     ← MCPToolClient class — bridges sync agents to async MCP
│   │
│   ├── mcp_servers/
│   │   ├── web_search_server.py     ← FastMCP server exposing DuckDuckGo search as a tool
│   │   ├── data_analysis_server.py  ← FastMCP server exposing Pandas analysis as a tool
│   │   └── file_server.py           ← FastMCP server for reading/writing local files
│   │
│   └── a2a/
│       ├── agent_card.py      ← The "business card" of this AI system (name, capabilities)
│       ├── a2a_server.py      ← FastAPI server with /.well-known/agent.json + /a2a/tasks/send
│       └── a2a_client.py      ← Demo client that calls the A2A server (simulates external app)
│
├── tests/
│   └── test_workflow.py       ← 31 unit tests covering all 6 agents + routing logic
│
└── data/
    └── uploads/test_data.csv  ← Sample sales CSV file for testing the Data Analyst
```

---

## 6. Every Agent Explained

### 🔵 Agent 0: BaseAgent (`base_v2.py`)
**Not a standalone agent — it's the parent class all others inherit from.**

What it provides:
- `__init__`: Connects to Groq using `ChatGroq`, sets model name and temperature
- `call_llm(prompt)`: Sends a message to Groq with **3 automatic retries** and exponential backoff
- `get_stats()`: Returns dict of how many LLM calls were made, total tokens, errors
- Every agent overrides `get_system_prompt()` and `execute(state)`

```python
# Every agent inherits this:
class BaseAgent:
    def __init__(self, name, model, temperature):
        self.llm = ChatGroq(model=model, temperature=temperature)
    
    def call_llm(self, prompt: str) -> str:
        # sends to Groq with retry logic
    
    def execute(self, state: AgentState) -> AgentState:
        # MUST be implemented by child classes
        raise NotImplementedError
```

---

### 🟢 Agent 1: PlannerAgent (`planner.py`)
**Temperature: 0.3 (low = precise, predictable decisions)**

**Job**: Read the user's query and decide: *Does this need web research? Does it need data analysis? Or both?*

**What it does**:
1. Sends the query to Groq LLM with a structured prompt
2. LLM decides: `task_type = research | analysis | combined`
3. Sets `state["next_agent"]` accordingly (`researcher` or `data_analyst`)
4. Writes the plan to `state["plan"]`

**Key Design**: The Planner uses a very low temperature (`0.3`) because routing decisions must be deterministic. If you ask it to analyze a CSV file, you always want `next_agent = data_analyst`, not something random.

---

### 🟡 Agent 2: ResearcherAgent (`researcher.py`)
**Temperature: 0.5 (balanced — factual but readable)**

**Job**: Generate smart search queries, search the web via MCP, synthesize results.

**What it does step by step**:
1. **Calls Groq** to generate 4 diverse search sub-queries from the main query
2. **Loops through each sub-query** → calls `get_web_search_client().call_tool("search_web", {...})`
3. The MCP client launches `web_search_server.py` as a subprocess, which runs DuckDuckGo
4. Results come back as JSON, gets deduplicated by URL
5. **Calls Groq again** with all results to synthesize into `state["research_findings"]`
6. Routes to `data_analyst` if a data file exists, else `synthesizer`

**MCP bridge**: The `MCPToolClient.call_tool()` method handles the async-to-sync conversion using `asyncio.run()` or a background thread if inside a running event loop (FastAPI context).

---

### 🟠 Agent 3: DataAnalystAgent (`data_analyst.py`)
**Temperature: 0.3 (low = precise statistical analysis)**

**Job**: Load the CSV/Excel file, compute statistics via MCP, generate business insights.

**What it does step by step**:
1. Checks if `state["data_path"]` exists. If not → routes to `synthesizer` immediately.
2. Calls `get_data_analysis_client().call_tool("analyze_dataset", {"file_path": ...})`
3. The MCP server (`data_analysis_server.py`) loads the file with Pandas and computes:
   - Shape (rows × columns), column names, data types
   - Missing value counts per column
   - Descriptive statistics (mean, std, min, max) for numeric columns
   - Sample rows
4. Returns this as a JSON dict which gets stored in `state["data_summary"]`
5. **Calls Groq** with this summary to generate narrative insights → `state["analysis_insights"]`

---

### 🔴 Agent 4: SynthesizerAgent (`synthesizer.py`)
**Temperature: 0.6 (slightly creative for narrative writing)**

**Job**: Read both research findings and data insights, combine them into one unified narrative.

**What it does**:
1. Reads `state["research_findings"]` and `state["analysis_insights"]`
2. Sends both to Groq with a prompt like: *"You have web research AND data analysis. Connect them."*
3. Writes the combined narrative to `state["combined_report"]`
4. Routes to `fact_checker` (ALWAYS — never skips QA)

**Key Design**: Synthesizer has a slightly higher temperature than Planner/DataAnalyst because narrative prose requires some creativity. But it's not too high (like a creative writer) because factual accuracy still matters.

---

### 🛡️ Agent 5: FactCheckerAgent (`fact_checker.py`)
**Temperature: 0.1 (extremely low = strict, analytical, no creativity)**

**Job**: Act as a strict QA auditor. Compare the synthesized report against raw source material. Assign a quality score.

**What it does**:
1. Reads `state["combined_report"]` (the draft to review)
2. Reads `state["research_findings"]` + `state["analysis_insights"]` (the raw sources)
3. Sends all three to Groq with a strict system prompt
4. Groq must respond with exactly two lines:
   - `SCORE: 0.85`
   - `FEEDBACK: Looks good, all claims supported`
5. Parses the score:
   - If `score < 0.7` → sets `needs_revision = True`, routes **back to Synthesizer**
   - If `score >= 0.7` → routes to Writer

**Why this is impressive**: This implements a **self-correcting AI loop**. The system doesn't just output blindly — it checks its own work and can rewrite until quality is acceptable. This is an advanced Agentic AI pattern called "Reflection."

---

### 📝 Agent 6: WriterAgent (`writer.py`)
**Temperature: 0.5 (balanced for professional writing)**

**Job**: Take the approved combined report and wrap it into a polished, professional Markdown document.

**What it does**:
1. Reads `state["combined_report"]`
2. Sends to Groq with instructions to format with headers, bullet points, bold text
3. Appends a metadata footer table:
   ```markdown
   | Field       | Value                  |
   |-------------|------------------------|
   | Generated   | 2026-05-09 18:41:11    |
   | Query       | What are AI trends...  |
   | Iterations  | 5                      |
   ```
4. Sets `state["final_report"]` and `next_agent = None` (signals END to LangGraph)

---

## 7. MCP (Model Context Protocol)

### What is MCP?
MCP is an **open standard by Anthropic** (released late 2024) that defines how AI models should connect to external tools and data sources. Think of it as a **USB standard for AI tools** — once a tool implements MCP, any AI that speaks MCP can use it.

### How MCP Works in This Project

**Before MCP** (what you should NOT do):
```python
# researcher.py directly imports duckduckgo_search
from duckduckgo_search import DDGS
results = DDGS().text("quantum computing", max_results=10)
```

**After MCP** (what this project does):
```python
# researcher.py calls a TOOL via MCP
client = get_web_search_client()                    # MCPToolClient
results = client.call_tool("search_web", {          # JSON-RPC call
    "query": "quantum computing",
    "max_results": 10
})
```

### The MCP Transport: stdio

This project uses **stdio transport** — the simplest MCP transport mode:
1. The `MCPToolClient` launches the MCP server as a **child subprocess**: `python src/mcp_servers/web_search_server.py`
2. Communication happens over **standard input/output streams** (stdin/stdout)
3. Messages are encoded as JSON-RPC 2.0 requests/responses
4. The subprocess is launched fresh for each tool call and exits when done

### The Three MCP Servers

| Server File | Tool Name | What It Does | Library Used |
|-------------|-----------|-------------|-------------|
| `web_search_server.py` | `search_web` | Searches DuckDuckGo, returns list of `{title, body, href}` | `duckduckgo_search` |
| `data_analysis_server.py` | `analyze_dataset` | Loads CSV/Excel, returns stats as JSON | `pandas`, `numpy` |
| `file_server.py` | `read_file`, `write_file` | Reads/writes text files | `pathlib` |

### The Async/Sync Challenge

MCP is fully **async** (uses `asyncio`). But LangGraph agents run **synchronously**. This creates a conflict.

**The Solution** (in `tool_client.py`):
```python
def call_tool(self, tool_name, arguments):
    try:
        loop = asyncio.get_running_loop()   # Is there already an event loop?
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside FastAPI — can't call asyncio.run() again!
        # Solution: Spawn a new thread with its own event loop
        result_container = {}
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            result_container["res"] = new_loop.run_until_complete(...)
            new_loop.close()
        thread = threading.Thread(target=run_in_thread)
        thread.start(); thread.join()
        return result_container["res"]
    else:
        # Normal case (CLI mode): just use asyncio.run()
        return asyncio.run(self._call_tool_async(tool_name, arguments))
```

---

## 8. A2A (Agent-to-Agent Protocol)

### What is A2A?
A2A is an **open standard by Google** (released 2025) for how AI agents should communicate with each other. It answers: *"If I have an AI agent and you have an AI agent, how do we plug them together?"*

A2A defines:
1. **Agent Cards**: Machine-readable metadata about what an agent can do (`/.well-known/agent.json`)
2. **Tasks API**: A JSON-RPC 2.0 endpoint (`/a2a/tasks/send`) to send tasks to an agent
3. **Streaming**: Optional SSE streaming for long-running tasks

### How A2A Works in This Project

**The Agent Card** (`agent_card.py`):
```json
GET /.well-known/agent.json
{
  "name": "Multi-Agent Research & Analysis System",
  "version": "1.0.0",
  "capabilities": {
    "web_search": true,
    "data_analysis": true,
    "markdown_reports": true
  },
  "url": "http://localhost:8000/a2a"
}
```

**Sending a Task** (`/a2a/tasks/send`):
```json
POST /a2a/tasks/send
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "tasks/send",
  "params": {
    "query": "What are the latest AI trends?",
    "data_path": null
  }
}
```

**Getting the Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "result": {
    "task_id": "uuid-here",
    "status": "completed",
    "result": {
      "final_report": "# AI Trends Report\n\n## Executive Summary...",
      "errors": [],
      "iterations": 5
    }
  }
}
```

### Why A2A Matters
Without A2A, your agent is a **black box** — you can only call it from your own code. With A2A:
- A CRM system can automatically trigger research reports
- A scheduling system can send batch analysis jobs
- Another AI agent (like a Planner bot) can discover and delegate tasks to your agent
- You can build a marketplace of AI agents that discover each other

---

## 9. LangGraph Workflow Orchestration

### What is a StateGraph?
LangGraph's `StateGraph` is a **directed graph** where:
- **Nodes** = individual agent functions
- **Edges** = routing rules between agents
- **State** = the shared dictionary passed between all agents

### The AgentState (Shared Memory)

```python
class AgentState(TypedDict):
    # INPUT
    query: str           # "What are AI trends?"
    data_path: Optional[str]  # Path to CSV file
    
    # PLANNING
    plan: Optional[str]       # Step-by-step plan from Planner
    next_agent: Optional[str] # Who runs next? ("researcher", "writer", None)
    
    # RESEARCH RESULTS
    research_findings: Optional[str]   # Synthesized web research
    search_results: List[Dict]         # Raw search results dicts
    
    # DATA ANALYSIS
    data_summary: Optional[Dict]       # Pandas stats as JSON
    analysis_insights: Optional[str]   # LLM narrative about the data
    
    # SYNTHESIS
    combined_report: Optional[str]     # Research + Data merged
    
    # QUALITY CONTROL
    quality_score: float   # 0.0 to 1.0
    needs_revision: bool   # Should Synthesizer rewrite?
    
    # FINAL OUTPUT
    final_report: Optional[str]  # The polished Markdown report
    
    # TRACKING
    iterations: int          # How many agent calls total
    errors: List[str]        # Any errors encountered
```

### The Router Function
Every routing decision goes through ONE function:

```python
def _router(self, state: AgentState) -> str:
    # Safety: Kill the workflow if it loops too long
    if state.get("iterations", 0) > 10:
        return "end"  # Force stop
    
    # Route to whatever agent was set
    next_agent = state.get("next_agent")
    if next_agent == "researcher":   return "researcher"
    if next_agent == "data_analyst": return "data_analyst"
    if next_agent == "fact_checker": return "fact_checker"
    if next_agent == "writer":       return "writer"
    return "end"  # None or unknown → end
```

### Graph Construction
```python
workflow = StateGraph(AgentState)

# ADD NODES
workflow.add_node("planner",      self._run_planner)
workflow.add_node("researcher",   self._run_researcher)
workflow.add_node("data_analyst", self._run_data_analyst)
workflow.add_node("synthesizer",  self._run_synthesizer)
workflow.add_node("fact_checker", self._run_fact_checker)
workflow.add_node("writer",       self._run_writer)

# SET ENTRY POINT
workflow.set_entry_point("planner")

# ADD ROUTING EDGES (conditional = uses _router function)
workflow.add_conditional_edges("planner",      self._router, routing_map)
workflow.add_conditional_edges("researcher",   self._router, routing_map)
workflow.add_conditional_edges("data_analyst", self._router, routing_map)
workflow.add_edge("synthesizer", "fact_checker")  # Always goes to QA
workflow.add_conditional_edges("fact_checker", self._router, routing_map)
workflow.add_edge("writer", END)  # Always ends

self.app = workflow.compile()
```

---

## 10. End-to-End Request Trace

### Scenario: "Research AI in healthcare and analyze the trends CSV"

**Step 0: User runs command**
```bash
python main.py "Research AI in healthcare" --data data/uploads/test_data.csv
```

**Step 1: main.py**
```python
workflow = ResearchWorkflow()          # Initializes all 6 agents
result = workflow.run(query, data_path) # Calls LangGraph .invoke()
```

**Step 2: LangGraph → Planner**
```
AgentState = {
  query: "Research AI in healthcare",
  data_path: "data/uploads/test_data.csv",
  next_agent: "planner",
  iterations: 0, ...
}
```
Planner LLM reads the query → sees it has BOTH research + data needs → sets:
```
next_agent = "researcher"
plan = "1. Research AI healthcare trends online. 2. Analyze CSV data. 3. Synthesize."
iterations = 1
```

**Step 3: LangGraph → Researcher**

Researcher calls Groq → gets 4 sub-queries:
- "AI trends in healthcare 2024"
- "machine learning medical diagnosis"
- "AI healthcare statistics adoption"
- "experts opinion AI medicine"

For each sub-query:
```
MCPToolClient("web_search_server.py").call_tool("search_web", {"query": "..."})
  → subprocess launched: python src/mcp_servers/web_search_server.py
  → DDGS().text("AI trends in healthcare 2024", max_results=8)
  → returns list of {title, body, href}
  → subprocess exits
```

Researcher calls Groq again → synthesizes 20+ results into `research_findings`.

Sets `next_agent = "data_analyst"` (because data_path exists).

**Step 4: LangGraph → DataAnalyst**

```
MCPToolClient("data_analysis_server.py").call_tool("analyze_dataset", {
  "file_path": "data/uploads/test_data.csv"
})
  → subprocess launched: python src/mcp_servers/data_analysis_server.py
  → pandas.read_csv(file_path)
  → computes shape, dtypes, describe(), missing values
  → returns JSON: {"shape": {"rows": 12, "columns": 5}, "numeric_stats": {...}}
  → subprocess exits
```

DataAnalyst calls Groq with the JSON stats → generates `analysis_insights`.

Sets `next_agent = "synthesizer"`.

**Step 5: LangGraph → Synthesizer**

Receives both `research_findings` and `analysis_insights`.
Calls Groq with a prompt to merge them into one connected narrative.
Sets `combined_report`. Edges force route to `fact_checker`.

**Step 6: LangGraph → FactChecker**

Sends `combined_report` + raw sources to Groq with strict QA prompt.
Groq responds:
```
SCORE: 0.92
FEEDBACK: Looks good, all claims are supported by the source material.
```

Score `0.92 >= 0.7` → sets `next_agent = "writer"`.

**Step 7: LangGraph → Writer**

Receives `combined_report`. Calls Groq to apply professional Markdown formatting.
Appends metadata table. Sets `final_report`. Sets `next_agent = None`.

**Step 8: LangGraph Router → END**

`next_agent = None` → Router returns `"end"` → LangGraph stops.

**Step 9: Output printed to console (or returned via A2A API)**

---

## 11. Testing Strategy

### Philosophy: Test Without Real APIs

All 31 unit tests use **mocking** — no real Groq API calls, no real internet searches.

```python
# Example: Testing Researcher Agent
with patch("src.agents.researcher.get_web_search_client") as mock_factory:
    mock_client = MagicMock()
    mock_factory.return_value = mock_client
    
    # Fake MCP response
    class FakeTextContent:
        text = json.dumps([{"title": "AI News", "body": "...", "href": "http://..."}])
    mock_client.call_tool.return_value = [FakeTextContent()]
    
    result = agent.execute(state)  # Runs WITHOUT internet

assert result["research_findings"] is not None
```

### Test Categories

| Test Class | Tests | What It Covers |
|-----------|-------|----------------|
| `TestAgentState` | 3 | State initialization and field validation |
| `TestPlannerAgent` | 4 | Routing decisions, fallback on LLM error |
| `TestResearcherAgent` | 5 | MCP search mock, routing, error handling |
| `TestDataAnalystAgent` | 4 | MCP data mock, missing files, stats validation |
| `TestSynthesizerAgent` | 3 | Combined and partial synthesis |
| `TestWriterAgent` | 3 | Report format, metadata footer, fallback |
| `TestWorkflowRouter` | 7 | Every routing case + circuit breaker |
| `TestErrorHandling` | 2 | Cross-agent error accumulation |

### Run Tests
```bash
# All unit tests (fast, no API needed)
python -m pytest tests/test_workflow.py -v -m "not integration"

# With coverage report
python -m pytest tests/test_workflow.py --cov=src --cov-report=html
```

---

## 12. How to Run the Project

### Prerequisites
```bash
# Set your Groq API key (get free at console.groq.com)
# Windows
set GROQ_API_KEY=gsk_your_key_here

# Or add to .env file:
echo GROQ_API_KEY=gsk_your_key_here > .env

# Install dependencies
pip install -r requirements.txt
```

### Mode 1: CLI (Direct Query)
```bash
# Research only
python main.py "What are the latest trends in quantum computing?"

# Data analysis only
python main.py "Analyze monthly sales performance" --data data/uploads/test_data.csv

# Combined (research + data)
python main.py "Compare AI adoption to our internal data" --data data/uploads/test_data.csv

# Save report to file
python main.py "AI trends" --output reports/ai_report.md
```

### Mode 2: A2A Microservice (Distributed Mode)
```bash
# Terminal 1: Start the A2A server
python run_a2a_server.py
# Server starts at http://localhost:8000
# API docs at http://localhost:8000/docs

# Terminal 2: Send a task from external client
python src/a2a/a2a_client.py
```

You can also call it with curl:
```bash
curl -X POST http://localhost:8000/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "id": "1",
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {"query": "What are AI trends in 2025?"}
  }'
```

### Mode 3: Python API
```python
from src.graph.workflow import ResearchWorkflow

workflow = ResearchWorkflow()
result = workflow.run("What are quantum computing trends?")
print(result["final_report"])

# Async streaming
async for chunk in workflow.stream("AI healthcare trends"):
    node = list(chunk.keys())[0]
    print(f"✅ Completed: {node}")
```

---

## 13. Common Interview Questions & Answers

**Q: What is a Multi-Agent System?**
> A: Instead of one AI trying to answer everything, multiple specialized agents work as a team. Each agent focuses on one task (research, data analysis, QA) and passes results through a shared state. This makes the system more reliable, easier to debug, and more scalable.

**Q: What is LangGraph and why did you use it?**
> A: LangGraph is a framework for building stateful, multi-agent workflows as directed graphs. I used it because it provides type-safe shared state (TypedDict), built-in conditional routing, and — critically — supports cyclic graphs so the FactChecker can loop back to the Synthesizer. Standard LangChain only does linear chains.

**Q: What is the Model Context Protocol (MCP)?**
> A: MCP is an open standard by Anthropic for connecting AI models to external tools. Instead of directly importing a library inside an agent, the agent calls a tool server over a standard protocol (like JSON-RPC over stdio). This makes tools isolated, testable, and reusable across different AI systems.

**Q: What is the Agent-to-Agent (A2A) Protocol?**
> A: A2A is a Google standard for how AI agents discover and communicate with each other. My system publishes an "Agent Card" at `/.well-known/agent.json` and accepts tasks at `/a2a/tasks/send`. Any other AI system that speaks A2A can discover my agent and delegate work to it — it's like a REST API but standardized for AI agents.

**Q: How do you handle hallucinations?**
> A: I built a FactChecker Agent that runs after the Synthesizer. It reads the final draft and cross-references every claim against the raw source material. It assigns a quality score from 0 to 1. If the score is below 0.7, the report is rejected and sent back to the Synthesizer for rewriting. This implements the AI "Reflection" pattern.

**Q: How do you handle errors?**
> A: Every agent is wrapped in a try/except block in `workflow.py`. If an agent crashes, the error is logged to `state["errors"]`, and the workflow continues with a fallback routing decision rather than crashing. There's also a circuit breaker: if `iterations > 10`, the Router forces the workflow to END, preventing infinite loops.

**Q: How do you test without real API keys?**
> A: I use `unittest.mock.patch`. For MCP tools, I patch `get_web_search_client` and return fake `MockTextContent` objects. For LLM calls, I mock `agent.llm.invoke` to return a predetermined string. This means all 31 unit tests run in under 30 seconds without any internet or API key.

**Q: What happens when DuckDuckGo returns no results?**
> A: The Researcher gracefully falls back to LLM knowledge. The `_search()` method returns an empty list. The agent checks: `if not all_results` and then passes `"No web search results available. Use your knowledge base."` to the LLM. The LLM still produces research findings from its training data and marks them as "LLM knowledge base" in the metadata.

**Q: What is the `asyncio` challenge you solved?**
> A: MCP uses `async/await` internally, but LangGraph agents run synchronously. When the A2A FastAPI server runs, it already has an event loop running. Calling `asyncio.run()` inside a running event loop raises `RuntimeError`. My solution: detect if a loop is running, and if so, spin up a new thread with its own event loop using `threading.Thread`.

**Q: Can this system handle concurrent requests?**
> A: Each request to the A2A server creates a fresh `AgentState` dictionary, so there's no shared mutable state between requests. However, the LangGraph workflow is currently synchronous (blocking), so concurrent requests would queue up. For production, you'd use `asyncio.gather` or run the workflow on a thread pool.

---

*Document generated for: Multi-Agent AI Research System v1.0*
*Technologies: LangGraph · Groq (Llama 3.3) · MCP · A2A · FastAPI · Python 3.10*
