# 🤖 Multi-Agent AI Research & Analysis System

A **production-grade multi-agent AI system** built with LangGraph, Groq (Llama 3), and Python. It automatically researches topics online and analyzes data files to generate professional markdown reports.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| **Multi-Agent Pipeline** | 6 specialized agents (Planner → Researcher → Data Analyst → Synthesizer → FactChecker → Writer) |
| **Web Research** | DuckDuckGo search — no API key needed, 3-5 parallel queries per topic |
| **Data Analysis** | CSV/Excel support with pandas: stats, correlations, quality checks |
| **Open-Source LLMs** | Llama 3 8B via Groq API (free, 500+ tokens/sec) |
| **Smart Routing** | LangGraph state machine automatically routes between agents |
| **Error Resilience** | Every agent has fallbacks — system never crashes mid-workflow |
| **CLI Interface** | Interactive and direct modes with colored output |

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────┐
│ PLANNER │  Analyzes query → decides workflow path
└────┬────┘
     │ (routes based on query type)
     ├─────────────────┬─────────────────┐
     ▼                 ▼                 ▼
┌──────────┐    ┌─────────────┐   (data-only path)
│RESEARCHER│    │DATA_ANALYST │◄──────────────────
│          │    │             │
│DuckDuckGo│    │   pandas    │
│ 3-5 qrs  │    │ CSV/Excel   │
└────┬─────┘    └──────┬──────┘
     │                 │
     └────────┬────────┘
              ▼
     ┌─────────────────┐
     │   SYNTHESIZER   │  Combines research + data → unified insights
     └────────┬────────┘
              ▼
     ┌────────────────┐
     │  FACT CHECKER  │  QA Review: Checks for hallucinations. Routes back if failed.
     └────────┬───────┘
              ▼ (if passed)
     ┌────────────────┐
     │     WRITER     │  Formats → professional markdown report
     └────────┬───────┘
              ▼
       📄 Final Report
```

### Agent Descriptions

| Agent | Model Temp | Role |
|-------|-----------|------|
| **Planner** | 0.3 (precise) | Analyzes query, creates execution plan, routes to agents |
| **Researcher** | 0.5 (balanced) | Multi-query DuckDuckGo search + LLM synthesis |
| **Data Analyst** | 0.3 (precise) | Pandas stats + LLM narrative insights |
| **Synthesizer** | 0.6 (creative) | Integrates research + data, finds connections |
| **FactChecker** | 0.1 (strict) | Adversarial QA agent to prevent hallucinations and logic errors |
| **Writer** | 0.5 (balanced) | Professional markdown report with metadata |

---

## 🚀 Installation

### Prerequisites
- Python 3.9+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Steps

```bash
# 1. Clone / navigate to project
cd "Agentic AI System"

# 2. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
# Edit .env file and add your Groq key:
# GROQ_API_KEY=your_key_here
```

---

## ⚙️ Configuration

Edit the `.env` file in the project root:

```env
# Required: Get free key at https://console.groq.com
GROQ_API_KEY=gsk_your_key_here

# Optional: Other API keys
HUGGINGFACE_API_TOKEN=hf_your_token
```

### Model Selection

Change the model in each agent's `__init__` (in `src/agents/`):

| Model | Context | Best For |
|-------|---------|---------|
| `llama3-8b-8192` | 8K tokens | Fast, default, good quality |
| `llama3-70b-8192` | 8K tokens | Higher quality, slower |
| `mixtral-8x7b-32768` | 32K tokens | Long documents, complex analysis |
| `gemma2-9b-it` | 8K tokens | Google model, alternative option |

---

## 💻 Usage

### Direct Mode

```bash
# Research-only query
python main.py "What are the latest trends in quantum computing?"

# Data analysis only
python main.py "Analyze sales performance" --data data/uploads/test_data.csv

# Combined research + data
python main.py "Research AI adoption and compare with our data" --data data.csv

# Save report to file
python main.py "AI trends" --output reports/ai_trends.md

# Quiet mode (pipe-friendly, report only)
python main.py "Query" --quiet > report.md
```

### Interactive Mode

```bash
python main.py --interactive
# OR
python main.py -i
```

Interactive mode prompts for:
1. Your research query
2. Data file path (optional)
3. Output file path (optional)

### Python API

```python
from src.graph.workflow import ResearchWorkflow

workflow = ResearchWorkflow()

# Research query
result = workflow.run("What are AI trends in healthcare?")
print(result["final_report"])

# With data file
result = workflow.run(
    "Analyze our sales data and compare with market trends",
    data_path="data/sales.csv"
)

# Access individual results
print(result["research_findings"])
print(result["analysis_insights"])
print(result["combined_report"])
print(result["final_report"])
print(result["errors"])  # Any errors
print(result["iterations"])  # Agent calls made

