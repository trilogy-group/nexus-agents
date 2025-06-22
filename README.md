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

## Components

- **Task Manager**: Manages the overall research process, tracking the state of each task.
- **Communication Bus**: A message-passing system that enables communication between agents.
- **Agent Spawner**: Responsible for creating and managing the lifecycle of agents.
- **Topic Decomposer Agent**: A specialized agent that takes a high-level research query and breaks it down into a hierarchical tree of sub-topics.
- **Planning Module**: Sets milestones, schedules, and agent assignments based on the decomposition tree.
- **Search Agents**: A pool of specialized agents responsible for querying various data sources.
- **Browser Agent**: A specialized agent capable of navigating websites and interacting with web UIs to extract specific information.
- **Data Aggregation Service**: Collects and normalizes data from the various search agents.
- **Summarization Agents**: Transforms raw data into concise, human-readable summaries.
- **Reasoning Agents**: Performs synthesis, analysis, and evaluation of the summarized data.
- **Knowledge Base**: A persistent storage system for all research artifacts.
- **Artifact Generator**: Generates various output formats from the research data.
- **Continuous Augmentation**: Continuously updates the knowledge base and artifacts.
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
   docker-compose up -d redis mongodb
   
   # Or manually
   docker run -d -p 6379:6379 redis
   docker run -d -p 27017:27017 mongo
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
import os
from dotenv import load_dotenv
from main import NexusAgents, LLMConfig, LLMProvider

# Load environment variables
load_dotenv()

async def run_example():
    # Configure the LLM client
    reasoning_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4-turbo",
        api_key=os.environ.get("OPENAI_API_KEY"),
        max_tokens=4096,
        temperature=0.7
    )
    
    task_config = LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-haiku-20240307",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        max_tokens=2048,
        temperature=0.5
    )
    
    # Create the Nexus Agents system
    nexus = NexusAgents(
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        mongo_uri=os.environ.get("MONGO_URI", "mongodb://localhost:27017/"),
        output_dir=os.environ.get("OUTPUT_DIR", "output"),
        llm_config_path=os.environ.get("LLM_CONFIG")  # Will use the configs above if None
    )
    
    # Start the system
    await nexus.start()
    
    try:
        # Create a research task
        task_id = await nexus.create_research_task(
            title="The Impact of Artificial Intelligence on Healthcare",
            description="Research the current and potential future impacts of AI on healthcare, including diagnostics, treatment planning, drug discovery, and patient care.",
            continuous_mode=True,
            continuous_interval_hours=24
        )
        
        # Wait for the task to complete
        while True:
            status = await nexus.get_task_status(task_id)
            if status["status"] == "completed":
                print(f"Task completed! Artifacts: {status['artifacts']}")
                break
            
            print(f"Task status: {status['status']}")
            await asyncio.sleep(10)
    finally:
        # Stop the system
        await nexus.stop()

if __name__ == "__main__":
    asyncio.run(run_example())
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
