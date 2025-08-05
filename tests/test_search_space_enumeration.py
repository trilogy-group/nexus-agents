"""Tests for LLM-based search space enumeration with universal geographic hierarchies."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from src.agents.aggregation.search_space_enumerator import SearchSpaceEnumerator
from src.agents.aggregation.search_space_enumerator import SearchSubspace
from src.llm import LLMClient


class TestSearchSpaceEnumerator:
    """Test cases for the LLM-based search space enumerator."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock(spec=LLMClient)
        # Mock successful LLM response for California counties
        client.generate = AsyncMock(return_value='''{
  "decomposition_type": "state_to_counties",
  "subspaces": [
    {
      "id": "county_001",
      "query": "private schools in Alameda County, California",
      "metadata": {
        "type": "county",
        "parent": "California",
        "name": "Alameda County",
        "level": "county"
      }
    },
    {
      "id": "county_002",
      "query": "private schools in Orange County, California",
      "metadata": {
        "type": "county",
        "parent": "California",
        "name": "Orange County",
        "level": "county"
      }
    }
  ]
}''')
        return client
    
    @pytest.fixture
    def enumerator(self, mock_llm_client):
        """Create a search space enumerator instance."""
        return SearchSpaceEnumerator(mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_llm_geographic_enumeration(self, enumerator):
        """Test that LLM properly enumerates geographic search spaces."""
        base_query = "private schools"
        search_space = "in California"
        
        subspaces = await enumerator.enumerate(base_query, search_space)
        
        # Should have subspaces from LLM response
        assert len(subspaces) == 2
        
        # Check that all subspaces are properly structured
        for subspace in subspaces:
            assert subspace.metadata["type"] == "county"
            assert subspace.metadata["parent"] == "California"
            assert subspace.metadata["level"] == "county"
            
            # Check that queries are properly formatted
            assert subspace.query.startswith("private schools in ")
            assert subspace.query.endswith(", California")
            
            # Check that each subspace has a unique ID
            assert subspace.id.startswith("county_")
    
    @pytest.mark.asyncio
    async def test_international_geography_support(self, mock_llm_client):
        """Test support for international geographic hierarchies."""
        # Mock LLM response for Colombian departments
        mock_llm_client.generate = AsyncMock(return_value='''{
  "decomposition_type": "country_to_departments",
  "subspaces": [
    {
      "id": "dept_001",
      "query": "universities in Amazonas, Colombia",
      "metadata": {
        "type": "department",
        "parent": "Colombia",
        "name": "Amazonas",
        "level": "department"
      }
    },
    {
      "id": "dept_002",
      "query": "universities in Antioquia, Colombia",
      "metadata": {
        "type": "department",
        "parent": "Colombia",
        "name": "Antioquia",
        "level": "department"
      }
    }
  ]
}''')
        
        enumerator = SearchSpaceEnumerator(mock_llm_client)
        base_query = "universities"
        search_space = "in Colombia"
        
        subspaces = await enumerator.enumerate(base_query, search_space)
        
        # Should have department-level subspaces
        assert len(subspaces) == 2
        
        # Check international geographic support
        for subspace in subspaces:
            assert subspace.metadata["type"] == "department"
            assert subspace.metadata["parent"] == "Colombia"
            assert subspace.metadata["level"] == "department"
            assert subspace.query.startswith("universities in ")
            assert subspace.query.endswith(", Colombia")
    
    @pytest.mark.asyncio
    async def test_canada_provinces_enumeration(self, mock_llm_client):
        """Test support for Canadian province enumeration."""
        # Mock LLM response for Canadian provinces
        mock_llm_client.generate = AsyncMock(return_value='''{
  "decomposition_type": "country_to_provinces",
  "subspaces": [
    {
      "id": "prov_001",
      "query": "hospitals in Ontario, Canada",
      "metadata": {
        "type": "province",
        "parent": "Canada",
        "name": "Ontario",
        "level": "province"
      }
    },
    {
      "id": "prov_002",
      "query": "hospitals in Quebec, Canada",
      "metadata": {
        "type": "province",
        "parent": "Canada",
        "name": "Quebec",
        "level": "province"
      }
    }
  ]
}''')
        
        enumerator = SearchSpaceEnumerator(mock_llm_client)
        base_query = "hospitals"
        search_space = "in Canada"
        
        subspaces = await enumerator.enumerate(base_query, search_space)
        
        # Should have province-level subspaces
        assert len(subspaces) == 2
        
        # Check Canadian geographic support
        for subspace in subspaces:
            assert subspace.metadata["type"] == "province"
            assert subspace.metadata["parent"] == "Canada"
            assert subspace.metadata["level"] == "province"
            assert subspace.query.startswith("hospitals in ")
            assert subspace.query.endswith(", Canada")
    
    @pytest.mark.asyncio
    async def test_direct_search_small_area(self, mock_llm_client):
        """Test that small/local search spaces use direct search."""
        # Mock LLM to return invalid JSON for small areas
        mock_llm_client.generate = AsyncMock(return_value="Invalid JSON response")
        
        enumerator = SearchSpaceEnumerator(mock_llm_client)
        base_query = "private schools"
        search_space = "in San Francisco, CA"
        
        subspaces = await enumerator.enumerate(base_query, search_space)
        
        # Should fall back to direct search
        assert len(subspaces) == 1
        
        subspace = subspaces[0]
        assert subspace.metadata["type"] == "direct"
        assert subspace.query == "private schools in San Francisco, CA"
    
    @pytest.mark.asyncio
    async def test_llm_json_parse_error_fallback(self, mock_llm_client):
        """Test that invalid LLM JSON responses fall back to direct search."""
        # Mock LLM to return invalid JSON
        mock_llm_client.generate = AsyncMock(return_value="Invalid JSON response")
        
        enumerator = SearchSpaceEnumerator(mock_llm_client)
        base_query = "private schools"
        search_space = "in California"
        
        subspaces = await enumerator.enumerate(base_query, search_space)
        
        # Should fall back to direct search
        assert len(subspaces) == 1
        
        subspace = subspaces[0]
        assert subspace.metadata["type"] == "direct"
        assert subspace.query == "private schools in California"
    
    @pytest.mark.asyncio
    async def test_error_fallback(self, mock_llm_client):
        """Test that errors fall back to direct search."""
        # Mock LLM to raise an exception
        mock_llm_client.generate = AsyncMock(side_effect=Exception("LLM Error"))
        
        enumerator = SearchSpaceEnumerator(mock_llm_client)
        base_query = "private schools"
        search_space = "in California"
        
        subspaces = await enumerator.enumerate(base_query, search_space)
        
        # Should fall back to direct search
        assert len(subspaces) == 1
        
        subspace = subspaces[0]
        assert subspace.metadata["type"] == "direct"
        assert "error" in subspace.metadata


if __name__ == "__main__":
    pytest.main([__file__])
