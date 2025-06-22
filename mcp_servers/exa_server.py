#!/usr/bin/env python3
"""
MCP Server for Exa Search API
"""
import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import aiohttp
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Exa Search Server")


@mcp.tool()
async def search_exa(
    query: str,
    num_results: int = 10,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    start_crawl_date: Optional[str] = None,
    end_crawl_date: Optional[str] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
    use_autoprompt: bool = True,
    type: str = "neural"
) -> Dict[str, Any]:
    """
    Search using Exa API.
    
    Args:
        query: The search query
        num_results: Number of results to return (default: 10)
        include_domains: List of domains to include
        exclude_domains: List of domains to exclude
        start_crawl_date: Start date for crawl filter (YYYY-MM-DD)
        end_crawl_date: End date for crawl filter (YYYY-MM-DD)
        start_published_date: Start date for published filter (YYYY-MM-DD)
        end_published_date: End date for published filter (YYYY-MM-DD)
        use_autoprompt: Whether to use autoprompt (default: True)
        type: Search type - "neural" or "keyword" (default: "neural")
    
    Returns:
        Dictionary containing search results
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return {"error": "EXA_API_KEY environment variable not set"}
    
    url = "https://api.exa.ai/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": query,
        "numResults": num_results,
        "useAutoprompt": use_autoprompt,
        "type": type
    }
    
    # Add optional filters
    if include_domains:
        payload["includeDomains"] = include_domains
    if exclude_domains:
        payload["excludeDomains"] = exclude_domains
    if start_crawl_date:
        payload["startCrawlDate"] = start_crawl_date
    if end_crawl_date:
        payload["endCrawlDate"] = end_crawl_date
    if start_published_date:
        payload["startPublishedDate"] = start_published_date
    if end_published_date:
        payload["endPublishedDate"] = end_published_date
    
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


@mcp.tool()
async def get_exa_contents(
    ids: List[str],
    text: bool = True,
    highlights: bool = False,
    summary: bool = False
) -> Dict[str, Any]:
    """
    Get contents for specific Exa result IDs.
    
    Args:
        ids: List of Exa result IDs
        text: Whether to include text content (default: True)
        highlights: Whether to include highlights (default: False)
        summary: Whether to include summary (default: False)
    
    Returns:
        Dictionary containing content results
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return {"error": "EXA_API_KEY environment variable not set"}
    
    url = "https://api.exa.ai/contents"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "ids": ids,
        "text": text,
        "highlights": highlights,
        "summary": summary
    }
    
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


@mcp.resource("exa://search/{query}")
async def get_search_results(query: str) -> str:
    """
    Get search results as a formatted resource.
    
    Args:
        query: The search query
    
    Returns:
        Formatted search results as text
    """
    results = await search_exa(query)
    
    if "error" in results:
        return f"Error: {results['error']}"
    
    if "results" not in results:
        return "No results found"
    
    formatted_results = []
    for i, result in enumerate(results["results"], 1):
        formatted_results.append(
            f"{i}. {result.get('title', 'No title')}\n"
            f"   URL: {result.get('url', 'No URL')}\n"
            f"   Score: {result.get('score', 'N/A')}\n"
            f"   Published: {result.get('publishedDate', 'Unknown')}\n"
        )
    
    return "\n".join(formatted_results)


if __name__ == "__main__":
    # Run the server
    mcp.run()