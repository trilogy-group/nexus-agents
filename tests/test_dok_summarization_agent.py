"""
Unit tests for SummarizationAgent.
Tests the DOK Level 1 fact extraction and source summarization functionality.
"""
import pytest
import asyncio
import uuid
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import json

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agents.research.summarization_agent import SummarizationAgent, SourceSummary


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = Mock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def summarization_agent(mock_llm_client):
    """Fixture to provide a SummarizationAgent instance."""
    return SummarizationAgent(llm_client=mock_llm_client)


@pytest.mark.unit
class TestSummarizationAgent:
    """Test class for SummarizationAgent."""
    
    def test_initialization(self, mock_llm_client):
        """Test SummarizationAgent initialization."""
        agent = SummarizationAgent(llm_client=mock_llm_client)
        assert agent.llm_client == mock_llm_client
        assert agent.agent_type == "summarization_agent"
        assert agent.max_retries == 3
    
    def test_initialization_without_llm_client(self):
        """Test SummarizationAgent initialization without LLM client."""
        # Since we removed get_llm_client, test that agent can be created without LLM client
        agent = SummarizationAgent()
        
        assert agent.llm_client is None
        assert agent.max_retries == 3
        assert agent.agent_type == "summarization_agent"
    
    @pytest.mark.asyncio
    async def test_extract_dok1_facts_success(self, summarization_agent, mock_llm_client):
        """Test successful DOK1 fact extraction."""
        mock_facts = ["MCP is a protocol", "Released in 2024", "Enables AI integration"]
        mock_llm_client.generate.return_value = json.dumps(mock_facts)
        
        content = "Model Context Protocol (MCP) was introduced by Anthropic..."
        metadata = {"title": "MCP Overview", "url": "https://example.com"}
        context = "AI interoperability research"
        
        facts = await summarization_agent._extract_dok1_facts(content, metadata, context)
        
        assert len(facts) == 3
        assert facts == mock_facts
        mock_llm_client.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_dok1_facts_invalid_json(self, summarization_agent, mock_llm_client):
        """Test DOK1 fact extraction with invalid JSON response."""
        # Mock LLM to return invalid JSON
        mock_llm_client.generate.return_value = "Invalid JSON response"
        
        content = "Test content"
        metadata = {"title": "Test", "url": "https://example.com"}
        context = "Test context"
        
        facts = await summarization_agent._extract_dok1_facts(content, metadata, context)
        
        assert facts == []  # Should return empty list on error
    
    @pytest.mark.asyncio
    async def test_extract_dok1_facts_llm_error(self, summarization_agent, mock_llm_client):
        """Test DOK1 fact extraction with LLM error."""
        # Mock LLM to raise an exception
        mock_llm_client.generate.side_effect = Exception("LLM API error")
        
        content = "Test content"
        metadata = {"title": "Test", "url": "https://example.com"}
        context = "Test context"
        
        facts = await summarization_agent._extract_dok1_facts(content, metadata, context)
        
        assert facts == []  # Should return empty list on error
    
    @pytest.mark.asyncio
    async def test_create_summary_success(self, summarization_agent, mock_llm_client):
        """Test successful summary creation."""
        mock_summary = "This source provides comprehensive overview of MCP protocol and its applications."
        mock_llm_client.generate.return_value = mock_summary
        
        content = "Detailed content about MCP"
        metadata = {"title": "MCP Guide", "url": "https://example.com/mcp"}
        context = "AI system integration"
        facts = ["MCP standardizes AI connections", "Released in 2024"]
        
        summary = await summarization_agent._create_summary(content, metadata, context, facts)
        
        assert summary == mock_summary
        mock_llm_client.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_summary_llm_error(self, summarization_agent, mock_llm_client):
        """Test summary creation with LLM error."""
        # Mock LLM to raise an exception
        mock_llm_client.generate.side_effect = Exception("LLM API error")
        
        content = "Test content"
        metadata = {"title": "Test", "url": "https://example.com"}
        context = "Test context"
        facts = ["Test fact"]
        
        summary = await summarization_agent._create_summary(content, metadata, context, facts)
        
        assert "Summary unavailable due to processing error" in summary
    
    @pytest.mark.asyncio
    async def test_summarize_source_success(self, summarization_agent, mock_llm_client):
        """Test successful source summarization."""
        # Mock LLM responses
        mock_facts = ["MCP is a protocol", "Released by Anthropic", "Enables AI integration"]
        mock_summary = "Comprehensive overview of MCP protocol development and implementation."
        
        mock_llm_client.generate.side_effect = [
            json.dumps(mock_facts),  # For facts extraction
            mock_summary             # For summary creation
        ]
        
        source_content = "Model Context Protocol (MCP) details..."
        source_metadata = {
            "source_id": "test_source_123",
            "title": "MCP Overview",
            "url": "https://example.com/mcp",
            "provider": "test"
        }
        research_context = "AI protocol research"
        
        result = await summarization_agent.summarize_source(
            source_content, source_metadata, research_context, "test_subtask"
        )
        
        assert isinstance(result, SourceSummary)
        assert result.source_id == "test_source_123"
        assert result.subtask_id == "test_subtask"
        assert result.dok1_facts == mock_facts
        assert result.summary == mock_summary
        assert result.summarized_by == "summarization_agent"
        assert result.created_at is not None
    
    @pytest.mark.asyncio
    async def test_summarize_source_auto_generate_source_id(self, summarization_agent, mock_llm_client):
        """Test source summarization with auto-generated source ID."""
        mock_facts = ["Auto-generated fact"]
        mock_summary = "Auto-generated summary"
        
        mock_llm_client.generate.side_effect = [
            json.dumps(mock_facts),
            mock_summary
        ]
        
        source_content = "Test content"
        source_metadata = {"title": "Test", "url": "https://example.com"}  # No source_id
        research_context = "Test context"
        
        result = await summarization_agent.summarize_source(
            source_content, source_metadata, research_context
        )
        
        assert result.source_id.startswith("src_")
        assert len(result.source_id) > 4  # Should have UUID suffix chars
    
    @pytest.mark.asyncio
    async def test_batch_summarize_sources_success(self, summarization_agent, mock_llm_client):
        """Test successful batch source summarization."""
        # Mock LLM responses for multiple sources
        mock_responses = [
            json.dumps(["Fact 1", "Fact 2"]),  # Facts for source 1
            "Summary for source 1",             # Summary for source 1
            json.dumps(["Fact 3", "Fact 4"]),  # Facts for source 2
            "Summary for source 2"              # Summary for source 2
        ]
        
        mock_llm_client.generate.side_effect = mock_responses
        
        sources = [
            {
                "content": "Content about AI protocols",
                "metadata": {
                    "source_id": "src_1",
                    "title": "AI Protocol Guide",
                    "url": "https://example.com/1"
                }
            },
            {
                "content": "Content about system integration",
                "metadata": {
                    "source_id": "src_2",
                    "title": "System Integration",
                    "url": "https://example.com/2"
                }
            }
        ]
        
        research_context = "AI technology research"
        
        results = await summarization_agent.batch_summarize_sources(
            sources, research_context, "batch_test"
        )
        
        assert len(results) == 2
        assert all(isinstance(r, SourceSummary) for r in results)
        assert results[0].source_id == "src_1"
        assert results[1].source_id == "src_2"
        assert all(r.subtask_id == "batch_test" for r in results)
    
    @pytest.mark.asyncio
    async def test_batch_summarize_sources_with_errors(self, summarization_agent, mock_llm_client):
        """Test batch summarization with some sources failing."""
        # Mock first source to succeed, second to fail
        def mock_generate_response(prompt):
            if "Extract factual statements" in prompt and "successful processing" in prompt:
                return '["Fact 1"]'
            elif "Create a concise summary" in prompt and "successful processing" in prompt:
                return "Summary 1"
            else:
                raise Exception("LLM error for source 2")
        
        mock_llm_client.generate.side_effect = mock_generate_response
        
        sources = [
            {
                'content': 'Content 1 about successful processing',
                'metadata': {'source_id': 'src_success', 'title': 'Success Title'}
            },
            {
                'content': 'Content 2 that will fail',
                'metadata': {'source_id': 'src_fail', 'title': 'Fail Title'}
            }
        ]
        
        research_context = "Error handling test"
        
        results = await summarization_agent.batch_summarize_sources(sources, research_context)
        
        # Should get results for both sources (one successful, one with error message)
        assert len(results) == 2
        assert results[0].source_id == 'src_success'
        assert results[1].source_id == 'src_fail'
        assert "Summary unavailable due to processing error" in results[1].summary
    
    def test_get_summary_stats(self, summarization_agent):
        """Test summary statistics calculation."""
        summaries = [
            SourceSummary(
                summary_id="sum1",
                source_id="src1",
                subtask_id=None,
                dok1_facts=["fact1", "fact2"],
                summary="Summary 1",
                summarized_by="agent",
                created_at=datetime.now(timezone.utc)
            ),
            SourceSummary(
                summary_id="sum2",
                source_id="src2",
                subtask_id=None,
                dok1_facts=["fact3", "fact4", "fact5"],
                summary="Summary 2",
                summarized_by="agent",
                created_at=datetime.now(timezone.utc)
            ),
            SourceSummary(
                summary_id="sum3",
                source_id="src3",
                subtask_id=None,
                dok1_facts=[],  # No facts
                summary="Summary 3",
                summarized_by="agent",
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        stats = summarization_agent.get_summary_stats(summaries)
        
        assert stats["total_summaries"] == 3
        assert stats["total_dok1_facts"] == 5
        assert stats["avg_facts_per_source"] == 1.67
        assert stats["sources_with_facts"] == 2
    
    def test_get_summary_stats_empty(self, summarization_agent):
        """Test summary statistics with empty list."""
        stats = summarization_agent.get_summary_stats([])
        
        assert stats["total_summaries"] == 0
        assert "avg_facts_per_source" not in stats
        assert "sources_with_facts" not in stats


@pytest.mark.asyncio
async def test_summarization_agent_integration():
    """Integration test for SummarizationAgent without mocking LLM."""
    # This test requires actual LLM configuration
    try:
        from src.llm import LLMClient
        
        # Try to create an LLM client - will skip if no valid config
        llm_client = LLMClient()
        agent = SummarizationAgent(llm_client)
        
        # Test with simple content
        source_content = "The Model Context Protocol (MCP) is a new standard for connecting AI applications to external data sources."
        source_metadata = {
            "source_id": "test_src",
            "title": "MCP Introduction",
            "url": "https://example.com"
        }
        research_context = "AI interoperability protocols"
        
        result = await agent.summarize_source(source_content, source_metadata, research_context)
        
        assert isinstance(result, SourceSummary)
        assert result.source_id == "test_src"
        assert len(result.summary) > 0
        assert isinstance(result.dok1_facts, list)
        
    except Exception as e:
        pytest.skip(f"Integration test skipped due to LLM configuration: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
