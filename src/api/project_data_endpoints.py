
"""
API endpoints for Project-Level Data Aggregation

This module provides REST API endpoints for accessing project-level consolidated entities
and their data lineage information.
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.database.project_data_repository import ProjectDataRepository


logger = logging.getLogger(__name__)

# Create router for project data endpoints
router = APIRouter(prefix="/api/projects", tags=["Project Data"])

# This router handles specialized project data operations
# Core project CRUD operations are in the main api.py file

# Dependency to get project data repository
async def get_project_data_repository() -> ProjectDataRepository:
    """Get project data repository instance."""
    return ProjectDataRepository()


class ProjectEntityResponse(BaseModel):
    """Response model for project entities"""
    project_id: str
    name: str
    unique_identifier: str
    entity_type: str
    consolidated_attributes: Dict[str, Any]
    source_tasks: List[str]
    confidence_score: float
    data_lineage: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str


class ProjectDOKResponse(BaseModel):
    """Response model for project DOK taxonomy data"""
    project_id: str
    knowledge_tree: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    spiky_povs: Dict[str, List[Dict[str, Any]]]
    consolidated_bibliography: Dict[str, Any]
    source_tasks: List[str]
    created_at: str
    updated_at: str
@router.get("/{project_id}/entities/{unique_identifier}")
async def get_project_entity(
    project_id: str,
    unique_identifier: str,
    project_repo: ProjectDataRepository = Depends(get_project_data_repository)
) -> ProjectEntityResponse:
    """Get a specific consolidated entity for a project."""
    try:
        entity = await project_repo.get_project_entity_by_identifier(project_id, unique_identifier)
        
        if not entity:
            raise HTTPException(status_code=404, detail="Project entity not found")
            
        return ProjectEntityResponse(
            project_id=entity['project_id'],
            name=entity['name'],
            unique_identifier=entity['unique_identifier'],
            entity_type=entity['entity_type'],
            consolidated_attributes=entity['consolidated_attributes'],
            source_tasks=entity['source_tasks'],
            confidence_score=entity['confidence_score'],
            data_lineage=entity.get('data_lineage'),
            created_at=entity['created_at'].isoformat() if entity.get('created_at') else None,
            updated_at=entity['updated_at'].isoformat() if entity.get('updated_at') else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project entity {unique_identifier} for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/dok")
async def get_project_dok(
    project_id: str,
    project_repo: ProjectDataRepository = Depends(get_project_data_repository)
) -> ProjectDOKResponse:
    """Get consolidated DOK taxonomy data for a project."""
    try:
        dok_data = await project_repo.get_project_dok_taxonomy(project_id)
        
        if not dok_data:
            raise HTTPException(status_code=404, detail="Project DOK taxonomy not found")
            
        return ProjectDOKResponse(
            project_id=dok_data['project_id'],
            knowledge_tree=dok_data['knowledge_tree'],
            insights=dok_data['insights'],
            spiky_povs=dok_data['spiky_povs'],
            consolidated_bibliography=dok_data['consolidated_bibliography'],
            source_tasks=dok_data['source_tasks'],
            created_at=dok_data['created_at'].isoformat() if dok_data.get('created_at') else None,
            updated_at=dok_data['updated_at'].isoformat() if dok_data.get('updated_at') else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project DOK taxonomy for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/entities/{unique_identifier}/lineage")
async def get_project_entity_lineage(
    project_id: str,
    unique_identifier: str,
    project_repo: ProjectDataRepository = Depends(get_project_data_repository)
) -> Dict[str, Any]:
    """Get data lineage information for a specific project entity."""
    try:
        entity = await project_repo.get_project_entity_by_identifier(project_id, unique_identifier)
        
        if not entity:
            raise HTTPException(status_code=404, detail="Project entity not found")
            
        # Return only the data lineage information
        return entity.get('data_lineage', {})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project entity lineage for project {project_id}, entity {unique_identifier}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/consolidate")
async def trigger_project_consolidation(
    project_id: str
) -> Dict[str, Any]:
    """Trigger project-level entity consolidation for all tasks in a project."""
    try:
        # Import here to avoid circular imports
        from ..services.project_data_aggregator import ProjectDataAggregator
        from ..database.data_aggregation_repository import DataAggregationRepository
        from ..persistence.postgres_knowledge_base import PostgresKnowledgeBase
        
        # Get the global knowledge base by importing it properly
        import asyncpg
        import os
        
        # Create a new connection pool for this operation
        db_url = os.getenv('DATABASE_URL', 'postgresql://nexus_user:nexus_password@localhost:5432/nexus_agents')
        
        # Create a temporary knowledge base instance
        kb = PostgresKnowledgeBase()
        await kb.connect()
        
        try:
            # Initialize repositories with the connected knowledge base
            project_repo = ProjectDataRepository(kb)
            data_aggregation_repo = DataAggregationRepository(kb)
            project_data_aggregator = ProjectDataAggregator(
                project_data_repository=project_repo,
                data_aggregation_repository=data_aggregation_repo
            )
        
            logger.info(f"Starting manual project-level entity consolidation for project {project_id}")
            
            # Trigger consolidation
            consolidated_entities = await project_data_aggregator.consolidate_project_entities(project_id)
            
            logger.info(f"Completed manual project-level entity consolidation for project {project_id}. Consolidated {len(consolidated_entities)} entities.")
            
            return {
                "message": "Project-level entity consolidation completed successfully",
                "project_id": project_id,
                "consolidated_entities_count": len(consolidated_entities),
                "status": "success"
            }
            
        finally:
            # Clean up the temporary knowledge base connection
            await kb.disconnect()
        
    except Exception as e:
        logger.error(f"Error triggering project consolidation for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to consolidate project entities: {str(e)}")


@router.get("/{project_id}/export/csv")
async def export_project_entities_csv(project_id: str):
    """Export project consolidated entities as CSV."""
    import os
    
    # Check if CSV file already exists
    csv_path = f"exports/project_{project_id}_consolidated.csv"
    
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        # Serve existing CSV file
        return FileResponse(csv_path, filename=f"project_{project_id}_entities.csv")
    
    # If no existing file, try to generate it
    try:
        # Create project CSV exporter directly
        from src.export.project_csv_exporter import ProjectCSVExporter
        from src.database.project_data_repository import ProjectDataRepository
        
        project_data_repository = ProjectDataRepository()
        project_csv_exporter = ProjectCSVExporter(project_data_repository=project_data_repository)
        
        # Generate CSV export
        csv_path = await project_csv_exporter.export(project_id)
        
        # Return CSV file
        return FileResponse(csv_path, filename=f"project_{project_id}_entities.csv")
        
    except Exception as e:
        logger.error(f"Error exporting project entities CSV for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {str(e)}")
