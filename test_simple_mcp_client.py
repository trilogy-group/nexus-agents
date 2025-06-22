#!/usr/bin/env python3
"""
Test script for Simple MCP Client implementation
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from simple_mcp_client import SimpleMCPClient, SimpleMCPSearchClient


async def test_simple_mcp_client():
    """Test Simple MCP client functionality."""
    print("Testing Simple MCP Client...")
    
    # Create search client
    search_client = SimpleMCPSearchClient()
    
    try:
        # Initialize connections
        print("Initializing Simple MCP Search Client...")
        await search_client.initialize()
        
        # Test each provider (only if API keys are available)
        
        # Test Linkup
        if os.getenv("LINKUP_API_KEY"):
            print("\nTesting Linkup search...")
            try:
                linkup_result = await search_client.search_linkup("artificial intelligence", max_results=3)
                if "error" in linkup_result:
                    print(f"Linkup error: {linkup_result['error']}")
                else:
                    print(f"✓ Linkup search successful: Found {len(linkup_result.get('results', []))} results")
            except Exception as e:
                print(f"✗ Linkup test failed: {e}")
        else:
            print("\nSkipping Linkup test (no API key)")
        
        # Test Exa
        if os.getenv("EXA_API_KEY"):
            print("\nTesting Exa search...")
            try:
                exa_result = await search_client.search_exa("machine learning", num_results=3)
                if "error" in exa_result:
                    print(f"Exa error: {exa_result['error']}")
                else:
                    print(f"✓ Exa search successful: Found {len(exa_result.get('results', []))} results")
            except Exception as e:
                print(f"✗ Exa test failed: {e}")
        else:
            print("\nSkipping Exa test (no API key)")
        
        # Test Perplexity
        if os.getenv("PERPLEXITY_API_KEY"):
            print("\nTesting Perplexity search...")
            try:
                perplexity_result = await search_client.search_perplexity("What is deep learning?")
                if "error" in perplexity_result:
                    print(f"Perplexity error: {perplexity_result['error']}")
                else:
                    print(f"✓ Perplexity search successful: Got response")
            except Exception as e:
                print(f"✗ Perplexity test failed: {e}")
        else:
            print("\nSkipping Perplexity test (no API key)")
        
        # Test Firecrawl
        if os.getenv("FIRECRAWL_API_KEY"):
            print("\nTesting Firecrawl scraping...")
            try:
                firecrawl_result = await search_client.scrape_url("https://example.com")
                if "error" in firecrawl_result:
                    print(f"Firecrawl error: {firecrawl_result['error']}")
                else:
                    print(f"✓ Firecrawl scraping successful")
            except Exception as e:
                print(f"✗ Firecrawl test failed: {e}")
        else:
            print("\nSkipping Firecrawl test (no API key)")
        
    finally:
        # Close connections
        print("\nClosing Simple MCP Search Client...")
        await search_client.close()
    
    print("Simple MCP Client test completed!")


async def test_direct_api_calls():
    """Test direct API calls without MCP wrapper."""
    print("\nTesting direct API calls...")
    
    client = SimpleMCPClient()
    
    # Test a simple call that doesn't require API keys
    print("Testing error handling for missing API keys...")
    
    # This should return an error about missing API key
    result = await client.call_tool("linkup", "search_linkup", {"query": "test"})
    if "error" in result and "API_KEY" in result["error"]:
        print("✓ Error handling works correctly for missing API keys")
    else:
        print(f"✗ Unexpected result: {result}")


if __name__ == "__main__":
    print("Starting Simple MCP Client tests...")
    
    # Test direct API calls first
    asyncio.run(test_direct_api_calls())
    
    print("\n" + "="*50 + "\n")
    
    # Test full search client
    asyncio.run(test_simple_mcp_client())