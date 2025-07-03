#!/usr/bin/env python3
"""
Export PostgreSQL data to JSON files for frontend development.

This script exports all task data from PostgreSQL to JSON files that can be
used by frontend engineers without needing API keys or running the full backend.
"""
import asyncio
import asyncpg
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, using environment variables only")


async def export_data():
    """Export all relevant data from PostgreSQL to JSON files."""
    
    # Get database connection info from environment
    # Prioritize individual POSTGRES_* variables from .env over DATABASE_URL
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    
    # If individual variables are set, use them
    if host and user and password:
        port = port or "5432"
        db = db or "nexus_agents"
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        print(f"Using individual POSTGRES_* variables from .env")
    else:
        # Fall back to DATABASE_URL if individual variables not set
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/nexus_agents")
        print(f"Using DATABASE_URL environment variable")
    
    # Redact password for display
    display_url = db_url.split('@')[0].split(':')[:-1] + ["[REDACTED]"] + ['@' + db_url.split('@')[1]] if '@' in db_url else [db_url]
    
    print(f"Connecting to database: {''.join(display_url)}")
    
    try:
        conn = await asyncpg.connect(db_url)
        print("✅ Connected to PostgreSQL")
        
        # Create export directory
        export_dir = Path("data/db_export")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Export research_tasks
        print("📦 Exporting research_tasks...")
        tasks = await conn.fetch("SELECT * FROM research_tasks ORDER BY created_at DESC")
        tasks_data = []
        for task in tasks:
            task_dict = dict(task)
            # Convert datetime objects to ISO strings
            for key, value in task_dict.items():
                if isinstance(value, datetime):
                    task_dict[key] = value.isoformat()
            tasks_data.append(task_dict)
        
        with open(export_dir / "research_tasks.json", "w") as f:
            json.dump(tasks_data, f, indent=2, default=str)
        print(f"   Exported {len(tasks_data)} tasks")
        
        # Export task_operations
        print("📦 Exporting task_operations...")
        operations = await conn.fetch("SELECT * FROM task_operations ORDER BY started_at DESC")
        operations_data = []
        for op in operations:
            op_dict = dict(op)
            # Convert datetime objects to ISO strings
            for key, value in op_dict.items():
                if isinstance(value, datetime):
                    op_dict[key] = value.isoformat()
            operations_data.append(op_dict)
        
        with open(export_dir / "task_operations.json", "w") as f:
            json.dump(operations_data, f, indent=2, default=str)
        print(f"   Exported {len(operations_data)} operations")
        
        # Export operation_evidence
        print("📦 Exporting operation_evidence...")
        evidence = await conn.fetch("SELECT * FROM operation_evidence ORDER BY created_at DESC")
        evidence_data = []
        for ev in evidence:
            ev_dict = dict(ev)
            # Convert datetime objects to ISO strings
            for key, value in ev_dict.items():
                if isinstance(value, datetime):
                    ev_dict[key] = value.isoformat()
            evidence_data.append(ev_dict)
        
        with open(export_dir / "operation_evidence.json", "w") as f:
            json.dump(evidence_data, f, indent=2, default=str)
        print(f"   Exported {len(evidence_data)} evidence items")
        
        # Export artifacts (research reports)
        print("📦 Exporting artifacts...")
        artifacts = await conn.fetch("SELECT * FROM artifacts ORDER BY created_at DESC")
        artifacts_data = []
        for artifact in artifacts:
            artifact_dict = dict(artifact)
            # Convert datetime objects to ISO strings
            for key, value in artifact_dict.items():
                if isinstance(value, datetime):
                    artifact_dict[key] = value.isoformat()
            artifacts_data.append(artifact_dict)
        
        with open(export_dir / "artifacts.json", "w") as f:
            json.dump(artifacts_data, f, indent=2, default=str)
        print(f"   Exported {len(artifacts_data)} artifacts")
        
        # Export research_subtasks
        print("📦 Exporting research_subtasks...")
        subtasks = await conn.fetch("SELECT * FROM research_subtasks ORDER BY created_at DESC")
        subtasks_data = []
        for subtask in subtasks:
            subtask_dict = dict(subtask)
            # Convert datetime objects to ISO strings
            for key, value in subtask_dict.items():
                if isinstance(value, datetime):
                    subtask_dict[key] = value.isoformat()
            subtasks_data.append(subtask_dict)
        
        with open(export_dir / "research_subtasks.json", "w") as f:
            json.dump(subtasks_data, f, indent=2, default=str)
        print(f"   Exported {len(subtasks_data)} subtasks")
        
        # Export sources
        print("📦 Exporting sources...")
        sources = await conn.fetch("SELECT * FROM sources ORDER BY accessed_at DESC")
        sources_data = []
        for source in sources:
            source_dict = dict(source)
            # Convert datetime objects to ISO strings
            for key, value in source_dict.items():
                if isinstance(value, datetime):
                    source_dict[key] = value.isoformat()
            sources_data.append(source_dict)
        
        with open(export_dir / "sources.json", "w") as f:
            json.dump(sources_data, f, indent=2, default=str)
        print(f"   Exported {len(sources_data)} sources")
        
        # Create export metadata
        metadata = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "tables_exported": {
                "research_tasks": len(tasks_data),
                "task_operations": len(operations_data),
                "operation_evidence": len(evidence_data),
                "artifacts": len(artifacts_data),
                "research_subtasks": len(subtasks_data),
                "sources": len(sources_data)
            },
            "database_url": db_url.split('@')[0] + "@[REDACTED]",  # Hide credentials
            "export_version": "1.0"
        }
        
        with open(export_dir / "export_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✅ Export completed successfully!")
        print(f"📁 Data exported to: {export_dir.absolute()}")
        print(f"📊 Total items: {sum(metadata['tables_exported'].values())}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            await conn.close()
    
    return True


if __name__ == "__main__":
    import sys
    
    # Check if DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("⚠️  DATABASE_URL environment variable not set.")
        print("   Please set it to your PostgreSQL connection string:")
        print("   export DATABASE_URL='postgresql://user:password@host:port/database'")
        sys.exit(1)
    
    # Run the export
    success = asyncio.run(export_data())
    sys.exit(0 if success else 1)
