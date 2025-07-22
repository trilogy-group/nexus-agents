'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, TaskTimeline as TaskTimelineType } from '@/lib/api';

interface TaskTimelineProps {
  taskId: string;
}

interface CalculatedMetrics {
  total_operations: number;
  completed_operations: number;
  failed_operations: number;
  total_evidence_items: number;
  search_providers_used: string[];
}

// Calculate metrics from timeline operations (based on old frontend implementation)
function calculateMetrics(timeline: TaskTimelineType | undefined): CalculatedMetrics {
  if (!timeline?.timeline) {
    return {
      total_operations: 0,
      completed_operations: 0,
      failed_operations: 0,
      total_evidence_items: 0,
      search_providers_used: []
    };
  }

  const operations = timeline.timeline;
  let totalSources = 0;
  let searchProvidersUsed = new Set<string>();
  let completedOps = 0;
  let failedOps = 0;

  operations.forEach(operation => {
    // Count completed/failed operations
    if (operation.status === 'completed') {
      completedOps++;
    } else if (operation.status === 'failed') {
      failedOps++;
    }

    // Extract evidence from operations (based on old frontend logic)
    const outputData = operation.output_data || {};
    
    // Track search providers from MCP search operations
    if (operation.operation_type === 'mcp_search') {
      const providers = outputData.providers_used || [];
      providers.forEach((provider: string) => {
        if (provider && provider !== 'unknown') {
          searchProvidersUsed.add(provider);
        }
      });
    }
    
    // Count actual processed sources from search summary operations
    // This gives us the true count of evidence items (sources that were summarized)
    if (operation.operation_type === 'search_summary') {
      const totalSummaries = outputData.total_summaries || 0;
      totalSources = totalSummaries; // Use assignment, not addition, to avoid double counting
    }
    
    // Count evidence from other operations
    if (operation.evidence && Array.isArray(operation.evidence)) {
      totalSources += operation.evidence.length;
    }
  });

  return {
    total_operations: operations.length,
    completed_operations: completedOps,
    failed_operations: failedOps,
    total_evidence_items: totalSources,
    search_providers_used: Array.from(searchProvidersUsed)
  };
}

// Get user-friendly display info for operations (based on old frontend)
function getOperationDisplayInfo(operation: any) {
  const operationType = operation.operation_type;
  const outputData = operation.output_data || {};
  
  let displayName = '';
  let badges = [];
  
  switch (operationType) {
    case 'topic_decomposition':
      displayName = 'Topic Decomposition';
      badges.push('topic_decomposition');
      break;
    case 'research_plan':
      displayName = 'Research Planning';
      badges.push('research_plan');
      break;
    case 'mcp_search':
      const focusArea = outputData.focus_area || outputData.subtopic || 'Search';
      const providersUsed = outputData.providers_used || [];
      const provider = providersUsed.length > 0 ? providersUsed[0] : 'MCP';
      displayName = focusArea;
      badges.push(provider);
      break;
    case 'search_summary':
      displayName = 'Search Summary';
      badges.push('search_summary');
      break;
    case 'reasoning_analysis':
      displayName = 'Reasoning Analysis';
      badges.push('reasoning_analysis');
      break;
    case 'dok_taxonomy':
      displayName = 'DOK Taxonomy';
      badges.push('dok_taxonomy');
      break;
    default:
      displayName = operation.operation_name || operationType.split('_').map((word: string) => 
        word.charAt(0).toUpperCase() + word.slice(1)
      ).join(' ');
      badges.push(operationType);
  }
  
  return { displayName, badges };
}

