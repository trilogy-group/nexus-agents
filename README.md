# Nexus Agents: Multi-Agent Deep Research System

A sophisticated multi-agent system designed for continuous, iterative, and deep research on complex topics. The system produces "living documents" that evolve with new information, leveraging Agent-to-Agent (A2A) communication and Model-Context-Protocol (MCP) for tool integration.

## 🏗️ Architecture Overview

The Nexus Agents system implements a hierarchical multi-agent architecture with the following layers:

### 1. Orchestration & Coordination Layer
- **Task Manager**: Central state machine managing research workflows
- **Communication Bus**: Redis-based pub-sub messaging for A2A communication
- **Agent Spawner**: Dynamic agent lifecycle management

### 2. Research Planning & Topic Decomposition
- **Topic Decomposer Agent**: Breaks complex queries into hierarchical sub-topics
- **Planning Module**: Creates execution plans and schedules

### 3. Parallel Search & Data Retrieval
- **Search Agents**: Specialized agents for each search provider
  - Linkup Search Agent (web search)
  - Exa Search Agent (semantic search)
  - Perplexity Search Agent (AI-powered search)
  - Firecrawl Search Agent (web scraping)
- **MCP Integration**: Proper Model Context Protocol implementation

### 4. Summarization & Higher-Order Reasoning
- **Summarization Agents**: Transform raw data into insights
- **Reasoning Agents**: Synthesis, analysis, and evaluation

### 5. Data Persistence & Living Documents
- **DuckDB Knowledge Base**: Lightweight, JSON-native database
- **File Storage**: Binary files stored on disk with metadata tracking
- **Artifact Generation**: Multiple output formats (Markdown, PDF, CSV, dashboards)

## 🚀 Features

- **Multi-Provider LLM Support**: OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama
- **Proper MCP Implementation**: Official MCP servers for external tool access
- **Continuous Research**: Persistent agents that evolve knowledge over time
- **Hierarchical Processing**: Tree-of-thoughts approach to complex queries
- **Human-in-the-Loop**: Interactive refinement and feedback mechanisms
- **Scalable Architecture**: Horizontal scaling and resilient error handling

## 📦 Installation

### Prerequisites
- Python 3.12+
- Node.js 18+ (for MCP servers)
- Redis (for agent communication) or Docker

### Quick Start with Development Environment

The easiest way to get started is using our unified development startup script:

```bash
# Clone the repository
git clone https://github.com/trilogy-group/nexus-agents.git
cd nexus-agents

# Install Python dependencies
uv sync

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys

# Start all services (Redis, API, Web UI)
./scripts/start_dev.sh

# Access the services:
# - Web UI: http://localhost:12001
# - API Docs: http://localhost:12000/docs
# - Redis: localhost:6379

# Stop all services (keeps Redis running by default)
./scripts/stop_dev.sh

# Stop all services including Redis
./scripts/stop_dev.sh --all
```

The startup script will:
1. Start Redis (using Docker if available, otherwise local redis-server)
2. Setup MCP servers if not already installed
3. Validate MCP configuration and API keys
4. Start the API backend on port 12000
5. Start the Web UI on port 12001
6. Follow logs in real-time

### Manual Installation

### Setup

1. **Clone the repository**:
```bash
git clone https://github.com/trilogy-group/nexus-agents.git
cd nexus-agents
```

2. **Install Python dependencies**:
```bash
uv sync
```

3. **Set up MCP servers and environment**:
```bash
# Run the automated setup script
bash scripts/setup_mcp_servers.sh
```

4. **Configure API keys**:
```bash
cp .env.example .env
# Edit .env with your API keys for the MCP servers you want to use:
# - FIRECRAWL_API_KEY
# - EXA_API_KEY  
# - PERPLEXITY_API_KEY
# - LINKUP_API_KEY
```

5. **Validate setup**:
```bash
uv run python scripts/validate_mcp_setup.py
```

## 🔧 Configuration

### ⚠️ API Key Security - Important Notice

**API keys are NEVER stored in configuration files!** The `config/mcp_config.json` file contains empty placeholder values (`""`) for API keys that are completely ignored by the system.

```json
// ❌ DO NOT PUT REAL API KEYS HERE!
"env": {
  "FIRECRAWL_API_KEY": "",  // ← This empty string is ignored
  "EXA_API_KEY": ""         // ← Only environment variable names matter
}
```

**✅ ALWAYS export API keys as environment variables:**
```bash
export FIRECRAWL_API_KEY=your_actual_firecrawl_key
export EXA_API_KEY=your_actual_exa_key
export PERPLEXITY_API_KEY=your_actual_perplexity_key
export LINKUP_API_KEY=your_actual_linkup_key
```

The configuration file only tells the system **which environment variable names to look for** - it never reads the placeholder values.

### MCP Server Configuration

The system uses official Model Context Protocol (MCP) servers. Configuration is managed through `config/mcp_config.json`:

