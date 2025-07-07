"""
Integration tests for DOKTaxonomyRepository.
Tests the database access layer for DOK taxonomy tables.
"""
import pytest
import asyncio
import uuid
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone
from unittest.mock import Mock

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.database.dok_taxonomy_repository import DOKTaxonomyRepository
from src.agents.research.summarization_agent import SourceSummary
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase

# Load environment variables
load_dotenv()


@pytest.fixture
async def dok_repository(test_knowledge_base):
    """Fixture to provide a DOKTaxonomyRepository instance."""
    repo = DOKTaxonomyRepository()
    # Share the connection pool from test_knowledge_base to avoid exhaustion
    repo.knowledge_base = test_knowledge_base
    yield repo
    # Cleanup is handled by the shared knowledge base fixture


@pytest.fixture
async def test_knowledge_base():
    """Fixture to provide a test PostgreSQL Knowledge Base."""
    kb = PostgresKnowledgeBase(storage_path="data/test_storage")
    await kb.connect()
    yield kb
    await kb.disconnect()


@pytest.fixture
def sample_source_summary():
    """Fixture providing a sample SourceSummary for testing."""
    return SourceSummary(
        summary_id=f"test_summary_{uuid.uuid4().hex[:8]}",
        source_id=f"test_source_{uuid.uuid4().hex[:8]}",
        subtask_id=f"test_subtask_{uuid.uuid4().hex[:8]}",
        dok1_facts=[
            "MCP introduced by Anthropic in late 2024",
            "Uses JSON-based message protocol",
            "Aims to standardize AI-data connections"
        ],
        summary="This source provides an overview of the Model Context Protocol.",
        summarized_by="test_summarization_agent",
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
async def test_task_data(test_knowledge_base):
    """Fixture providing test task data."""
    task_id = f"test_task_{uuid.uuid4().hex[:8]}"
    
    # Create test task
    await test_knowledge_base.create_task(
        task_id=task_id,
        query="Test AI interoperability research",
        title="Test Research Task",
        description="Test task for DOK taxonomy repository"
    )
    
    # Create test subtask
    subtask_id = f"test_subtask_{uuid.uuid4().hex[:8]}"
    await test_knowledge_base.create_research_subtask(
        subtask_id=subtask_id,
        task_id=task_id,
        topic="AI Protocol Testing",
        description="Testing DOK taxonomy integration"
    )
    
    # Create test source
    source_id = f"test_source_{uuid.uuid4().hex[:8]}"
    await test_knowledge_base.create_source(
        source_id=source_id,
        url="https://example.com/test",
        title="Test Source",
        description="Test source for DOK taxonomy",
        source_type="web",
        provider="test"
    )
    
    return {
        "task_id": task_id,
        "subtask_id": subtask_id,
        "source_id": source_id
    }


@pytest.mark.integration
@pytest.mark.postgres
class TestDOKTaxonomyRepository:
    """Integration tests for DOKTaxonomyRepository."""
    
    async def test_store_and_retrieve_source_summary(self, dok_repository, test_task_data):
        """Test storing and retrieving source summaries."""
        # Create source summary using the source_id from test_task_data
        source_summary = SourceSummary(
            summary_id=f"test_summary_{uuid.uuid4().hex[:8]}",
            source_id=test_task_data["source_id"],
            subtask_id=test_task_data["subtask_id"],
            dok1_facts=[
                "MCP introduced by Anthropic in late 2024",
                "Uses JSON-based message protocol",
                "Aims to standardize AI-data connections"
            ],
            summary="This source provides an overview of the Model Context Protocol.",
            summarized_by="test_summarization_agent",
            created_at=datetime.now(timezone.utc)
        )
        
        # Store source summary
        success = await dok_repository.store_source_summary(source_summary)
        assert success, "Should successfully store source summary"
        
        # Note: We can't directly retrieve by summary_id without a task relationship
        # This test validates the storage operation
    
    async def test_store_source_summary_duplicate(self, dok_repository, test_task_data):
        """Test storing duplicate source summaries (should update)."""
        # Create source summary using the source_id from test_task_data
        source_summary = SourceSummary(
            summary_id=f"test_summary_{uuid.uuid4().hex[:8]}",
            source_id=test_task_data["source_id"],
            subtask_id=test_task_data["subtask_id"],
            dok1_facts=["Test fact 1", "Test fact 2"],
            summary="Test summary for duplicate test",
            summarized_by="test_summarization_agent",
            created_at=datetime.now(timezone.utc)
        )
        
        # Store first time
        success1 = await dok_repository.store_source_summary(source_summary)
        assert success1
        
        # Store again (should update)
        success2 = await dok_repository.store_source_summary(source_summary)
        assert success2
    
    async def test_create_knowledge_node(self, dok_repository, test_task_data):
        """Test creating knowledge nodes."""
        task_id = test_task_data["task_id"]
        
        # Create root knowledge node
        node_id = await dok_repository.create_knowledge_node(
            task_id=task_id,
            category="AI Interoperability",
            summary="Overview of AI interoperability protocols and standards",
            dok_level=2
        )
        
        assert node_id is not None
        assert node_id.startswith("node_")
        
        # Create child knowledge node
        child_node_id = await dok_repository.create_knowledge_node(
            task_id=task_id,
            category="Model Context Protocol",
            summary="Specific protocol for AI-data connections",
            dok_level=2,
            subcategory="Communication Protocols",
            parent_id=node_id
        )
        
        assert child_node_id is not None
        assert child_node_id != node_id
    
    async def test_link_sources_to_knowledge_node(self, dok_repository, test_task_data, test_knowledge_base):
        """Test linking sources to knowledge nodes."""
        task_id = test_task_data["task_id"]
        source_id = test_task_data["source_id"]
        
        node_id = await dok_repository.create_knowledge_node(
            task_id=task_id,
            category="Test Category",
            summary="Test summary",
            dok_level=2
        )
        
        # Create additional source
        additional_source_id = f"additional_source_{uuid.uuid4().hex[:8]}"
        await test_knowledge_base.create_source(
            source_id=additional_source_id,
            url="https://example.com/additional",
            title="Additional Test Source",
            description="Additional source for linking test",
            source_type="web",
            provider="test"
        )
        
        # Link sources to node
        source_ids = [source_id, additional_source_id]
        relevance_scores = [0.9, 0.7]
        
        success = await dok_repository.link_sources_to_knowledge_node(
            node_id, source_ids, relevance_scores
        )
        assert success
    
    async def test_link_sources_empty_list(self, dok_repository, test_task_data):
        """Test linking empty source list (should succeed)."""
        task_id = test_task_data["task_id"]
        
        node_id = await dok_repository.create_knowledge_node(
            task_id=task_id,
            category="Empty Test",
            summary="Test with no sources",
            dok_level=2
        )
        
        success = await dok_repository.link_sources_to_knowledge_node(node_id, [])
        assert success
    
    async def test_get_knowledge_tree(self, dok_repository, test_task_data):
        """Test retrieving knowledge tree."""
        task_id = test_task_data["task_id"]
        
        # Create hierarchical knowledge nodes
        root_id = await dok_repository.create_knowledge_node(
            task_id=task_id,
            category="Root Category",
            summary="Root level knowledge",
            dok_level=1
        )
        
        child_id = await dok_repository.create_knowledge_node(
            task_id=task_id,
            category="Child Category",
            summary="Child level knowledge",
            dok_level=2,
            parent_id=root_id
        )
        
        # Retrieve knowledge tree
        tree = await dok_repository.get_knowledge_tree(task_id)
        
        assert len(tree) >= 2
        # Verify hierarchical structure
        root_nodes = [node for node in tree if node['parent_id'] is None]
        child_nodes = [node for node in tree if node['parent_id'] is not None]
        
        assert len(root_nodes) >= 1
        assert len(child_nodes) >= 1
    
    async def test_create_insight(self, dok_repository, test_task_data):
        """Test creating insights."""
        task_id = test_task_data["task_id"]
        source_id = test_task_data["source_id"]
        
        insight_id = await dok_repository.create_insight(
            task_id=task_id,
            category="AI Protocol Analysis",
            insight_text="MCP represents a significant advancement in AI interoperability standards.",
            source_ids=[source_id],
            confidence_score=0.85
        )
        
        assert insight_id is not None
        assert insight_id.startswith("insight_")
    
    async def test_create_insight_multiple_sources(self, dok_repository, test_task_data, test_knowledge_base):
        """Test creating insights with multiple sources."""
        task_id = test_task_data["task_id"]
        
        # Create additional sources
        source2_id = f"source2_{uuid.uuid4().hex[:8]}"
        source3_id = f"source3_{uuid.uuid4().hex[:8]}"
        
        await test_knowledge_base.create_source(
            source_id=source2_id,
            url="https://example.com/source2",
            title="Test Source 2",
            description="Second test source for insights",
            source_type="web",
            provider="test"
        )
        
        await test_knowledge_base.create_source(
            source_id=source3_id,
            url="https://example.com/source3",
            title="Test Source 3",
            description="Third test source for insights",
            source_type="web",
            provider="test"
        )
        
        source_ids = [
            test_task_data["source_id"],
            source2_id,
            source3_id
        ]
        
        insight_id = await dok_repository.create_insight(
            task_id=task_id,
            category="Multi-Source Analysis",
            insight_text="Analysis across multiple sources reveals consistent patterns.",
            source_ids=source_ids,
            confidence_score=0.92
        )
        
        assert insight_id is not None
    
    async def test_get_insights_by_task(self, dok_repository, test_task_data):
        """Test retrieving insights by task."""
        task_id = test_task_data["task_id"]
        source_id = test_task_data["source_id"]
        
        # Create multiple insights
        insight1_id = await dok_repository.create_insight(
            task_id=task_id,
            category="Category 1",
            insight_text="First insight",
            source_ids=[source_id]
        )
        
        insight2_id = await dok_repository.create_insight(
            task_id=task_id,
            category="Category 2",
            insight_text="Second insight",
            source_ids=[source_id]
        )
        
        # Retrieve insights
        insights = await dok_repository.get_insights_by_task(task_id)
        
        assert len(insights) >= 2
        insight_ids = [insight['insight_id'] for insight in insights]
        assert insight1_id in insight_ids
        assert insight2_id in insight_ids
    
    async def test_create_spiky_pov(self, dok_repository, test_task_data):
        """Test creating spiky POVs."""
        task_id = test_task_data["task_id"]
        source_id = test_task_data["source_id"]
        
        # Create insight first
        insight_id = await dok_repository.create_insight(
            task_id=task_id,
            category="Test Category",
            insight_text="Test insight for POV",
            source_ids=[source_id]
        )
        
        # Create truth POV
        truth_pov_id = await dok_repository.create_spiky_pov(
            task_id=task_id,
            pov_type="truth",
            statement="AI interoperability will be the defining factor for AI adoption success.",
            reasoning="Based on historical technology adoption patterns and current market fragmentation.",
            insight_ids=[insight_id]
        )
        
        assert truth_pov_id is not None
        assert truth_pov_id.startswith("pov_")
        
        # Create myth POV
        myth_pov_id = await dok_repository.create_spiky_pov(
            task_id=task_id,
            pov_type="myth",
            statement="AI agents will naturally figure out how to collaborate without explicit protocols.",
            reasoning="This contradicts evidence showing the need for standardized communication protocols.",
            insight_ids=[insight_id]
        )
        
        assert myth_pov_id is not None
        assert myth_pov_id != truth_pov_id
    
    async def test_get_spiky_povs_by_task(self, dok_repository, test_task_data):
        """Test retrieving spiky POVs by task."""
        task_id = test_task_data["task_id"]
        source_id = test_task_data["source_id"]
        
        # Create insight
        insight_id = await dok_repository.create_insight(
            task_id=task_id,
            category="Test Category",
            insight_text="Test insight",
            source_ids=[source_id]
        )
        
        # Create POVs
        await dok_repository.create_spiky_pov(
            task_id=task_id,
            pov_type="truth",
            statement="Truth statement",
            reasoning="Truth reasoning",
            insight_ids=[insight_id]
        )
        
        await dok_repository.create_spiky_pov(
            task_id=task_id,
            pov_type="myth",
            statement="Myth statement",
            reasoning="Myth reasoning",
            insight_ids=[insight_id]
        )
        
        # Retrieve POVs
        povs = await dok_repository.get_spiky_povs_by_task(task_id)
        
        assert "truth" in povs
        assert "myth" in povs
        assert len(povs["truth"]) >= 1
        assert len(povs["myth"]) >= 1
    
    async def test_track_report_section_sources(self, dok_repository, test_task_data):
        """Test tracking report section sources."""
        task_id = test_task_data["task_id"]
        source_ids = [
            test_task_data["source_id"],
            f"source2_{uuid.uuid4().hex[:8]}"
        ]
        
        # Track sources for different sections
        success1 = await dok_repository.track_report_section_sources(
            task_id=task_id,
            section_type="key_findings",
            source_ids=source_ids
        )
        
        success2 = await dok_repository.track_report_section_sources(
            task_id=task_id,
            section_type="evidence_analysis",
            source_ids=[source_ids[0]]  # Only first source
        )
        
        assert success1
        assert success2
    
    async def test_get_bibliography_by_task(self, dok_repository, test_task_data):
        """Test getting bibliography by task."""
        task_id = test_task_data["task_id"]
        
        # Track some sources in different sections
        source_ids = [f"source_{i}_{uuid.uuid4().hex[:8]}" for i in range(3)]
        
        await dok_repository.track_report_section_sources(
            task_id=task_id,
            section_type="key_findings",
            source_ids=source_ids[:2]
        )
        
        await dok_repository.track_report_section_sources(
            task_id=task_id,
            section_type="evidence_analysis",
            source_ids=source_ids[1:]
        )
        
        # Get bibliography
        bibliography = await dok_repository.get_bibliography_by_task(task_id)
        
        assert "sources" in bibliography
        assert "total_sources" in bibliography
        assert "section_usage" in bibliography
        assert isinstance(bibliography["sources"], list)
        assert bibliography["total_sources"] >= 0
        assert isinstance(bibliography["section_usage"], dict)


@pytest.mark.integration
@pytest.mark.postgres
async def test_dok_repository_end_to_end():
    """End-to-end integration test for DOK taxonomy repository."""
    try:
        # Initialize repository
        repo = DOKTaxonomyRepository()
        kb = PostgresKnowledgeBase()
        await kb.connect()
        
        # Create test task
        task_id = f"e2e_test_{uuid.uuid4().hex[:8]}"
        await kb.create_task(
            task_id=task_id,
            query="End-to-end DOK taxonomy test",
            title="E2E Test Task",
            description="End-to-end test for DOK taxonomy"
        )
        
        # Create subtask
        subtask_id = f"e2e_subtask_{uuid.uuid4().hex[:8]}"
        await kb.create_research_subtask(
            subtask_id=subtask_id,
            task_id=task_id,
            topic="E2E Testing",
            description="End-to-end testing of DOK taxonomy"
        )
        
        # Create source first
        source_id = f"e2e_source_{uuid.uuid4().hex[:8]}"
        await kb.create_source(
            source_id=source_id,
            url="https://example.com/e2e-test",
            title="E2E Test Source",
            description="End-to-end test source for DOK taxonomy",
            source_type="web",
            provider="test"
        )
        
        # Create and store source summary
        summary = SourceSummary(
            summary_id=f"e2e_summary_{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            subtask_id=subtask_id,
            dok1_facts=["E2E test fact 1", "E2E test fact 2"],
            summary="End-to-end test summary",
            summarized_by="e2e_test_agent",
            created_at=datetime.now(timezone.utc)
        )
        
        await repo.store_source_summary(summary)
        
        # Create knowledge tree
        node_id = await repo.create_knowledge_node(
            task_id=task_id,
            category="E2E Testing",
            summary="End-to-end testing knowledge",
            dok_level=2
        )
        
        await repo.link_sources_to_knowledge_node(node_id, [summary.source_id])
        
        # Create insight
        insight_id = await repo.create_insight(
            task_id=task_id,
            category="E2E Analysis",
            insight_text="End-to-end testing reveals system integration success.",
            source_ids=[summary.source_id],
            confidence_score=0.95
        )
        
        # Create spiky POV
        pov_id = await repo.create_spiky_pov(
            task_id=task_id,
            pov_type="truth",
            statement="Comprehensive testing is essential for reliable systems.",
            reasoning="E2E testing validates complete system behavior.",
            insight_ids=[insight_id]
        )
        
        # Track sources in report sections
        await repo.track_report_section_sources(
            task_id=task_id,
            section_type="key_findings",
            source_ids=[summary.source_id]
        )
        
        # Verify all data can be retrieved
        knowledge_tree = await repo.get_knowledge_tree(task_id)
        insights = await repo.get_insights_by_task(task_id)
        povs = await repo.get_spiky_povs_by_task(task_id)
        bibliography = await repo.get_bibliography_by_task(task_id)
        
        # Assertions
        assert len(knowledge_tree) >= 1
        assert len(insights) >= 1
        assert len(povs["truth"]) >= 1
        assert bibliography["total_sources"] >= 0
        
        print(f"✅ End-to-end test completed successfully for task {task_id}")
        
        await kb.disconnect()
        
    except Exception as e:
        pytest.fail(f"End-to-end test failed: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
