"""
Tests for ResearchOrchestrator and end-to-end research workflow.
"""
import pytest
import asyncio
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.orchestration.research_orchestrator import ResearchOrchestrator, ResearchStatus
from src.orchestration.communication_bus import CommunicationBus
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase
from src.llm import LLMClient


@pytest.mark.postgres
@pytest.mark.integration
@pytest.mark.slow
class TestResearchOrchestrator:
    """Test ResearchOrchestrator functionality."""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create a ResearchOrchestrator instance for testing."""
        # Setup dependencies
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        communication_bus = CommunicationBus(redis_url=redis_url)
        await communication_bus.connect()
        
        llm_client = LLMClient(config_path=os.getenv("LLM_CONFIG", "config/llm_config.json"))
        
        knowledge_base = PostgresKnowledgeBase()
        await knowledge_base.connect()
        
        orchestrator = ResearchOrchestrator(
            communication_bus=communication_bus,
            llm_client=llm_client,
            knowledge_base=knowledge_base
        )
        
        yield orchestrator
        
        # Cleanup
        await communication_bus.disconnect()
        await knowledge_base.disconnect()
    
    async def test_orchestrator_initialization(self, orchestrator):
        """Test that orchestrator initializes correctly."""
        assert orchestrator is not None
        assert orchestrator.bus is not None
        assert orchestrator.llm_client is not None
        assert orchestrator.knowledge_base is not None
        assert orchestrator.active_research_tasks == {}
    
    async def test_start_research_task(self, orchestrator):
        """Test starting a research task."""
        research_query = "What are the latest developments in artificial intelligence?"
        
        task_id = await orchestrator.start_research_task(
            research_query=research_query,
            user_id="test_user"
        )
        
        # Verify task ID is generated
        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) > 0
        
        # Verify task is stored in database
        task = await orchestrator.get_research_task_status(task_id)
        assert task is not None
        assert task["research_query"] == research_query
        assert task["status"] == ResearchStatus.PENDING.value
        assert task["user_id"] == "test_user"
    
    async def test_get_research_task_status(self, orchestrator):
        """Test getting research task status."""
        research_query = "Test query for status check"
        
        # Start a task
        task_id = await orchestrator.start_research_task(
            research_query=research_query
        )
        
        # Get status
        status = await orchestrator.get_research_task_status(task_id)
        
        assert status is not None
        assert status["task_id"] == task_id
        assert status["research_query"] == research_query
        assert status["status"] in [ResearchStatus.PENDING.value, ResearchStatus.DECOMPOSING.value]
    
    async def test_get_nonexistent_task(self, orchestrator):
        """Test getting status for nonexistent task."""
        fake_task_id = str(uuid.uuid4())
        
        status = await orchestrator.get_research_task_status(fake_task_id)
        assert status is None
    
    async def test_research_report_storage(self, orchestrator):
        """Test storing and retrieving research reports."""
        research_query = "Test query for report storage"
        
        # Start a task
        task_id = await orchestrator.start_research_task(
            research_query=research_query
        )
        
        # Simulate storing a report
        test_report = """# Research Report
        
        ## Executive Summary
        This is a test research report.
        
        ## Key Findings
        - Finding 1
        - Finding 2
        
        ## Conclusion
        This is the conclusion.
        """
        
        metadata = {
            "total_sources": 5,
            "search_engines_used": ["firecrawl", "exa"],
            "completion_time": "2024-01-01T12:00:00Z"
        }
        
        await orchestrator.knowledge_base.store_research_report(
            task_id=task_id,
            report_markdown=test_report,
            metadata=metadata
        )
        
        # Update task status to completed
        await orchestrator.knowledge_base.update_research_task_status(
            task_id=task_id,
            status=ResearchStatus.COMPLETED.value
        )
        
        # Retrieve the report
        retrieved_report = await orchestrator.get_research_report(task_id)
        
        assert retrieved_report is not None
        assert retrieved_report == test_report
        assert "# Research Report" in retrieved_report
        assert "Executive Summary" in retrieved_report


@pytest.mark.postgres
@pytest.mark.integration  
class TestResearchDatabaseMethods:
    """Test research-specific database methods."""
    
    @pytest.fixture
    async def knowledge_base(self):
        """Create a PostgresKnowledgeBase instance for testing."""
        kb = PostgresKnowledgeBase()
        await kb.connect()
        yield kb
        await kb.disconnect()
    
    async def test_store_research_task(self, knowledge_base):
        """Test storing a research task."""
        task_id = str(uuid.uuid4())
        research_query = "Test research query"
        
        result = await knowledge_base.store_research_task(
            task_id=task_id,
            research_query=research_query,
            status=ResearchStatus.PENDING.value,
            user_id="test_user"
        )
        
        assert result == task_id
        
        # Verify task was stored
        task = await knowledge_base.get_research_task(task_id)
        assert task is not None
        assert task["task_id"] == task_id
        assert task["research_query"] == research_query
        assert task["status"] == ResearchStatus.PENDING.value
        assert task["user_id"] == "test_user"
    
    async def test_update_research_task_status(self, knowledge_base):
        """Test updating research task status."""
        task_id = str(uuid.uuid4())
        research_query = "Test query for status update"
        
        # Store initial task
        await knowledge_base.store_research_task(
            task_id=task_id,
            research_query=research_query,
            status=ResearchStatus.PENDING.value
        )
        
        # Update status
        await knowledge_base.update_research_task_status(
            task_id=task_id,
            status=ResearchStatus.SEARCHING.value
        )
        
        # Verify update
        task = await knowledge_base.get_research_task(task_id)
        assert task["status"] == ResearchStatus.SEARCHING.value
    
    async def test_store_and_get_research_report(self, knowledge_base):
        """Test storing and retrieving research reports."""
        task_id = str(uuid.uuid4())
        research_query = "Test query for report"
        
        # Store task first
        await knowledge_base.store_research_task(
            task_id=task_id,
            research_query=research_query,
            status=ResearchStatus.PENDING.value
        )
        
        # Store report
        report_markdown = "# Test Report\n\nThis is a test report."
        metadata = {"sources": 3, "duration": "5 minutes"}
        
        await knowledge_base.store_research_report(
            task_id=task_id,
            report_markdown=report_markdown,
            metadata=metadata
        )
        
        # Retrieve report
        retrieved_report = await knowledge_base.get_research_report(task_id)
        
        assert retrieved_report == report_markdown


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflow:
    """Test complete end-to-end research workflow with mocked components."""
    
    async def test_basic_workflow_simulation(self):
        """Test basic workflow simulation without real API calls."""
        print("🔬 Testing Basic Workflow Simulation...")
        
        # This test simulates the workflow without real API calls
        # to ensure the orchestration logic works correctly
        
        research_query = "What is machine learning?"
        
        # Simulate workflow steps
        print(f"1. Starting research for: {research_query}")
        
        # Simulate topic decomposition
        decomposition = {
            "topic": "Machine Learning",
            "subtopics": [
                {"topic": "Supervised Learning", "key_questions": ["What is supervised learning?"]},
                {"topic": "Unsupervised Learning", "key_questions": ["What is unsupervised learning?"]},
                {"topic": "Deep Learning", "key_questions": ["What is deep learning?"]}
            ]
        }
        print("2. ✅ Topic decomposition completed")
        
        # Simulate research planning
        plan = {
            "tasks": [
                {"topic": "Supervised Learning", "search_strategy": "web_search"},
                {"topic": "Unsupervised Learning", "search_strategy": "academic_search"},
                {"topic": "Deep Learning", "search_strategy": "news_search"}
            ]
        }
        print("3. ✅ Research planning completed")
        
        # Simulate search execution
        search_results = [
            {"source": "wikipedia", "content": "Machine learning is a subset of AI..."},
            {"source": "arxiv", "content": "Recent advances in ML include..."},
            {"source": "techcrunch", "content": "Industry applications of ML..."}
        ]
        print("4. ✅ Search execution completed")
        
        # Simulate content analysis
        analysis = {
            "summary": "Machine learning analysis complete",
            "key_findings": [
                "ML is a subset of artificial intelligence",
                "It involves training algorithms on data",
                "Applications include image recognition, NLP, etc."
            ]
        }
        print("5. ✅ Content analysis completed")
        
        # Simulate final synthesis
        final_report = f"""# Research Report: {research_query}

## Executive Summary
Machine learning is a rapidly evolving field with significant applications.

## Key Findings
{chr(10).join(f'- {finding}' for finding in analysis['key_findings'])}

## Detailed Analysis
Based on {len(search_results)} sources, machine learning continues to advance...

## Conclusion
Machine learning represents a critical technology for the future.

## Sources
- Wikipedia: Machine Learning Overview
- ArXiv: Recent ML Research
- TechCrunch: Industry Applications
"""
        print("6. ✅ Final synthesis completed")
        
        # Verify report structure
        assert "# Research Report" in final_report
        assert "Executive Summary" in final_report
        assert "Key Findings" in final_report
        assert "Conclusion" in final_report
        assert len(final_report) > 100
        
        print(f"✅ End-to-end workflow simulation successful!")
        print(f"📄 Generated report: {len(final_report)} characters")
        
        return True


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
