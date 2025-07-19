"""
Real data integration test for end-to-end research workflow validation.

This test uses actual MCP search agents and LLM calls to validate the complete
research workflow with real data, including DOK taxonomy generation.
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.orchestration.research_orchestrator import ResearchOrchestrator
from src.orchestration.parallel_task_coordinator import ParallelTaskCoordinator
from src.agents.research.dok_workflow_orchestrator import DOKWorkflowOrchestrator
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase
from src.orchestration.rate_limiter import RateLimiter
from src.llm import LLMClient
import redis.asyncio as aioredis
import json


@pytest.mark.asyncio
@pytest.mark.real_data
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or not os.getenv("PERPLEXITY_API_KEY"),
    reason="Real API keys required for real data testing"
)
class TestRealDataIntegration:
    """Test suite for real data integration testing."""
    
    @pytest.fixture
    async def real_orchestrator(self):
        """Create a real orchestrator with actual dependencies."""
        # Create real database connection
        db = PostgresKnowledgeBase()
        await db.connect()
        
        # Create real Redis connection
        redis_client = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
        
        # Create real rate limiter
        rate_limiter = RateLimiter()
        
        # Create real task coordinator
        task_coordinator = ParallelTaskCoordinator(
            redis_client=redis_client,
            rate_limiter=rate_limiter
        )
        
        # Create real LLM client
        llm_client = LLMClient(
            config_path=os.getenv("LLM_CONFIG", "config/llm_config.json")
        )
        
        # Create real DOK workflow
        dok_workflow = DOKWorkflowOrchestrator(
            llm_client=llm_client
        )
        
        # Load real LLM config
        llm_config_path = os.getenv("LLM_CONFIG", "config/llm_config.json")
        with open(llm_config_path, 'r') as f:
            llm_config = json.load(f)
        
        # Create real orchestrator
        orchestrator = ResearchOrchestrator(
            task_coordinator=task_coordinator,
            dok_workflow=dok_workflow,
            db=db,
            llm_config=llm_config
        )
        
        yield orchestrator
        
        # Cleanup
        await redis_client.aclose()
        await db.disconnect()
    
    @pytest.fixture
    def test_tasks_to_cleanup(self):
        """Track task IDs created during testing for cleanup."""
        task_ids = []
        yield task_ids
        # Cleanup will be handled by the cleanup fixture
    
    async def test_real_analytical_report_workflow(self, real_orchestrator, test_tasks_to_cleanup):
        """Test complete analytical report workflow with real data."""
        # Use a focused, realistic research query
        research_query = "What are the latest developments in AI video generation technology in 2024?"
        
        # Create task in database
        task_id = await real_orchestrator.db.create_research_task(
            research_query=research_query,
            research_type="analytical_report",
            user_id="test_real_data"
        )
        test_tasks_to_cleanup.append(task_id)
        
        print(f"\n🔍 Starting real data test for task: {task_id}")
        print(f"📝 Query: {research_query}")
        
        # Execute the real workflow
        try:
            report = await real_orchestrator.execute_analytical_report(task_id, research_query)
            
            # Validate report structure and content
            assert report is not None
            assert isinstance(report, str)
            assert len(report) > 2000  # Should be substantial with real data
            
            # Validate expected sections are present
            assert "# Research Report" in report
            assert "## Executive Summary" in report
            assert "## Key Findings" in report
            assert "## Knowledge Tree" in report
            assert "## Critical Insights" in report
            assert "## Bibliography" in report
            
            # Validate real content indicators
            assert "AI" in report or "artificial intelligence" in report.lower()
            assert "video" in report.lower()
            assert "2024" in report
            
            # Check for real sources in bibliography
            bibliography_section = report.split("## Bibliography")[1] if "## Bibliography" in report else ""
            assert len(bibliography_section) > 100  # Should have real sources
            
            print(f"✅ Report generated successfully ({len(report)} characters)")
            print(f"📊 Report contains real data and proper structure")
            
            # Validate database storage
            stored_report = await real_orchestrator.db.get_research_report(task_id)
            assert stored_report is not None
            assert stored_report == report
            
            print(f"💾 Report successfully stored in database")
            
            # Validate task operations were recorded
            operations = await real_orchestrator.db.get_task_operations(task_id)
            assert len(operations) > 0
            print(f"📋 {len(operations)} task operations recorded")
            
            # Print sample of the report for manual validation
            print(f"\n📄 Sample of generated report:")
            print("=" * 50)
            print(report[:500] + "..." if len(report) > 500 else report)
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Real data test failed: {e}")
            raise
    
    async def test_real_dok_taxonomy_validation(self, real_orchestrator, test_tasks_to_cleanup):
        """Test DOK taxonomy generation with real data."""
        research_query = "What are the environmental impacts of electric vehicles?"
        
        # Create task in database
        task_id = await real_orchestrator.db.create_research_task(
            research_query=research_query,
            research_type="analytical_report",
            user_id="test_dok_real"
        )
        test_tasks_to_cleanup.append(task_id)
        
        print(f"\n🧠 Testing DOK taxonomy with real data for task: {task_id}")
        
        # Execute workflow
        report = await real_orchestrator.execute_analytical_report(task_id, research_query)
        
        # Validate DOK taxonomy sections
        assert "## Knowledge Tree" in report
        assert "## Critical Insights" in report
        
        # Check for DOK-specific content
        knowledge_tree_section = report.split("## Knowledge Tree")[1].split("##")[0] if "## Knowledge Tree" in report else ""
        insights_section = report.split("## Critical Insights")[1].split("##")[0] if "## Critical Insights" in report else ""
        
        assert len(knowledge_tree_section) > 200  # Should have substantial DOK1-2 content
        assert len(insights_section) > 200  # Should have substantial DOK3-4 content
        
        print(f"🧠 DOK taxonomy sections validated with real content")
        print(f"📊 Knowledge Tree: {len(knowledge_tree_section)} chars")
        print(f"💡 Insights: {len(insights_section)} chars")


@pytest.fixture(scope="session", autouse=True)
async def cleanup_test_data():
    """Clean up all test data after the session."""
    yield
    
    # Connect to database for cleanup
    db = PostgresKnowledgeBase()
    await db.connect()
    
    try:
        # Delete all test tasks and related data
        print("\n🧹 Cleaning up test data...")
        
        # Get all test tasks created by tests
        async with db.pool.acquire() as conn:
            test_tasks = await conn.fetch(
                "SELECT task_id FROM research_tasks WHERE user_id LIKE 'test_%'"
            )
        
        task_count = 0
        for task_row in test_tasks:
            task_id = task_row['task_id']
            success = await db.delete_research_task(task_id)
            if success:
                task_count += 1
        
        print(f"✅ Cleaned up {task_count} test tasks and related data")
        
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    # Run the real data tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-m", "real_data"
    ])