export function TaskTimeline({ taskId }: TaskTimelineProps) {
  const [expandedOperations, setExpandedOperations] = useState<Set<string>>(new Set());

  // Fetch task timeline
  const { data: timeline, isLoading: timelineLoading } = useQuery({
    queryKey: ['task-timeline', taskId],
    queryFn: async () => {
      const response = await api.tasks.getTimeline(taskId);
      return response.data as TaskTimelineType;
    },
  });

  // Toggle operation expansion
  const toggleOperation = (operationId: string) => {
    const newExpanded = new Set(expandedOperations);
    if (newExpanded.has(operationId)) {
      newExpanded.delete(operationId);
    } else {
      newExpanded.add(operationId);
    }
    setExpandedOperations(newExpanded);
  };

  // Calculate metrics from timeline
  const metrics = calculateMetrics(timeline);

  if (timelineLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        <div className="h-4 bg-gray-200 rounded w-full"></div>
        <div className="h-4 bg-gray-200 rounded w-5/6"></div>
      </div>
    );
  }

  if (!timeline?.timeline) {
    return <div className="text-gray-500">No timeline data available</div>;
  }

  return (
    <div>
      {/* Statistics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-2xl font-semibold text-gray-900">{metrics.total_operations}</div>
          <div className="text-sm text-gray-600">Total Operations</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-2xl font-semibold text-green-600">
            {metrics.completed_operations}
          </div>
          <div className="text-sm text-gray-600">Completed</div>
        </div>
        <div className="bg-red-50 p-4 rounded-lg">
          <div className="text-2xl font-semibold text-red-600">
            {metrics.failed_operations}
          </div>
          <div className="text-sm text-gray-600">Failed</div>
        </div>
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-2xl font-semibold text-blue-600">
            {metrics.total_evidence_items}
          </div>
          <div className="text-sm text-gray-600">Evidence Items</div>
        </div>
      </div>

      {/* Search Providers Used */}
      {metrics.search_providers_used.length > 0 && (
        <div className="mb-6">
          <div className="text-sm font-medium text-gray-700 mb-2">Search Providers Used:</div>
          <div className="flex flex-wrap gap-2">
            {metrics.search_providers_used.map((provider, idx) => (
              <span key={idx} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {provider}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="space-y-4">
        {timeline.timeline.map((op: any, idx: number) => {
          const isExpanded = expandedOperations.has(op.operation_id || idx.toString());
          const { displayName, badges } = getOperationDisplayInfo(op);
          
          return (
            <div key={op.operation_id || idx} className="border rounded-lg p-4 bg-white shadow-sm">
              <div 
                className="flex items-start justify-between mb-2 cursor-pointer hover:bg-gray-50 p-2 rounded"
                onClick={() => toggleOperation(op.operation_id || idx.toString())}
              >
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900">{displayName}</h3>
                  <div className="flex items-center space-x-2 mt-1">
                    <p className="text-sm text-gray-600">{op.operation_type}</p>
                    {badges.map((badge, badgeIdx) => (
                      <span key={badgeIdx} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                        {badge}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`text-sm px-2 py-1 rounded ${
                    op.status === 'completed' ? 'bg-green-100 text-green-700' :
                    op.status === 'failed' ? 'bg-red-100 text-red-700' :
                    op.status === 'running' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {op.status}
                  </span>
                  <span className="text-gray-400 text-lg">
                    {isExpanded ? '▼' : '▶'}
                  </span>
                </div>
              </div>
              
              {isExpanded && op.output_data && (
                <div className="mt-3 bg-gray-50 p-3 rounded border">
                  <div className="text-sm font-medium text-gray-700 mb-2">Operation Details:</div>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-64 bg-white p-3 rounded border">
                    {JSON.stringify(op.output_data, null, 2)}
                  </pre>
                </div>
              )}
              
              {op.evidence && op.evidence.length > 0 && (
                <div className="mt-3 space-y-2">
                  <div className="text-sm font-medium text-gray-700">Evidence ({op.evidence.length}):</div>
                  {op.evidence.map((ev: any, evIdx: number) => (
                    <div key={evIdx} className="bg-gray-50 p-3 rounded text-sm border">
                      <div className="font-medium text-gray-900">{ev.title || ev.evidence_type}</div>
                      {ev.url && (
                        <a href={ev.url} target="_blank" rel="noopener noreferrer" 
                           className="text-blue-600 hover:underline text-xs break-all">
                          {ev.url}
                        </a>
                      )}
                      {ev.content && (
                        <div className="text-gray-600 text-xs mt-1 line-clamp-3">
                          {ev.content.substring(0, 200)}...
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
