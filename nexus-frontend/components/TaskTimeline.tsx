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

// Render topic decomposition data in a visually appealing way
function renderTopicDecomposition(outputData: any) {
  const subtopics = outputData.subtopics || [];
  const totalSubtopics = outputData.total_subtopics || subtopics.length;

  if (subtopics.length === 0) {
    return (
      <div className="text-gray-500 text-sm">No subtopics found</div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">Research Subtopics</h4>
        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
          {totalSubtopics} topics
        </span>
      </div>
      
      <div className="grid gap-3">
        {subtopics.map((subtopic: any, idx: number) => (
          <div key={idx} className="border border-gray-200 rounded-lg p-4 bg-white hover:bg-gray-50 transition-colors">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded">
                {subtopic.focus_area || `Topic ${idx + 1}`}
              </span>
              <span className="text-xs text-gray-500">
                #{idx + 1}
              </span>
            </div>
            
            <p className="text-xs text-gray-700 leading-relaxed bg-gray-50 px-3 py-2 rounded">
              {subtopic.query}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// Render data aggregation search space enumeration data
function renderSearchSpaceEnumeration(outputData: any) {
  const subspaces = outputData.subspaces || [];
  const baseQuery = outputData.base_query || '';
  const searchSpace = outputData.search_space || '';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">Search Space Enumeration</h4>
        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
          {subspaces.length} subspaces
        </span>
      </div>
      
      <div className="mb-4 p-3 bg-gray-50 rounded border">
        <div className="text-xs font-medium text-gray-600 mb-1">Base Query</div>
        <div className="text-xs text-gray-800">{baseQuery}</div>
      </div>
      
      <div className="mb-4 p-3 bg-gray-50 rounded border">
        <div className="text-xs font-medium text-gray-600 mb-1">Search Space</div>
        <div className="text-xs text-gray-800">{searchSpace}</div>
      </div>
      
      <div className="grid gap-3">
        {subspaces.map((subspace: any, idx: number) => (
          <div key={idx} className="border border-gray-200 rounded-lg p-4 bg-white">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded">
                Subspace {idx + 1}
              </span>
              <span className="text-xs text-gray-500">
                #{idx + 1}
              </span>
            </div>
            
            <div className="space-y-2">
              <div>
                <div className="text-xs font-medium text-gray-600">Query</div>
                <div className="text-xs text-gray-800 bg-gray-50 px-3 py-2 rounded">
                  {subspace.query}
                </div>
              </div>
              
              {subspace.metadata && (
                <div>
                  <div className="text-xs font-medium text-gray-600">Metadata</div>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-32 bg-white p-3 rounded border">
                    {JSON.stringify(subspace.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Render data aggregation entity extraction data
function renderEntityExtraction(outputData: any) {
  const entities = outputData.entities || [];
  const entityType = outputData.entity_type || 'Unknown';
  const attributes = outputData.attributes || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">Entity Extraction</h4>
        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
          {entities.length} entities
        </span>
      </div>
      
      <div className="mb-4 p-3 bg-gray-50 rounded border">
        <div className="text-xs font-medium text-gray-600 mb-1">Entity Type</div>
        <div className="text-xs text-gray-800">{entityType}</div>
      </div>
      
      {attributes.length > 0 && (
        <div className="mb-4 p-3 bg-gray-50 rounded border">
          <div className="text-xs font-medium text-gray-600 mb-1">Attributes to Extract</div>
          <div className="flex flex-wrap gap-1">
            {attributes.map((attr: string, idx: number) => (
              <span key={idx} className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                {attr}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {entities.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">Extracted Entities</h5>
          <div className="space-y-3">
            {entities.map((entity: any, idx: number) => (
              <div key={idx} className="border border-green-200 rounded-lg p-3 bg-green-50">
                <div className="text-xs font-medium text-gray-800 mb-2">{entity.name}</div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(entity.attributes || {}).map(([key, value]: [string, any]) => (
                    <div key={key} className="text-xs">
                      <span className="font-medium text-gray-700">{key}:</span>
                      <span className="text-gray-600 ml-1">{String(value)}</span>
                    </div>
                  ))}
                </div>
                {entity.confidence && (
                  <div className="mt-2">
                    <span className="text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded">
                      Confidence: {entity.confidence}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Render data aggregation entity resolution data
function renderEntityResolution(outputData: any) {
  const resolvedEntities = outputData.resolved_entities || [];
  const unresolvedEntities = outputData.unresolved_entities || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">Entity Resolution</h4>
        <div className="flex gap-2">
          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
            {resolvedEntities.length} resolved
          </span>
          {unresolvedEntities.length > 0 && (
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full">
              {unresolvedEntities.length} unresolved
            </span>
          )}
        </div>
      </div>
      
      {resolvedEntities.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">Resolved Entities</h5>
          <div className="space-y-3">
            {resolvedEntities.map((entity: any, idx: number) => (
              <div key={idx} className="border border-green-200 rounded-lg p-3 bg-green-50">
                <div className="text-xs font-medium text-gray-800 mb-2">{entity.name}</div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(entity.attributes || {}).map(([key, value]: [string, any]) => (
                    <div key={key} className="text-xs">
                      <span className="font-medium text-gray-700">{key}:</span>
                      <span className="text-gray-600 ml-1">{String(value)}</span>
                    </div>
                  ))}
                </div>
                {entity.unique_identifier && (
                  <div className="mt-2 text-xs text-gray-600">
                    Unique ID: {entity.unique_identifier}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {unresolvedEntities.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">Unresolved Entities</h5>
          <div className="space-y-3">
            {unresolvedEntities.map((entity: any, idx: number) => (
              <div key={idx} className="border border-yellow-200 rounded-lg p-3 bg-yellow-50">
                <div className="text-xs font-medium text-gray-800 mb-2">{entity.name}</div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(entity.attributes || {}).map(([key, value]: [string, any]) => (
                    <div key={key} className="text-xs">
                      <span className="font-medium text-gray-700">{key}:</span>
                      <span className="text-gray-600 ml-1">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Render research plan data
function renderResearchPlan(outputData: any) {
  const plan = outputData.plan || {};
  const objectives = plan.objectives || [];
  const deliverables = plan.deliverables || [];
  const keyQuestions = plan.key_questions || [];
  const searchStrategies = plan.search_strategies || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">Research Plan</h4>
        <div className="flex gap-2">
          {objectives.length > 0 && (
            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
              {objectives.length} objectives
            </span>
          )}
          {deliverables.length > 0 && (
            <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
              {deliverables.length} deliverables
            </span>
          )}
        </div>
      </div>

      {objectives.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">📋 Objectives</h5>
          <div className="space-y-2">
            {objectives.map((obj: string, idx: number) => (
              <div key={idx} className="text-xs text-gray-700 bg-green-50 px-3 py-2 rounded border-l-2 border-green-200">
                {obj}
              </div>
            ))}
          </div>
        </div>
      )}

      {deliverables.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">🎯 Deliverables</h5>
          <div className="space-y-2">
            {deliverables.map((del: string, idx: number) => (
              <div key={idx} className="text-xs text-gray-700 bg-purple-50 px-3 py-2 rounded border-l-2 border-purple-200">
                {del}
              </div>
            ))}
          </div>
        </div>
      )}

      {keyQuestions.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">❓ Key Questions ({keyQuestions.length})</h5>
          <div className="space-y-2">
            {keyQuestions.map((q: string, idx: number) => (
              <div key={idx} className="text-xs text-gray-700 bg-blue-50 px-3 py-2 rounded border-l-2 border-blue-200">
                {q}
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(searchStrategies).length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">🔍 Search Strategies</h5>
          <div className="grid gap-2">
            {Object.entries(searchStrategies).map(([strategy, details]: [string, any], idx: number) => (
              <div key={idx} className="bg-gray-50 px-3 py-2 rounded border">
                <div className="text-xs font-medium text-gray-800 mb-1">{strategy}</div>
                <div className="flex gap-2 text-xs">
                  {details.methods && (
                    <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded">
                      {details.methods.length} methods
                    </span>
                  )}
                  {details.sources && (
                    <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                      {details.sources.length} sources
                    </span>
                  )}
                  {details.keywords && (
                    <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded">
                      {details.keywords.length} keywords
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Render MCP search data
function renderMcpSearch(outputData: any) {
  const subtopic = outputData.subtopic || '';
  const focusArea = outputData.focus_area || '';
  const resultsCount = outputData.results_count || 0;
  const providersUsed = outputData.providers_used || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">MCP Search Results</h4>
        <div className="flex gap-2">
          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
            {resultsCount} results
          </span>
          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
            {providersUsed.length} providers
          </span>
        </div>
      </div>

      {focusArea && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">🎯 Focus Area</h5>
          <div className="text-xs bg-blue-50 text-blue-800 px-3 py-2 rounded border-l-2 border-blue-200">
            {focusArea}
          </div>
        </div>
      )}

      {subtopic && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">🔍 Search Query</h5>
          <div className="text-xs text-gray-700 bg-gray-50 px-3 py-2 rounded">
            {subtopic}
          </div>
        </div>
      )}

      {providersUsed.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">🔌 Providers Used</h5>
          <div className="flex flex-wrap gap-2">
            {providersUsed.map((provider: string, idx: number) => (
              <span key={idx} className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                {provider}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Render search summary data
function renderSearchSummary(outputData: any) {
  const totalSubtopics = outputData.total_subtopics || 0;
  const totalSummaries = outputData.total_summaries || 0;
  const successfulSearches = outputData.successful_searches || 0;
  const failedSearches = outputData.failed_searches || 0;
  const searchFailures = outputData.search_failures || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">Search Summary</h4>
        <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded-full">
          {totalSummaries} summaries
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-green-50 p-3 rounded border-l-2 border-green-200">
          <div className="text-lg font-semibold text-green-700">{successfulSearches}</div>
          <div className="text-xs text-gray-600">Successful Searches</div>
        </div>
        <div className="bg-red-50 p-3 rounded border-l-2 border-red-200">
          <div className="text-lg font-semibold text-red-700">{failedSearches}</div>
          <div className="text-xs text-gray-600">Failed Searches</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-blue-50 p-3 rounded border-l-2 border-blue-200">
          <div className="text-lg font-semibold text-blue-700">{totalSubtopics}</div>
          <div className="text-xs text-gray-600">Total Subtopics</div>
        </div>
        <div className="bg-purple-50 p-3 rounded border-l-2 border-purple-200">
          <div className="text-lg font-semibold text-purple-700">{totalSummaries}</div>
          <div className="text-xs text-gray-600">Total Summaries</div>
        </div>
      </div>

      {searchFailures.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-red-600 mb-2">⚠️ Search Failures</h5>
          <div className="space-y-1">
            {searchFailures.map((failure: string, idx: number) => (
              <div key={idx} className="text-xs text-red-700 bg-red-50 px-3 py-2 rounded">
                {failure}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Render reasoning analysis data
function renderReasoningAnalysis(outputData: any) {
  const keyFindings = outputData.key_findings || [];
  const limitations = outputData.limitations || [];
  const causalRelationships = outputData.causal_relationships || [];
  const alternativeInterpretations = outputData.alternative_interpretations || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">Reasoning Analysis</h4>
        <div className="flex gap-2">
          {keyFindings.length > 0 && (
            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
              {keyFindings.length} findings
            </span>
          )}
          {causalRelationships.length > 0 && (
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
              {causalRelationships.length} causal
            </span>
          )}
        </div>
      </div>

      {keyFindings.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">🔍 Key Findings</h5>
          <div className="space-y-3">
            {keyFindings.map((finding: any, idx: number) => (
              <div key={idx} className="border border-green-200 rounded-lg p-3 bg-green-50">
                <div className="text-xs text-gray-800 mb-2">{finding.finding}</div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded">
                    Confidence: {finding.confidence || 'unknown'}
                  </span>
                  {finding.evidence && (
                    <span className="text-xs text-gray-600">
                      {finding.evidence.length} evidence
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {limitations.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">⚠️ Limitations ({limitations.length})</h5>
          <div className="space-y-2">
            {limitations.map((limitation: string, idx: number) => (
              <div key={idx} className="text-xs text-orange-800 bg-orange-50 px-3 py-2 rounded border-l-2 border-orange-200">
                {limitation}
              </div>
            ))}
          </div>
        </div>
      )}

      {causalRelationships.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">🔗 Causal Relationships ({causalRelationships.length})</h5>
          <div className="space-y-2">
            {causalRelationships.map((rel: any, idx: number) => (
              <div key={idx} className="border border-blue-200 rounded p-3 bg-blue-50">
                <div className="text-xs text-gray-800 mb-1">
                  <span className="font-medium">Cause:</span> {rel.cause}
                </div>
                <div className="text-xs text-gray-800 mb-2">
                  <span className="font-medium">Effect:</span> {rel.effect}
                </div>
                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                  Strength: {rel.strength || 'unknown'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {alternativeInterpretations.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-600 mb-2">🤔 Alternative Interpretations ({alternativeInterpretations.length})</h5>
          <div className="space-y-2">
            {alternativeInterpretations.map((alt: any, idx: number) => (
              <div key={idx} className="text-xs text-purple-800 bg-purple-50 px-3 py-2 rounded border-l-2 border-purple-200">
                {alt.interpretation}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Render DOK taxonomy data
function renderDokTaxonomy(outputData: any) {
  const insightsCount = outputData.insights_count || 0;
  const spikyPovsCount = outputData.spiky_povs_count || 0;
  const sourcesProcessed = outputData.sources_processed || 0;
  const bibliographySources = outputData.bibliography_sources || 0;
  const knowledgeTreeNodes = outputData.knowledge_tree_nodes || 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">DOK Taxonomy Results</h4>
        <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded-full">
          Webb's DOK
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-green-50 p-3 rounded border-l-2 border-green-200">
          <div className="text-lg font-semibold text-green-700">{knowledgeTreeNodes}</div>
          <div className="text-xs text-gray-600">Knowledge Tree Nodes</div>
          <div className="text-xs text-green-600 mt-1">DOK 1-2: Facts & Concepts</div>
        </div>
        <div className="bg-blue-50 p-3 rounded border-l-2 border-blue-200">
          <div className="text-lg font-semibold text-blue-700">{insightsCount}</div>
          <div className="text-xs text-gray-600">Insights Generated</div>
          <div className="text-xs text-blue-600 mt-1">DOK 3: Strategic Thinking</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-purple-50 p-3 rounded border-l-2 border-purple-200">
          <div className="text-lg font-semibold text-purple-700">{spikyPovsCount}</div>
          <div className="text-xs text-gray-600">Spiky POVs</div>
          <div className="text-xs text-purple-600 mt-1">DOK 4: Extended Thinking</div>
        </div>
        <div className="bg-orange-50 p-3 rounded border-l-2 border-orange-200">
          <div className="text-lg font-semibold text-orange-700">{sourcesProcessed}</div>
          <div className="text-xs text-gray-600">Sources Processed</div>
          <div className="text-xs text-orange-600 mt-1">Bibliography: {bibliographySources}</div>
        </div>
      </div>

      <div className="bg-indigo-50 p-3 rounded border border-indigo-200">
        <div className="text-xs font-medium text-indigo-800 mb-1">Webb's Depth of Knowledge Taxonomy</div>
        <div className="text-xs text-indigo-700">
          Structured knowledge from basic recall through extended thinking and analysis
        </div>
      </div>
    </div>
  );
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
                  {op.operation_type === 'topic_decomposition' && renderTopicDecomposition(op.output_data)}
                  {op.operation_type === 'research_plan' && renderResearchPlan(op.output_data)}
                  {op.operation_type === 'mcp_search' && renderMcpSearch(op.output_data)}
                  {op.operation_type === 'search_summary' && renderSearchSummary(op.output_data)}
                  {op.operation_type === 'reasoning_analysis' && renderReasoningAnalysis(op.output_data)}
                  {op.operation_type === 'dok_taxonomy' && renderDokTaxonomy(op.output_data)}
                  {op.operation_type === 'data_aggregation_search_space' && renderSearchSpaceEnumeration(op.output_data)}
                  {op.operation_type === 'data_aggregation_entity_extraction' && renderEntityExtraction(op.output_data)}
                  {op.operation_type === 'data_aggregation_entity_resolution' && renderEntityResolution(op.output_data)}
                  {!['topic_decomposition', 'research_plan', 'mcp_search', 'search_summary', 'reasoning_analysis', 'dok_taxonomy', 'data_aggregation_search_space', 'data_aggregation_entity_extraction', 'data_aggregation_entity_resolution'].includes(op.operation_type) && (
                    <>
                      <div className="text-sm font-medium text-gray-700 mb-2">Operation Details:</div>
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-64 bg-white p-3 rounded border">
                        {JSON.stringify(op.output_data, null, 2)}
                      </pre>
                    </>
                  )}
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
