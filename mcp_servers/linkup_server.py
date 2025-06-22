#!/usr/bin/env python3
"""
MCP Server for Linkup Search API
"""
import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import aiohttp
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Linkup Search Server")


@mcp.tool()
async def search_linkup(
    query: str,
    max_results: int = 10,
    depth: str = "standard",
    output_type: str = "searchResults"
) -> Dict[str, Any]:
    """
    Search the web using Linkup API.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 10)
        depth: Search depth - "standard" or "deep" (default: "standard")
        output_type: Type of output - "searchResults" or "sourcedAnswer" (default: "searchResults")
    
    Returns:
        Dictionary containing search results
    """
    api_key = os.getenv("LINKUP_API_KEY")
    if not api_key:
        return {"error": "LINKUP_API_KEY environment variable not set"}
    
    url = "https://api.linkup.com/v1/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "q": query,
        "depth": depth,
        "outputType": output_type
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    # Limit results if needed
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


@mcp.tool()
async def search_linkup_sourced_answer(
    query: str,
    max_results: int = 5
) -> Dict[str, Any]:
    """
    Get a sourced answer from Linkup API.
    
    Args:
        query: The search query
        max_results: Maximum number of source results (default: 5)
    
    Returns:
        Dictionary containing sourced answer and sources
    """
    return await search_linkup(
        query=query,
        max_results=max_results,
        depth="deep",
        output_type="sourcedAnswer"
    )


@mcp.resource("linkup://search/{query}")
async def get_search_results(query: str) -> str:
    """
    Get search results as a formatted resource.
    
    Args:
        query: The search query
    
    Returns:
        Formatted search results as text
    """
    results = await search_linkup(query)
    
    if "error" in results:
        return f"Error: {results['error']}"
    
    if "results" not in results:
        return "No results found"
    
    formatted_results = []
    for i, result in enumerate(results["results"], 1):
        formatted_results.append(
            f"{i}. {result.get('title', 'No title')}\n"
            f"   URL: {result.get('url', 'No URL')}\n"
            f"   Content: {result.get('content', 'No content')[:200]}...\n"
        )
    
    return "\n".join(formatted_results)


if __name__ == "__main__":
    # Run the server
    mcp.run()