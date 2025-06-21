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

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/trilogy-group/nexus-agents.git
   cd nexus-agents
   ```

2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Start the required services:
   ```
   # Start Redis
   docker run -d -p 6379:6379 redis
   
   # Start MongoDB
   docker run -d -p 27017:27017 mongo
   ```

4. Run the system:
   ```
   python main.py
   ```

## Usage

```python
import asyncio
from main import NexusAgents

async def run_example():
    # Create the Nexus Agents system
    nexus = NexusAgents()
    
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

## License

This project is licensed under the MIT License - see the LICENSE file for details.
