"""
Comprehensive test suite for data aggregation functionality.
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
from src.domain_processors.private_schools import PrivateSchoolsProcessor
from src.domain_processors.registry import DomainProcessorRegistry


class TestDataAggregationComprehensive:
    """Comprehensive test suite for data aggregation functionality."""
    
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
        repo.get_research_task = AsyncMock(return_value={
            "task_id": "test-task-123",
            "title": "Test Data Aggregation Task",
            "description": "Test data aggregation task",
            "research_type": "data_aggregation",
            "status": "pending"
        })
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
        # Create a data aggregation orchestrator with mock components
        data_agg_orchestrator = DataAggregationOrchestrator(
            llm_client=mock_llm_client,
            dok_repository=mock_dok_repository,
            task_coordinator=mock_task_coordinator
        )
        
        # Replace the components with AsyncMock objects
        data_agg_orchestrator.search_enumerator = Mock()
        data_agg_orchestrator.search_enumerator.enumerate = AsyncMock()
        
        # Don't mock the entity extractor - let it use the real implementation
        # but with our mock domain processor registered in the global registry
        data_agg_orchestrator.entity_resolver = Mock()
        data_agg_orchestrator.entity_resolver.resolve_entities = AsyncMock()
        
        orchestrator = ResearchOrchestrator(
            task_coordinator=mock_task_coordinator,
            dok_workflow=mock_dok_workflow,
            db=mock_dok_repository,
            llm_config={}
        )
        
        # Replace the data aggregation orchestrator with our mock version
        orchestrator.data_aggregation_orchestrator = data_agg_orchestrator
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_complete_data_aggregation_workflow(self, research_orchestrator, mock_dok_repository):
        """Test the complete data aggregation workflow with all components."""
        
        # Create task configuration
        config = DataAggregationConfig(
            entities=["private schools"],
            attributes=["name", "address", "website", "enrollment", "tuition"],
            search_space="in California",
            domain_hint="education.private_schools"
        )
        
        task_id = "test-complete-data-aggregation"
        
        # Mock the _collect_search_results method to return mock search results
        research_orchestrator.data_aggregation_orchestrator._collect_search_results = AsyncMock(return_value=[
            {
                "content": "Mock search result content 1",
                "url": "https://example.com/result1",
                "title": "Mock Result 1"
            },
            {
                "content": "Mock search result content 2",
                "url": "https://example.com/result2",
                "title": "Mock Result 2"
            }
        ])
        
        # Mock the _collect_extracted_entities method to return mock extracted entities
        research_orchestrator.data_aggregation_orchestrator._collect_extracted_entities = AsyncMock(return_value=[
            {
                "name": "Test School 1",
                "attributes": {
                    "name": "Test School 1",
                    "address": "123 Main St, California",
                    "website": "https://testschool1.edu",
                    "enrollment": "500",
                    "tuition": "$20,000"
                },
                "confidence": 0.95
            },
            {
                "name": "Test School 2",
                "attributes": {
                    "name": "Test School 2",
                    "address": "456 Oak Ave, California",
                    "website": "https://testschool2.edu",
                    "enrollment": "300",
                    "tuition": "$15,000"
                },
                "confidence": 0.85
            }
        ])
        
        # Mock the task coordinator submit_tasks method
        research_orchestrator.data_aggregation_orchestrator.task_coordinator.submit_tasks = AsyncMock(return_value=None)
        
        # Mock the _generate_csv method
        research_orchestrator.data_aggregation_orchestrator._generate_csv = AsyncMock(return_value=f"exports/{task_id}_aggregation.csv")
        
        # Mock the _store_aggregation_results method
        research_orchestrator.data_aggregation_orchestrator._store_aggregation_results = AsyncMock(return_value=True)
        
        # Execute the data aggregation workflow
        result = await research_orchestrator.execute_data_aggregation(task_id, config.model_dump())
        
        # Verify the result structure
        assert "entity_count" in result
        assert "csv_path" in result
        assert result["entity_count"] >= 0
        assert task_id in result["csv_path"]
    
    @pytest.mark.asyncio
    async def test_private_schools_domain_processor_integration(self, research_orchestrator):
        """Test integration with the private schools domain processor."""
        
        # Create a mock domain processor
        mock_processor = Mock()
        mock_processor.extract_entities = AsyncMock(return_value=[
            {
                "name": "Domain Processed School",
                "attributes": {
                    "name": "Domain Processed School",
                    "address": "789 Domain St, California",
                    "website": "https://domainprocessedschool.edu",
                    "enrollment": "400",
                    "tuition": "$18,000"
                },
                "confidence": 0.90
            }
        ])
        mock_processor.resolve_entities = AsyncMock(return_value=[
            {
                "name": "Domain Processed School",
                "attributes": {
                    "name": "Domain Processed School",
                    "address": "789 Domain St, California",
                    "website": "https://domainprocessedschool.edu",
                    "enrollment": "400",
                    "tuition": "$18,000"
                },
                "confidence": 0.90
            }
        ])
        
        # Get the global registry and register the mock processor
        from src.domain_processors.registry import get_global_registry
        registry = get_global_registry()
        registry.register(mock_processor, "education.private_schools")
        
        # Test the entity extractor directly with the domain hint
        content = "Mock search result content for private schools"
        entity_type = "private schools"
        attributes = ["name", "address", "website", "enrollment", "tuition"]
        domain_hint = "education.private_schools"
        
        # Call the entity extractor's extract method directly
        extracted_entities = await research_orchestrator.data_aggregation_orchestrator.entity_extractor.extract(
            content, entity_type, attributes, domain_hint
        )
        
        # Verify that the domain processor's extract_entities method was called
        assert mock_processor.extract_entities.called
        # Verify that the extracted entities match what the domain processor returned
        assert len(extracted_entities) == 1
        assert extracted_entities[0]["name"] == "Domain Processed School"
        
        # Clean up the registry after the test
        registry.clear()
    
    @pytest.mark.asyncio
    async def test_data_aggregation_with_multiple_entities(self, research_orchestrator, mock_dok_repository):
        """Test data aggregation workflow with multiple entity types."""
        
        # Create task configuration with multiple entities
        config = DataAggregationConfig(
            entities=["private schools", "public schools"],
            attributes=["name", "address", "website"],
            search_space="in California"
        )
        
        task_id = "test-multiple-entities-aggregation"
        
        # Mock the _collect_search_results method to return mock search results
        research_orchestrator.data_aggregation_orchestrator._collect_search_results = AsyncMock(return_value=[
            {
                "content": "Mock search result content for private schools",
                "url": "https://example.com/private_schools",
                "title": "Private Schools Search Results"
            },
            {
                "content": "Mock search result content for public schools",
                "url": "https://example.com/public_schools",
                "title": "Public Schools Search Results"
            }
        ])
        
        # Mock the _collect_extracted_entities method to return mock extracted entities
        research_orchestrator.data_aggregation_orchestrator._collect_extracted_entities = AsyncMock(return_value=[
            {
                "name": "Private School 1",
                "attributes": {
                    "name": "Private School 1",
                    "address": "123 Private St, California",
                    "website": "https://privateschool1.edu"
                },
                "confidence": 0.95
            },
            {
                "name": "Public School 1",
                "attributes": {
                    "name": "Public School 1",
                    "address": "456 Public Ave, California",
                    "website": "https://publicschool1.edu"
                },
                "confidence": 0.90
            }
        ])
        
        # Mock the task coordinator submit_tasks method
        research_orchestrator.data_aggregation_orchestrator.task_coordinator.submit_tasks = AsyncMock(return_value=None)
        
        # Mock the _generate_csv method
        research_orchestrator.data_aggregation_orchestrator._generate_csv = AsyncMock(return_value=f"exports/{task_id}_aggregation.csv")
        
        # Mock the _store_aggregation_results method
        research_orchestrator.data_aggregation_orchestrator._store_aggregation_results = AsyncMock(return_value=True)
        
        # Execute the data aggregation workflow
        result = await research_orchestrator.execute_data_aggregation(task_id, config.model_dump())
        
        # Verify the result structure
        assert "entity_count" in result
        assert "csv_path" in result
        assert result["entity_count"] >= 0
        assert task_id in result["csv_path"]
    
    @pytest.mark.asyncio
    async def test_data_aggregation_error_handling(self, research_orchestrator, mock_dok_repository):
        """Test error handling in the data aggregation workflow."""
        
        # Create task configuration
        config = DataAggregationConfig(
            entities=["private schools"],
            attributes=["name", "address", "website"],
            search_space="in California"
        )
        
        task_id = "test-error-handling-aggregation"
        
        # Mock the search space enumerator to raise an exception
        with patch.object(research_orchestrator.data_aggregation_orchestrator.search_enumerator, 'enumerate') as mock_enumerate:
            mock_enumerate.side_effect = Exception("Search enumeration failed")
            
            # Execute the data aggregation workflow and verify it raises an exception
            with pytest.raises(Exception) as exc_info:
                await research_orchestrator.execute_data_aggregation(task_id, config.model_dump())
            
            # Verify the exception message
            assert "Search enumeration failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_data_aggregation_database_storage(self, research_orchestrator, mock_dok_repository):
        """Test that data aggregation results are properly stored in the database."""
        
        # Create task configuration
        config = DataAggregationConfig(
            entities=["private schools"],
            attributes=["name", "address", "website"],
            search_space="in California"
        )
        
        task_id = "test-database-storage-aggregation"
        
        # Set up the mock components directly on the orchestrator
        research_orchestrator.data_aggregation_orchestrator.search_enumerator.enumerate = AsyncMock(return_value=[
            Mock(id="subspace_1", query="private schools in California", metadata={"region": "California"})
        ])
        
        research_orchestrator.data_aggregation_orchestrator.task_coordinator.submit_tasks = AsyncMock(return_value=None)
        
        research_orchestrator.data_aggregation_orchestrator.entity_extractor.extract = AsyncMock(return_value=[
            {
                "name": "Database Test School",
                "attributes": {
                    "name": "Database Test School",
                    "address": "123 Database St, California",
                    "website": "https://databasetestschool.edu"
                },
                "confidence": 0.95
            }
        ])
        
        research_orchestrator.data_aggregation_orchestrator.entity_resolver.resolve_entities = AsyncMock(return_value=[
            {
                "name": "Database Test School",
                "attributes": {
                    "name": "Database Test School",
                    "address": "123 Database St, California",
                    "website": "https://databasetestschool.edu"
                },
                "confidence": 0.95
            }
        ])
        
        research_orchestrator.data_aggregation_orchestrator._generate_csv = AsyncMock(return_value=f"exports/{task_id}_aggregation.csv")
        
        # Mock the database storage method
        mock_dok_repository.store_data_aggregation_result = AsyncMock(return_value=True)
        
        # Execute the data aggregation workflow
        result = await research_orchestrator.execute_data_aggregation(task_id, config.model_dump())
        
        # Verify that the database storage method was called
        assert mock_dok_repository.store_data_aggregation_result.called
        
        # Verify the result structure
        assert "entity_count" in result
        assert "csv_path" in result
        assert result["entity_count"] >= 0
        assert task_id in result["csv_path"]
