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
                              attributes: List[str]) -> List[Dict[str, Any]]:
        """Extract private school entities with requested attributes."""
        logger.info(f"Extracting private school entities with attributes: {attributes}")
        
        # Always try to extract NCES ID as it's the unique identifier
        enhanced_attributes = ["nces_id"] + [attr for attr in attributes if attr != "nces_id"]
        
        # Use the LLM client to extract entities - check if it's available
        if not hasattr(self, 'llm_client') or self.llm_client is None:
            logger.warning("LLM client not available for private school extraction, using general extraction")
            # Fallback to basic extraction without LLM
            return self._extract_basic_entities(content, enhanced_attributes)
        
        # Use specialized prompt for private school extraction
        prompt = f"""
Extract private school information from the following content. Extract ANY school information found, even if incomplete.

Look for:
- School name (any name that could be a school)
- Address (street address, city, state, zip)
- Phone number
- Website URL
- Grades served (K-12, PreK-8, etc.)
- Enrollment numbers
- Tuition costs
- NCES ID (format: XX-XXXXXXX, if available)

IMPORTANT: Extract information even if only partial data is available. Use "unknown" for missing required fields.

Return ONLY a JSON array with this exact structure:
[
  {{
    "name": "School Name or unknown",
    "nces_id": "XX-XXXXXXX or unknown",
    "attributes": {{
      "address": "Full address or partial address or unknown",
      "website": "URL or unknown",
      "enrollment population": "Number or unknown",
      "tuition cost": "Amount or unknown"
    }},
    "confidence": 0.8
  }}
]

Content to analyze:
{content}
"""
        
        # Use the LLM client to extract entities
        try:
            response = await self.llm_client.generate(prompt)
            logger.info(f"LLM response: {response[:200]}..." if len(response) > 200 else f"LLM response: {response}")
            
            if not response or not response.strip():
                logger.warning("LLM returned empty response")
                return self._extract_basic_entities(content, enhanced_attributes)
            
            import json
            import re
            
            # Extract JSON from the response, handling explanatory text and code blocks
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                cleaned_response = json_match.group(1).strip()
            else:
                # Try to find JSON array or object in the response
                json_match = re.search(r'(\[[\s\S]*?\]|\{[\s\S]*?\})', response)
                if json_match:
                    cleaned_response = json_match.group(1).strip()
                else:
                    cleaned_response = response.strip()
            
            logger.info(f"Cleaned JSON: {cleaned_response}")
            entities = json.loads(cleaned_response)
            return entities
        except Exception as e:
            logger.error(f"Error extracting entities with LLM: {e}")
            logger.error(f"Raw LLM response: {repr(response) if 'response' in locals() else 'No response'}")
            # Fallback to basic extraction
            return self._extract_basic_entities(content, enhanced_attributes)
    
    def _extract_basic_entities(self, content: str, attributes: List[str]) -> List[Dict[str, Any]]:
        """Basic entity extraction without LLM."""
        # Simple regex-based extraction for private schools
        import re
        
        # Look for school names and basic info in the content
        entities = []
        
        # Try to find school names with common patterns
        lines = content.split('\n')
        current_entity = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for school names (lines that might be school names)
            if any(keyword in line.lower() for keyword in ['school', 'academy', 'institute', 'christian', 'montessori']):
                if current_entity:
                    entities.append(current_entity)
                current_entity = {
                    "name": line,
                    "nces_id": "",
                    "attributes": {},
                    "confidence": 0.5
                }
        
        if current_entity:
            entities.append(current_entity)
        
        return entities
    
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
        return await self.extract_entities(content, attributes)
