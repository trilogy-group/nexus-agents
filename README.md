# Nexus Agents

A sophisticated multi-agent deep research system designed to conduct continuous, iterative, and deep research on complex topics, producing "living documents" that evolve with new information.

## Overview

Nexus Agents is a multi-agent system that leverages a hierarchical architecture to break down complex research queries into manageable sub-tasks that can be executed in parallel by specialized agents. The system is designed to be proactive, continuously monitoring information sources for updates and suggesting new research avenues.

## Architecture

The system is composed of several layers and components, each with a specific role:

1. **Orchestration & Coordination Layer**: The central nervous system of the system, responsible for task decomposition, agent management, and workflow control.
2. **Research Planning & Topic Decomposition Layer**: This layer breaks down high-level research queries into a structured plan.
3. **Parallel Search & Data Retrieval Layer**: Comprised of specialized agents that execute search queries in parallel across various data sources.
4. **Summarization & Higher-Order Reasoning Layer**: Responsible for synthesizing information, identifying insights, and evaluating the quality of data.
5. **Feedback & Iterative Refinement Layer**: This layer enables the system to learn from its operations and to continuously improve its performance.

## Multi-Agent Architecture

Nexus Agents uses a true multi-agent architecture with the following key components:

1. **Agent-to-Agent (A2A) Communication Protocol**: Agents communicate with each other using a standardized protocol that enables them to exchange messages, request services, and collaborate on tasks.

2. **Model-Context-Protocol (MCP) for Tool Use**: Agents use the Model-Context-Protocol to interact with external tools and services, such as search engines and web crawlers.

3. **Specialized Agents**: Each agent has a specific role and capabilities, and they work together to accomplish complex tasks.

## Components

- **Task Manager**: Manages the overall research process, tracking the state of each task.
- **Communication Bus**: A message-passing system that enables communication between agents using the A2A protocol.
- **Agent Spawner**: Responsible for creating and managing the lifecycle of agents.
- **Topic Decomposer Agent**: A specialized agent that takes a high-level research query and breaks it down into a hierarchical tree of sub-topics.
- **Research Planning Agent**: Creates a research plan based on a topic decomposition.
- **Search Agents**: Specialized agents for different search providers:
  - **LinkUp Search Agent**: Uses the LinkUp MCP server to perform searches.
  - **Exa Search Agent**: Uses the Exa MCP server to perform searches.
  - **Perplexity Search Agent**: Uses the Perplexity MCP server to perform searches.
  - **Firecrawl Search Agent**: Uses the Firecrawl MCP server to perform searches and crawling.
- **Summarization Agent**: Transforms raw data into concise, human-readable summaries.
- **Reasoning Agent**: Performs higher-order reasoning on summarized data.
- **Knowledge Base**: A persistent storage system using DuckDB for structured/JSON data and file system for binary files.
- **LLM Client**: A client for interacting with various language model providers, including OpenAI, Anthropic, Google, xAI, OpenRouter, and Ollama.

## LLM Configuration

The system uses two types of language models:

1. **Reasoning Model**: A more capable model used for complex tasks like planning, synthesis, and review.
2. **Task Model**: A more lightweight model used for smaller, direct tasks.

You can configure these models in the `config/llm_config.json` file:

```json
{
    "reasoning_model": {
        "provider": "openai",
        "model_name": "gpt-4-turbo",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 1.0,
        "additional_params": {
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0
        }
    },
    "task_model": {
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
        "max_tokens": 2048,
        "temperature": 0.5,
        "top_p": 1.0,
        "additional_params": {
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0
        }
    }
}
```

### Supported Providers

- **OpenAI** (`openai`): Models like GPT-4 and GPT-3.5
- **Anthropic** (`anthropic`): Claude models
- **Google** (`google`): Gemini models
- **xAI** (`xai`): Grok models
- **OpenRouter** (`openrouter`): Access to various models through OpenRouter
- **Ollama** (`ollama`): Local models served by Ollama

