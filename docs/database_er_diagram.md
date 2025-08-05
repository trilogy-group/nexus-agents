# Nexus Agents Database ER Diagram

## Entity Relationship Diagram

```mermaid
erDiagram
    research_tasks {
        VARCHAR task_id PK
        TEXT research_query
        VARCHAR title
        TEXT description
        VARCHAR status
        VARCHAR user_id
        TEXT error_message
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ completed_at
        JSONB metadata
        JSONB decomposition
        JSONB plan
        JSONB results
        JSONB summary
        JSONB reasoning
        VARCHAR research_type
        JSONB aggregation_config
        TEXT external_resource
    }

    research_reports {
        VARCHAR task_id PK
        TEXT report_markdown
        JSONB metadata
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    research_subtasks {
        VARCHAR subtask_id PK
        VARCHAR task_id FK
        VARCHAR topic
        TEXT description
        VARCHAR status
        VARCHAR assigned_agent
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ completed_at
        JSONB key_questions
        JSONB search_results
    }

    artifacts {
        VARCHAR artifact_id PK
        VARCHAR task_id FK
        VARCHAR subtask_id FK
        VARCHAR title
        VARCHAR type
        VARCHAR format
        VARCHAR file_path
        JSONB content
        JSONB metadata
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        BIGINT size_bytes
        VARCHAR checksum
    }

    sources {
        VARCHAR source_id PK
        VARCHAR url
        VARCHAR title
        TEXT description
        VARCHAR source_type
        VARCHAR provider
        TIMESTAMPTZ accessed_at
        JSONB metadata
        VARCHAR content_hash
        DECIMAL reliability_score
    }

    search_results {
        VARCHAR result_id PK
        VARCHAR query
        VARCHAR provider
        JSONB results
        TIMESTAMPTZ created_at
        TIMESTAMPTZ expires_at
        JSONB metadata
    }

    task_operations {
        VARCHAR operation_id PK
        VARCHAR task_id FK
        VARCHAR operation_type
        VARCHAR operation_name
        VARCHAR status
        VARCHAR agent_type
        TIMESTAMPTZ started_at
        TIMESTAMPTZ completed_at
        INTEGER duration_ms
        JSONB input_data
        JSONB output_data
        TEXT error_message
        JSONB metadata
    }

    operation_evidence {
        VARCHAR evidence_id PK
        VARCHAR operation_id FK
        VARCHAR evidence_type
        JSONB evidence_data
        VARCHAR source_url
        VARCHAR provider
        TIMESTAMPTZ created_at
        BIGINT size_bytes
        JSONB metadata
    }

    operation_dependencies {
        VARCHAR dependency_id PK
        VARCHAR operation_id FK
        VARCHAR depends_on_operation_id FK
        VARCHAR dependency_type
        TIMESTAMPTZ created_at
    }

    data_aggregation_results {
        UUID id PK
        VARCHAR task_id FK
        TEXT entity_type
        JSONB entity_data
        TEXT unique_identifier
        JSONB search_context
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    source_summaries {
        VARCHAR summary_id PK
        VARCHAR source_id FK
        VARCHAR subtask_id FK
        VARCHAR task_id FK
        JSONB dok1_facts
        TEXT summary
        VARCHAR summarized_by
        TEXT subtopic
        INTEGER dok_level
        JSONB facts
        JSONB metadata
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    knowledge_nodes {
        VARCHAR node_id PK
        VARCHAR task_id FK
        VARCHAR parent_id FK
        VARCHAR category
        VARCHAR subcategory
        TEXT summary
        INTEGER dok_level
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    knowledge_node_sources {
        VARCHAR node_id PK FK
        VARCHAR source_id PK FK
        DECIMAL relevance_score
    }

    insights {
        VARCHAR insight_id PK
        VARCHAR task_id FK
        VARCHAR category
        TEXT insight_text
        DECIMAL confidence_score
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    insight_sources {
        VARCHAR insight_id PK FK
        VARCHAR source_id PK FK
    }

    spiky_povs {
        VARCHAR pov_id PK
        VARCHAR task_id FK
        VARCHAR pov_type
        TEXT statement
        TEXT reasoning
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    pov_insights {
        VARCHAR pov_id PK FK
        VARCHAR insight_id PK FK
    }

    report_section_sources {
        VARCHAR report_section_id PK
        VARCHAR task_id FK
        VARCHAR section_type
        JSONB source_ids
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    %% Relationships
    research_tasks ||--|| research_reports : "has final report"
    research_tasks ||--o{ research_subtasks : "decomposed into"
    research_tasks ||--o{ artifacts : "generates"
    research_tasks ||--o{ task_operations : "tracked by"
    research_tasks ||--o{ data_aggregation_results : "aggregates data"
    research_tasks ||--o{ source_summaries : "has summaries"
    research_tasks ||--o{ knowledge_nodes : "builds knowledge tree"
    research_tasks ||--o{ insights : "generates insights"
    research_tasks ||--o{ spiky_povs : "creates POVs"
    research_tasks ||--o{ report_section_sources : "tracks section sources"
    
    research_subtasks ||--o{ artifacts : "generates"
    research_subtasks ||--o{ source_summaries : "has summaries"
    
    sources ||--o{ source_summaries : "summarized in"
    sources ||--o{ knowledge_node_sources : "linked to nodes"
    sources ||--o{ insight_sources : "supports insights"
    
    knowledge_nodes ||--o{ knowledge_nodes : "parent-child"
    knowledge_nodes ||--o{ knowledge_node_sources : "references sources"
    
    insights ||--o{ insight_sources : "supported by sources"
    insights ||--o{ pov_insights : "supports POVs"
    
    spiky_povs ||--o{ pov_insights : "based on insights"
    
    task_operations ||--o{ operation_evidence : "produces"
    task_operations ||--o{ operation_dependencies : "depends on"
    task_operations ||--o{ operation_dependencies : "depended by"
```

