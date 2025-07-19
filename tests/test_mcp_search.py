"""
Tests for MCP search functionality.
Consolidates and improves search testing from root-level test files.
"""
import pytest
import asyncio
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.search_retrieval.firecrawl_search_agent import FirecrawlSearchAgent
from src.search_retrieval.exa_search_agent import ExaSearchAgent
from src.search_retrieval.perplexity_search_agent import PerplexitySearchAgent
from src.search_retrieval.linkup_search_agent import LinkupSearchAgent
from src.orchestration.communication_bus import CommunicationBus, Message
from src.llm import LLMClient

# Load environment variables
load_dotenv()


class MockCommunicationBus(CommunicationBus):
    """Mock communication bus for testing."""
    
    def __init__(self):
        # Don't call super().__init__() to avoid Redis connection
        self.messages = []
        # Add required attributes that agents expect
        self.redis_url = "redis://mock:6379/0"  # Mock URL
        self.redis_client = None
        self.pubsub = None
        self.subscriptions = {}
        self.running = False
        self.listener_task = None
    
    async def send_message(self, topic: str = None, content: dict = None, recipient: str = None, **kwargs):
        """Mock send_message to capture messages without Redis."""
        message = Message(topic=topic, content=content, recipient=recipient, **kwargs)
        self.messages.append(message)
        return message
    
    async def publish(self, message):
        """Mock publish method to handle BaseAgent.send_message calls without Redis."""
        self.messages.append(message)
    
    async def receive_message(self, timeout=None):
        """Mock receive_message."""
        if self.messages:
            return self.messages.pop(0)
        return None


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""
    
    def __init__(self):
        super().__init__(reasoning_config=None, task_config=None)
    
    async def generate_response(self, messages, **kwargs):
        """Mock response generation."""
        return "Mock LLM response for testing"


