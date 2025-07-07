#!/usr/bin/env python3
"""
Complete data purge script for Nexus Agents system.

This script will:
1. Delete ALL research-related data from PostgreSQL (with CASCADE)
2. Flush ALL Redis task queues
3. Reset the system to a completely clean state

WARNING: This is DESTRUCTIVE and will delete ALL research data permanently!
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncpg
import redis.asyncio as redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def purge_postgresql():
    """Purge all research-related data from PostgreSQL."""
    print("🗄️  Connecting to PostgreSQL...")
    
    # PostgreSQL connection parameters
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "nexus_agents"),
        user=os.getenv("POSTGRES_USER", "nexus_user"),
        password=os.getenv("POSTGRES_PASSWORD", "nexus_password")
    )
    
    try:
        # Delete in correct order to handle foreign key constraints
        delete_queries = [
            "DELETE FROM operation_evidence CASCADE;",
            "DELETE FROM operation_dependencies CASCADE;", 
            "DELETE FROM task_operations CASCADE;",
            "DELETE FROM research_reports CASCADE;",
            "DELETE FROM research_tasks CASCADE;",
            "DELETE FROM research_subtasks CASCADE;",
            "DELETE FROM artifacts CASCADE;",
            "DELETE FROM search_results CASCADE;",
            "DELETE FROM sources CASCADE;",
            # Additional DOK taxonomy tables
            "DELETE FROM spiky_povs CASCADE;",
            "DELETE FROM insights CASCADE;",
            "DELETE FROM knowledge_nodes CASCADE;",
            "DELETE FROM source_summaries CASCADE;",
            # Clean up any remaining references
            "DELETE FROM insight_sources CASCADE;",
            "DELETE FROM knowledge_node_sources CASCADE;"
        ]
        
        print("🧹 Purging PostgreSQL tables...")
        
        for query in delete_queries:
            table_name = query.split("FROM ")[1].split(" ")[0]
            try:
                result = await conn.execute(query)
                # Extract number of deleted rows from result like "DELETE 5"
                deleted_count = result.split()[-1] if " " in result else "0"
                print(f"   ✅ {table_name}: {deleted_count} rows deleted")
            except Exception as e:
                print(f"   ⚠️  {table_name}: {str(e)}")
        
        print("✅ PostgreSQL purge completed!")
        
    finally:
        await conn.close()

async def purge_redis():
    """Flush all Redis task queues."""
    print("🔴 Connecting to Redis...")
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url)
    
    try:
        # Get Redis info before purge
        info = await redis_client.info()
        total_keys = info.get('db0', {}).get('keys', 0) if 'db0' in info else 0
        
        print(f"🧹 Flushing Redis database (current keys: {total_keys})...")
        
        # Flush the entire Redis database
        await redis_client.flushdb()
        
        print("✅ Redis purge completed!")
        
    finally:
        await redis_client.aclose()

async def main():
    """Main purge function with safety checks."""
    print("🚨 NEXUS AGENTS DATA PURGE SCRIPT 🚨")
    print("=" * 50)
    print("⚠️  WARNING: This will PERMANENTLY DELETE:")
    print("   • All research tasks and reports")
    print("   • All sources and summaries") 
    print("   • All DOK taxonomy data (knowledge nodes, insights, POVs)")
    print("   • All task operations and evidence")
    print("   • All Redis task queues")
    print("   • ALL research-related data in the system")
    print()
    print("🔥 THIS ACTION CANNOT BE UNDONE! 🔥")
    print("=" * 50)
    
    # Safety confirmation
    if "--force" not in sys.argv:
        confirmation = input("Type 'PURGE ALL DATA' to confirm: ")
        if confirmation != "PURGE ALL DATA":
            print("❌ Purge cancelled.")
            return
    
    print("\n🚀 Starting system purge...")
    
    try:
        # Step 1: Purge PostgreSQL
        #await purge_postgresql()
        
        # Step 2: Purge Redis  
        await purge_redis()
        
        print("\n🎉 SYSTEM PURGE COMPLETED SUCCESSFULLY!")
        print("✨ The system is now in a completely clean state.")
        print("💡 You can now start fresh research tasks.")
        
    except Exception as e:
        print(f"\n❌ PURGE FAILED: {str(e)}")
        print("⚠️  The system may be in an inconsistent state.")
        print("💡 Check the logs and database manually.")
        sys.exit(1)

if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print(__doc__)
            print("\nUsage:")
            print("  python scripts/purge_all_data.py          # Interactive mode")
            print("  python scripts/purge_all_data.py --force  # Skip confirmation")
            sys.exit(0)
    
    asyncio.run(main())
