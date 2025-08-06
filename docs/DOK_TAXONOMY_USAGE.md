# DOK Taxonomy System - Usage Guide

## Overview

The DOK (Depth of Knowledge) Taxonomy system has been successfully integrated into the Nexus Agents research workflow. This system provides hierarchical knowledge organization based on Webb's Depth of Knowledge methodology, enabling better source management, bibliography tracking, and insight generation.

## System Architecture

### Components

1. **SummarizationAgent** - Handles per-source summarization and DOK Level 1 fact extraction
2. **DOKWorkflowOrchestrator** - Coordinates the complete DOK taxonomy workflow
3. **DOKTaxonomyRepository** - Database access layer for DOK taxonomy tables
4. **DOK API Endpoints** - REST API for accessing DOK taxonomy data

### Database Schema

The following tables have been added to support DOK taxonomy:

- `source_summaries` - Stores source summaries with DOK Level 1 facts
- `knowledge_nodes` - Hierarchical knowledge tree (DOK Levels 1-2)
- `knowledge_node_sources` - Links sources to knowledge nodes
- `insights` - DOK Level 3 strategic insights
- `insight_sources` - Links insights to supporting sources
- `spiky_povs` - DOK Level 4 contrarian perspectives
- `pov_insights` - Links POVs to supporting insights
- `report_section_sources` - Tracks source usage in report sections

## DOK Taxonomy Levels

### DOK Level 1: Recall & Reproduction
- **Implementation**: Atomic facts extracted from each source
- **Storage**: `dok1_facts` JSONB field in `source_summaries`
- **Purpose**: Preserve verifiable, concrete information

### DOK Level 2: Skills & Concepts
- **Implementation**: Categorized knowledge tree with summaries
- **Storage**: `knowledge_nodes` table with hierarchical structure
- **Purpose**: Organize information into thematic categories

### DOK Level 3: Strategic Thinking
- **Implementation**: Insights that synthesize multiple sources
- **Storage**: `insights` table with source cross-references
- **Purpose**: Generate strategic thinking and evidence-based conclusions

### DOK Level 4: Extended Thinking
- **Implementation**: "Spiky POVs" (Truths and Myths)
- **Storage**: `spiky_povs` table with insight references
- **Purpose**: Contrarian perspectives and challenging conventional wisdom

## API Endpoints

### DOK Taxonomy Endpoints

All endpoints are prefixed with `/api/dok/`:

#### GET `/api/dok/tasks/{task_id}/stats`
Returns comprehensive statistics for a research task's DOK taxonomy data.

**Response:**
```json
{
  "total_sources": 15,
  "total_dok1_facts": 127,
  "knowledge_tree_nodes": 5,
  "total_insights": 8,
  "spiky_povs_truths": 3,
  "spiky_povs_myths": 2,
  "total_spiky_povs": 5
}
```

#### GET `/api/dok/tasks/{task_id}/knowledge-tree`
Returns the hierarchical knowledge tree for a research task.

**Response:**
```json
[
  {
    "node_id": "node_abc123",
    "category": "AI-to-Data/Tool Interoperability",
    "subcategory": "Model Context Protocol",
    "summary": "MCP standardizes AI connections to external data sources...",
    "dok_level": 2,
    "source_count": 4,
    "sources": [...]
  }
]
```

#### GET `/api/dok/tasks/{task_id}/insights`
Returns strategic insights (DOK Level 3) for a research task.

**Response:**
```json
[
  {
    "insight_id": "insight_def456",
    "category": "AI Interoperability",
    "insight_text": "MCP's potential extends beyond its commonly discussed 'Tools' concept...",
    "confidence_score": 0.85,
    "supporting_sources": [...]
  }
]
```

#### GET `/api/dok/tasks/{task_id}/spiky-povs`
Returns spiky points of view (DOK Level 4) grouped by type.

**Response:**
```json
{
  "truth": [
    {
      "pov_id": "pov_ghi789",
      "statement": "The most significant barrier to AI agent deployment is not individual agent intelligence...",
      "reasoning": "Based on analysis of interoperability protocols...",
      "supporting_insights": [...]
    }
  ],
  "myth": [...]
}
```

#### GET `/api/dok/tasks/{task_id}/bibliography`
Returns comprehensive bibliography with source usage tracking.

**Response:**
```json
{
  "sources": [
    {
      "source_id": "src_123",
      "title": "Introducing the Model Context Protocol",
      "url": "https://anthropic.com/news/model-context-protocol",
      "provider": "anthropic",
      "summary": "Overview of MCP goals and architecture...",
      "dok1_facts": ["MCP introduced by Anthropic in late 2024", ...],
      "used_in_sections": ["key_findings", "evidence_analysis"]
    }
  ],
  "total_sources": 15,
  "section_usage": {
    "key_findings": 8,
    "evidence_analysis": 12,
    "causal_relationships": 5,
    "alternative_interpretations": 3
  }
}
```

#### GET `/api/dok/tasks/{task_id}/dok-complete`
Returns complete DOK taxonomy data for a research task (all levels).

### Project-Level DOK Taxonomy Endpoints

#### GET `/api/projects/{project_id}/entities`
Returns all consolidated entities for a project with their data lineage information.

#### GET `/api/projects/{project_id}/entities/{unique_identifier}`
Returns a specific consolidated entity for a project with its data lineage information.