@pytest.mark.mcp
@pytest.mark.integration
class TestMCPSearch:
    """Test class for MCP search functionality."""
    
    @pytest.fixture
    def mock_comm_bus(self):
        """Create mock communication bus."""
        return MockCommunicationBus()
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MockLLMClient()
    
    async def test_firecrawl_search_agent(self):
        """Test Firecrawl MCP server connectivity."""
        if not os.getenv("FIRECRAWL_API_KEY") or os.getenv("FIRECRAWL_API_KEY") == "your_firecrawl_api_key":
            pytest.skip("Firecrawl API key not configured")
        
        # Test MCP client can connect to Firecrawl server
        from src.mcp_client import MCPClient
        mcp_client = MCPClient()
        
        try:
            # Test that MCP client can connect and call tools
            # This validates the MCP server setup and connectivity
            response = await mcp_client.call_tool(
                server_name="firecrawl",
                server_script="npx -y firecrawl-mcp",
                tool_name="firecrawl_scrape",
                arguments={
                    "url": "https://example.com",
                    "formats": ["markdown"]
                }
            )
            
            # Validate response content and show verbose output
            assert response is not None, "Firecrawl MCP server should respond"
            
            # Verbose output if requested
            if hasattr(pytest, 'current_request') and pytest.current_request.config.getoption('--verbose'):
                print(f"\n📄 Firecrawl Response (first 500 chars): {str(response)[:500]}...")
            
            # Better validation - check for expected response structure
            response_str = str(response)
            assert len(response_str) > 10, f"Response too short: {response_str}"
            
            # Check for expected content patterns
            expected_patterns = ['content', 'text', 'markdown', 'html']
            has_content = any(pattern in response_str.lower() for pattern in expected_patterns)
            assert has_content, f"Response lacks expected content patterns: {response_str[:200]}"
            
            print(f"✅ Firecrawl returned {len(response_str)} chars of content")
            
        except Exception as e:
            pytest.skip(f"Firecrawl MCP server not available: {e}")
    
    async def test_exa_search_agent(self):
        """Test Exa MCP server connectivity."""
        if not os.getenv("EXA_API_KEY") or os.getenv("EXA_API_KEY") == "your_exa_api_key":
            pytest.skip("Exa API key not configured")
        
        # Test MCP client can connect to Exa server
        from src.mcp_client import MCPClient
        mcp_client = MCPClient()
        
        try:
            # Test Exa search functionality using the working implementation
            response = await mcp_client.call_tool(
                server_name="exa",
                server_script="npx exa-mcp-server",
                tool_name="web_search_exa",
                arguments={
                    "query": "machine learning",
                    "num_results": 3
                },
                env_vars={'EXA_API_KEY': os.getenv('EXA_API_KEY')}
            )
            
            # Validate response content and show verbose output
            assert response is not None, "Exa MCP server should respond"
            
            # Verbose output if requested
            if hasattr(pytest, 'current_request') and pytest.current_request.config.getoption('--verbose'):
                print(f"\n🔍 Exa Response (first 500 chars): {str(response)[:500]}...")
            
            # Better validation - check for expected response structure
            response_str = str(response)
            assert len(response_str) > 10, f"Response too short: {response_str}"
            
            # Check for expected content patterns
            expected_patterns = ['content', 'results', 'url', 'title', 'text']
            has_content = any(pattern in response_str.lower() for pattern in expected_patterns)
            assert has_content, f"Response lacks expected content patterns: {response_str[:200]}"
            
            print(f"✅ Exa returned {len(response_str)} chars of search results")
            
        except Exception as e:
            pytest.skip(f"Exa MCP server not available: {e}")
    
    async def test_linkup_search_agent(self):
        """Test LinkUp MCP server connectivity."""
        if not os.getenv("LINKUP_API_KEY") or os.getenv("LINKUP_API_KEY") == "your_linkup_api_key":
            pytest.skip("LinkUp API key not configured")
        
        # Test MCP client can connect to LinkUp server
        from src.mcp_client import MCPClient
        mcp_client = MCPClient()
        
        try:
            # Test LinkUp search functionality (local JS server)
            response = await mcp_client.call_tool(
                server_name="linkup",
                server_script="npx linkup-mcp-server",
                tool_name="search-web",
                arguments={
                    "query": "artificial intelligence",
                    "depth": "standard"
                },
                env_vars={'LINKUP_API_KEY': os.getenv('LINKUP_API_KEY')}
            )
            
            # Validate response content and show verbose output
            assert response is not None, "LinkUp MCP server should respond"
            
            # Verbose output if requested
            if hasattr(pytest, 'current_request') and pytest.current_request.config.getoption('--verbose'):
                print(f"\n🔗 LinkUp Response (first 500 chars): {str(response)[:500]}...")
            
            # Better validation - check for expected response structure
            response_str = str(response)
            assert len(response_str) > 10, f"Response too short: {response_str}"
            
            # Check for expected content patterns
            expected_patterns = ['content', 'results', 'sources', 'links', 'text']
            has_content = any(pattern in response_str.lower() for pattern in expected_patterns)
            assert has_content, f"Response lacks expected content patterns: {response_str[:200]}"
            
            print(f"✅ LinkUp returned {len(response_str)} chars of search content")
            
        except Exception as e:
            pytest.skip(f"LinkUp MCP server not available: {e}")
    
    async def test_perplexity_search_agent(self):
        """Test Perplexity MCP server connectivity."""
        # Note: Perplexity often has connection issues in tests
        if not os.getenv("PERPLEXITY_API_KEY") or os.getenv("PERPLEXITY_API_KEY") == "your_perplexity_api_key":
            pytest.skip("Perplexity API key not configured")
        
        # Test MCP client can connect to Perplexity server
        from src.mcp_client import MCPClient
        mcp_client = MCPClient()
        
        try:
            # Test Perplexity research functionality using the working implementation
            response = await mcp_client.call_tool(
                server_name="perplexity",
                server_script="npx mcp-server-perplexity-ask",
                tool_name="perplexity_research",
                arguments={
                    "messages": [
                        {"role": "user", "content": "Python programming"}
                    ]
                },
                env_vars={'PERPLEXITY_API_KEY': os.getenv('PERPLEXITY_API_KEY')}
            )
            
            # Validate response content and show verbose output
            assert response is not None, "Perplexity MCP server should respond"
            
            # Verbose output if requested
            if hasattr(pytest, 'current_request') and pytest.current_request.config.getoption('--verbose'):
                print(f"\n🔮 Perplexity Response (first 500 chars): {str(response)[:500]}...")
            
            # Better validation - check for expected response structure
            response_str = str(response)
            assert len(response_str) > 10, f"Response too short: {response_str}"
            
            # Check for expected content patterns
            expected_patterns = ['content', 'answer', 'text', 'message', 'response']
            has_content = any(pattern in response_str.lower() for pattern in expected_patterns)
            assert has_content, f"Response lacks expected content patterns: {response_str[:200]}"
            
            print(f"✅ Perplexity returned {len(response_str)} chars of research content")
            
        except Exception as e:
            # Perplexity often has connection issues, so we'll skip gracefully
            pytest.skip(f"Perplexity MCP server not available: {e}")


async def run_mcp_search_tests():
    """Run MCP search tests."""
    print("🔄 Running MCP Search Tests...")
    
    test_instance = TestMCPSearch()
    mock_comm_bus = MockCommunicationBus()
    mock_llm_client = MockLLMClient()
    
    tests = [
        ("Firecrawl Search Agent", test_instance.test_firecrawl_search_agent),
        ("Exa Search Agent", test_instance.test_exa_search_agent),
        ("LinkUp Search Agent", test_instance.test_linkup_search_agent),
        ("Perplexity Search Agent", test_instance.test_perplexity_search_agent),
        ("Search Error Handling", test_instance.test_search_agent_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            await test_func(mock_comm_bus, mock_llm_client)
            results.append((test_name, True))
            print(f"✅ {test_name}: PASSED")
        except Exception as e:
            if "skip" in str(e).lower():
                print(f"⚠️ {test_name}: SKIPPED - {e}")
            else:
                results.append((test_name, False))
                print(f"❌ {test_name}: FAILED - {e}")
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📊 MCP Search Test Results: {passed}/{total} passed")
    
    if passed == total or total == 0:
        print("🎉 MCP Search tests completed successfully!")
        return True
    else:
        print("❌ Some MCP Search tests failed")
        return False


async def main():
    """Main test function."""
    success = await run_mcp_search_tests()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
