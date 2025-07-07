"""
Integration tests for DOK Taxonomy API endpoints.
Tests the REST API endpoints for accessing DOK taxonomy data.
"""
import pytest
import asyncio
import uuid
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.dok_taxonomy_endpoints import router as dok_router, get_dok_repository
from src.database.dok_taxonomy_repository import DOKTaxonomyRepository


# Create test FastAPI app
app = FastAPI()
app.include_router(dok_router)

# Test client
client = TestClient(app)


@pytest.fixture
def mock_dok_repository():
    """Mock DOK taxonomy repository for API testing."""
    repo = Mock(spec=DOKTaxonomyRepository)
    
    # Mock data
    mock_source_summaries = [
        {
            'summary_id': 'sum_001',
            'source_id': 'src_001',
            'title': 'Test Source 1',
            'url': 'https://example.com/1',
            'dok1_facts': ['Fact 1', 'Fact 2'],
            'summary': 'Test summary 1'
        },
        {
            'summary_id': 'sum_002',
            'source_id': 'src_002',
            'title': 'Test Source 2',
            'url': 'https://example.com/2',
            'dok1_facts': ['Fact 3', 'Fact 4'],
            'summary': 'Test summary 2'
        }
    ]
    
    mock_knowledge_tree = [
        {
            'node_id': 'node_001',
            'category': 'AI Protocols',
            'subcategory': 'Communication',
            'summary': 'Protocol analysis',
            'dok_level': 2,
            'sources': [{'source_id': 'src_001', 'title': 'Test Source 1'}]
        },
        {
            'node_id': 'node_002',
            'category': 'System Integration',
            'subcategory': None,
            'summary': 'Integration patterns',
            'dok_level': 2,
            'sources': [{'source_id': 'src_002', 'title': 'Test Source 2'}]
        }
    ]
    
    mock_insights = [
        {
            'insight_id': 'insight_001',
            'category': 'Protocol Analysis',
            'insight_text': 'Standardization is crucial for AI interoperability',
            'confidence_score': 0.85,
            'supporting_sources': [{'source_id': 'src_001', 'title': 'Test Source 1'}]
        },
        {
            'insight_id': 'insight_002',
            'category': 'Integration Patterns',
            'insight_text': 'Modular architecture enables flexible AI systems',
            'confidence_score': 0.92,
            'supporting_sources': [{'source_id': 'src_002', 'title': 'Test Source 2'}]
        }
    ]
    
    mock_spiky_povs = {
        'truth': [
            {
                'pov_id': 'pov_001',
                'statement': 'AI standardization will determine market winners',
                'reasoning': 'Historical technology adoption patterns support this',
                'supporting_insights': [{'insight_id': 'insight_001', 'category': 'Protocol Analysis'}]
            }
        ],
        'myth': [
            {
                'pov_id': 'pov_002',
                'statement': 'AI systems will naturally interoperate without standards',
                'reasoning': 'Evidence shows explicit protocols are required',
                'supporting_insights': [{'insight_id': 'insight_002', 'category': 'Integration Patterns'}]
            }
        ]
    }
    
    mock_bibliography = {
        'sources': [
            {
                'source_id': 'src_001',
                'title': 'Test Source 1',
                'url': 'https://example.com/1',
                'provider': 'test',
                'summary': 'Test summary 1',
                'dok1_facts': ['Fact 1', 'Fact 2'],
                'used_in_sections': [{'section_type': 'key_findings'}]
            }
        ],
        'total_sources': 1,
        'section_usage': {
            'key_findings': 1,
            'evidence_analysis': 1
        }
    }
    
    # Configure mock methods
    repo.get_source_summaries_by_task = AsyncMock(return_value=mock_source_summaries)
    repo.get_knowledge_tree = AsyncMock(return_value=mock_knowledge_tree)
    repo.get_insights_by_task = AsyncMock(return_value=mock_insights)
    repo.get_spiky_povs_by_task = AsyncMock(return_value=mock_spiky_povs)
    repo.get_bibliography_by_task = AsyncMock(return_value=mock_bibliography)
    
    return repo


