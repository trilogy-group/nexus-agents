# Data Aggregation Research Type

The Data Aggregation research type is a specialized workflow designed to systematically collect structured data about entities across multiple sources. It uses dynamic search space decomposition, entity extraction, and intelligent merging to create comprehensive data matrices that can be exported as CSV files.

## Overview

Unlike the Analytical Report research type which produces narrative documents, Data Aggregation focuses on extracting structured data points about specific entities. This makes it ideal for creating datasets, directories, or comparative analyses of entities like schools, companies, products, etc.

## Workflow

The data aggregation workflow consists of several specialized agents working together:

1. **Search Space Enumerator**: Dynamically decomposes the search space using LLM analysis
2. **Search Agents**: Execute searches across multiple providers for each subspace
3. **Entity Extractor**: Extracts structured data from search results
4. **Entity Resolver**: Merges duplicate entities and resolves conflicts
5. **CSV Exporter**: Generates CSV exports of the aggregated data

### Search Space Enumeration

The search space enumerator analyzes the research query and search constraints to determine the optimal way to decompose the search. For example:

- If searching for "private schools in the US", it might decompose by states
- If searching for "hospitals in California", it might decompose by regions or counties
- If searching for "companies in New York City", it might decompose by boroughs or business categories

### Entity Extraction

The entity extractor parses search results to identify entities and extract specified attributes. It can use:

- **General-purpose extraction**: Works with any entity type using LLM analysis
- **Domain-specific processors**: Optimized extraction for specific domains (e.g., education, healthcare)

### Entity Resolution

The entity resolver handles duplicate entities and merges complementary data:

- Groups entities by unique identifiers when available (e.g., NCES ID for schools)
- Merges entities with the same name but different attributes
- Calculates confidence scores for merged entities

### CSV Export

The final step generates a CSV file containing all extracted entities and their attributes. The CSV can be downloaded through the web interface or API.

## Configuration

Data aggregation tasks require specific configuration parameters:

### Entities
A list of entity types to search for (e.g., ["private schools", "charter schools"])

### Attributes
A list of attributes to extract for each entity (e.g., ["name", "address", "website", "enrollment", "tuition"])

### Search Space
Constraints on where to search (e.g., "in California", "in the US", "in New York City")

### Domain Hint (Optional)
A hint for domain-specific processing (e.g., "education.private_schools", "healthcare.hospitals")

## Example Usage

### Web Interface

1. Create a new research task
2. Select "Data Aggregation" as the research type
3. Fill in the configuration fields:
   - Entities: "private schools"
   - Attributes: "name, address, website, enrollment, tuition"
   - Search Space: "in California"
   - Domain Hint: "education.private_schools"
4. Start the research task
5. Once completed, download the CSV export

### API

Create a data aggregation task:
```bash
curl -X POST http://localhost:12000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "California Private Schools",
    "research_query": "Private schools in California",
    "research_type": "data_aggregation",
    "data_aggregation_config": {
      "entities": ["private schools"],
      "attributes": ["name", "address", "website", "enrollment", "tuition"],
      "search_space": "in California",
      "domain_hint": "education.private_schools"
    }
  }'
```

Export results as CSV:
```bash
curl -X GET http://localhost:12000/tasks/{task_id}/export/csv \
  -O -J
```

## Domain Processors

Domain processors provide specialized handling for specific types of entities:

### Private Schools Processor
Optimized for extracting data about private schools with support for:
- NCES ID matching for entity resolution
- Standardized attribute extraction
- Domain-specific search strategies

### Adding New Domain Processors
To add support for new entity types:

1. Create a new processor in `src/domain_processors/`
2. Implement `extract_entities` and `resolve_entities` methods
3. Register the processor in `src/domain_processors/__init__.py`

## Database Schema

Data aggregation results are stored in a flexible JSONB structure:

```sql
CREATE TABLE data_aggregation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES research_tasks(id),
    entity_type TEXT NOT NULL,
    entity_data JSONB NOT NULL,  -- {name, attributes, sources, confidence}
    unique_identifier TEXT,      -- e.g., NCES_ID for schools
    search_context JSONB,       -- {location, subspace, query}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Future Enhancements

### Near Term
- Excel export support
- More sophisticated entity matching algorithms
- Progress tracking for long-running aggregation tasks

### Medium Term
- Google Sheets integration
- Additional domain processors for common entity types
- Incremental updates to existing datasets

### Long Term
- Machine learning-based entity resolution
- Automated attribute discovery
- Data quality scoring and validation
