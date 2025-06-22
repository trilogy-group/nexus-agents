#!/usr/bin/env python3
"""
MCP Server for Firecrawl API
"""
import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import aiohttp
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Firecrawl Server")


@mcp.tool()
async def scrape_url(
    url: str,
    formats: List[str] = None,
    include_tags: List[str] = None,
    exclude_tags: List[str] = None,
    only_main_content: bool = True,
    wait_for: int = 0,
    timeout: int = 30000
) -> Dict[str, Any]:
    """
    Scrape a single URL using Firecrawl.
    
    Args:
        url: The URL to scrape
        formats: List of formats to extract (e.g., ["markdown", "html"])
        include_tags: HTML tags to include
        exclude_tags: HTML tags to exclude
        only_main_content: Whether to extract only main content (default: True)
        wait_for: Time to wait before scraping in milliseconds (default: 0)
        timeout: Request timeout in milliseconds (default: 30000)
    
    Returns:
        Dictionary containing scraped content
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return {"error": "FIRECRAWL_API_KEY environment variable not set"}
    
    api_url = "https://api.firecrawl.dev/v1/scrape"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": url,
        "formats": formats or ["markdown"],
        "onlyMainContent": only_main_content,
        "waitFor": wait_for,
        "timeout": timeout
    }
    
    # Add optional filters
    if include_tags:
        payload["includeTags"] = include_tags
    if exclude_tags:
        payload["excludeTags"] = exclude_tags
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
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


@mcp.tool()
async def crawl_website(
    url: str,
    max_depth: int = 2,
    limit: int = 10,
    include_paths: List[str] = None,
    exclude_paths: List[str] = None,
    formats: List[str] = None,
    only_main_content: bool = True
) -> Dict[str, Any]:
    """
    Crawl a website using Firecrawl.
    
    Args:
        url: The base URL to crawl
        max_depth: Maximum crawl depth (default: 2)
        limit: Maximum number of pages to crawl (default: 10)
        include_paths: URL patterns to include
        exclude_paths: URL patterns to exclude
        formats: List of formats to extract (e.g., ["markdown", "html"])
        only_main_content: Whether to extract only main content (default: True)
    
    Returns:
        Dictionary containing crawl job information
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return {"error": "FIRECRAWL_API_KEY environment variable not set"}
    
    api_url = "https://api.firecrawl.dev/v1/crawl"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": url,
        "maxDepth": max_depth,
        "limit": limit,
        "formats": formats or ["markdown"],
        "onlyMainContent": only_main_content
    }
    
    # Add optional filters
    if include_paths:
        payload["includePaths"] = include_paths
    if exclude_paths:
        payload["excludePaths"] = exclude_paths
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
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


@mcp.tool()
async def get_crawl_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a crawl job.
    
    Args:
        job_id: The crawl job ID
    
    Returns:
        Dictionary containing job status and results
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return {"error": "FIRECRAWL_API_KEY environment variable not set"}
    
    api_url = f"https://api.firecrawl.dev/v1/crawl/{job_id}"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
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


@mcp.resource("firecrawl://scrape/{url}")
async def get_scraped_content(url: str) -> str:
    """
    Get scraped content as a formatted resource.
    
    Args:
        url: The URL to scrape
    
    Returns:
        Scraped content as markdown text
    """
    # URL decode the parameter
    import urllib.parse
    decoded_url = urllib.parse.unquote(url)
    
    result = await scrape_url(decoded_url)
    
    if "error" in result:
        return f"Error: {result['error']}"
    
    if "data" not in result:
        return "No content found"
    
    data = result["data"]
    content = data.get("markdown", data.get("content", "No content available"))
    
    return content


if __name__ == "__main__":
    # Run the server
    mcp.run()