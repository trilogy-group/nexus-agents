"""
Test suite for data aggregation functionality.
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


class TestDataAggregationOrchestrator:
    """Test data aggregation orchestrator functionality."""
    
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
    def orchestrator(self, mock_llm_client, mock_dok_repository, mock_task_coordinator):
        """Create a data aggregation orchestrator with mock dependencies."""
        return DataAggregationOrchestrator(
            llm_client=mock_llm_client,
            dok_repository=mock_dok_repository,
            task_coordinator=mock_task_coordinator
        )
    
    def test_data_aggregation_config(self):
        """Test data aggregation configuration structure."""
        config = {
            "entities": ["private schools"],
            "attributes": ["name", "address", "website", "enrollment", "tuition"],
            "search_space": "in California",
            "domain_hint": "education.private_schools"
        }
        
        # Verify required fields are present
        assert "entities" in config
        assert "attributes" in config
        assert "search_space" in config
        assert isinstance(config["entities"], list)
        assert isinstance(config["attributes"], list)
        assert isinstance(config["search_space"], str)
        
        # Verify entities and attributes are not empty
        assert len(config["entities"]) > 0
        assert len(config["attributes"]) > 0
    
    @pytest.mark.asyncio
    async def test_execute_data_aggregation(self, orchestrator, mock_dok_repository):
        """Test executing data aggregation workflow."""
        task_id = "test-task-123"
        config = {
            "entities": ["private schools"],
            "attributes": ["name", "address", "website"],
            "search_space": "in California"
        }
        
        # Mock the methods that would normally interact with external systems
        with patch.object(orchestrator, '_collect_search_results', AsyncMock(return_value=[])):
            with patch.object(orchestrator, '_collect_extracted_entities', AsyncMock(return_value=[])):
                with patch.object(orchestrator.entity_resolver, '_general_resolution', AsyncMock(return_value=[])):
                    result = await orchestrator.execute_data_aggregation(task_id, config)
                    
                    # Verify the result structure
                    assert "entity_count" in result
                    assert "csv_path" in result
                    assert result["entity_count"] == 0
                    assert result["csv_path"].endswith(".csv")
    
    @pytest.mark.asyncio
    async def test_search_space_enumeration(self, orchestrator, mock_llm_client):
        """Test search space enumeration."""
        base_query = "private schools"
        search_space = "in the US"
        
        # Mock LLM response for search space enumeration
        mock_response = """
        [
            {
                "id": "state_1",
                "query": "private schools in California",
                "metadata": {
                    "type": "state",
                    "state": "California",
                    "query": "private schools in California"
                }
            },
            {
                "id": "state_2",
                "query": "private schools in Texas",
                "metadata": {
                    "type": "state",
                    "state": "Texas",
                    "query": "private schools in Texas"
                }
            }
        ]
        """
        mock_llm_client.generate.return_value = mock_response
        
        subspaces = await orchestrator.search_enumerator.enumerate(base_query, search_space)
        
        # Verify subspaces are created
        assert len(subspaces) > 0
        assert all(hasattr(subspace, 'id') for subspace in subspaces)
        assert all(hasattr(subspace, 'query') for subspace in subspaces)
        assert all(hasattr(subspace, 'metadata') for subspace in subspaces)
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self, orchestrator, mock_llm_client):
        """Test entity extraction."""
        content = "Sample content about schools"
        entity_type = "private schools"
        attributes = ["name", "address", "website"]
        
        # Mock LLM response for entity extraction
        mock_response = """
        [
            {
                "name": "Test School 1",
                "attributes": {
                    "name": "Test School 1",
                    "address": "123 Main St, California",
                    "website": "https://testschool1.edu"
                },
                "confidence": 0.95
            },
            {
                "name": "Test School 2",
                "attributes": {
                    "name": "Test School 2",
                    "address": "456 Oak Ave, California",
                    "website": "https://testschool2.edu"
                },
                "confidence": 0.85
            }
        ]
        """
        mock_llm_client.generate.return_value = mock_response
        
        entities = await orchestrator.entity_extractor.extract(content, entity_type, attributes)
        
        # Verify entities are extracted
        assert len(entities) == 2
        for entity in entities:
            assert "name" in entity
            assert "attributes" in entity
            assert "confidence" in entity
            assert isinstance(entity["attributes"], dict)
    
    @pytest.mark.asyncio
    async def test_entity_resolution(self, orchestrator, mock_llm_client):
        """Test entity resolution."""
        entities = [
            {
                "name": "Test School",
                "attributes": {
                    "name": "Test School",
                    "address": "123 Main St, California"
                },
                "confidence": 0.95
            },
            {
                "name": "Test School",
                "attributes": {
                    "name": "Test School",
                    "website": "https://testschool.edu"
                },
                "confidence": 0.85
            }
        ]
        
        # Mock LLM response for entity resolution
        mock_llm_client.generate.return_value = json.dumps(entities)
        
        resolved = await orchestrator.entity_resolver.resolve_entities(entities)
        
        # Verify entities are resolved (should merge duplicates)
        assert len(resolved) <= len(entities)
        if resolved:
            assert "name" in resolved[0]
            assert "attributes" in resolved[0]
            assert "confidence" in resolved[0]
    
    @pytest.mark.asyncio
    async def test_csv_export(self, orchestrator, mock_dok_repository):
        """Test CSV export functionality."""
        task_id = "test-task-123"
        entities = [
            {
                "name": "Test School 1",
                "attributes": {
                    "name": "Test School 1",
                    "address": "123 Main St, California",
                    "website": "https://testschool1.edu"
                },
                "confidence": 0.95
            },
            {
                "name": "Test School 2",
                "attributes": {
                    "name": "Test School 2",
                    "address": "456 Oak Ave, California",
                    "website": "https://testschool2.edu"
                },
                "confidence": 0.85
            }
        ]
        
        # Mock database fetch
        mock_rows = [
            Mock(
                entity_data=json.dumps(entities[0]),
                unique_identifier="school-1",
                search_context=json.dumps({})
            ),
            Mock(
                entity_data=json.dumps(entities[1]),
                unique_identifier="school-2",
                search_context=json.dumps({})
            )
        ]
        mock_dok_repository.fetch_all.return_value = mock_rows
        
        csv_path = await orchestrator._generate_csv(task_id, entities)
        
        # Verify CSV path is returned
        assert csv_path is not None
        assert csv_path.endswith(".csv")
        assert task_id in csv_path


class TestDataAggregationIntegration:
    """Test data aggregation integration with research orchestrator."""
    
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
        # Add the missing mock method
        mock_dok_repository.update_research_task_status = AsyncMock(return_value=None)
        
        orchestrator = ResearchOrchestrator(
            task_coordinator=mock_task_coordinator,
            dok_workflow=mock_dok_workflow,
            db=mock_dok_repository,
            llm_config={}
        )
        
        # Set up the data aggregation orchestrator within the research orchestrator
        orchestrator.data_aggregation_orchestrator = DataAggregationOrchestrator(
            llm_client=mock_llm_client,
            dok_repository=mock_dok_repository,
            task_coordinator=mock_task_coordinator
        )
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_data_aggregation_task_execution(self, research_orchestrator, mock_dok_repository):
        """Test executing a data aggregation task through the research orchestrator."""
        task_id = "test-data-aggregation-task"
        config = {
            "entities": ["private schools"],
            "attributes": ["name", "address", "website"],
            "search_space": "in California"
        }
        
        # Mock the data aggregation orchestrator's execute method
        with patch.object(research_orchestrator.data_aggregation_orchestrator, 'execute_data_aggregation') as mock_execute:
            mock_execute.return_value = {
                "entity_count": 5,
                "csv_path": "exports/test-data-aggregation-task_aggregation.csv"
            }
            
            result = await research_orchestrator.execute_data_aggregation(task_id, config)
            
            # Verify the task execution
            mock_execute.assert_called_once_with(task_id, config)
            assert "entity_count" in result
            assert "csv_path" in result
            assert result["entity_count"] == 5
