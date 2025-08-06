# Nexus Agents API Endpoints

## Research Tasks

### Create Research Task
**POST** `/tasks`

Create a new research task with either analytical report or data aggregation research type.

#### Request Body
```json
{
  "title": "string",
  "research_query": "string",
  "user_id": "string (optional)",
  "research_type": "analytical_report | data_aggregation",
  "data_aggregation_config": {
    "entities": ["string"],
    "attributes": ["string"],
    "search_space": "string",
    "domain_hint": "string (optional)"
  },
  "project_id": "string (optional)"
}
```

#### Response
```json
{
  "task_id": "string",
  "title": "string",
  "research_query": "string",
  "research_type": "analytical_report | data_aggregation",
  "status": "pending",
  "user_id": "string",
  "project_id": "string",
  "created_at": "datetime",
  "message": "string"
}
```

### Get All Tasks
**GET** `/tasks`

Retrieve all research tasks with their status and artifacts.

#### Response
```json
[
  {
    "task_id": "string",
    "title": "string",
    "description": "string",
    "status": "string",
    "continuous_mode": "boolean",
    "continuous_interval_hours": "integer (optional)",
    "created_at": "string",
    "updated_at": "string",
    "artifacts": [
      {
        "type": "string",
        "name": "string",
        "path": "string",
        "size": "integer",
        "created_at": "string"
      }
    ]
  }
]
```

### Get Task Status
**GET** `/tasks/{task_id}`

Retrieve the status and details of a specific research task.

#### Response
```json
{
  "task_id": "string",
  "title": "string",
  "description": "string",
  "status": "string",
  "continuous_mode": "boolean",
  "continuous_interval_hours": "integer (optional)",
  "created_at": "string",
  "updated_at": "string",
  "artifacts": [
    {
      "type": "string",
      "name": "string",
      "path": "string",
      "size": "integer",
      "created_at": "string"
    }
  ]
}
```

### Delete Task
**DELETE** `/tasks/{task_id}`

Delete a research task and all related data.

#### Response
```json
{
  "message": "string",
  "task_id": "string",
  "deleted": "boolean"
}
```

### Get Task Report
**GET** `/tasks/{task_id}/report`

Retrieve the final report for a completed research task.

#### Response
- **Content-Type**: `text/plain` for analytical reports
- **Content-Type**: `application/json` for data aggregation results
- **Body**: Report content or JSON data depending on research type

### Export Data Aggregation CSV
**GET** `/tasks/{task_id}/export/csv`

Export data aggregation results as a CSV file.

#### Response
- **Content-Type**: `text/csv`
- **Body**: CSV file with aggregated entity data
- **Filename**: `{task_id}_data.csv`

#### Error Responses
- **404**: CSV file not found and exporter not available
- **500**: Failed to export CSV

## DOK Taxonomy

### Get DOK Statistics
**GET** `/api/dok/{task_id}/stats`

Get DOK taxonomy statistics for a research task.

#### Response
```json
{
  "total_sources": 15,
  "total_dok1_facts": 45,
  "knowledge_tree_nodes": 8,
  "total_insights": 12,
  "spiky_povs_truths": 3,
  "spiky_povs_myths": 2,
  "total_spiky_povs": 5
}
```

### Get Knowledge Tree
**GET** `/api/dok/{task_id}/knowledge-tree`

Get the knowledge tree for a research task.

#### Response
```json
[
  {
    "node_id": "string",
    "category": "string",
    "subcategory": "string",
    "summary": "string",
    "dok_level": 1,
    "source_count": 5,
    "sources": [
      {
        "source_id": "string",
        "url": "string",
        "title": "string",
        "relevance_score": 0.95
      }
    ]
  }
]
```

### Get Insights
**GET** `/api/dok/{task_id}/insights`

Get insights for a research task.

#### Response
```json
[
  {
    "insight_id": "string",
    "category": "string",
    "insight_text": "string",
    "confidence_score": 0.85
  }
]
```

### Get Spiky POVs
**GET** `/api/dok/{task_id}/spiky-povs`

Get spiky POVs (controversial points of view) for a research task.

#### Response
```json
[
  {
    "pov_id": "string",
    "pov_type": "truth",
    "statement": "string",
    "reasoning": "string",
    "supporting_insights": [
      {
        "insight_id": "string",
        "insight_text": "string"
      }
    ]
  }
]
```

### Get Bibliography
**GET** `/api/dok/{task_id}/bibliography`

Get bibliography for a research task.