#### GET `/api/projects/{project_id}/dok`
Returns consolidated DOK taxonomy data for a project.

## Research Workflow Integration

### Enhanced Workflow Steps

The research workflow now includes DOK taxonomy processing:

1. **Topic Decomposition** - Breaks down research query
2. **Research Planning** - Creates search strategy
3. **Search Execution** - Gathers sources from MCP servers
4. **Source Summarization** (NEW) - Each source gets summarized with DOK1 facts
5. **Knowledge Tree Building** (NEW) - Organizes sources into hierarchical categories
6. **Insight Generation** (NEW) - Creates strategic insights from knowledge tree
7. **Spiky POV Analysis** (NEW) - Generates contrarian perspectives
8. **Content Analysis** - Enhanced with DOK taxonomy data
9. **Report Synthesis** - Comprehensive report using all DOK levels
10. **Bibliography Generation** - Complete source tracking and citations

### Status Tracking

New research statuses have been added:
- `summarizing` - DOK Level 1: Source summarization
- `building_knowledge` - DOK Level 2: Knowledge tree construction
- `generating_insights` - DOK Level 3: Insight generation
- `analyzing_povs` - DOK Level 4: Spiky POV analysis

## Usage Examples

### Starting a Research Task with DOK Taxonomy

```python
from src.orchestration.research_orchestrator import ResearchOrchestrator
from src.llm import LLMClient
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase

# Initialize orchestrator
llm_client = LLMClient.from_config("config/llm_config.json")
knowledge_base = PostgresKnowledgeBase()
orchestrator = ResearchOrchestrator(llm_client, knowledge_base)

# Start research task
task_id = await orchestrator.start_research_task(
    research_query="How do AI agents collaborate effectively?",
    user_id="user123"
)
```

### Accessing DOK Taxonomy Data

```python
from src.database.dok_taxonomy_repository import DOKTaxonomyRepository

# Initialize repository
dok_repo = DOKTaxonomyRepository()

# Get complete DOK taxonomy data
knowledge_tree = await dok_repo.get_knowledge_tree(task_id)
insights = await dok_repo.get_insights_by_task(task_id)
spiky_povs = await dok_repo.get_spiky_povs_by_task(task_id)
bibliography = await dok_repo.get_bibliography_by_task(task_id)
```

### Frontend Integration

The DOK taxonomy data is accessible through the API and can be integrated into the frontend:

```javascript
// Get DOK taxonomy stats
const stats = await fetch(`/api/dok/tasks/${taskId}/stats`);

// Get complete DOK data
const dokData = await fetch(`/api/dok/tasks/${taskId}/dok-complete`);

// Display knowledge tree
const knowledgeTree = await fetch(`/api/dok/tasks/${taskId}/knowledge-tree`);
```

## Benefits

### 1. Enhanced Source Management
- Every source is summarized and classified
- DOK Level 1 facts are preserved for verification
- Source usage is tracked throughout the workflow

### 2. Hierarchical Knowledge Organization
- Knowledge tree provides structured categorization
- Easy navigation from facts to insights to POVs
- Clear provenance from sources to final conclusions

### 3. Strategic Insight Generation
- DOK Level 3 insights synthesize multiple sources
- Evidence-based conclusions with source references
- Confidence scoring for insight reliability

### 4. Contrarian Analysis
- Spiky POVs challenge conventional thinking
- Separate "truths" and "myths" perspectives
- Reasoning provided for each position

### 5. Complete Bibliography Management
- Comprehensive source tracking and citations
- Section-level usage tracking
- Format-ready bibliography generation

## Best Practices

### 1. Source Quality
- Ensure diverse, high-quality sources for better insights
- Verify DOK Level 1 facts for accuracy
- Review source summaries for completeness

### 2. Knowledge Tree Structure
- Use clear, descriptive category names
- Maintain logical hierarchical relationships
- Balance breadth and depth of categorization

### 3. Insight Generation
- Ensure insights are evidence-based
- Provide appropriate confidence scores
- Link insights to supporting sources

### 4. Spiky POV Analysis
- Focus on genuinely contrarian perspectives
- Provide strong reasoning for each position
- Balance "truths" and "myths" where appropriate

## Troubleshooting

### Common Issues

1. **Missing DOK taxonomy data**
   - Check if the DOK workflow was executed
   - Verify database migration was applied
   - Ensure DOK taxonomy endpoints are accessible

2. **Empty knowledge tree**
   - Verify source summarization completed successfully
   - Check for errors in categorization process
   - Ensure sources contain sufficient content

3. **No insights generated**
   - Verify knowledge tree contains data
   - Check for LLM API errors during insight generation
   - Ensure research context is clear and specific

### Error Handling

The system includes comprehensive error handling:
- Database connection failures are logged and retried
- LLM API errors are caught and gracefully handled
- Partial failures preserve completed work
- Full error traces are available in logs

## Next Steps

The DOK taxonomy system is now fully integrated and ready for use. Future enhancements could include:

1. **Advanced Visualization** - Interactive knowledge tree and insight graphs
2. **Export Capabilities** - PDF, Word, and other format exports
3. **Collaboration Features** - Multi-user insight annotation and discussion
4. **Machine Learning** - Automated quality scoring and insight ranking
5. **Integration Extensions** - Connect to external knowledge bases and citation managers

---

For technical support or questions about the DOK taxonomy system, please refer to the source code documentation or contact the development team.
