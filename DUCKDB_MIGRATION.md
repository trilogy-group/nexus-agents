# DuckDB Migration

This document outlines the migration from MongoDB to DuckDB for the Nexus Agents knowledge base.

## Why DuckDB?

1. **Native JSON Support**: DuckDB has excellent native JSON support, making it perfect for storing research artifacts with varying structures.
2. **Embedded Database**: No need for a separate database server - DuckDB runs embedded in the application.
3. **Analytical Queries**: DuckDB is optimized for analytical workloads, which is perfect for research data analysis.
4. **Lightweight**: Much lighter than MongoDB for our use case.
5. **SQL Interface**: Standard SQL interface makes it easier to query and maintain.

## Architecture Changes

### Database Schema

The new DuckDB schema includes the following tables:

1. **research_tasks**: Main research tasks with JSON fields for metadata, decomposition, plan, results, summary, and reasoning
2. **research_subtasks**: Subtasks with JSON fields for key questions and search results
3. **artifacts**: Generated artifacts with support for both JSON content and file references
4. **sources**: Information sources with metadata and reliability scores
5. **search_results**: Cached search results with expiration

### File Storage

Binary files (PDFs, Word docs, images, etc.) are now stored on the file system with metadata in the database:

- Files are organized by task ID in the storage directory
- Each file gets a unique UUID-based filename
- File metadata (path, size, checksum, type) is stored in the artifacts table
- Supports automatic file type detection based on extension

### Key Features

1. **JSON Native Storage**: Complex research data is stored as JSON directly in DuckDB
2. **File Management**: Binary files are stored on disk with database references
3. **Search Capabilities**: Full-text search across sources and artifacts
4. **Caching**: Search results are cached with expiration times
5. **Versioning**: All records include created_at and updated_at timestamps

## Configuration Changes

### Environment Variables

Old MongoDB configuration:
```bash
MONGO_URI=mongodb://localhost:27017/nexus_agents
```

New DuckDB configuration:
```bash
DUCKDB_PATH=data/nexus_agents.db
STORAGE_PATH=data/storage
```

### Docker Compose

- Removed MongoDB service
- Added data volume mapping for persistent storage
- Updated environment variables

## API Changes

The KnowledgeBase class now provides:

### Core Methods
- `store_task()`, `get_task()`, `update_task_status()`
- `store_subtask()`, `get_subtask()`, `get_subtasks_for_task()`
- `store_artifact()`, `get_artifact()`, `get_artifacts_for_task()`
- `store_source()`, `get_source()`

### File Operations
- `store_file()`: Store binary files with automatic metadata generation
- `get_file()`: Retrieve binary file content
- File type detection and organization

### Search & Caching
- `search_sources()`, `search_artifacts()`: Full-text search
- `cache_search_results()`, `get_cached_search_results()`: Result caching

## Migration Benefits

1. **Simplified Deployment**: No need to run MongoDB server
2. **Better Performance**: DuckDB is optimized for analytical queries
3. **Native JSON**: No need for complex document mapping
4. **File Management**: Proper handling of binary files
5. **Reduced Dependencies**: One less service to manage
6. **Better Development Experience**: Embedded database for local development

## Backward Compatibility

The API interface remains the same, so existing code using the KnowledgeBase class will continue to work without changes. The migration is transparent to the rest of the system.