"""
Test suite for duplicate source prevention functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.database.dok_taxonomy_repository import DOKTaxonomyRepository
from src.orchestration.research_orchestrator import ResearchOrchestrator
from src.agents.research.dok_workflow_orchestrator import DOKWorkflowOrchestrator


@pytest.mark.asyncio
async def test_check_source_exists_for_task():
    """Test the check_source_exists_for_task method in DOKTaxonomyRepository."""
    # Mock database connection
    mock_db = MagicMock()
    mock_fetch_one = AsyncMock()
    
    # Create repository instance
    repo = DOKTaxonomyRepository(mock_db)
    repo.fetch_one = mock_fetch_one
    
    task_id = "test_task_123"
    url = "https://example.com/article"
    
    # Test case 1: Source exists (count > 0)
    mock_fetch_one.return_value = {'count': 1}
    result = await repo.check_source_exists_for_task(task_id, url)
    assert result is True
    
    # Verify the correct query was called
    expected_query = """
            SELECT COUNT(*) as count
            FROM source_summaries ss
            JOIN sources s ON ss.source_id = s.source_id
            JOIN research_subtasks rs ON ss.subtask_id = rs.subtask_id
            WHERE rs.task_id = $1 AND s.url = $2
        """
    mock_fetch_one.assert_called_with(expected_query, task_id, url)
    
    # Test case 2: Source doesn't exist (count = 0)
    mock_fetch_one.return_value = {'count': 0}
    result = await repo.check_source_exists_for_task(task_id, url)
    assert result is False
    
    # Test case 3: Database error
    mock_fetch_one.side_effect = Exception("Database error")
    result = await repo.check_source_exists_for_task(task_id, url)
    assert result is False  # Should return False on error


@pytest.mark.asyncio
async def test_duplicate_prevention_integration():
    """Test duplicate prevention logic integration."""
    # Mock database connection
    mock_db = MagicMock()
    repo = DOKTaxonomyRepository(mock_db)
    repo.fetch_one = AsyncMock()
    
    task_id = "test_task_123"
    
    # Test scenario: Check multiple URLs, some duplicates
    test_urls = [
        "https://example.com/article1",
        "https://example.com/article2", 
        "https://example.com/article1",  # Duplicate
        "https://example.com/article3"
    ]
    
    # Mock responses: article1 exists (duplicate), others don't
    repo.fetch_one.side_effect = [
        {'count': 0},  # article1 first check - doesn't exist
        {'count': 0},  # article2 - doesn't exist
        {'count': 1},  # article1 second check - exists (duplicate)
        {'count': 0}   # article3 - doesn't exist
    ]
    
    # Simulate the duplicate checking logic
    unique_urls = []
    duplicate_count = 0
    
    for url in test_urls:
        exists = await repo.check_source_exists_for_task(task_id, url)
        if exists:
            duplicate_count += 1
        else:
            unique_urls.append(url)
    
    # Verify results
    assert duplicate_count == 1  # One duplicate found
    assert len(unique_urls) == 3  # Three unique URLs processed
    assert "https://example.com/article1" in unique_urls  # First occurrence kept
    assert "https://example.com/article2" in unique_urls
    assert "https://example.com/article3" in unique_urls
    
    # Verify the correct number of database calls were made
    assert repo.fetch_one.call_count == 4


@pytest.mark.asyncio
async def test_duplicate_prevention_with_empty_url():
    """Test that sources with empty URLs are not filtered out."""
    # Mock database connection
    mock_db = MagicMock()
    repo = DOKTaxonomyRepository(mock_db)
    repo.fetch_one = AsyncMock()
    
    task_id = "test_task_123"
    empty_url = ""
    
    # Should not call database for empty URLs
    result = await repo.check_source_exists_for_task(task_id, empty_url)
    
    # Should return False for empty URLs (allowing them to be processed)
    assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
