'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, Book, Lightbulb, Target, FileText, Download } from 'lucide-react';
import { BrainLiftExportModal } from './BrainLiftExportModal';

interface DOKTaxonomySectionProps {
  taskId: string;
  taskTitle?: string;
}

interface DOKTaxonomyData {
  task_id: string;
  knowledge_tree?: any[];
  insights?: any[];
  spiky_povs?: {
    truth?: any[];
    myth?: any[];
  };
  bibliography?: any[];
  source_summaries?: any[];
  stats?: {
    total_sources: number;
    total_dok1_facts: number;
    knowledge_tree_nodes: number;
    total_insights: number;
    spiky_povs_truths: number;
    spiky_povs_myths: number;
    total_spiky_povs: number;
  };
}

export function DOKTaxonomySection({ taskId, taskTitle }: DOKTaxonomySectionProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['knowledge_tree']));
  const [showBrainLiftModal, setShowBrainLiftModal] = useState(false);

  // Fetch DOK taxonomy data
  const { data: dokData, isLoading: dokLoading, error: dokError } = useQuery({
    queryKey: ['dok-taxonomy', taskId],
    queryFn: async () => {
      const response = await fetch(`http://localhost:12000/api/dok/tasks/${taskId}/dok-complete`);
      if (!response.ok) {
        throw new Error(`Failed to fetch DOK taxonomy: ${response.status}`);
      }
      return response.json();
    },
  });

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  if (dokLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-gray-200 rounded w-1/3"></div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  if (dokError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <div className="text-red-800">
            <h3 className="font-medium">Error Loading DOK Taxonomy</h3>
            <p className="text-sm mt-1">
              Unable to load DOK taxonomy and bibliography information. Please try again later.
            </p>
            <p className="text-xs mt-2 text-red-600">
              Error: {dokError instanceof Error ? dokError.message : 'Unknown error'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!dokData) {
    return (
      <div className="text-center py-8">
        <div className="text-gray-500 mb-2">No DOK taxonomy data available</div>
        <div className="text-sm text-gray-400">
          DOK taxonomy analysis has not been completed for this task.
        </div>
      </div>
    );
  }

  // Process spiky_povs data structure
  const spikyPovsData = dokData.spiky_povs ? [
    ...(dokData.spiky_povs.truth || []).map((item: any) => ({ ...item, type: 'truth' })),
    ...(dokData.spiky_povs.myth || []).map((item: any) => ({ ...item, type: 'myth' }))
  ] : [];

  // Normalize bibliography data to ensure it's always an array
  const normalizeBibliography = (bibliography: any) => {
    if (Array.isArray(bibliography)) {
      return bibliography;
    } else if (bibliography && typeof bibliography === 'object') {
      // If it's an object, try to extract an array from common properties
      if (bibliography.sources && Array.isArray(bibliography.sources)) {
        return bibliography.sources;
      } else if (bibliography.bibliography && Array.isArray(bibliography.bibliography)) {
        return bibliography.bibliography;
      } else {
        // Convert single object to array
        return [bibliography];
      }
    }
    return [];
  };

  const sections = [
    {
      id: 'knowledge_tree',
      title: 'Knowledge Tree',
      icon: Book,
      data: dokData.knowledge_tree || [],
      description: 'Hierarchical knowledge structure extracted from research'
    },
    {
      id: 'insights',
      title: 'Key Insights',
      icon: Lightbulb,
      data: dokData.insights || [],
      description: 'Important findings and analytical insights'
    },
    {
      id: 'spiky_povs',
      title: 'Spiky Points of View',
      icon: Target,
      data: spikyPovsData,
      description: 'Controversial or distinctive perspectives identified'
    },
    {
      id: 'bibliography',
      title: 'Bibliography',
      icon: FileText,
      data: normalizeBibliography(dokData.bibliography),
      description: 'Sources and references used in the analysis'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">DOK Taxonomy Analysis</h2>
            <p className="text-sm text-gray-600 mt-1">
              Depth of Knowledge taxonomy and structured analysis of research findings
            </p>
          </div>
          <button
            onClick={() => setShowBrainLiftModal(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            title="Export to BrainLift format"
          >
            <Download className="w-4 h-4" />
            <span>Export to BrainLift</span>
          </button>
        </div>
      </div>

      {sections.map(({ id, title, icon: Icon, data, description }) => (
        <div key={id} className="border border-gray-200 rounded-lg">
          <div
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
            onClick={() => toggleSection(id)}
          >
            <div className="flex items-center space-x-3">
              <Icon className="w-5 h-5 text-gray-600" />
              <div>
                <h3 className="font-medium text-gray-900">{title}</h3>
                <p className="text-sm text-gray-600">{description}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
                {data.length} items
              </span>
              {expandedSections.has(id) ? (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronRight className="w-5 h-5 text-gray-400" />
              )}
            </div>
          </div>

          {expandedSections.has(id) && (
            <div className="border-t border-gray-200 p-4 bg-gray-50">
              {data.length === 0 ? (
                <div className="text-gray-500 text-sm italic">
                  No {title.toLowerCase()} data available
                </div>
              ) : (
                <div className="space-y-3">
                  {data.map((item: any, idx: number) => (
                    <div key={idx} className="bg-white p-3 rounded border">
                      {id === 'knowledge_tree' && (
                        <div>
                          <div className="flex items-center space-x-2 mb-2">
                            <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                              DOK {item.dok_level || 1}
                            </span>
                            <div className="font-medium text-gray-900">
                              {item.category}
                              {item.subcategory && (
                                <span className="text-gray-500"> / {item.subcategory}</span>
                              )}
                            </div>
                          </div>
                          <p className="text-sm text-gray-700 mb-3">{item.summary}</p>
                          {item.sources && item.sources.length > 0 && (
                            <div className="mt-3">
                              <div className="text-xs text-gray-500 mb-2">
                                Sources ({item.source_count || item.sources.length}):
                              </div>
                              <div className="flex flex-wrap gap-1">
                                {item.sources.map((source: any, sourceIdx: number) => (
                                  <a
                                    key={sourceIdx}
                                    href={source.url || '#'}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                                    title={source.title}
                                  >
                                    {source.title ? (
                                      source.title.length > 50 ? 
                                        source.title.substring(0, 50) + '...' : 
                                        source.title
                                    ) : 'Source'}
                                  </a>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {id === 'insights' && (
                        <div>
                          <div className="flex items-center space-x-2 mb-2">
                            <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                              DOK 3
                            </span>
                            <div className="font-medium text-gray-900">
                              {item.category}
                            </div>
                            {item.confidence_score && (
                              <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                                {Math.round(item.confidence_score * 100)}% confidence
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-700 mb-3">{item.insight_text}</p>
                          {item.supporting_sources && item.supporting_sources.length > 0 && (
                            <div className="mt-3">
                              <div className="text-xs text-gray-500 mb-2">
                                Supporting Sources:
                              </div>
                              <div className="flex flex-wrap gap-1">
                                {item.supporting_sources.map((source: any, sourceIdx: number) => (
                                  <a
                                    key={sourceIdx}
                                    href={source.url || '#'}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                                    title={source.title}
                                  >
                                    {source.title ? (
                                      source.title.length > 50 ? 
                                        source.title.substring(0, 50) + '...' : 
                                        source.title
                                    ) : 'Unknown'}
                                  </a>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {id === 'spiky_povs' && (
                        <div>
                          <div className="flex items-center space-x-2 mb-3">
                            <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                              DOK 4
                            </span>
                            <span className={`px-2 py-1 text-xs rounded font-medium ${
                              item.type === 'truth' ? 'bg-green-100 text-green-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {item.type?.toUpperCase() || 'UNKNOWN'}
                            </span>
                          </div>
                          
                          {item.statement && (
                            <blockquote className="border-l-4 border-gray-300 pl-4 mb-3">
                              <p className="text-sm text-gray-700 italic">"{item.statement}"</p>
                            </blockquote>
                          )}
                          
                          {item.reasoning && (
                            <div className="mb-3">
                              <div className="text-xs font-medium text-gray-600 mb-1">Reasoning:</div>
                              <p className="text-sm text-gray-700">{item.reasoning}</p>
                            </div>
                          )}
                          
                          {item.supporting_insights && item.supporting_insights.length > 0 && (
                            <div className="mt-3">
                              <div className="text-xs text-gray-500 mb-2">
                                Supporting Insights:
                              </div>
                              <div className="flex flex-wrap gap-1">
                                {item.supporting_insights.map((insight: any, insightIdx: number) => (
                                  <span
                                    key={insightIdx}
                                    className="inline-block px-2 py-1 text-xs bg-green-100 text-green-700 rounded"
                                    title={insight.insight_text}
                                  >
                                    {insight.category}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {id === 'bibliography' && (
                        <div>
                          <div className="font-medium text-gray-900 mb-2">
                            {item.title || (item.url ? new URL(item.url).hostname : 'Untitled Source')}
                          </div>
                          {item.url && (
                            <div className="mb-2">
                              <a 
                                href={item.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:underline text-sm break-all"
                              >
                                {item.url}
                              </a>
                            </div>
                          )}
                          <div className="flex flex-wrap gap-2 mt-2">
                            {item.provider && (
                              <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                                {item.provider}
                              </span>
                            )}
                            {item.usage_count && (
                              <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                                Used {item.usage_count} times
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Fallback for unknown structure */}
                      {!['knowledge_tree', 'insights', 'spiky_povs', 'bibliography'].includes(id) && (
                        <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-32">
                          {JSON.stringify(item, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
      
      {/* BrainLift Export Modal */}
      <BrainLiftExportModal
        isOpen={showBrainLiftModal}
        onClose={() => setShowBrainLiftModal(false)}
        dokData={dokData}
        taskTitle={taskTitle || `Research Task ${taskId}`}
      />
    </div>
  );
}