- **Firecrawl**: Web scraping and crawling (`uv run firecrawl-mcp`)
- **Exa**: Web search (`uv run exa-mcp-server`)  
- **Perplexity**: AI-powered search (`uv run mcp-server-perplexity-ask`)
- **Linkup**: Web search (`uv run python -m mcp_search_linkup`)

### Environment Variables

Create a `.env` file with the following variables:

```env
# LLM Provider API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
XAI_API_KEY=your_xai_key
OPENROUTER_API_KEY=your_openrouter_key

# Search Provider API Keys
LINKUP_API_KEY=your_linkup_key
EXA_API_KEY=your_exa_key
PERPLEXITY_API_KEY=your_perplexity_key
FIRECRAWL_API_KEY=your_firecrawl_key

# Database Configuration
REDIS_URL=redis://localhost:6379
DUCKDB_PATH=./data/nexus.db
STORAGE_PATH=./data/storage
```

### LLM Configuration

The system supports two-model configuration:
- **Reasoning Model**: More capable model for complex analysis (e.g., GPT-4, Claude-3.5-Sonnet)
- **Task Model**: Lightweight model for routine tasks (e.g., GPT-3.5-turbo, Claude-3-Haiku)

## 🎯 Usage

### Basic Usage

```python
import asyncio
from src.nexus_agents import NexusAgents
from src.llm import LLMClient, LLMConfig, LLMProvider
from src.orchestration.communication_bus import CommunicationBus
from src.config.search_providers import SearchProvidersConfig

async def main():
    # Configure LLM
    reasoning_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4",
        api_key="your_openai_key"
    )
    
    task_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="your_openai_key"
    )
    
    llm_client = LLMClient(
        reasoning_config=reasoning_config,
        task_config=task_config
    )
    
    # Create system components
    communication_bus = CommunicationBus()
    search_config = SearchProvidersConfig()
    
    # Initialize Nexus Agents
    nexus = NexusAgents(
        llm_client=llm_client,
        communication_bus=communication_bus,
        search_providers_config=search_config,
        duckdb_path="./data/nexus.db",
        storage_path="./data/storage"
    )
    
    # Start the system
    await nexus.start()
    
    # Conduct research
    research_query = "What are the latest developments in quantum computing?"
    results = await nexus.conduct_research(research_query)
    
    print(f"Research completed: {results}")

if __name__ == "__main__":
    asyncio.run(main())

## 🔍 Live Search Workflow with Real API Keys

To test and use the system with actual search capabilities, set up your API keys:

### Step 1: Configure API Keys

```bash
# Set your real API keys for MCP servers
export FIRECRAWL_API_KEY="fc-your_actual_firecrawl_key"
export EXA_API_KEY="your_actual_exa_key"
export PERPLEXITY_API_KEY="pplx-your_actual_perplexity_key"
export LINKUP_API_KEY="your_actual_linkup_key"
export OPENAI_API_KEY="sk-your_actual_openai_key"
```

### Step 2: Run Live Search Tests

```bash
# Test live search functionality with real API calls
uv run python test_live_search_workflow.py
```

### Step 3: Use Live Search in Code

```python
import asyncio
from src.mcp_client import MCPClient

async def live_search_example():
    """Example of using live search capabilities."""
    
    # Initialize MCP client
    mcp_client = MCPClient()
    
    # Example 1: Web scraping with Firecrawl
    print("🔥 Scraping web page...")
    result = await mcp_client.scrape_url("https://example.com")
    print(f"Scraped content: {result}")
    
    # Example 2: Web search with Firecrawl
    print("🔍 Searching the web...")
    search_result = await mcp_client.search_web("AI latest news 2024", "firecrawl")
    print(f"Search results: {search_result}")
    
    # Example 3: Research search with Exa
    print("📚 Research search...")
    research_result = await mcp_client.search_web("machine learning papers", "exa")
    print(f"Research results: {research_result}")

if __name__ == "__main__":
    asyncio.run(live_search_example())

### Step 4: Full Research Workflow

```python
import asyncio
from src.llm.client import LLMClient
from src.communication.bus import CommunicationBus
from src.agents.nexus import NexusAgents
from src.search.providers_config import SearchProvidersConfig

async def real_research_workflow():
    """Complete research workflow with live API calls."""
    
    # Initialize system with real API access
    llm_client = LLMClient()
    communication_bus = CommunicationBus()
    search_config = SearchProvidersConfig()
    
    nexus = NexusAgents(
        llm_client=llm_client,
        communication_bus=communication_bus,
        search_providers_config=search_config,
        duckdb_path="./data/nexus.db",
        storage_path="./data/storage"
    )
    
    await nexus.start()
    
    # Perform live research with multiple sources
    research_topics = [
        "renewable energy trends 2024",
        "artificial intelligence breakthroughs",
        "quantum computing applications"
    ]
    
    for topic in research_topics:
        print(f"\n🔍 Researching: {topic}")
        
        # Use MCP servers for diverse search results
        firecrawl_results = await nexus.mcp_client.search_web(topic, "firecrawl")
        exa_results = await nexus.mcp_client.search_web(topic, "exa")
        
        print(f"✅ Found {len(firecrawl_results)} Firecrawl results")
        print(f"✅ Found {len(exa_results)} Exa results")
        
        # Process and analyze results with LLM
        # (Implementation depends on your specific research needs)

if __name__ == "__main__":
    asyncio.run(real_research_workflow())

## 🔧 Testing

Run the test suite to verify installation:

```bash
# Test system initialization
uv run python test_system_initialization.py

