# Frontend Development Guide

This guide helps frontend engineers work on the Nexus Agents UI without needing API keys, MCP servers, or the full backend stack.

## Quick Start for Frontend Engineers

### Step 1: Get Sample Data

Ask a colleague to share their data/db_export/ folder:
```bash
python scripts/export_data.py
```

### Step 2: Import Data to Local PostgreSQL

Import the exported data into your local PostgreSQL:
```bash
python scripts/import_data.py
```

### Step 3: Start Services

Start all services in read-only mode (no worker/Redis/MCP/LLM keys required):
```bash
./scripts/start_dev.sh --read-only
```
Or start all services (full development mode):
```bash
./scripts/start_dev.sh
```

### Step 4: Access the UI

- **Web UI**: http://localhost:12001
- **API Docs**: http://localhost:12000/docs

### Step 5: Stop Services

Stop all services:
```bash
./scripts/stop_dev.sh
```

## Data Export/Import Scripts

### Export Data (`scripts/export_data.py`)

Exports current PostgreSQL data to JSON files in `data/db_export/`:

Export data from your development database:
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nexus_agents"
python scripts/export_data.py
```

**Exported Files:**
- `research_tasks.json` - All research tasks with metadata
- `task_operations.json` - Operation timeline data
- `operation_evidence.json` - Evidence and search results
- `artifacts.json` - Research reports and files
- `research_subtasks.json` - Task decomposition data
- `sources.json` - External source references
- `export_metadata.json` - Export metadata and checksums

### Import Data (`scripts/import_data.py`)

Imports JSON files back into PostgreSQL:

Import exported data to a fresh database:
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nexus_agents"
python scripts/import_data.py
```

**Note:** This will clear existing data before importing.



## Frontend Structure

```
frontend/
├── index.html              # Main HTML page
├── css/
│   ├── components.css      # Component styles
│   └── themes.css          # Light/dark theme styles
└── js/
    ├── main.js             # Application initialization
    ├── modules/
    │   ├── tasks.js        # Task management functions
    │   ├── renderer.js     # UI rendering utilities
    │   └── polling.js      # Data polling and updates
    └── lib/
        └── json-viewer/    # JSON tree viewer component
```

## Key Frontend Features

### Task Management
- **Task Cards**: Collapsible cards showing task details
- **Status Badges**: Color-coded status indicators
- **Timeline View**: Expandable operation timeline with JSON trees
- **Evidence Summary**: Statistics on search providers and evidence items

### Research Reports
- **Markdown Rendering**: Full research reports in modal dialogs
- **Report Metadata**: Word count, timestamps, export options

### Theme Support
- **Light/Dark Toggle**: Site-wide theme switching
- **JSON Viewer Theming**: Color-coded JSON trees that adapt to theme

### Real-time Updates
- **Auto-polling**: Automatic refresh of task status and data
- **State Preservation**: Maintains expanded/collapsed states during updates

## API Integration

The frontend expects these API response formats:

### Task List (`GET /tasks`)
```json
[
  {
    "task_id": "uuid",
    "title": "Task Title", 
    "description": "Description",
    "status": "completed|running|pending|failed",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "completed_at": "2024-01-01T00:00:00"
  }
]
```

### Task Operations (`GET /tasks/{id}/operations`)
```json
{
  "operations": [
    {
      "operation_id": "uuid",
      "task_id": "uuid", 
      "operation_type": "search|planning|synthesis",
      "operation_name": "Human readable name",
      "status": "completed|running|pending|failed",
      "agent_type": "search_agent|planning_agent", 
      "started_at": "2024-01-01T00:00:00",
      "completed_at": "2024-01-01T00:00:00",
      "duration_ms": 5000,
      "input_data": { "query": "..." },
      "output_data": { "results": "..." }
    }
  ]
}
```

### Task Evidence (`GET /tasks/{id}/evidence`)
```json
{
  "evidence": [...],
  "operations": [...],
  "statistics": {
    "evidence_items": 42,
    "search_providers_used": ["openai", "mcp_search"],
    "operations_count": 5
  }
}
```

## Development Workflow

### 1. Setup
```bash
# Clone and setup
git clone <repo>
cd nexus-agents

# Install dependencies
uv sync
```

### 2. Get Sample Data
```bash
# Option A: Export from existing database
python scripts/export_data.py

# Option B: Ask a colleague to share their data/db_export/ folder
```

### 3. Start Development
```bash
# Import sample data
python scripts/import_data.py

# Start services in read-only mode
./scripts/start_dev.sh --read-only

# Access the UI at http://localhost:12001
```

### 4. Frontend Development
- Edit files in `frontend/`
- Refresh browser to see changes
- Use browser dev tools for debugging
- API provides realistic data from imported database

### 5. Testing with Full Backend
```bash
# Start all services (including worker for task processing)
./scripts/start_dev.sh

# Now you can create and process tasks end-to-end
```

### 6. Stop Services
```bash
# Stop all services when done
./scripts/stop_dev.sh
```

## Troubleshooting

### Service Issues
- **Port conflicts**: Services run on ports 12000 (API) and 12001 (Web UI)
- **Services won't start**: Check logs in `logs/` directory for errors
- **PostgreSQL connection**: Ensure PostgreSQL is running with `docker compose ps`

### Frontend Issues
- **API calls failing**: Check if services are running with `./scripts/start_dev.sh --read-only`
- **Styles not loading**: Check file paths and Web UI server
- **JavaScript errors**: Check browser console for detailed error messages

### Database Issues
- **Import fails**: Ensure PostgreSQL is running and schema exists
- **Connection errors**: Check PostgreSQL connection in `.env` file
- **Permission errors**: Ensure database user has sufficient privileges

## Contributing

When making frontend changes:

1. **Start with Read-Only Mode**: Use `./scripts/start_dev.sh --read-only` for development
2. **Test with Imported Data**: Import sample data for realistic testing
3. **Check Responsive Design**: Test on different screen sizes
4. **Verify Theme Support**: Check both light and dark themes
5. **Document Changes**: Update this guide if adding new features

## Environment Variables

For the export/import scripts:

```bash
# Database connection (for export/import scripts)
export DATABASE_URL="postgresql://user:password@host:port/database"

# For full backend development (not needed for frontend-only mode)
export OPENAI_API_KEY="your-key"
export REDIS_URL="redis://localhost:6379"
```

## Getting Help

- **Frontend Issues**: Check browser console and network tab
- **API Issues**: Check logs in `logs/api.log` and `logs/web.log`
- **Service Issues**: Check `logs/` directory for all service logs
- **Database Issues**: Check PostgreSQL logs with `docker compose logs postgres`
- **General Setup**: Refer to main README.md for full development setup