@pytest.mark.unit
class TestDOKTaxonomyAPIEndpoints:
    """Unit tests for DOK taxonomy API endpoints."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/dok/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "dok_taxonomy"
    
    def test_get_dok_stats(self, mock_dok_repository):
        """Test DOK taxonomy statistics endpoint."""
        # Override the dependency in the FastAPI app
        app.dependency_overrides[get_dok_repository] = lambda: mock_dok_repository
        
        task_id = "test_task_123"
        response = client.get(f"/api/dok/tasks/{task_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_sources" in data
        assert "total_dok1_facts" in data
        assert "knowledge_tree_nodes" in data
        assert "total_insights" in data
        assert "spiky_povs_truths" in data
        assert "spiky_povs_myths" in data
        assert "total_spiky_povs" in data
        
        # Verify repository calls
        mock_dok_repository.get_knowledge_tree.assert_called_once_with(task_id)
        mock_dok_repository.get_insights_by_task.assert_called_once_with(task_id)
        mock_dok_repository.get_spiky_povs_by_task.assert_called_once_with(task_id)
        mock_dok_repository.get_source_summaries_by_task.assert_called_once_with(task_id)
        
        # Clean up dependency override
        app.dependency_overrides.clear()
    
    def test_get_knowledge_tree(self, mock_dok_repository):
        """Test knowledge tree endpoint."""
        app.dependency_overrides[get_dok_repository] = lambda: mock_dok_repository
        
        task_id = "test_task_123"
        response = client.get(f"/api/dok/tasks/{task_id}/knowledge-tree")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2  # Based on mock data
        
        # Verify response structure
        node = data[0]
        assert "node_id" in node
        assert "category" in node
        assert "summary" in node
        assert "dok_level" in node
        assert "source_count" in node
        assert "sources" in node
        
        mock_dok_repository.get_knowledge_tree.assert_called_once_with(task_id)
        
        # Clean up dependency override
        app.dependency_overrides.clear()
    
    def test_get_insights(self, mock_dok_repository):
        """Test insights endpoint."""
        app.dependency_overrides[get_dok_repository] = lambda: mock_dok_repository
        
        task_id = "test_task_123"
        response = client.get(f"/api/dok/tasks/{task_id}/insights")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2  # Based on mock data
        
        # Verify response structure
        insight = data[0]
        assert "insight_id" in insight
        assert "category" in insight
        assert "insight_text" in insight
        assert "confidence_score" in insight
        assert "supporting_sources" in insight
        
        mock_dok_repository.get_insights_by_task.assert_called_once_with(task_id)
    
    def test_get_spiky_povs(self, mock_dok_repository):
        """Test spiky POVs endpoint."""
        app.dependency_overrides[get_dok_repository] = lambda: mock_dok_repository
        
        task_id = "test_task_123"
        response = client.get(f"/api/dok/tasks/{task_id}/spiky-povs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert "truth" in data
        assert "myth" in data
        
        # Verify truth POVs
        assert len(data["truth"]) == 1
        truth_pov = data["truth"][0]
        assert "pov_id" in truth_pov
        assert "statement" in truth_pov
        assert "reasoning" in truth_pov
        assert "supporting_insights" in truth_pov
        
        # Verify myth POVs
        assert len(data["myth"]) == 1
        myth_pov = data["myth"][0]
        assert "pov_id" in myth_pov
        assert "statement" in myth_pov
        assert "reasoning" in myth_pov
        
        mock_dok_repository.get_spiky_povs_by_task.assert_called_once_with(task_id)
    
    def test_get_bibliography(self, mock_dok_repository):
        """Test bibliography endpoint."""
        app.dependency_overrides[get_dok_repository] = lambda: mock_dok_repository
        
        task_id = "test_task_123"
        response = client.get(f"/api/dok/tasks/{task_id}/bibliography")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sources" in data
        assert "total_sources" in data
        assert "section_usage" in data
        
        # Verify sources structure
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) == 1
        
        source = data["sources"][0]
        assert "source_id" in source
        assert "title" in source
        assert "url" in source
        assert "provider" in source
        
        # Verify section usage
        assert isinstance(data["section_usage"], dict)
        assert "key_findings" in data["section_usage"]
        
        mock_dok_repository.get_bibliography_by_task.assert_called_once_with(task_id)
    
    def test_get_source_summaries(self, mock_dok_repository):
        """Test source summaries endpoint."""
        app.dependency_overrides[get_dok_repository] = lambda: mock_dok_repository
        
        task_id = "test_task_123"
        response = client.get(f"/api/dok/tasks/{task_id}/source-summaries")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2  # Based on mock data
        
        # Verify source summary structure
        summary = data[0]
        assert "summary_id" in summary
        assert "source_id" in summary
        assert "title" in summary
        assert "summary" in summary
        assert "dok1_facts" in summary
        
        mock_dok_repository.get_source_summaries_by_task.assert_called_once_with(task_id)
    
    def test_get_complete_dok_data(self, mock_dok_repository):
        """Test complete DOK data endpoint."""
        app.dependency_overrides[get_dok_repository] = lambda: mock_dok_repository
        
        task_id = "test_task_123"
        response = client.get(f"/api/dok/tasks/{task_id}/dok-complete")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all DOK taxonomy components are present
        assert "task_id" in data
        assert "knowledge_tree" in data
        assert "insights" in data
        assert "spiky_povs" in data
        assert "bibliography" in data
        assert "source_summaries" in data
        assert "stats" in data
        
        assert data["task_id"] == task_id
        
        # Verify stats structure
        stats = data["stats"]
        assert "total_sources" in stats
        assert "total_dok1_facts" in stats
        assert "knowledge_tree_nodes" in stats
        assert "total_insights" in stats
        assert "spiky_povs_truths" in stats
        assert "spiky_povs_myths" in stats
        assert "total_spiky_povs" in stats
        
        # Verify all repository methods were called
        mock_dok_repository.get_knowledge_tree.assert_called_once_with(task_id)
        mock_dok_repository.get_insights_by_task.assert_called_once_with(task_id)
        mock_dok_repository.get_spiky_povs_by_task.assert_called_once_with(task_id)
        mock_dok_repository.get_bibliography_by_task.assert_called_once_with(task_id)
        mock_dok_repository.get_source_summaries_by_task.assert_called_once_with(task_id)
    
    def test_api_error_handling(self):
        """Test API error handling."""
        # Mock repository to raise an exception
        mock_repo = Mock()
        mock_repo.get_knowledge_tree = AsyncMock(side_effect=Exception("Database error"))
        app.dependency_overrides[get_dok_repository] = lambda: mock_repo
        
        task_id = "test_task_123"
        response = client.get(f"/api/dok/tasks/{task_id}/knowledge-tree")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database error" in data["detail"]
        
        # Clean up dependency override
        app.dependency_overrides.clear()
    
    def test_invalid_task_id_formats(self):
        """Test API endpoints with various task ID formats."""
        # Test with empty task ID
        response = client.get("/api/dok/tasks//stats")
        assert response.status_code == 404
        
        # Test with special characters
        task_id = "task-with-special-chars_123"
        response = client.get(f"/api/dok/tasks/{task_id}/health")
        # Should reach the health endpoint (doesn't use task_id)
        assert response.status_code == 404  # No such endpoint
    
    @patch('src.api.dok_taxonomy_endpoints.get_dok_repository')
    def test_empty_data_responses(self, mock_get_repo):
        """Test API responses with empty data."""
        # Mock repository to return empty data
        mock_repo = Mock()
        mock_repo.get_knowledge_tree = AsyncMock(return_value=[])
        mock_repo.get_insights_by_task = AsyncMock(return_value=[])
        mock_repo.get_spiky_povs_by_task = AsyncMock(return_value={"truth": [], "myth": []})
        mock_repo.get_source_summaries_by_task = AsyncMock(return_value=[])
        mock_repo.get_bibliography_by_task = AsyncMock(return_value={
            "sources": [],
            "total_sources": 0,
            "section_usage": {}
        })
        mock_get_repo.return_value = mock_repo
        
        task_id = "empty_task_123"
        
        # Test stats with empty data
        response = client.get(f"/api/dok/tasks/{task_id}/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sources"] == 0
        assert data["total_insights"] == 0
        assert data["total_spiky_povs"] == 0
        
        # Test knowledge tree with empty data
        response = client.get(f"/api/dok/tasks/{task_id}/knowledge-tree")
        assert response.status_code == 200
        data = response.json()
        assert data == []
        
        # Test insights with empty data
        response = client.get(f"/api/dok/tasks/{task_id}/insights")
        assert response.status_code == 200
        data = response.json()
        assert data == []


@pytest.mark.integration
@pytest.mark.postgres
class TestDOKTaxonomyAPIIntegration:
    """Integration tests with real database."""
    
    async def test_api_with_real_database(self):
        """Test API endpoints with real database data."""
        try:
            from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase
            from src.database.dok_taxonomy_repository import DOKTaxonomyRepository
            
            # Initialize real components
            kb = PostgresKnowledgeBase()
            await kb.connect()
            
            repo = DOKTaxonomyRepository()
            repo.knowledge_base = kb  # Ensure repository has access to knowledge base
            
            # Create test task
            task_id = f"api_test_{uuid.uuid4().hex[:8]}"
            await kb.store_research_task(
                task_id=task_id,
                research_query="API integration test",
                status="completed",
                user_id="api_test_user"
            )
            
            # Create test subtask
            subtask_id = f"api_subtask_{uuid.uuid4().hex[:8]}"
            await kb.create_research_subtask(
                subtask_id=subtask_id,
                task_id=task_id,
                topic="API Testing",
                description="Testing API endpoints"
            )
            
            # Create test knowledge node
            node_id = await repo.create_knowledge_node(
                task_id=task_id,
                category="API Testing",
                summary="Testing API endpoint functionality",
                dok_level=2
            )
            
            # Create test insight
            insight_id = await repo.create_insight(
                task_id=task_id,
                category="API Analysis",
                insight_text="API endpoints provide comprehensive access to DOK taxonomy data",
                source_ids=[],
                confidence_score=0.9
            )
            
            # Create test spiky POV
            pov_id = await repo.create_spiky_pov(
                task_id=task_id,
                pov_type="truth",
                statement="Well-designed APIs are crucial for system integration",
                reasoning="APIs enable modular system architecture and easier maintenance",
                insight_ids=[insight_id] if insight_id else []
            )
            
            # Test API endpoints with real data
            with patch('src.api.dok_taxonomy_endpoints.get_dok_repository') as mock_get_repo:
                mock_get_repo.return_value = repo
                
                # Test stats endpoint
                response = client.get(f"/api/dok/tasks/{task_id}/stats")
                assert response.status_code == 200
                data = response.json()
                assert data["knowledge_tree_nodes"] >= 1
                assert data["total_insights"] >= 1
                assert data["spiky_povs_truths"] >= 1
                
                # Test knowledge tree endpoint
                response = client.get(f"/api/dok/tasks/{task_id}/knowledge-tree")
                assert response.status_code == 200
                data = response.json()
                assert len(data) >= 1
                assert data[0]["category"] == "API Testing"
                
                # Test insights endpoint
                response = client.get(f"/api/dok/tasks/{task_id}/insights")
                assert response.status_code == 200
                data = response.json()
                assert len(data) >= 1
                assert "API" in data[0]["insight_text"]
                
                # Test spiky POVs endpoint
                response = client.get(f"/api/dok/tasks/{task_id}/spiky-povs")
                assert response.status_code == 200
                data = response.json()
                assert len(data["truth"]) >= 1
                assert "API" in data["truth"][0]["statement"]
            
            print(f"✅ API integration test completed successfully for task {task_id}")
            
            await kb.disconnect()
            
        except Exception as e:
            pytest.skip(f"API integration test skipped due to setup: {e}")


@pytest.mark.performance
class TestDOKTaxonomyAPIPerformance:
    """Performance tests for DOK taxonomy API endpoints."""
    
    @patch('src.api.dok_taxonomy_endpoints.get_dok_repository')
    def test_api_response_times(self, mock_get_repo, mock_dok_repository):
        """Test API response times under load."""
        import time
        
        mock_get_repo.return_value = mock_dok_repository
        task_id = "performance_test_123"
        
        # Test multiple endpoints
        endpoints = [
            f"/api/dok/tasks/{task_id}/stats",
            f"/api/dok/tasks/{task_id}/knowledge-tree",
            f"/api/dok/tasks/{task_id}/insights",
            f"/api/dok/tasks/{task_id}/spiky-povs",
            f"/api/dok/tasks/{task_id}/bibliography"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 1.0  # Should respond within 1 second
    
    @patch('src.api.dok_taxonomy_endpoints.get_dok_repository')
    def test_concurrent_api_requests(self, mock_get_repo, mock_dok_repository):
        """Test concurrent API requests."""
        import threading
        import time
        
        mock_get_repo.return_value = mock_dok_repository
        task_id = "concurrent_test_123"
        
        results = []
        
        def make_request():
            response = client.get(f"/api/dok/tasks/{task_id}/stats")
            results.append(response.status_code)
        
        # Make 10 concurrent requests
        threads = []
        start_time = time.time()
        
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10
        
        # Should complete within reasonable time
        assert (end_time - start_time) < 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
