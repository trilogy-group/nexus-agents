"""
Search Agent for the Nexus Agents system.

This module provides a specialized agent that executes search queries
across various data sources.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.orchestration.agent_spawner import Agent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, TaskStatus


class SearchAgent(Agent):
    """
    A specialized agent that executes search queries across various data sources.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Search Agent."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.task_id = parameters.get("task_id")
        self.subtask_id = parameters.get("subtask_id")
        self.search_tools = parameters.get("search_tools", ["web_search", "document_search"])
        self.llm_client = parameters.get("llm_client")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Search Agent")
        
        if not self.task_id:
            raise ValueError("Task ID is required for Search Agent")
        
        if not self.subtask_id:
            raise ValueError("Subtask ID is required for Search Agent")
        
        if not self.llm_client:
            raise ValueError("LLM Client is required for Search Agent")
    
    async def run(self):
        """Run the agent."""
        # Get the task and subtask
        task = self.task_manager.get_task(self.task_id)
        if not task:
            print(f"Task with ID {self.task_id} not found")
            return
        
        # Update the subtask status
        self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.SEARCHING)
        
        try:
            # Get the subtask information
            subtask = self._get_subtask(task)
            if not subtask:
                print(f"Subtask with ID {self.subtask_id} not found")
                return
            
            # Extract key questions from the subtask
            key_questions = []
            if subtask.result and "key_questions" in subtask.result:
                key_questions = subtask.result["key_questions"]
            
            # Generate search queries for each key question
            search_queries = await self._generate_search_queries(subtask.description, key_questions)
            
            # Execute the search queries
            search_results = await self._execute_search_queries(search_queries)
            
            # Process the search results
            processed_results = await self._process_search_results(search_results, subtask.description)
            
            # Update the subtask result
            self.task_manager.update_subtask_result(
                task_id=self.task_id,
                subtask_id=self.subtask_id,
                result={
                    "key_questions": key_questions,
                    "search_queries": search_queries,
                    "search_results": processed_results
                }
            )
            
            # Update the subtask status
            self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.COMPLETED)
            
            # Notify that the search is complete
            await self.send_message(
                topic="search_complete",
                content={
                    "task_id": self.task_id,
                    "subtask_id": self.subtask_id,
                    "result": processed_results
                }
            )
        except Exception as e:
            # Update the subtask status
            self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.FAILED)
            
            # Send an error message
            await self.send_message(
                topic="error",
                content={"error": f"Failed to execute search: {str(e)}"}
            )
        
        # Stop the agent
        await self.stop()
    
    def _get_subtask(self, task):
        """Get the subtask from the task."""
        if not task.root_task:
            return None
        
        def find_subtask(subtask):
            if subtask.id == self.subtask_id:
                return subtask
            
            for child in subtask.children:
                result = find_subtask(child)
                if result:
                    return result
            
            return None
        
        return find_subtask(task.root_task)
    
    async def _generate_search_queries(self, description: str, key_questions: List[str]) -> List[str]:
        """
        Generate search queries based on the subtask description and key questions.
        
        Args:
            description: The description of the subtask.
            key_questions: The key questions to answer.
            
        Returns:
            A list of search queries.
        """
        # If there are no key questions, generate a query from the description
        if not key_questions:
            return [description]
        
        # Generate a search query for each key question
        search_queries = []
        for question in key_questions:
            # Construct the prompt for the LLM
            prompt = f"""
            You are a search query optimization expert. Your task is to convert a research question into an effective search query.
            
            Research Question: {question}
            Context: {description}
            
            Please generate an effective search query that will help find information to answer this research question.
            The query should be concise and use appropriate search operators (e.g., quotes for exact phrases, site: for specific websites).
            
            Return only the search query, without any explanation or additional text.
            """
            
            # Call the LLM to generate the search query
            response = await self.llm_client.generate(prompt)
            
            # Clean the response
            query = response.strip().strip('"\'')
            
            search_queries.append(query)
        
        return search_queries
    
    async def _execute_search_queries(self, search_queries: List[str]) -> List[Dict[str, Any]]:
        """
        Execute the search queries using the available search tools.
        
        Args:
            search_queries: The search queries to execute.
            
        Returns:
            A list of search results.
        """
        # Simulate search results for now
        # In a real implementation, this would call external search APIs
        search_results = []
        
        for query in search_queries:
            # Simulate web search
            if "web_search" in self.search_tools:
                web_results = await self._simulate_web_search(query)
                search_results.append({
                    "query": query,
                    "tool": "web_search",
                    "results": web_results
                })
            
            # Simulate document search
            if "document_search" in self.search_tools:
                doc_results = await self._simulate_document_search(query)
                search_results.append({
                    "query": query,
                    "tool": "document_search",
                    "results": doc_results
                })
        
        return search_results
    
    async def _simulate_web_search(self, query: str) -> List[Dict[str, Any]]:
        """Simulate a web search."""
        # In a real implementation, this would call a web search API
        return [
            {
                "title": f"Web Result 1 for {query}",
                "url": f"https://example.com/result1?q={query}",
                "snippet": f"This is a snippet of the first web result for the query '{query}'."
            },
            {
                "title": f"Web Result 2 for {query}",
                "url": f"https://example.com/result2?q={query}",
                "snippet": f"This is a snippet of the second web result for the query '{query}'."
            }
        ]
    
    async def _simulate_document_search(self, query: str) -> List[Dict[str, Any]]:
        """Simulate a document search."""
        # In a real implementation, this would search a document database
        return [
            {
                "title": f"Document 1 for {query}",
                "id": f"doc1_{query}",
                "snippet": f"This is a snippet of the first document result for the query '{query}'."
            },
            {
                "title": f"Document 2 for {query}",
                "id": f"doc2_{query}",
                "snippet": f"This is a snippet of the second document result for the query '{query}'."
            }
        ]
    
    async def _process_search_results(self, search_results: List[Dict[str, Any]], context: str) -> Dict[str, Any]:
        """
        Process the search results to extract relevant information.
        
        Args:
            search_results: The search results to process.
            context: The context of the search (subtask description).
            
        Returns:
            A dictionary containing the processed search results.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        You are a research assistant. Your task is to process search results and extract relevant information.
        
        Context: {context}
        
        Search Results:
        {json.dumps(search_results, indent=2)}
        
        Please analyze these search results and extract the most relevant information for the given context.
        Organize your response as a JSON object with the following structure:
        {{
            "summary": "A brief summary of the key findings",
            "key_points": ["Point 1", "Point 2", ...],
            "sources": [
                {{
                    "title": "Source Title",
                    "url": "Source URL",
                    "relevance": "High/Medium/Low",
                    "key_information": "Key information extracted from this source"
                }},
                ...
            ]
        }}
        """
        
        # Call the LLM to process the search results
        response = await self.llm_client.generate(prompt)
        
        # Parse the response as JSON
        try:
            processed_results = json.loads(response)
            return processed_results
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    processed_results = json.loads(json_str)
                    return processed_results
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If all else fails, return a simple dictionary
            return {
                "summary": "Failed to process search results",
                "key_points": [],
                "sources": []
            }
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        # This agent doesn't need to handle messages, as it runs once and then stops