# Async streaming
import asyncio

async def stream_example():
    async for chunk in workflow.stream("AI trends"):
        node_name = list(chunk.keys())[0]
        print(f"✅ Completed: {node_name}")

asyncio.run(stream_example())
```

---

## 🧪 Testing

```bash
# Run all unit tests (no API key needed — uses mocked LLM)
pytest tests/test_workflow.py -v -m "not integration"

# Run integration tests (requires GROQ_API_KEY)
pytest tests/test_workflow.py -v -m integration

# Run all tests
pytest tests/test_workflow.py -v

# Run with coverage
pytest tests/test_workflow.py --cov=src --cov-report=html
```

### Test Sample Data

A test CSV is included at `data/uploads/test_data.csv`:

```csv
month,sales,profit,region,units
Jan,10000,2000,North,500
Feb,12000,2400,North,600
...
```

Test it:
```bash
python main.py "Analyze monthly sales trends and identify peak months" \
    --data data/uploads/test_data.csv \
    --output reports/sales_analysis.md
```

---

## 📁 Project Structure

```
agentic-ai-system/
├── src/
│   ├── agents/
│   │   ├── __init__.py           # Package exports
│   │   ├── base_v2.py            # Abstract base with Groq + retry logic
│   │   ├── planner.py            # Query analysis & routing
│   │   ├── researcher.py         # DuckDuckGo search + LLM synthesis
│   │   ├── data_analyst.py       # Pandas analysis + LLM insights
│   │   ├── synthesizer.py        # Integration of all sources
│   │   ├── fact_checker.py       # QA loop and hallucination checks
│   │   └── writer.py             # Markdown report generation
│   │
│   ├── graph/
│   │   ├── __init__.py           # Package exports
│   │   ├── state.py              # AgentState TypedDict definition
│   │   └── workflow.py           # LangGraph StateGraph orchestration
│   │
│   └── tools/
│       └── __init__.py
│
├── data/
│   ├── uploads/
│   │   └── test_data.csv         # Sample CSV for testing
│   └── outputs/                  # Generated reports go here
│
├── tests/
│   └── test_workflow.py          # Comprehensive test suite
│
├── main.py                       # CLI entry point
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (add GROQ_API_KEY)
└── README.md                     # This file
```

---

## 🔧 Design Decisions

### Why Groq instead of Ollama?
- ✅ No GPU/local hardware required
- ✅ 500+ tokens/sec (10x faster inference)  
- ✅ Same open-source models (Llama 3, Mixtral)
- ✅ Free tier: 14,400 requests/day

### Why DuckDuckGo for search?
- ✅ No API key needed
- ✅ No rate limits for normal use
- ✅ Returns structured results (title, snippet, URL)
- ✅ Privacy-friendly

### Why LangGraph for orchestration?
- ✅ Type-safe state management (TypedDict)
- ✅ Conditional routing built-in
- ✅ Automatic state merging
- ✅ Async streaming support
- ✅ Easy to visualize and debug

### Distributed Microservice Architecture (A2A & MCP)

This system implements a production-grade distributed architecture:

1. **Model Context Protocol (MCP)**:
   - Instead of direct library calls, agents delegate actions to specialized MCP Tool Servers.
   - Servers available in `src/mcp_servers/`: `web_search_server.py`, `data_analysis_server.py`, `file_server.py`.
   - The tools run as independent processes connected via `stdio`.

2. **Agent-to-Agent (A2A) Protocol**:
   - The LangGraph workflow can be exposed as an independent, interoperable service using the A2A protocol.
   - Run `python run_a2a_server.py` to launch the A2A JSON-RPC server (FastAPI).
   - Discovery endpoint available at `/.well-known/agent.json`.
   - A demonstration client is provided in `src/a2a/a2a_client.py`.

## Running the Distributed System

```bash
# 1. (Optional) Run MCP servers standalone for testing
python run_mcp_servers.py

# 2. Start the A2A Server (Exposes the Agentic AI System to other agents)
python run_a2a_server.py

# 3. Test the A2A Client
python src/a2a/a2a_client.py
```

---

## 🛣️ Roadmap / Optional Enhancements

- [ ] FastAPI REST backend with `/research` endpoint
- [ ] WebSocket streaming for real-time progress updates
- [ ] Redis caching for repeated queries
- [ ] Matplotlib/Plotly chart generation in reports
- [x] Quality scoring with auto-retry loop (Implemented via FactChecker)
- [ ] Token usage cost tracking
- [ ] Vector DB (Chroma/Pinecone) for research memory

---

## 📄 License

MIT License — free for personal and commercial use.
