
'use client';

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react';
import { api } from '@/lib/api';

interface ProjectEntityExplorerProps {
  projectId: string;
}

interface ProjectEntity {
  entity_id: string;
  project_id: string;
  name: string;
  entity_type: string;
  consolidated_attributes: Record<string, any>;
  source_tasks: string[];
  unique_identifier: string;
  confidence_score: number;
  created_at: string;
  updated_at: string;
}

export function ProjectEntityExplorer({ projectId }: ProjectEntityExplorerProps) {
  const [selectedEntityType, setSelectedEntityType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 100;
  
  const { data: entities, isLoading, error } = useQuery<ProjectEntity[]>({
    queryKey: ['project-entities', projectId],
    queryFn: async () => {
      const response = await api.projects.getProjectEntities(projectId);
      return response.data;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Get unique entity types for filter dropdown
  const entityTypes = [...new Set(entities?.map(entity => entity.entity_type) || [])];

  // Filter entities based on selected type and search term
  const filteredEntities = entities?.filter(entity => {
    const matchesType = selectedEntityType === 'all' || entity.entity_type === selectedEntityType;
    const matchesSearch = entity.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         Object.values(entity.consolidated_attributes).some(value => 
                           String(value).toLowerCase().includes(searchTerm.toLowerCase())
                         );
    return matchesType && matchesSearch;
  }) || [];

  // Pagination calculations
  const total = filteredEntities.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, total);
  const pagedEntities = filteredEntities.slice(startIndex, endIndex);

  // Reset to page 1 when filters/search change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedEntityType, searchTerm]);

  // Clamp current page if data size changes
  useEffect(() => {
    setCurrentPage((p) => Math.min(Math.max(1, p), totalPages));
  }, [totalPages]);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-500">Failed to load project entities</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-800">Project Entities</h2>
          
          {/* CSV Export Button */}
          {entities && entities.length > 0 && (
            <button
              onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:12000'}/api/projects/${projectId}/export/csv`, '_blank')}
              className="inline-flex items-center px-4 py-2 border border-green-300 text-sm font-medium rounded-md text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </button>
          )}
        </div>
        
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search entities..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div>
            <select
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={selectedEntityType}
              onChange={(e) => setSelectedEntityType(e.target.value)}
            >
              <option value="all">All Types</option>
              {entityTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Pagination controls (top) */}
        <div className="flex items-center justify-between mt-2">
          <div className="text-sm text-gray-600">
            Showing {total === 0 ? 0 : startIndex + 1}–{endIndex} of {total}
          </div>
          <div className="flex items-center gap-2">
            <button
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">Page {currentPage} of {totalPages}</span>
            <button
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Entity List */}
      {filteredEntities.length === 0 ? (
        <div className="text-gray-500 text-center py-8">
          No entities found. Run data aggregation tasks to populate project entities.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pagedEntities.map(entity => (
            <div key={entity.entity_id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-gray-800">{entity.name}</h3>
                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                  {entity.entity_type}
                </span>
              </div>
              
              <div className="text-xs text-gray-600 mb-3">
                Confidence: {(entity.confidence_score * 100).toFixed(1)}%
              </div>
              
              <div className="text-sm text-gray-700 mb-3">
                <div className="font-medium mb-1">Attributes:</div>
                {Object.entries(entity.consolidated_attributes).map(([key, value]) => (
                  <div key={key} className="flex justify-between py-1 border-b border-gray-100">
                    <span className="font-medium">{key}:</span>
                    <span className="text-gray-600">{String(value)}</span>
                  </div>
                ))}
              </div>
              
              <div className="text-xs text-gray-500">
                Source Tasks: {entity.source_tasks.length}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
