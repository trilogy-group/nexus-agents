#!/usr/bin/env python3
"""
Clean up test data from the database.

This script removes all research tasks and related data created during testing
to ensure a clean state for UI/API/frontend development.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.persistence.postgres_knowledge_base import PostgresKnowledgeBase


async def cleanup_test_data():
    """Clean up all test-related data from the database."""
    print("🧹 Starting test data cleanup...")
    
    # Connect to database
    db = PostgresKnowledgeBase()
    await db.connect()
    
    try:
        # Get all test tasks
        async with db.pool.acquire() as conn:
            # Find test tasks (those with test user IDs or specific test patterns)
            test_tasks = await conn.fetch("""
                SELECT task_id, research_query, user_id, created_at 
                FROM research_tasks 
                WHERE user_id LIKE 'test_%' 
                   OR research_query LIKE '%test%'
                   OR research_query LIKE '%Test%'
                   OR research_query LIKE '%AI video generation%'
                   OR research_query LIKE '%environmental impacts%'
                ORDER BY created_at DESC
            """)
            
            if not test_tasks:
                print("✅ No test data found to clean up")
                return
            
            print(f"📊 Found {len(test_tasks)} test tasks to clean up:")
            for task in test_tasks:
                print(f"  - {task['task_id']}: {task['research_query'][:60]}... (user: {task['user_id']})")
            
            # Confirm cleanup
            if len(sys.argv) > 1 and sys.argv[1] == "--force":
                confirm = "y"
            else:
                confirm = input(f"\n❓ Delete these {len(test_tasks)} test tasks and all related data? (y/N): ")
            
            if confirm.lower() != 'y':
                print("❌ Cleanup cancelled")
                return
            
            # Delete tasks and related data
            deleted_count = 0
            for task in test_tasks:
                task_id = task['task_id']
                try:
                    success = await db.delete_research_task(task_id)
                    if success:
                        deleted_count += 1
                        print(f"  ✅ Deleted task {task_id}")
                    else:
                        print(f"  ⚠️ Failed to delete task {task_id}")
                except Exception as e:
                    print(f"  ❌ Error deleting task {task_id}: {e}")
            
            print(f"\n🎉 Successfully cleaned up {deleted_count}/{len(test_tasks)} test tasks")
            
            # Additional cleanup: remove orphaned data
            print("\n🔍 Cleaning up orphaned data...")
            
            # Clean up orphaned research reports
            orphaned_reports = await conn.execute("""
                DELETE FROM research_reports 
                WHERE task_id NOT IN (SELECT task_id FROM research_tasks)
            """)
            print(f"  📄 Removed {orphaned_reports} orphaned research reports")
            
            # Clean up orphaned task operations
            orphaned_operations = await conn.execute("""
                DELETE FROM task_operations 
                WHERE task_id NOT IN (SELECT task_id FROM research_tasks)
            """)
            print(f"  ⚙️ Removed {orphaned_operations} orphaned task operations")
            
            # Clean up orphaned operation evidence
            orphaned_evidence = await conn.execute("""
                DELETE FROM operation_evidence 
                WHERE operation_id NOT IN (SELECT operation_id FROM task_operations)
            """)
            print(f"  📋 Removed {orphaned_evidence} orphaned operation evidence")
            
            print("✅ Database cleanup completed successfully!")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        raise
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(cleanup_test_data())
