"""
Integration tests for Enhanced Research Orchestrator with DOK taxonomy and real MCP search agents.
"""
import pytest
import asyncio
import os
import sys
import uuid
import json
import redis.asyncio as redis
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.orchestration.research_orchestrator import ResearchOrchestrator
from src.orchestration.research_orchestrator import ResearchStatus
from src.orchestration.communication_bus import CommunicationBus
from src.orchestration.parallel_task_coordinator import ParallelTaskCoordinator
from src.orchestration.rate_limiter import RateLimiter
from src.agents.research.dok_workflow_orchestrator import DOKWorkflowOrchestrator
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase
from src.llm import LLMClient


@pytest.mark.postgres
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestEnhancedOrchestratorIntegration:
    """Test Enhanced Research Orchestrator with real MCP search agents and DOK taxonomy."""
    
    @pytest.fixture
    async def test_knowledge_base(self):
        """Create a test PostgreSQL Knowledge Base."""
        kb = PostgresKnowledgeBase(storage_path="data/test_storage")
        await kb.connect()
        yield kb
        await kb.disconnect()
    
    @pytest.fixture
    async def enhanced_orchestrator(self, test_knowledge_base):
        """Create an Enhanced Research Orchestrator instance for testing."""
        # Setup dependencies
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = await redis.from_url(redis_url)
        
        llm_client = LLMClient(config_path=os.getenv("LLM_CONFIG", "config/llm_config.json"))
        
        # Create RateLimiter
        rate_limiter = RateLimiter()
        
        # Create ParallelTaskCoordinator
        task_coordinator = ParallelTaskCoordinator(
            redis_client=redis_client,
            rate_limiter=rate_limiter
        )
        
        # Create DOKWorkflowOrchestrator
        dok_workflow = DOKWorkflowOrchestrator(
            llm_client=llm_client
        )
        
        # Load LLM config
        import json
        llm_config_path = os.getenv("LLM_CONFIG", "config/llm_config.json")
        with open(llm_config_path, 'r') as f:
            llm_config = json.load(f)
        
        orchestrator = ResearchOrchestrator(
            task_coordinator=task_coordinator,
            dok_workflow=dok_workflow,
            db=test_knowledge_base,
            llm_config=llm_config
        )
        
        yield orchestrator
        
        # Cleanup
        await redis_client.aclose()
    
    @pytest.mark.skipif(
        not all([
            os.getenv("FIRECRAWL_API_KEY"),
            os.getenv("EXA_API_KEY"),
            os.getenv("LINKUP_API_KEY"),
            os.getenv("PERPLEXITY_API_KEY")
        ]),
        reason="Skipping live MCP test - API keys not configured"
    )
    async def test_full_dok_workflow_with_real_search(self, enhanced_orchestrator):
        """Test complete DOK taxonomy workflow with real MCP search agents."""
        # Create research task
        task_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Use a specific research query that should yield good results
        research_query = "What are the latest breakthroughs in quantum computing hardware in 2024?"
        
        # Execute research workflow
        result = await enhanced_orchestrator.execute_analytical_research(
            task_id=task_id,
            research_query=research_query,
            user_id=user_id,
            max_iterations=2  # Limit iterations for test
        )
        
        # Basic validation
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 1000  # Should have substantial content
        
        # Validate report contains all DOK taxonomy sections
        report_content = result
        
        # Check for main sections
        assert "# Research Report:" in report_content
        assert "## Executive Summary" in report_content
        assert "## Key Findings" in report_content
        assert "## Knowledge Tree" in report_content
        assert "## Critical Insights" in report_content
        assert "## Bibliography" in report_content
        assert "## Appendix: Source Summaries" in report_content
        
        # Check for DOK-specific content
        assert "### Category:" in report_content  # Knowledge tree categories
        assert "Confidence:" in report_content  # Insights confidence scores
        assert "### Truths" in report_content or "## Truths" in report_content
        assert "### Myths" in report_content or "## Myths" in report_content
        
        # Validate bibliography format
        assert "- **" in report_content  # Bibliography entries
        assert "URL:" in report_content  # Source URLs
        assert "Provider:" in report_content  # Search providers
        
        # Validate source summaries appendix
        assert "Summary:" in report_content
        assert not "No source summaries available" in report_content
        
        # Save report for manual inspection
        test_report_path = f"test_output/dok_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        os.makedirs("test_output", exist_ok=True)
        with open(test_report_path, "w") as f:
            f.write(report_content)
        
        print(f"\n✅ DOK taxonomy report saved to: {test_report_path}")
        print(f"   Report length: {len(report_content)} characters")
    
    async def test_dok_workflow_with_mock_search(self, enhanced_orchestrator, monkeypatch):
        """Test DOK taxonomy workflow with mocked search agents for CI/CD."""
        # Mock the search agent calls
        mock_search_results = [
            {
                "title": "Quantum Computing Hardware Breakthrough 2024",
                "url": "https://example.com/quantum-breakthrough",
                "snippet": "Researchers at MIT have achieved a significant milestone in quantum computing...",
                "provider": "test_search"
            },
            {
                "title": "Google's Quantum Supremacy Update",
                "url": "https://example.com/google-quantum",
                "snippet": "Google's latest quantum processor demonstrates error rates below the threshold...",
                "provider": "test_search"
            }
        ]
        
        async def mock_search_agent_execute(*args, **kwargs):
            return {
                "results": mock_search_results,
                "status": "success"
            }
        
        # Monkey patch search agent methods
        for agent_name in ["exa_agent", "linkup_agent", "perplexity_agent", "firecrawl_agent"]:
            if hasattr(enhanced_orchestrator, agent_name):
                agent = getattr(enhanced_orchestrator, agent_name)
                if agent:
                    monkeypatch.setattr(agent, "execute", mock_search_agent_execute)
        
        # Create research task
        user_id = str(uuid.uuid4())
        research_query = "Quantum computing hardware breakthroughs 2024"
        
        # Create the research task in database first
        task_id = await enhanced_orchestrator.db.create_research_task(
            research_query=research_query,
            research_type="Analytical Report",
            user_id=user_id
        )
        
        # Execute research workflow
        result = await enhanced_orchestrator.execute_analytical_report(
            task_id=task_id,
            query=research_query
        )
        
        # Basic validation
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 1000  # Should have substantial content
        
        # Validate DOK sections exist
        assert "## Knowledge Tree" in result
        assert "## Critical Insights" in result
        assert "## Bibliography" in result
    
    async def test_dok_database_persistence(self, enhanced_orchestrator, test_knowledge_base):
        """Test that DOK taxonomy data is properly persisted in the database."""
        # Create a task
        task_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        research_query = "Test DOK persistence"
        
        # Mock search results
        async def mock_search_agent_execute(*args, **kwargs):
            return {
                "results": [{
                    "title": "Test Source",
                    "url": "https://example.com/test",
                    "snippet": "Test content for DOK persistence",
                    "provider": "test"
                }],
                "status": "success"
            }
        
        # Execute workflow with mocked search
        for agent_name in ["exa_agent", "linkup_agent", "perplexity_agent", "firecrawl_agent"]:
            if hasattr(enhanced_orchestrator, agent_name):
                agent = getattr(enhanced_orchestrator, agent_name)
                if agent:
                    agent.execute = mock_search_agent_execute
        
        result = await enhanced_orchestrator.execute_analytical_research(
            task_id=task_id,
            research_query=research_query,
            user_id=user_id,
            max_iterations=1
        )
        
        assert result.status == ResearchStatus.COMPLETED
        
        # Verify data persistence (use the same knowledge base instance)
        knowledge_base = test_knowledge_base
        
        # Check knowledge tree was stored
        knowledge_tree = await knowledge_base.get_knowledge_tree(task_id)
        assert knowledge_tree is not None
        assert len(knowledge_tree) > 0
        
        # Check insights were stored
        insights = await knowledge_base.get_insights_by_task(task_id)
        assert insights is not None
        assert len(insights) > 0
        
        # Check spiky POVs were stored
        spiky_povs = await knowledge_base.get_spiky_povs_by_task(task_id)
        assert spiky_povs is not None
        assert len(spiky_povs) >= 2  # At least 1 truth and 1 myth
        
        # Check report was stored
        report = await knowledge_base.get_research_report(task_id)
        assert report is not None
        assert len(report.content) > 1000
    
    async def test_error_handling_in_dok_workflow(self, enhanced_orchestrator):
        """Test error handling in DOK taxonomy workflow."""
        # Create task with intentionally problematic query
        task_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        research_query = ""  # Empty query should be handled gracefully
        
        # Execute workflow
        result = await enhanced_orchestrator.execute_analytical_research(
            task_id=task_id,
            research_query=research_query,
            user_id=user_id,
            max_iterations=1
        )
        
        # Should handle error gracefully
        assert result is not None
        assert result.status in [ResearchStatus.FAILED, ResearchStatus.COMPLETED]
        
        # If failed, should have error message
        if result.status == ResearchStatus.FAILED:
            assert result.error is not None
    
    async def test_concurrent_dok_workflows(self, enhanced_orchestrator):
        """Test running multiple DOK workflows concurrently."""
        # Create multiple tasks
        tasks = []
        for i in range(3):
            task_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            research_query = f"Quantum computing test query {i}"
            
            task = enhanced_orchestrator.execute_analytical_research(
                task_id=task_id,
                research_query=research_query,
                user_id=user_id,
                max_iterations=1
            )
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result.status == ResearchStatus.COMPLETED
            assert result.report is not None


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s", "-k", "test_dok"])
