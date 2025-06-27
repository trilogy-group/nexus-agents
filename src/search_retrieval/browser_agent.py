"""
Browser Agent for the Nexus Agents system.

This module provides a specialized agent capable of navigating websites
and interacting with web UIs to extract specific information.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.orchestration.agent_spawner import Agent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.orchestration.task_manager import TaskManager, TaskStatus


class BrowserAgent(Agent):
    """
    A specialized agent capable of navigating websites and interacting with web UIs
    to extract specific information.
    """
    
    def __init__(self, agent_id: str, name: str, description: str,
                 communication_bus: CommunicationBus, tools: List[str] = [],
                 parameters: Dict[str, Any] = {}):
        """Initialize the Browser Agent."""
        super().__init__(agent_id, name, description, communication_bus, tools, parameters)
        self.task_manager = parameters.get("task_manager")
        self.task_id = parameters.get("task_id")
        self.subtask_id = parameters.get("subtask_id")
        self.urls = parameters.get("urls", [])
        self.llm_client = parameters.get("llm_client")
        self.browser_client = parameters.get("browser_client")
        
        if not self.task_manager:
            raise ValueError("Task Manager is required for Browser Agent")
        
        if not self.task_id:
            raise ValueError("Task ID is required for Browser Agent")
        
        if not self.subtask_id:
            raise ValueError("Subtask ID is required for Browser Agent")
        
        if not self.llm_client:
            raise ValueError("LLM Client is required for Browser Agent")
    
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
            
            # If no URLs are provided, generate them based on the key questions
            if not self.urls:
                self.urls = await self._generate_urls(subtask.description, key_questions)
            
            # Browse the URLs and extract information
            browsing_results = await self._browse_urls(self.urls, subtask.description, key_questions)
            
            # Process the browsing results
            processed_results = await self._process_browsing_results(browsing_results, subtask.description)
            
            # Update the subtask result
            self.task_manager.update_subtask_result(
                task_id=self.task_id,
                subtask_id=self.subtask_id,
                result={
                    "key_questions": key_questions,
                    "urls": self.urls,
                    "browsing_results": processed_results
                }
            )
            
            # Update the subtask status
            self.task_manager.update_subtask_status(self.task_id, self.subtask_id, TaskStatus.COMPLETED)
            
            # Notify that the browsing is complete
            await self.send_message(
                topic="browsing_complete",
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
                content={"error": f"Failed to browse URLs: {str(e)}"}
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
    
    async def _generate_urls(self, description: str, key_questions: List[str]) -> List[str]:
        """
        Generate URLs based on the subtask description and key questions.
        
        Args:
            description: The description of the subtask.
            key_questions: The key questions to answer.
            
        Returns:
            A list of URLs.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        You are a web research expert. Your task is to generate a list of URLs that are likely to contain information
        relevant to a research topic.
        
        Research Topic: {description}
        Key Questions:
        {json.dumps(key_questions, indent=2)}
        
        Please generate a list of 3-5 URLs that are likely to contain information relevant to this research topic and key questions.
        The URLs should be specific and diverse, covering different aspects of the topic.
        
        Format your response as a JSON array of strings, e.g.:
        ["https://example.com/page1", "https://example.com/page2", ...]
        """
        
        # Call the LLM to generate the URLs
        response = await self.llm_client.generate(prompt)
        
        # Parse the response as JSON
        try:
            urls = json.loads(response)
            if isinstance(urls, list):
                return urls
        except json.JSONDecodeError:
            # If the response is not valid JSON, try to extract the JSON part
            try:
                json_start = response.find("[")
                json_end = response.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    urls = json.loads(json_str)
                    if isinstance(urls, list):
                        return urls
            except (json.JSONDecodeError, ValueError):
                pass
        
        # If all else fails, return a default URL
        return ["https://www.google.com/search?q=" + description.replace(" ", "+")]
    
    async def _browse_urls(self, urls: List[str], description: str, key_questions: List[str]) -> List[Dict[str, Any]]:
        """
        Browse the URLs and extract information.
        
        Args:
            urls: The URLs to browse.
            description: The description of the subtask.
            key_questions: The key questions to answer.
            
        Returns:
            A list of browsing results.
        """
        # If we have a browser client, use it to browse the URLs
        if self.browser_client:
            return await self._browse_with_client(urls, description, key_questions)
        
        # Otherwise, simulate browsing
        return await self._simulate_browsing(urls, description, key_questions)
    
    async def _browse_with_client(self, urls: List[str], description: str, key_questions: List[str]) -> List[Dict[str, Any]]:
        """Browse the URLs using a browser client."""
        browsing_results = []
        
        for url in urls:
            try:
                # Navigate to the URL
                await self.browser_client.goto(url)
                
                # Wait for the page to load
                await asyncio.sleep(2)
                
                # Get the page content
                content = await self.browser_client.content()
                
                # Extract information from the page
                extraction_prompt = f"""
                You are a web content extraction expert. Your task is to extract relevant information from a web page.
                
                Research Topic: {description}
                Key Questions:
                {json.dumps(key_questions, indent=2)}
                
                Web Page Content:
                {content[:10000]}  # Truncate to avoid token limits
                
                Please extract the most relevant information from this web page that helps answer the key questions.
                Format your response as a JSON object with the following structure:
                {{
                    "title": "The title of the web page",
                    "url": "{url}",
                    "relevant_sections": [
                        {{
                            "heading": "Section heading",
                            "content": "Extracted content from this section",
                            "relevance": "High/Medium/Low"
                        }},
                        ...
                    ],
                    "key_information": "A summary of the key information extracted from this page"
                }}
                """
                
                # Call the LLM to extract information
                extraction_response = await self.llm_client.generate(extraction_prompt)
                
                # Parse the response as JSON
                try:
                    extraction = json.loads(extraction_response)
                    browsing_results.append(extraction)
                except json.JSONDecodeError:
                    # If the response is not valid JSON, try to extract the JSON part
                    try:
                        json_start = extraction_response.find("{")
                        json_end = extraction_response.rfind("}") + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = extraction_response[json_start:json_end]
                            extraction = json.loads(json_str)
                            browsing_results.append(extraction)
                    except (json.JSONDecodeError, ValueError):
                        # If all else fails, add a simple result
                        browsing_results.append({
                            "title": "Failed to extract information",
                            "url": url,
                            "relevant_sections": [],
                            "key_information": "Failed to extract information from this page"
                        })
            except Exception as e:
                # If there's an error, add a simple result
                browsing_results.append({
                    "title": "Error browsing URL",
                    "url": url,
                    "relevant_sections": [],
                    "key_information": f"Error browsing URL: {str(e)}"
                })
        
        return browsing_results
    
    async def _simulate_browsing(self, urls: List[str], description: str, key_questions: List[str]) -> List[Dict[str, Any]]:
        """Simulate browsing the URLs."""
        browsing_results = []
        
        for url in urls:
            # Simulate browsing result
            browsing_results.append({
                "title": f"Simulated browsing result for {url}",
                "url": url,
                "relevant_sections": [
                    {
                        "heading": "Section 1",
                        "content": f"Simulated content for section 1 of {url}",
                        "relevance": "High"
                    },
                    {
                        "heading": "Section 2",
                        "content": f"Simulated content for section 2 of {url}",
                        "relevance": "Medium"
                    }
                ],
                "key_information": f"Simulated key information extracted from {url}"
            })
        
        return browsing_results
    
    async def _process_browsing_results(self, browsing_results: List[Dict[str, Any]], context: str) -> Dict[str, Any]:
        """
        Process the browsing results to extract relevant information.
        
        Args:
            browsing_results: The browsing results to process.
            context: The context of the browsing (subtask description).
            
        Returns:
            A dictionary containing the processed browsing results.
        """
        # Construct the prompt for the LLM
        prompt = f"""
        You are a research assistant. Your task is to process browsing results and extract relevant information.
        
        Context: {context}
        
        Browsing Results:
        {json.dumps(browsing_results, indent=2)}
        
        Please analyze these browsing results and extract the most relevant information for the given context.
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
        
        # Call the LLM to process the browsing results
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
                "summary": "Failed to process browsing results",
                "key_points": [],
                "sources": []
            }
    
    async def handle_message(self, message: Message):
        """Handle a message from the communication bus."""
        # This agent doesn't need to handle messages, as it runs once and then stops