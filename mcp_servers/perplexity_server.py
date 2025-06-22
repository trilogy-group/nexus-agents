#!/usr/bin/env python3
"""
MCP Server for Perplexity API
"""
import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import aiohttp
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Perplexity Search Server")


@mcp.tool()
async def search_perplexity(
    query: str,
    model: str = "llama-3.1-sonar-small-128k-online",
    max_tokens: int = 1000,
    temperature: float = 0.2,
    top_p: float = 0.9,
    search_domain_filter: Optional[List[str]] = None,
    return_images: bool = False,
    return_related_questions: bool = False,
    search_recency_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search using Perplexity API.
    
    Args:
        query: The search query
        model: Model to use (default: "llama-3.1-sonar-small-128k-online")
        max_tokens: Maximum tokens in response (default: 1000)
        temperature: Temperature for generation (default: 0.2)
        top_p: Top-p for generation (default: 0.9)
        search_domain_filter: List of domains to filter
        return_images: Whether to return images (default: False)
        return_related_questions: Whether to return related questions (default: False)
        search_recency_filter: Recency filter - "month", "week", "day", "hour" (optional)
    
    Returns:
        Dictionary containing search results and answer
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return {"error": "PERPLEXITY_API_KEY environment variable not set"}
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
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
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "return_citations": True,
        "return_images": return_images,
        "return_related_questions": return_related_questions
    }
    
    # Add optional filters
    if search_domain_filter:
        payload["search_domain_filter"] = search_domain_filter
    if search_recency_filter:
        payload["search_recency_filter"] = search_recency_filter
    
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


@mcp.tool()
async def ask_perplexity(
    question: str,
    model: str = "llama-3.1-sonar-large-128k-online"
) -> Dict[str, Any]:
    """
    Ask a question to Perplexity with online search.
    
    Args:
        question: The question to ask
        model: Model to use (default: "llama-3.1-sonar-large-128k-online")
    
    Returns:
        Dictionary containing the answer and citations
    """
    return await search_perplexity(
        query=question,
        model=model,
        max_tokens=2000,
        return_related_questions=True
    )


@mcp.resource("perplexity://search/{query}")
async def get_search_results(query: str) -> str:
    """
    Get search results as a formatted resource.
    
    Args:
        query: The search query
    
    Returns:
        Formatted search results as text
    """
    results = await search_perplexity(query)
    
    if "error" in results:
        return f"Error: {results['error']}"
    
    if "choices" not in results or not results["choices"]:
        return "No results found"
    
    choice = results["choices"][0]
    message = choice.get("message", {})
    content = message.get("content", "No content")
    
    formatted_result = f"Answer: {content}\n\n"
    
    # Add citations if available
    if "citations" in results:
        formatted_result += "Sources:\n"
        for i, citation in enumerate(results["citations"], 1):
            formatted_result += f"{i}. {citation}\n"
    
    # Add related questions if available
    if "related_questions" in results:
        formatted_result += "\nRelated Questions:\n"
        for question in results["related_questions"]:
            formatted_result += f"- {question}\n"
    
    return formatted_result


if __name__ == "__main__":
    # Run the server
    mcp.run()