#### Response
```json
{
  "sources": [
    {
      "source_id": "string",
      "url": "string",
      "title": "string",
      "description": "string",
      "provider": "string",
      "accessed_at": "datetime"
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

### Get Source Summaries
**GET** `/api/dok/{task_id}/source-summaries`

Get source summaries for a research task.

#### Response
```json
[
  {
    "summary_id": "string",
    "source_id": "string",
    "summary": "string",
    "dok1_facts": ["fact1", "fact2"],
    "dok_level": 1,
    "subtopic": "string"
  }
]
```

### Get Complete DOK Data
**GET** `/api/dok/{task_id}/complete`

Get complete DOK taxonomy data for a research task.

#### Response
```json
{
  "stats": {
    "total_sources": 15,
    "knowledge_tree_nodes": 8,
    "total_insights": 12,
    "total_spiky_povs": 5
  },
  "knowledge_tree": [...],
  "insights": [...],
  "spiky_povs": [...],
  "bibliography": {...},
  "source_summaries": [...]
}
```

### DOK Health Check
**GET** `/api/dok/health`

Health check for DOK taxonomy service.

#### Response
```json
{
  "status": "healthy",
  "timestamp": "datetime"
}
```

## Projects

### Create Project
**POST** `/projects`

Create a new research project.

#### Request Body
```json
{
  "name": "string",
  "description": "string (optional)",
  "user_id": "string (optional)"
}
```

#### Response
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "user_id": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### List Projects
**GET** `/projects`

List all projects, optionally filtered by user.

#### Query Parameters
- `user_id` (optional): Filter projects by user ID

#### Response
```json
[
  {
    "id": "string",
    "name": "string",
    "description": "string",
    "user_id": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

### Get Project
**GET** `/projects/{project_id}`

Get project details by ID.

#### Response
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "user_id": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Update Project
**PUT** `/projects/{project_id}`

Update project details.

#### Request Body
```json
{
  "name": "string (optional)",
  "description": "string (optional)"
}
```

#### Response
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "user_id": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Delete Project
**DELETE** `/projects/{project_id}`

Delete a project and all associated data.

#### Response
```json
{
  "message": "string"
}
```

### List Project Tasks
**GET** `/projects/{project_id}/tasks`

List all research tasks in a project.

#### Response
```json
[
  {
    "task_id": "string",
    "title": "string",
    "research_query": "string",
    "status": "string",
    "research_type": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

### Create Project Task
**POST** `/projects/{project_id}/tasks`

Create a new research task within a project.

#### Request Body
```json
{
  "title": "string",
  "research_query": "string",
  "user_id": "string (optional)",
  "research_type": "analytical_report | data_aggregation",
  "data_aggregation_config": {
    "entities": ["string"],
    "attributes": ["string"],
    "search_space": "string",
    "domain_hint": "string (optional)"
  }
}
```

#### Response
```json
{
  "task_id": "string",
  "title": "string",
  "research_query": "string",
  "research_type": "analytical_report | data_aggregation",
  "status": "pending",
  "user_id": "string",
  "project_id": "string",
  "created_at": "datetime",
  "message": "string"
}
```

## Health Check

### System Health
**GET** `/health`

Check the health status of the API and its dependencies.

#### Response
```json
{
  "status": "healthy | unhealthy",
  "redis": "connected | disconnected | unhealthy",
  "postgresql": "connected | disconnected | unhealthy"
}
```

## Project Data Aggregation

### Get Project Entities
**GET** `/api/projects/{project_id}/entities`

Get all consolidated entities for a project.

#### Response
```json
[
  {
    "project_id": "string",
    "name": "string",
    "unique_identifier": "string",
    "entity_type": "string",
    "consolidated_attributes": {
      "attribute1": "value1",
      "attribute2": "value2"
    },
    "source_tasks": ["task_id1", "task_id2"],
    "confidence_score": 0.95,
    "data_lineage": {
      "attribute1": {
        "sources": [
          {
            "task_id": "task_id1",
            "confidence_score": 0.9,
            "timestamp": "2023-01-01T00:00:00Z"
          }
        ],
        "last_updated": "2023-01-01T00:00:00Z"
      },
      "attribute2": {
        "sources": [
          {
            "task_id": "task_id2",
            "confidence_score": 0.85,
            "timestamp": "2023-01-01T00:00:00Z"
          }
        ],
        "last_updated": "2023-01-01T00:00:00Z"
      },
      "metadata": {
        "consolidation_timestamp": "2023-01-01T00:00:00Z",
        "source_tasks": ["task_id1", "task_id2"],
        "average_confidence": 0.875
      }
    },
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

### Get Project Entity
**GET** `/api/projects/{project_id}/entities/{unique_identifier}`

Get a specific consolidated entity for a project.

#### Response
```json
{
  "project_id": "string",
  "name": "string",
  "unique_identifier": "string",
  "entity_type": "string",
  "consolidated_attributes": {
    "attribute1": "value1",
    "attribute2": "value2"
  },
  "source_tasks": ["task_id1", "task_id2"],
  "confidence_score": 0.95,
  "data_lineage": {
    "attribute1": {
      "sources": [
        {
          "task_id": "task_id1",
          "confidence_score": 0.9,
          "timestamp": "2023-01-01T00:00:00Z"
        }
      ],
      "last_updated": "2023-01-01T00:00:00Z"
    },
    "attribute2": {
      "sources": [
        {
          "task_id": "task_id2",
          "confidence_score": 0.85,
          "timestamp": "2023-01-01T00:00:00Z"
        }
      ],
      "last_updated": "2023-01-01T00:00:00Z"
    },
    "metadata": {
      "consolidation_timestamp": "2023-01-01T00:00:00Z",
      "source_tasks": ["task_id1", "task_id2"],
      "average_confidence": 0.875
    }
  },
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Get Project DOK Taxonomy
**GET** `/api/projects/{project_id}/dok`

Get consolidated DOK taxonomy data for a project.

#### Response
```json
{
  "project_id": "string",
  "knowledge_tree": [...],
  "insights": [...],
  "spiky_povs": {...},
  "consolidated_bibliography": {...},
  "source_tasks": ["task_id1", "task_id2"],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Get Project Entity Lineage
**GET** `/api/projects/{project_id}/lineage/{unique_identifier}`

Get data lineage information for a specific project entity.

#### Response
```json
{
  "attribute1": {
    "sources": [
      {
        "task_id": "task_id1",
        "confidence_score": 0.9,
        "timestamp": "2023-01-01T00:00:00Z"
      }
    ],
    "last_updated": "2023-01-01T00:00:00Z"
  },
  "attribute2": {
    "sources": [
      {
        "task_id": "task_id2",
        "confidence_score": 0.85,
        "timestamp": "2023-01-01T00:00:00Z"
      }
    ],
    "last_updated": "2023-01-01T00:00:00Z"
  },
  "metadata": {
    "consolidation_timestamp": "2023-01-01T00:00:00Z",
    "source_tasks": ["task_id1", "task_id2"],
    "average_confidence": 0.875
  }
}
```

### Trigger Project Entity Consolidation
**POST** `/api/projects/{project_id}/consolidate`

Trigger project-level entity consolidation for all tasks in a project.

#### Response
```json
{
  "message": "Project entity consolidation completed successfully",
  "entities_processed": 1085,
  "consolidation_timestamp": "2023-01-01T00:00:00Z"
}
```

#### Error Responses
- **404 Not Found**: Project not found
- **500 Internal Server Error**: Consolidation failed

### Export Project Entities CSV
**GET** `/api/projects/{project_id}/export/csv`

Export project consolidated entities as CSV file.

#### Response
- **Content-Type**: `text/csv`
- **Content-Disposition**: `attachment; filename="project_{project_id}_entities.csv"`

CSV file containing:
- Entity metadata (name, type, unique_identifier)
- Consolidated attributes (flattened)
- Source tasks and confidence scores
- Data lineage information
- Timestamps

#### Error Responses
- **404 Not Found**: Project not found or no entities available
- **500 Internal Server Error**: CSV generation failed

### Get Project Knowledge Graph
**GET** `/projects/{project_id}/knowledge`

Get project knowledge graph data.

#### Response
```json
{
  "project_id": "string",
  "knowledge_data": {
    "nodes": [
      {
        "id": "string",
        "label": "string",
        "type": "string",
        "attributes": {}
      }
    ],
    "edges": [
      {
        "source": "string",
        "target": "string",
        "relationship": "string",
        "weight": 0.95
      }
    ]
  },
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Update Project Knowledge Graph
**PUT** `/projects/{project_id}/knowledge`

Update project knowledge graph data.

#### Request Body
```json
{
  "knowledge_data": {
    "nodes": [
      {
        "id": "string",
        "label": "string",
        "type": "string",
        "attributes": {}
      }
    ],
    "edges": [
      {
        "source": "string",
        "target": "string",
        "relationship": "string",
        "weight": 0.95
      }
    ]
  }
}
```

#### Response
```json
{
  "message": "Project knowledge graph updated successfully",
  "project_id": "string",
  "updated_at": "datetime"
}
```
