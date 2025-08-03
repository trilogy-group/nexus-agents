"""End-to-end tests for data aggregation functionality."""

import asyncio
import pytest
import json
from typing import Dict, Any
from src.models.research_types import ResearchType, DataAggregationConfig


@pytest.mark.asyncio
async def test_private_schools_aggregation():
    """End-to-end test for private schools data aggregation."""
    # This test would require a running API server and database
    # For now, we'll just verify the structure of the DataAggregationConfig
    
    # Create configuration
    config = DataAggregationConfig(
        entities=["private schools"],
        attributes=["name", "address", "website", "enrollment", "tuition"],
        search_space="in San Francisco, CA",
        domain_hint="education.private_schools"
    )
    
    # Verify configuration structure
    assert config.entities == ["private schools"]
    assert "name" in config.attributes
    assert "address" in config.attributes
    assert "website" in config.attributes
    assert "enrollment" in config.attributes
    assert "tuition" in config.attributes
    assert config.search_space == "in San Francisco, CA"
    assert config.domain_hint == "education.private_schools"


@pytest.mark.asyncio
async def test_data_aggregation_config_serialization():
    """Test serialization of DataAggregationConfig to/from JSON."""
    # Create configuration
    config = DataAggregationConfig(
        entities=["private schools"],
        attributes=["name", "address", "website"],
        search_space="in California",
        domain_hint="education.private_schools"
    )
    
    # Serialize to JSON
    config_json = config.model_dump_json()
    parsed_config = json.loads(config_json)
    
    # Verify serialization
    assert parsed_config["entities"] == ["private schools"]
    assert parsed_config["attributes"] == ["name", "address", "website"]
    assert parsed_config["search_space"] == "in California"
    assert parsed_config["domain_hint"] == "education.private_schools"
    
    # Deserialize from JSON
    config_from_json = DataAggregationConfig.model_validate_json(config_json)
    
    # Verify deserialization
    assert config_from_json.entities == config.entities
    assert config_from_json.attributes == config.attributes
    assert config_from_json.search_space == config.search_space
    assert config_from_json.domain_hint == config.domain_hint


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
