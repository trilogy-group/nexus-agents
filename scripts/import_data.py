#!/usr/bin/env python3
"""
Import JSON data files back into PostgreSQL for frontend development.

This script imports exported JSON data into a fresh PostgreSQL instance,
allowing teams to restore realistic test data.
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


async def import_data():
    """Import JSON data files into PostgreSQL."""
    
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
    
    # Check if export data exists
    export_dir = Path("data/db_export")
    if not export_dir.exists():
        print(f"❌ Export directory not found: {export_dir.absolute()}")
        print("   Please run scripts/export_data.py first")
        return False
    
    metadata_file = export_dir / "export_metadata.json"
    if not metadata_file.exists():
        print(f"❌ Export metadata not found: {metadata_file}")
        return False
    
    # Load metadata
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
    
    print(f"📦 Found export from {metadata['export_timestamp']}")
    print(f"📊 Tables to import: {metadata['tables_exported']}")
    
    try:
        conn = await asyncpg.connect(db_url)
        print("✅ Connected to PostgreSQL")
        
        # Check if tables exist (they should be created by the schema)
        tables_to_check = [
            'research_tasks', 'task_operations', 'operation_evidence', 
            'artifacts', 'research_subtasks', 'sources'
        ]
        
        for table in tables_to_check:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)", 
                table
            )
            if not exists:
                print(f"❌ Table {table} does not exist. Please run schema creation first.")
                return False
        
        print("✅ All required tables exist")
        
        # Clear existing data (optional - comment out if you want to append)
        print("🧹 Clearing existing data...")
        for table in reversed(tables_to_check):  # Reverse order to handle foreign keys
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            if count > 0:
                await conn.execute(f"DELETE FROM {table}")
                print(f"   Cleared {count} rows from {table}")
        
        # Import research_tasks
        tasks_file = export_dir / "research_tasks.json"
        if tasks_file.exists():
            print("📥 Importing research_tasks...")
            with open(tasks_file, "r") as f:
                tasks_data = json.load(f)
            
            for task in tasks_data:
                await conn.execute("""
                    INSERT INTO research_tasks (
                        task_id, title, description, research_query, status, 
                        created_at, updated_at, completed_at, metadata, 
                        decomposition, plan, results, summary, reasoning
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """, 
                    task['task_id'], task['title'], task['description'], 
                    task.get('research_query'), task['status'],
                    datetime.fromisoformat(task['created_at']) if task.get('created_at') else None,
                    datetime.fromisoformat(task['updated_at']) if task.get('updated_at') else None,
                    datetime.fromisoformat(task['completed_at']) if task.get('completed_at') else None,
                    task.get('metadata'),  # Already JSON string from export
                    task.get('decomposition'),  # Already JSON string from export
                    task.get('plan'),  # Already JSON string from export
                    task.get('results'),  # Already JSON string from export
                    task.get('summary'),  # Already JSON string from export
                    task.get('reasoning')  # Already JSON string from export
                )
            print(f"   Imported {len(tasks_data)} tasks")
        
        # Import task_operations
        operations_file = export_dir / "task_operations.json"
        if operations_file.exists():
            print("📥 Importing task_operations...")
            with open(operations_file, "r") as f:
                operations_data = json.load(f)
            
            for op in operations_data:
                await conn.execute("""
                    INSERT INTO task_operations (
                        operation_id, task_id, operation_type, operation_name, status,
                        agent_type, started_at, completed_at, duration_ms,
                        input_data, output_data, error_message, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                    op['operation_id'], op['task_id'], op['operation_type'], 
                    op['operation_name'], op['status'], op.get('agent_type'),
                    datetime.fromisoformat(op['started_at']) if op.get('started_at') else None,
                    datetime.fromisoformat(op['completed_at']) if op.get('completed_at') else None,
                    op.get('duration_ms'),
                    op.get('input_data'),  # Already JSON string from export
                    op.get('output_data'),  # Already JSON string from export
                    op.get('error_message'),
                    op.get('metadata')  # Already JSON string from export
                )
            print(f"   Imported {len(operations_data)} operations")
        
        # Import operation_evidence
        evidence_file = export_dir / "operation_evidence.json"
        if evidence_file.exists():
            print("📥 Importing operation_evidence...")
            with open(evidence_file, "r") as f:
                evidence_data = json.load(f)
            
            for ev in evidence_data:
                await conn.execute("""
                    INSERT INTO operation_evidence (
                        evidence_id, operation_id, evidence_type, evidence_data,
                        source_url, provider, created_at, size_bytes, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    ev['evidence_id'], ev['operation_id'], ev['evidence_type'],
                    ev.get('evidence_data'),  # Already JSON string from export
                    ev.get('source_url'), ev.get('provider'),
                    datetime.fromisoformat(ev['created_at']) if ev.get('created_at') else None,
                    ev.get('size_bytes'),
                    ev.get('metadata')  # Already JSON string from export
                )
            print(f"   Imported {len(evidence_data)} evidence items")
        
        # Import artifacts
        artifacts_file = export_dir / "artifacts.json"
        if artifacts_file.exists():
            print("📥 Importing artifacts...")
            with open(artifacts_file, "r") as f:
                artifacts_data = json.load(f)
            
            for artifact in artifacts_data:
                await conn.execute("""
                    INSERT INTO artifacts (
                        artifact_id, task_id, subtask_id, title, type, format,
                        file_path, content, metadata, created_at, updated_at,
                        size_bytes, checksum
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                    artifact['artifact_id'], artifact.get('task_id'), artifact.get('subtask_id'),
                    artifact['title'], artifact['type'], artifact['format'],
                    artifact.get('file_path'),
                    artifact.get('content'),  # Already JSON string from export
                    artifact.get('metadata'),  # Already JSON string from export
                    datetime.fromisoformat(artifact['created_at']) if artifact.get('created_at') else None,
                    datetime.fromisoformat(artifact['updated_at']) if artifact.get('updated_at') else None,
                    artifact.get('size_bytes'), artifact.get('checksum')
                )
            print(f"   Imported {len(artifacts_data)} artifacts")
        
        print(f"\n✅ Import completed successfully!")
        print(f"📊 Data restored from export: {metadata['export_timestamp']}")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
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
    
    # Run the import
    success = asyncio.run(import_data())
    sys.exit(0 if success else 1)
