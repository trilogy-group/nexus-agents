"""Simple test for data aggregation functionality."""

import pytest
from src.models.research_types import ResearchType, DataAggregationConfig


def test_data_aggregation_config():
    """Test that DataAggregationConfig model works correctly."""
    config = DataAggregationConfig(
        entities=["private schools"],
        attributes=["name", "address", "website", "enrollment", "tuition"],
        search_space="in San Francisco, CA",
        domain_hint="education.private_schools"
    )
    
    assert config.entities == ["private schools"]
    assert "name" in config.attributes
    assert "address" in config.attributes
    assert "website" in config.attributes
    assert "enrollment" in config.attributes
    assert "tuition" in config.attributes
    assert config.search_space == "in San Francisco, CA"
    assert config.domain_hint == "education.private_schools"


def test_research_type_enum():
    """Test that ResearchType enum includes data aggregation."""
    assert ResearchType.DATA_AGGREGATION.value == "data_aggregation"
    assert ResearchType.ANALYTICAL_REPORT.value == "analytical_report"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