# Test live search functionality with real API calls
# (Requires API keys to be set in environment)
uv run python test_live_search_workflow.py

# Test research workflow (basic components)
uv run python test_research_workflow.py

# Test MCP server integration
uv run python test_official_mcp_integration.py

# Test individual components
uv run python -m pytest tests/
```

### Test Levels

1. **Basic Tests** - System initialization and component setup (no API keys required)
2. **Integration Tests** - MCP server handshakes and tool discovery (dummy keys work)
3. **Live Tests** - Real search operations and scraping (requires valid API keys)

⚠️ **Note**: Live tests require actual API keys. Set them in your environment or they will be skipped.

## 🔍 MCP Integration

The system uses proper Model Context Protocol (MCP) implementation with official servers:

### Available MCP Servers

1. **Linkup MCP Server** (Python-based)
   - Command: `uv run python -m mcp_search_linkup`
   - Purpose: Web search capabilities

2. **Exa MCP Server** (Node.js-based)
   - Command: `uv run node external_mcp_servers/exa-mcp/.smithery/index.cjs`
   - Purpose: Semantic search

3. **Perplexity MCP Server** (Node.js-based, Official)
   - Command: `uv run node external_mcp_servers/perplexity-official-mcp/perplexity-ask/dist/index.js`
   - Purpose: AI-powered search

4. **Firecrawl MCP Server** (Node.js-based)
   - Command: `uv run node external_mcp_servers/firecrawl-mcp/dist/index.js`
   - Purpose: Web scraping and content extraction

### MCP Client Implementation

The system includes two MCP client implementations:

- **SimpleMCPClient**: On-demand connections (recommended)
- **MCPClient**: Persistent connections (experimental)

## 📊 Data Storage

### DuckDB Knowledge Base

The system uses DuckDB for its native JSON support and lightweight deployment:

```sql
-- Research tasks table
CREATE TABLE research_tasks (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Search results table
CREATE TABLE search_results (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    provider TEXT,
    query TEXT,
    results JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### File Storage

Binary files are stored on disk with metadata references in the database:
- Documents: PDF, DOCX, etc.
- Images: PNG, JPG, etc.
- Data files: CSV, JSON, etc.

## 🔄 Continuous Research

The system supports continuous research modes:

1. **One-shot Research**: Single query execution
2. **Iterative Research**: Multi-round refinement
3. **Continuous Monitoring**: Ongoing information updates
4. **Living Documents**: Auto-updating research artifacts

## 🛠️ Development

### Project Structure

```
nexus-agents/
├── src/
│   ├── orchestration/          # Core coordination layer
│   ├── research_planning/      # Topic decomposition and planning
│   ├── search_retrieval/       # Search agents and MCP integration
│   ├── summarization/          # Analysis and reasoning agents
│   ├── data_persistence/       # Knowledge base and storage
│   ├── llm/                    # Multi-provider LLM client
│   ├── config/                 # Configuration management
│   └── mcp_client_simple.py    # MCP client implementation
├── external_mcp_servers/       # External MCP server installations
├── tests/                      # Test suite
├── config/                     # Configuration files
└── requirements.txt            # Python dependencies
```

### Adding New Search Providers

1. Install the MCP server for the provider
2. Add server configuration to `SimpleMCPClient`
3. Create a new search agent in `src/search_retrieval/`
4. Update the system configuration

### Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## 📝 Current Status

### ✅ Completed Features

- **Full system architecture implemented**
- **Multi-provider LLM client with 6 providers**
- **Proper MCP integration with 4 official servers**
- **DuckDB-based knowledge base**
- **Complete agent hierarchy**
- **A2A communication infrastructure**
- **Comprehensive test suite**

### 🔄 In Progress

- **MCP client connection stability** (simplified client working)
- **Redis integration for full A2A communication**
- **End-to-end workflow testing with real API keys**

### 🎯 Next Steps

1. **Production Deployment**: Docker containerization and cloud deployment
2. **Web Interface**: React-based dashboard for research management
3. **Advanced Analytics**: Research quality metrics and insights
4. **Plugin System**: Extensible architecture for custom agents

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

For questions, issues, or contributions:

- **GitHub Issues**: [Report bugs or request features](https://github.com/trilogy-group/nexus-agents/issues)
- **Documentation**: [Full documentation](https://docs.nexus-agents.com)
- **Community**: [Join our Discord](https://discord.gg/nexus-agents)

---

**Nexus Agents** - Transforming how we conduct deep research through intelligent multi-agent collaboration.
