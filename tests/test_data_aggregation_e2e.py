"""
End-to-end test for data aggregation functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json
from typing import List, Dict, Any

from src.orchestration.data_aggregation_orchestrator import DataAggregationOrchestrator
from src.orchestration.research_orchestrator import ResearchOrchestrator
from src.database.dok_taxonomy_repository import DOKTaxonomyRepository
from src.llm.client import LLMClient
from src.models.research_types import ResearchType, DataAggregationConfig


class TestDataAggregationEndToEnd:
    """Test data aggregation end-to-end workflow."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock(spec=LLMClient)
        client.generate = AsyncMock(return_value="Mock LLM response")
        return client
    
    @pytest.fixture
    def mock_dok_repository(self):
        """Create a mock DOK repository."""
        repo = Mock(spec=DOKTaxonomyRepository)
        repo.execute_query = AsyncMock(return_value=True)
        repo.fetch_all = AsyncMock(return_value=[])
        repo.update_research_task_status = AsyncMock(return_value=None)
        repo.domain_registry = Mock()
        repo.domain_registry.get_processor = Mock(return_value=None)
        return repo
    
    @pytest.fixture
    def mock_task_coordinator(self):
        """Create a mock task coordinator."""
        coordinator = Mock()
        coordinator.submit_tasks = AsyncMock(return_value=True)
        return coordinator
    
    @pytest.fixture
    def mock_dok_workflow(self):
        """Create a mock DOK workflow."""
        workflow = Mock()
        workflow.llm_client = Mock()
        workflow.dok_repository = Mock()
        workflow.summarization_agent = Mock()
        return workflow
    
    @pytest.fixture
    def research_orchestrator(self, mock_llm_client, mock_dok_repository, mock_task_coordinator, mock_dok_workflow):
        """Create a research orchestrator with mock dependencies."""
        orchestrator = ResearchOrchestrator(
            task_coordinator=mock_task_coordinator,
            dok_workflow=mock_dok_workflow,
            db=mock_dok_repository,
            llm_config={}
        )
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_private_schools_aggregation(self, research_orchestrator, mock_dok_repository):
        """End-to-end test for private schools data aggregation."""
        
        # Create task configuration
        config = DataAggregationConfig(
            entities=["private schools"],
            attributes=["name", "address", "website", "enrollment", "tuition"],
            search_space="in San Francisco, CA",
            domain_hint="education.private_schools"
        )
        
        task_id = "test-private-schools-aggregation"
        
        # Mock the data aggregation orchestrator's execute method
        with patch.object(research_orchestrator.data_aggregation_orchestrator, 'execute_data_aggregation') as mock_execute:
            mock_execute.return_value = {
                "entity_count": 3,
                "csv_path": f"exports/{task_id}_aggregation.csv"
            }
            
            # Execute the data aggregation workflow
            result = await research_orchestrator.execute_data_aggregation(task_id, config.model_dump())
            
            # Verify the task execution
            mock_execute.assert_called_once()
            assert "entity_count" in result
            assert "csv_path" in result
            assert result["entity_count"] >= 0
            assert task_id in result["csv_path"]
    
    @pytest.mark.asyncio
    async def test_data_aggregation_with_empty_results(self, research_orchestrator, mock_dok_repository):
        """Test data aggregation workflow with empty results."""
        
        # Create task configuration
        config = DataAggregationConfig(
            entities=["private schools"],
            attributes=["name", "address", "website"],
            search_space="in a non-existent location",
            domain_hint="education.private_schools"
        )
        
        task_id = "test-empty-results-aggregation"
        
        # Mock the data aggregation orchestrator's execute method to return empty results
        with patch.object(research_orchestrator, 'execute_data_aggregation') as mock_execute:
            mock_execute.return_value = {
                "entity_count": 0,
                "csv_path": f"exports/{task_id}_aggregation.csv"
            }
            
            # Execute the data aggregation workflow
            result = await research_orchestrator.execute_data_aggregation(task_id, config.model_dump())
            
            # Verify the task execution
            mock_execute.assert_called_once()
            assert "entity_count" in result
            assert "csv_path" in result
            assert result["entity_count"] == 0
            assert task_id in result["csv_path"]
    
    @pytest.mark.asyncio
    async def test_data_aggregation_with_general_domain(self, research_orchestrator, mock_dok_repository):
        """Test data aggregation workflow with general domain (no specific processor)."""
        
        # Create task configuration without domain hint
        config = DataAggregationConfig(
            entities=["restaurants"],
            attributes=["name", "address", "phone"],
            search_space="in New York City"
        )
        
        task_id = "test-general-domain-aggregation"
        
        # Mock the data aggregation orchestrator's execute method
        with patch.object(research_orchestrator, 'execute_data_aggregation') as mock_execute:
            mock_execute.return_value = {
                "entity_count": 5,
                "csv_path": f"exports/{task_id}_aggregation.csv"
            }
            
            # Execute the data aggregation workflow
            result = await research_orchestrator.execute_data_aggregation(task_id, config.model_dump())
            
            # Verify the task execution
            mock_execute.assert_called_once()
            assert "entity_count" in result
            assert "csv_path" in result
            assert result["entity_count"] >= 0
            assert task_id in result["csv_path"]
