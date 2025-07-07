"""Research type models and enums."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ResearchType(Enum):
    """Types of research that can be performed."""
    ANALYTICAL_REPORT = "analytical_report"
    DATA_AGGREGATION = "data_aggregation"


class DataAggregationConfig(BaseModel):
    """Configuration for data aggregation research."""
    entities: List[str] = Field(..., description="Entity types to extract (e.g., ['private schools'])")
    attributes: List[str] = Field(..., description="Attributes to extract for each entity")
    search_space: str = Field(..., description="Geographic or categorical search space (e.g., 'in California')")
    domain_hint: Optional[str] = Field(None, description="Domain hint for specialized processing (e.g., 'education.private_schools')")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entities": ["private schools"],
                "attributes": ["name", "address", "website", "enrollment", "tuition"],
                "search_space": "in San Francisco, CA",
                "domain_hint": "education.private_schools"
            }
        }
    )