For local development without API keys, you can use the Ollama configuration:

```json
{
    "reasoning_model": {
        "provider": "ollama",
        "model_name": "llama3",
        "api_base": "http://localhost:11434",
        "max_tokens": 4096,
        "temperature": 0.7
    },
    "task_model": {
        "provider": "ollama",
        "model_name": "mistral",
        "api_base": "http://localhost:11434",
        "max_tokens": 2048,
        "temperature": 0.5
    }
}
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/trilogy-group/nexus-agents.git
   cd nexus-agents
   ```

2. Set up environment variables:
   ```
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Start the required services:
   ```
   # Using Docker Compose (recommended)
   docker-compose up -d redis
   
   # Or manually
   docker run -d -p 6379:6379 redis
   
   # Note: DuckDB is embedded and doesn't require a separate service
   ```

5. Run the system:
   ```
   # Using the start script
   python start.py
   
   # Or run the API and web servers separately
   python api.py --host 0.0.0.0 --port 12000
   python web/server.py --host 0.0.0.0 --port 12001
   
   # Or run just the main system
   python main.py
   ```

6. Access the web interface:
   ```
   http://localhost:12001
   ```

## Usage

### Using the API

You can interact with the system through the API:

```bash
# Create a research task
curl -X POST http://localhost:12000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Impact of Artificial Intelligence on Healthcare",
    "description": "Research the current and potential future impacts of AI on healthcare, including diagnostics, treatment planning, drug discovery, and patient care.",
    "continuous_mode": true,
    "continuous_interval_hours": 24
  }'

# Get the status of a task
curl http://localhost:12000/tasks/{task_id}
```

### Using the Python Library

```python
import asyncio
import json
import os
from dotenv import load_dotenv
from src.nexus_agents import NexusAgents
from src.orchestration.communication_bus import CommunicationBus
from src.llm import LLMClient
from src.config.search_providers import SearchProvidersConfig

# Load environment variables
load_dotenv()

async def run_example(query):
    # Load the LLM client configuration
    llm_config_path = os.environ.get("LLM_CONFIG", "config/llm_config.json")
    
    # Create the LLM client
    llm_client = LLMClient.from_config(llm_config_path)
    
    # Create the communication bus
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    communication_bus = CommunicationBus(redis_url=redis_url)
    
    # Load the search providers configuration
    search_providers_config = SearchProvidersConfig.from_env()
    
    # Get the DuckDB configuration
    duckdb_path = os.environ.get("DUCKDB_PATH", "data/nexus_agents.db")
    storage_path = os.environ.get("STORAGE_PATH", "data/storage")
    
    # Get the Neo4j configuration
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
    
    # Create the Nexus Agents system
    nexus_agents = NexusAgents(
        llm_client=llm_client,
        communication_bus=communication_bus,
        search_providers_config=search_providers_config,
        duckdb_path=duckdb_path,
        storage_path=storage_path,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password
    )
    
    # Start the system
    await nexus_agents.start()
    
    try:
        # Run the research query
        results = await nexus_agents.research(query)
        
        # Print the results
        print(f"Research ID: {results['research_id']}")
        print(f"Query: {results['query']}")
        print(f"Decomposition: {len(results['decomposition'].get('subtopics', []))} subtopics")
        print(f"Plan: {len(results['plan'].get('tasks', []))} tasks")
        print(f"Results: {len(results['results'])} task results")
        
        # Save the results to a file
        output_path = f"output/{results['research_id']}.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {output_path}")
        
        return results
    finally:
        # Stop the system
        await nexus_agents.stop()

if __name__ == "__main__":
    query = "The Impact of Artificial Intelligence on Healthcare"
    asyncio.run(run_example(query))
```

### Using the Web Interface

1. Start the system using the start script:
   ```
   python start.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:12001
   ```

3. Use the web interface to create and monitor research tasks.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
