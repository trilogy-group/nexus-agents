"""
API endpoints for DOK Taxonomy and Bibliography Management

This module provides REST API endpoints for accessing DOK taxonomy data including
knowledge trees, insights, spiky POVs, and bibliography information.
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.database.dok_taxonomy_repository import DOKTaxonomyRepository
from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase


logger = logging.getLogger(__name__)

# Create router for DOK taxonomy endpoints
router = APIRouter(prefix="/api/dok", tags=["DOK Taxonomy"])


class DOKTaxonomyStats(BaseModel):
    """Statistics for DOK taxonomy data"""
    total_sources: int
    total_dok1_facts: int
    knowledge_tree_nodes: int
    total_insights: int
    spiky_povs_truths: int
    spiky_povs_myths: int
    total_spiky_povs: int


class KnowledgeNodeResponse(BaseModel):
    """Response model for knowledge tree nodes"""
    node_id: str
    category: str
    subcategory: Optional[str]
    summary: str
    dok_level: int
    source_count: int
    sources: List[Dict[str, Any]]


class InsightResponse(BaseModel):
    """Response model for insights"""
    insight_id: str
    category: str
    insight_text: str
    confidence_score: float
    supporting_sources: List[Dict[str, Any]]


class SpikyPOVResponse(BaseModel):
    """Response model for spiky POVs"""
    pov_id: str
    pov_type: str
    statement: str
    reasoning: str
    supporting_insights: List[Dict[str, Any]]


class BibliographyResponse(BaseModel):
    """Response model for bibliography"""
    sources: List[Dict[str, Any]]
    total_sources: int
    section_usage: Dict[str, int]


# Dependency to get DOK taxonomy repository
async def get_dok_repository() -> DOKTaxonomyRepository:
    """Get DOK taxonomy repository instance."""
    return DOKTaxonomyRepository()


@router.get("/tasks/{task_id}/stats")
async def get_dok_stats(
    task_id: str,
    dok_repo: DOKTaxonomyRepository = Depends(get_dok_repository)
) -> DOKTaxonomyStats:
    """Get DOK taxonomy statistics for a research task."""
    try:
        # Get all DOK taxonomy data for the task
        knowledge_tree = await dok_repo.get_knowledge_tree(task_id)
        insights = await dok_repo.get_insights_by_task(task_id)
        spiky_povs = await dok_repo.get_spiky_povs_by_task(task_id)
        source_summaries = await dok_repo.get_source_summaries_by_task(task_id)
        
        # Calculate statistics
        total_facts = sum(len(summary.get('dok1_facts', [])) for summary in source_summaries)
        
        return DOKTaxonomyStats(
            total_sources=len(source_summaries),
            total_dok1_facts=total_facts,
            knowledge_tree_nodes=len(knowledge_tree),
            total_insights=len(insights),
            spiky_povs_truths=len(spiky_povs.get('truth', [])),
            spiky_povs_myths=len(spiky_povs.get('myth', [])),
            total_spiky_povs=len(spiky_povs.get('truth', [])) + len(spiky_povs.get('myth', []))
        )
        
    except Exception as e:
        logger.error(f"Error getting DOK stats for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/knowledge-tree")
async def get_knowledge_tree(
    task_id: str,
    dok_repo: DOKTaxonomyRepository = Depends(get_dok_repository)
) -> List[KnowledgeNodeResponse]:
    """Get the knowledge tree for a research task."""
    try:
        knowledge_tree = await dok_repo.get_knowledge_tree(task_id)
        
        return [
            KnowledgeNodeResponse(
                node_id=node['node_id'],
                category=node['category'],
                subcategory=node.get('subcategory'),
                summary=node['summary'],
                dok_level=node['dok_level'],
                source_count=len(node.get('sources', [])),
                sources=node.get('sources', [])
            )
            for node in knowledge_tree
        ]
        
    except Exception as e:
        logger.error(f"Error getting knowledge tree for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/insights")
async def get_insights(
    task_id: str,
    dok_repo: DOKTaxonomyRepository = Depends(get_dok_repository)
) -> List[InsightResponse]:
    """Get insights for a research task."""
    try:
        insights = await dok_repo.get_insights_by_task(task_id)
        
        return [
            InsightResponse(
                insight_id=insight['insight_id'],
                category=insight['category'],
                insight_text=insight['insight_text'],
                confidence_score=insight['confidence_score'],
                supporting_sources=insight.get('supporting_sources', [])
            )
            for insight in insights
        ]
        
    except Exception as e:
        logger.error(f"Error getting insights for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/spiky-povs")
async def get_spiky_povs(
    task_id: str,
    dok_repo: DOKTaxonomyRepository = Depends(get_dok_repository)
) -> Dict[str, List[SpikyPOVResponse]]:
    """Get spiky POVs for a research task."""
    try:
        spiky_povs = await dok_repo.get_spiky_povs_by_task(task_id)
        
        response = {}
        for pov_type, povs in spiky_povs.items():
            response[pov_type] = [
                SpikyPOVResponse(
                    pov_id=pov['pov_id'],
                    pov_type=pov_type,
                    statement=pov['statement'],
                    reasoning=pov['reasoning'],
                    supporting_insights=pov.get('supporting_insights', [])
                )
                for pov in povs
            ]
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting spiky POVs for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/bibliography")
async def get_bibliography(
    task_id: str,
    dok_repo: DOKTaxonomyRepository = Depends(get_dok_repository)
) -> BibliographyResponse:
    """Get bibliography for a research task."""
    try:
        bibliography = await dok_repo.get_bibliography_by_task(task_id)
        
        return BibliographyResponse(
            sources=bibliography.get('sources', []),
            total_sources=bibliography.get('total_sources', 0),
            section_usage=bibliography.get('section_usage', {})
        )
        
    except Exception as e:
        logger.error(f"Error getting bibliography for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/source-summaries")
async def get_source_summaries(
    task_id: str,
    dok_repo: DOKTaxonomyRepository = Depends(get_dok_repository)
) -> List[Dict[str, Any]]:
    """Get source summaries for a research task."""
    try:
        source_summaries = await dok_repo.get_source_summaries_by_task(task_id)
        return source_summaries
        
    except Exception as e:
        logger.error(f"Error getting source summaries for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/dok-complete")
async def get_complete_dok_data(
    task_id: str,
    dok_repo: DOKTaxonomyRepository = Depends(get_dok_repository)
) -> Dict[str, Any]:
    """Get complete DOK taxonomy data for a research task."""
    try:
        # Get all DOK taxonomy data
        knowledge_tree = await dok_repo.get_knowledge_tree(task_id)
        insights = await dok_repo.get_insights_by_task(task_id)
        spiky_povs = await dok_repo.get_spiky_povs_by_task(task_id)
        bibliography = await dok_repo.get_bibliography_by_task(task_id)
        source_summaries = await dok_repo.get_source_summaries_by_task(task_id)
        
        # Calculate comprehensive statistics
        total_facts = sum(len(summary.get('dok1_facts', [])) for summary in source_summaries)
        
        return {
            "task_id": task_id,
            "knowledge_tree": knowledge_tree,
            "insights": insights,
            "spiky_povs": spiky_povs,
            "bibliography": bibliography,
            "source_summaries": source_summaries,
            "stats": {
                "total_sources": len(source_summaries),
                "total_dok1_facts": total_facts,
                "knowledge_tree_nodes": len(knowledge_tree),
                "total_insights": len(insights),
                "spiky_povs_truths": len(spiky_povs.get('truth', [])),
                "spiky_povs_myths": len(spiky_povs.get('myth', [])),
                "total_spiky_povs": len(spiky_povs.get('truth', [])) + len(spiky_povs.get('myth', []))
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting complete DOK data for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for DOK taxonomy service."""
    return {"status": "healthy", "service": "dok_taxonomy"}