## Table Descriptions

### Core Research Tables

**research_tasks**
- Primary entity representing a research request
- Contains the original query, status, and high-level results
- Stores decomposition, plan, results, summary, and reasoning as JSONB
- `research_type`: Distinguishes between 'analytical_report' and 'data_aggregation' tasks
- `aggregation_config`: Configuration for data aggregation tasks (entity types, attributes, etc.)
- `external_resource`: Future support for external integrations (Google Sheets, etc.)

**research_reports** 
- Final markdown reports generated from completed research
- One-to-one relationship with research_tasks
- Contains the polished, human-readable research output

**research_subtasks**
- Breakdown of main research task into focused topics
- Each subtask can be assigned to specific agents
- Tracks key questions and search results per subtask

### Artifact Management

**artifacts**
- Generated documents, reports, data files, etc.
- Can be linked to either main tasks or subtasks
- Supports both file storage (file_path) and JSON content
- Tracks metadata like size, checksum, format

**sources**
- Information sources discovered during research
- Tracks URLs, reliability scores, providers
- Deduplicated by content hash

### Data Aggregation

**data_aggregation_results**
- Stores structured entities extracted from data aggregation tasks
- `entity_type`: Type of entity (e.g., 'school', 'company', 'person')
- `entity_data`: JSONB containing entity attributes, sources, and confidence scores
- `unique_identifier`: External identifier for deduplication (e.g., NCES_ID for schools)
- `search_context`: Location, subspace, and query context for the entity
- Supports CSV export and cross-task entity consolidation

### DOK Taxonomy System

**source_summaries**
- Summarized content from sources with DOK Level 1-2 facts
- Links sources to subtasks and main tasks
- `dok1_facts`: Extracted factual information (DOK Level 1)
- `dok_level`: Webb's Depth of Knowledge level (1-4)
- `subtopic`: Categorization within the research scope
- Supports both legacy and integrated workflow patterns

**knowledge_nodes**
- Hierarchical knowledge tree structure (DOK Level 1-2)
- `category`/`subcategory`: Organized knowledge classification
- `parent_id`: Enables tree structure with nested categories
- `dok_level`: Depth of Knowledge level for the node
- Forms the foundation of the DOK taxonomy

**knowledge_node_sources**
- Many-to-many relationship between knowledge nodes and sources
- `relevance_score`: Quantifies how relevant a source is to a knowledge node
- Enables source attribution and evidence tracking

**insights**
- Higher-level insights derived from knowledge (DOK Level 3)
- `category`: Thematic grouping of insights
- `confidence_score`: AI-generated confidence in the insight
- Represents analytical synthesis beyond basic facts

**insight_sources**
- Links insights to their supporting sources
- Enables evidence trail for analytical conclusions
- Many-to-many relationship for comprehensive source attribution

**spiky_povs**
- Controversial or contrarian points of view (DOK Level 4)
- `pov_type`: Either 'truth' (supported) or 'myth' (debunked)
- `statement`: The controversial claim or assertion
- `reasoning`: Evidence-based justification for the POV classification
- Represents the highest level of analytical thinking

**pov_insights**
- Links spiky POVs to the insights that support them
- Enables evidence chain from facts → insights → POVs
- Many-to-many relationship for complex argumentation

**report_section_sources**
- Tracks which sources are used in specific report sections
- `section_type`: Report section (key_findings, evidence_analysis, etc.)
- `source_ids`: JSONB array of source IDs used in the section
- Enables source attribution and bibliography generation

### Operation Tracking

**task_operations**
- Individual operations within a research workflow
- Tracks decomposition, search, scraping, summarization, etc.
- Records timing, agent type, input/output data
- Enables detailed workflow analysis

**operation_evidence**
- Detailed evidence for each operation
- Stores search queries, results, LLM prompts/responses
- Links to external sources and providers
- Enables audit trail and debugging

**operation_dependencies**
- Tracks dependencies between operations
- Supports sequential, parallel, and conditional workflows
- Enables complex workflow orchestration

### Caching

**search_results**
- Cached search results to avoid duplicate API calls
- Expires after a configurable time period
- Indexed by query and provider

## Key Design Patterns

1. **Hierarchical Structure**: Tasks → Subtasks → Operations → Evidence
2. **JSONB Storage**: Flexible schema for evolving data structures
3. **Audit Trail**: Complete tracking of all operations and evidence
4. **Caching**: Search results cached to optimize API usage
5. **Referential Integrity**: Cascading deletes maintain data consistency
6. **Temporal Tracking**: Created/updated timestamps on all entities
7. **DOK Taxonomy Integration**: Webb's Depth of Knowledge levels (1-4) structure analytical outputs
8. **Data Aggregation Support**: Structured entity extraction with deduplication capabilities
9. **Many-to-Many Relationships**: Flexible source attribution and evidence linking
10. **Research Type Differentiation**: Support for both analytical reports and data aggregation workflows
