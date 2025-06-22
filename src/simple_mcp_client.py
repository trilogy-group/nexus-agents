"""
Simple MCP Client that uses subprocess to communicate with MCP servers
"""
import asyncio
import json
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
from pathlib import Path


class SimpleMCPClient:
    """Simple MCP client that uses subprocess to communicate with servers."""
    
    def __init__(self):
        self.server_configs = {
            "linkup": {
                "script": "mcp_servers/linkup_server.py",
                "tools": ["search_linkup", "search_linkup_sourced_answer"]
            },
            "exa": {
                "script": "mcp_servers/exa_server.py", 
                "tools": ["search_exa", "get_exa_contents"]
            },
            "perplexity": {
                "script": "mcp_servers/perplexity_server.py",
                "tools": ["search_perplexity", "ask_perplexity"]
            },
            "firecrawl": {
                "script": "mcp_servers/firecrawl_server.py",
                "tools": ["scrape_url", "crawl_website", "get_crawl_status"]
            }
        }
    
    async def call_tool(self, provider: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on an MCP server using direct API calls.
        
        Args:
            provider: The provider name (linkup, exa, perplexity, firecrawl)
            tool_name: The tool to call
            arguments: Arguments for the tool
        
        Returns:
            Tool result
        """
        if provider == "linkup":
            return await self._call_linkup_tool(tool_name, arguments)
        elif provider == "exa":
            return await self._call_exa_tool(tool_name, arguments)
        elif provider == "perplexity":
            return await self._call_perplexity_tool(tool_name, arguments)
        elif provider == "firecrawl":
            return await self._call_firecrawl_tool(tool_name, arguments)
        else:
            return {"error": f"Unknown provider: {provider}"}
    
    async def _call_linkup_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call Linkup API directly."""
        import os
        import aiohttp
        
        api_key = os.getenv("LINKUP_API_KEY")
        if not api_key:
            return {"error": "LINKUP_API_KEY environment variable not set"}
        
        if tool_name == "search_linkup":
            url = "https://api.linkup.com/v1/search"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": arguments.get("query"),
                "depth": arguments.get("depth", "standard"),
                "outputType": arguments.get("output_type", "searchResults")
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            max_results = arguments.get("max_results", 10)
                            if "results" in data and len(data["results"]) > max_results:
                                data["results"] = data["results"][:max_results]
                            return data
                        else:
                            error_text = await response.text()
                            return {
                                "error": f"Linkup API error: {response.status}",
                                "details": error_text
                            }
            except Exception as e:
                return {"error": f"Request failed: {str(e)}"}
        
        return {"error": f"Unknown Linkup tool: {tool_name}"}
    
    async def _call_exa_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call Exa API directly."""
        import os
        import aiohttp
        
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            return {"error": "EXA_API_KEY environment variable not set"}
        
        if tool_name == "search_exa":
            url = "https://api.exa.ai/search"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "query": arguments.get("query"),
                "numResults": arguments.get("num_results", 10),
                "useAutoprompt": arguments.get("use_autoprompt", True),
                "type": arguments.get("type", "neural")
            }
            
            # Add optional filters
            for key in ["include_domains", "exclude_domains", "start_crawl_date", 
                       "end_crawl_date", "start_published_date", "end_published_date"]:
                if key in arguments:
                    # Convert snake_case to camelCase
                    camel_key = ''.join(word.capitalize() if i > 0 else word 
                                      for i, word in enumerate(key.split('_')))
                    payload[camel_key] = arguments[key]
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=payload) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            return {
                                "error": f"Exa API error: {response.status}",
                                "details": error_text
                            }
            except Exception as e:
                return {"error": f"Request failed: {str(e)}"}
        
        return {"error": f"Unknown Exa tool: {tool_name}"}
    
    async def _call_perplexity_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call Perplexity API directly."""
        import os
        import aiohttp
        
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            return {"error": "PERPLEXITY_API_KEY environment variable not set"}
        
        if tool_name in ["search_perplexity", "ask_perplexity"]:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            query = arguments.get("query") or arguments.get("question")
            model = arguments.get("model", "llama-3.1-sonar-small-128k-online")
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Be precise and concise. Provide factual information with sources."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": arguments.get("max_tokens", 1000),
                "temperature": arguments.get("temperature", 0.2),
                "top_p": arguments.get("top_p", 0.9),
                "return_citations": True,
                "return_images": arguments.get("return_images", False),
                "return_related_questions": arguments.get("return_related_questions", False)
            }
            
            # Add optional filters
            if "search_domain_filter" in arguments:
                payload["search_domain_filter"] = arguments["search_domain_filter"]
            if "search_recency_filter" in arguments:
                payload["search_recency_filter"] = arguments["search_recency_filter"]
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=payload) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            return {
                                "error": f"Perplexity API error: {response.status}",
                                "details": error_text
                            }
            except Exception as e:
                return {"error": f"Request failed: {str(e)}"}
        
        return {"error": f"Unknown Perplexity tool: {tool_name}"}
    
    async def _call_firecrawl_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call Firecrawl API directly."""
        import os
        import aiohttp
        
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return {"error": "FIRECRAWL_API_KEY environment variable not set"}
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        if tool_name == "scrape_url":
            url = "https://api.firecrawl.dev/v1/scrape"
            payload = {
                "url": arguments.get("url"),
                "formats": arguments.get("formats", ["markdown"]),
                "onlyMainContent": arguments.get("only_main_content", True),
                "waitFor": arguments.get("wait_for", 0),
                "timeout": arguments.get("timeout", 30000)
            }
            
            # Add optional filters
            if "include_tags" in arguments:
                payload["includeTags"] = arguments["include_tags"]
            if "exclude_tags" in arguments:
                payload["excludeTags"] = arguments["exclude_tags"]
        
        elif tool_name == "crawl_website":
            url = "https://api.firecrawl.dev/v1/crawl"
            payload = {
                "url": arguments.get("url"),
                "maxDepth": arguments.get("max_depth", 2),
                "limit": arguments.get("limit", 10),
                "formats": arguments.get("formats", ["markdown"]),
                "onlyMainContent": arguments.get("only_main_content", True)
            }
            
            # Add optional filters
            if "include_paths" in arguments:
                payload["includePaths"] = arguments["include_paths"]
            if "exclude_paths" in arguments:
                payload["excludePaths"] = arguments["exclude_paths"]
        
        elif tool_name == "get_crawl_status":
            job_id = arguments.get("job_id")
            url = f"https://api.firecrawl.dev/v1/crawl/{job_id}"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            return {
                                "error": f"Firecrawl API error: {response.status}",
                                "details": error_text
                            }
            except Exception as e:
                return {"error": f"Request failed: {str(e)}"}
        
        else:
            return {"error": f"Unknown Firecrawl tool: {tool_name}"}
        
        # For scrape_url and crawl_website
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"Firecrawl API error: {response.status}",
                            "details": error_text
                        }
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}


class SimpleMCPSearchClient:
    """High-level client for search operations using simple MCP client."""
    
    def __init__(self):
        self.mcp_client = SimpleMCPClient()
    
    async def initialize(self):
        """Initialize the client (no-op for simple client)."""
        print("Simple MCP Search Client initialized")
    
    async def search_linkup(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search using Linkup."""
        return await self.mcp_client.call_tool(
            "linkup",
            "search_linkup",
            {"query": query, "max_results": max_results}
        )
    
    async def search_exa(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Search using Exa."""
        return await self.mcp_client.call_tool(
            "exa",
            "search_exa",
            {"query": query, "num_results": num_results}
        )
    
    async def search_perplexity(self, query: str) -> Dict[str, Any]:
        """Search using Perplexity."""
        return await self.mcp_client.call_tool(
            "perplexity",
            "search_perplexity",
            {"query": query}
        )
    
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a URL using Firecrawl."""
        return await self.mcp_client.call_tool(
            "firecrawl",
            "scrape_url",
            {"url": url}
        )
    
    async def crawl_website(self, url: str, max_depth: int = 2, limit: int = 10) -> Dict[str, Any]:
        """Crawl a website using Firecrawl."""
        return await self.mcp_client.call_tool(
            "firecrawl",
            "crawl_website",
            {"url": url, "max_depth": max_depth, "limit": limit}
        )
    
    async def close(self):
        """Close the client (no-op for simple client)."""
        print("Simple MCP Search Client closed")