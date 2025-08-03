"""Domain-specific processor for private schools data aggregation."""

import logging
from typing import List, Dict, Any, Optional
import re

from .base import DomainProcessor


logger = logging.getLogger(__name__)


class PrivateSchoolsProcessor(DomainProcessor):
    """Domain-specific processing for private schools."""
    
    KNOWN_SOURCES = {
        "nces": "https://nces.ed.gov/privateSchoolSearch/",
        "privateschoolreview": "https://www.privateschoolreview.com/",
        "niche": "https://www.niche.com/k12/search/best-private-schools/"
    }
    
    def matches_domain(self, query: str) -> bool:
        """Check if this processor handles the query."""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in [
            "private school", "private schools", "independent school", "independent schools"
        ])
    
    async def extract_entities(self, 
                              content: str, 
                              attributes: List[str],
                              llm_client=None) -> List[Dict[str, Any]]:
        """Extract private school entities with requested attributes."""
        logger.info(f"Extracting private school entities with attributes: {attributes}")
        
        # Always try to extract NCES ID as it's the unique identifier
        enhanced_attributes = ["nces_id"] + [attr for attr in attributes if attr != "nces_id"]
        
        # Use specialized prompt for private school extraction
        prompt = f"""
Extract private school information from the following content. Look for:
- School name (official name)
- NCES ID (format: XX-XXXXXXX)
- Attributes: {', '.join(enhanced_attributes)}

Common patterns:
- Grades served: "K-12", "9-12", "PreK-8"
- Enrollment: Look for "students" or "enrollment"
- Tuition: Annual amount, may be range

Return as a JSON array with this structure:
[
  {{
    "name": "School Name",
    "nces_id": "XX-XXXXXXX",
    "attributes": {{
      "address": "123 Main St, City, State",
      "website": "https://school.edu",
      "enrollment": "500",
      "tuition": "$25,000",
      ...
    }},
    "confidence": 0.95
  }}
]

Content:
{content}
"""
        
        # If we have an LLM client, use it to extract entities
        if llm_client:
            try:
                response = await llm_client.generate(prompt)
                import json
                entities = json.loads(response)
                return entities
            except Exception as e:
                logger.error(f"Error extracting entities with LLM: {e}")
                return []
        else:
            # For now, we'll return an empty list as we need an LLM client to process this
            # In a real implementation, this would call an LLM to extract entities
            logger.warning("PrivateSchoolsProcessor.extract_entities is not fully implemented - needs LLM integration")
            return []
    
    async def resolve_entities(self, 
                              entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve private school entities using NCES ID as primary key."""
        logger.info(f"Resolving {len(entities)} private school entities")
        
        # Group by NCES ID first
        by_nces_id = {}
        no_nces_id = []
        
        for entity in entities:
            nces_id = entity.get("attributes", {}).get("nces_id")
            if nces_id:
                if nces_id not in by_nces_id:
                    by_nces_id[nces_id] = []
                by_nces_id[nces_id].append(entity)
            else:
                no_nces_id.append(entity)
        
        # Merge entities with the same NCES ID
        resolved = []
        for nces_id, group in by_nces_id.items():
            if len(group) == 1:
                resolved.append(group[0])
            else:
                # Merge multiple entities with the same NCES ID
                merged = self._merge_by_nces_id(group)
                resolved.append(merged)
        
        # Add entities without NCES ID (future: implement fuzzy matching on name + address)
        resolved.extend(no_nces_id)
        
        logger.info(f"Resolved to {len(resolved)} unique private school entities")
        return resolved
    
    def _merge_by_nces_id(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple entities with the same NCES ID."""
        if not entities:
            return {}
        
        # Start with the first entity
        merged = entities[0].copy()
        merged_attributes = merged.get("attributes", {}).copy()
        
        # Merge attributes from all entities
        for entity in entities[1:]:
            entity_attributes = entity.get("attributes", {})
            for key, value in entity_attributes.items():
                # If the attribute is missing in merged or is empty, take it from entity
                if not merged_attributes.get(key) and value:
                    merged_attributes[key] = value
                # If we have a better (more complete) value, use it
                elif value and len(str(value)) > len(str(merged_attributes.get(key, ""))):
                    merged_attributes[key] = value
        
        merged["attributes"] = merged_attributes
        
        # Calculate average confidence
        confidences = [entity.get("confidence", 0.0) for entity in entities]
        merged["confidence"] = sum(confidences) / len(confidences) if confidences else 0.0
        
        return merged
    
    def get_specialized_sources(self) -> Dict[str, str]:
        """Get specialized data sources for private schools."""
        return self.KNOWN_SOURCES
    
    def get_unique_identifier_field(self) -> Optional[str]:
        """Get the field name used as unique identifier for private schools."""
        return "nces_id"
    
    async def process(self, content: str, attributes: List[str], llm_client=None) -> List[Dict[str, Any]]:
        """Process content to extract private school entities."""
        return await self.extract_entities(content, attributes, llm_client)
