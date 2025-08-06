
-- Migration: Add Project-Level Entities and DOK Taxonomy Tables
-- This migration adds tables for project-level entity consolidation and DOK taxonomy aggregation

-- Create project_entities table for consolidated entities across tasks in a project
CREATE TABLE IF NOT EXISTS project_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    unique_identifier VARCHAR(255),
    entity_type VARCHAR(100),
    consolidated_attributes JSONB DEFAULT '{}',
    source_tasks JSONB DEFAULT '[]', -- Array of task IDs that contributed
    confidence_score FLOAT DEFAULT 1.0,
    data_lineage JSONB DEFAULT '{}', -- Track attribute sources and confidence
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, unique_identifier)
);

-- Create indexes for efficient querying of project entities
CREATE INDEX IF NOT EXISTS idx_project_entities_project_id ON project_entities(project_id);
CREATE INDEX IF NOT EXISTS idx_project_entities_entity_type ON project_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_project_entities_name ON project_entities(name);

-- Create project_dok_taxonomy table for consolidated DOK taxonomy across tasks in a project
CREATE TABLE IF NOT EXISTS project_dok_taxonomy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    knowledge_tree JSONB NOT NULL,
    insights JSONB DEFAULT '[]',
    spiky_povs JSONB DEFAULT '[]',
    consolidated_bibliography JSONB DEFAULT '[]',
    source_tasks JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying of project DOK taxonomy
CREATE INDEX IF NOT EXISTS idx_project_dok_taxonomy_project_id ON project_dok_taxonomy(project_id);
