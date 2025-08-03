"""Entity extractor for data aggregation tasks."""

import logging
from typing import List, Dict, Any, Optional

from src.llm import LLMClient
from src.domain_processors.registry import get_global_registry


logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extract structured data from search results."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize the entity extractor."""
        self.llm_client = llm_client
        self.domain_registry = get_global_registry()
        
    async def extract(self, 
                     content: str, 
                     entity_type: str,
                     attributes: List[str],
                     domain_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract entities with requested attributes from content.
        
        Args:
            content: The content to extract entities from
            entity_type: The type of entities to extract
            attributes: List of attributes to extract for each entity
            domain_hint: Optional domain hint for specialized processing
            
        Returns:
            List of extracted entities with their attributes
        """
        logger.info(f"Extracting {entity_type} entities with attributes: {attributes}")
        
        # Check for domain-specific processor
        processor = None
        if domain_hint:
            processor = self.domain_registry.get_processor_by_hint(domain_hint)
            # Set the LLM client for the processor if it has that attribute
            if processor and hasattr(processor, 'llm_client'):
                processor.llm_client = self.llm_client
            
        entities = []
        if processor:
            # Use domain-specific extraction
            logger.info(f"Using domain-specific processor for {domain_hint}")
            entities = await processor.extract_entities(content, attributes)
        else:
            # Use general-purpose extraction
            logger.info("Using general-purpose entity extraction")
            entities = await self._general_extraction(content, entity_type, attributes)
        
        # Add unique identifiers to entities if a domain processor is available
        if domain_hint and entities:
            processor = self.domain_registry.get_processor_by_hint(domain_hint)
            if processor:
                unique_id_field = processor.get_unique_identifier_field()
                if unique_id_field:
                    for entity in entities:
                        if "attributes" in entity:
                            unique_identifier = entity["attributes"].get(unique_id_field)
                            entity["unique_identifier"] = unique_identifier
        
        return entities
            
    async def _general_extraction(self, 
                                 content: str, 
                                 entity_type: str,
                                 attributes: List[str]) -> List[Dict[str, Any]]:
        """
        General-purpose entity extraction using LLM.
        
        Args:
            content: The content to extract entities from
            entity_type: The type of entities to extract
            attributes: List of attributes to extract for each entity
            
        Returns:
            List of extracted entities with their attributes
        """
        # Create prompt for entity extraction
        prompt = f"""
Extract all {entity_type} from the following content.
For each entity, extract these attributes: {', '.join(attributes)}

Return as JSON array with structure:
[
  {{
    "name": "Entity Name",
    "attributes": {{
      "attribute1": "value1",
      "attribute2": "value2"
    }},
    "confidence": 0.95
  }}
]

Content:
{content}
"""
        
        try:
            response = await self.llm_client.generate(prompt, use_reasoning_model=False)
            
            # Parse JSON response
            import json
            
            # Clean the response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            entities = json.loads(cleaned_response)
            logger.info(f"Extracted {len(entities)} entities using general extraction")
            return entities
            
        except Exception as e:
            logger.error(f"Error in general entity extraction: {str(e)}")
            return []
