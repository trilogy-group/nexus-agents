

"""Project-level CSV exporter for consolidated data aggregation results."""

import logging
import json
import io
import csv
import os
from typing import List, Dict, Any

from src.database.project_data_repository import ProjectDataRepository


logger = logging.getLogger(__name__)


class ProjectCSVExporter:
    """Export project-level consolidated aggregation results to CSV."""
    
    def __init__(self, project_data_repository: ProjectDataRepository):
        """Initialize the project CSV exporter."""
        self.project_data_repository = project_data_repository
    
    async def export(self, project_id: str) -> str:
        """
        Export project-level consolidated entities to CSV.
        
        Args:
            project_id: The project identifier
            
        Returns:
            Path to the exported CSV file
        """
        logger.info(f"Exporting project-level consolidated entities for project {project_id} to CSV")
        
        try:
            # Fetch from database
            results = await self._get_project_entities(project_id)
            
            if not results:
                logger.warning(f"No consolidated entities found for project {project_id}")
                # Create empty CSV with headers
                csv_path = f"exports/project_{project_id}_consolidated.csv"
                # Ensure exports directory exists
                os.makedirs("exports", exist_ok=True)
                
                # Create empty CSV file
                with open(csv_path, "w") as f:
                    f.write("")
                
                return csv_path
            
            # Determine all unique attributes
            all_attributes = set()
            for result in results:
                attributes = result.get("consolidated_attributes", {})
                if isinstance(attributes, str):
                    try:
                        attributes = json.loads(attributes)
                    except json.JSONDecodeError:
                        continue
                
                if isinstance(attributes, dict):
                    all_attributes.update(attributes.keys())
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.DictWriter(
                output, 
                fieldnames=["name", "unique_identifier", "entity_type", "confidence_score"] + sorted(list(all_attributes))
            )
            writer.writeheader()
            
            # Write rows
            for result in results:
                attributes = result.get("consolidated_attributes", {})
                if isinstance(attributes, str):
                    try:
                        attributes = json.loads(attributes)
                    except json.JSONDecodeError:
                        attributes = {}
                
                row = {
                    "name": result.get("name", "Unknown"),
                    "unique_identifier": result.get("unique_identifier", ""),
                    "entity_type": result.get("entity_type", ""),
                    "confidence_score": result.get("confidence_score", 1.0)
                }
                
                if isinstance(attributes, dict):
                    row.update(attributes)
                
                writer.writerow(row)
            
            # Save to file
            csv_path = f"exports/project_{project_id}_consolidated.csv"
            
            # Ensure exports directory exists
            os.makedirs("exports", exist_ok=True)
            
            with open(csv_path, "w") as f:
                f.write(output.getvalue())
            
            logger.info(f"Exported {len(results)} consolidated project entities to CSV at {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Error exporting project CSV for project {project_id}: {str(e)}")
            raise
    
    async def _get_project_entities(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get consolidated entities for a project from the database.
        
        Args:
            project_id: The project identifier
            
        Returns:
            List of consolidated project entities
        """
        try:
            return await self.project_data_repository.get_project_entities(project_id)
        except Exception as e:
            logger.error(f"Error fetching project entities for project {project_id}: {str(e)}")
            return []

