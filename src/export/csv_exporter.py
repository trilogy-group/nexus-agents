"""CSV exporter for data aggregation results."""

import logging
import json
import io
import csv
from typing import List, Dict, Any

from src.database.data_aggregation_repository import DataAggregationRepository


logger = logging.getLogger(__name__)


class CSVExporter:
    """Export aggregation results to CSV."""
    
    def __init__(self, data_aggregation_repository: DataAggregationRepository):
        """Initialize the CSV exporter."""
        self.data_aggregation_repository = data_aggregation_repository
    
    async def export(self, task_id: str) -> str:
        """
        Export data aggregation results to CSV.
        
        Args:
            task_id: The research task identifier
            
        Returns:
            Path to the exported CSV file
        """
        logger.info(f"Exporting data aggregation results for task {task_id} to CSV")
        
        try:
            # Fetch from database
            results = await self._get_aggregation_results(task_id)
            
            if not results:
                logger.warning(f"No aggregation results found for task {task_id}")
                # Create empty CSV with headers
                csv_path = f"exports/{task_id}_aggregation.csv"
                # Ensure exports directory exists
                import os
                os.makedirs("exports", exist_ok=True)
                
                # Create empty CSV file
                with open(csv_path, "w") as f:
                    f.write("")
                
                return csv_path
            
            # Determine all unique attributes
            all_attributes = set()
            for result in results:
                entity_data = result.get("entity_data", {})
                if isinstance(entity_data, str):
                    try:
                        entity_data = json.loads(entity_data)
                    except json.JSONDecodeError:
                        continue
                
                attributes = entity_data.get("attributes", {})
                if isinstance(attributes, dict):
                    all_attributes.update(attributes.keys())
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.DictWriter(
                output, 
                fieldnames=["name", "unique_identifier"] + sorted(list(all_attributes))
            )
            writer.writeheader()
            
            # Write rows
            for result in results:
                entity_data = result.get("entity_data", {})
                if isinstance(entity_data, str):
                    try:
                        entity_data = json.loads(entity_data)
                    except json.JSONDecodeError:
                        entity_data = {}
                
                row = {
                    "name": entity_data.get("name", "Unknown"),
                    "unique_identifier": result.get("unique_identifier", "")
                }
                
                attributes = entity_data.get("attributes", {})
                if isinstance(attributes, dict):
                    row.update(attributes)
                
                writer.writerow(row)
            
            # Save to file
            csv_path = f"exports/{task_id}_aggregation.csv"
            
            # Ensure exports directory exists
            import os
            os.makedirs("exports", exist_ok=True)
            
            with open(csv_path, "w") as f:
                f.write(output.getvalue())
            
            logger.info(f"Exported {len(results)} aggregation results to CSV at {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Error exporting CSV for task {task_id}: {str(e)}")
            raise
    
    async def _get_aggregation_results(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get aggregation results for a task from the database.
        
        Args:
            task_id: The research task identifier
            
        Returns:
            List of aggregation results
        """
        try:
            return await self.data_aggregation_repository.get_data_aggregation_results(task_id)
        except Exception as e:
            logger.error(f"Error fetching aggregation results for task {task_id}: {str(e)}")
            return []
