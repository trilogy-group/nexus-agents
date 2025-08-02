'use client';

import React, { useState } from 'react';
import { X, Copy, Check, Download } from 'lucide-react';

interface BrainLiftExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  dokData: any;
  taskTitle?: string;
}

export function BrainLiftExportModal({ isOpen, onClose, dokData, taskTitle }: BrainLiftExportModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const generateBrainLiftContent = () => {
    const title = taskTitle || 'Research Topic';
    
    // Helper function to safely get array data
    const safeArray = (data: any) => Array.isArray(data) ? data : [];
    
    // Helper function to normalize bibliography
    const normalizeBibliography = (bibliography: any) => {
      if (Array.isArray(bibliography)) {
        return bibliography;
      } else if (bibliography && typeof bibliography === 'object') {
        if (bibliography.sources && Array.isArray(bibliography.sources)) {
          return bibliography.sources;
        } else if (bibliography.bibliography && Array.isArray(bibliography.bibliography)) {
          return bibliography.bibliography;
        } else {
          return [bibliography];
        }
      }
      return [];
    };

    const knowledgeTree = safeArray(dokData.knowledge_tree);
    const insights = safeArray(dokData.insights);
    const spikyPovs = dokData.spiky_povs || {};
    const truths = safeArray(spikyPovs.truth);
    const myths = safeArray(spikyPovs.myth);
    const bibliography = normalizeBibliography(dokData.bibliography);
    const sourceSummaries = safeArray(dokData.source_summaries);
    
    // Create a lookup map for source summaries by source_id
    const summaryLookup = new Map();
    sourceSummaries.forEach((summary: any) => {
      if (summary.source_id) {
        summaryLookup.set(summary.source_id, summary);
      }
    });

    let content = `- ${title}\n`;
    
    // Purpose section
    content += `  - Purpose\n`;
    content += `    - Reason: Comprehensive research analysis and knowledge synthesis on ${title}\n`;
    content += `    - How it can be used: Strategic decision-making, academic research, policy development, and informed analysis\n`;
    content += `    - In Scope: Detailed analysis of ${title} including expert perspectives, evidence-based insights, and comprehensive source documentation\n`;
    content += `    - Out of Scope: Unverified claims, personal opinions without evidence, and information outside the defined research scope\n\n`;

    // Experts section (derived from bibliography and sources)
    content += `  - Experts\n`;
    const expertSources = bibliography.slice(0, 5); // Limit to top 5 sources as experts
    if (expertSources.length > 0) {
      expertSources.forEach((source: any) => {
        const expertName = source.author || source.title?.split(' - ')[0] || 'Research Source';
        content += `    - ${expertName}\n`;
        content += `      - Who: ${source.author || 'Research contributor'}\n`;
        content += `      - Focus: ${source.title || 'Subject matter expertise'}\n`;
        content += `      - Why Follow: Authoritative source with verified research contributions\n`;
        content += `      - Where:\n`;
        if (source.url) {
          content += `        - ${source.url}\n`;
        }
        if (source.domain) {
          content += `        - ${source.domain}\n`;
        }
      });
    } else {
      content += `    - Research Contributors\n`;
      content += `      - Who: Various subject matter experts and researchers\n`;
      content += `      - Focus: ${title} domain expertise\n`;
      content += `      - Why Follow: Evidence-based research and analysis\n`;
      content += `      - Where:\n`;
      content += `        - Academic and professional sources\n`;
    }
    content += `\n`;

    // DOK4 SPOV section
    content += `  - DOK4 SPOV\n`;
    content += `    - Truths\n`;
    if (truths.length > 0) {
      truths.forEach((truth: any, index: number) => {
        const statement = truth.statement || truth.content || truth;
        const reasoning = truth.reasoning || '';
        const supportingInsights = safeArray(truth.supporting_insights || []);
        
        content += `      - Spiky POV Truth ${index + 1}: ${statement}\n`;
        if (reasoning) {
          content += `        - Reasoning: ${reasoning}\n`;
        }
        if (supportingInsights.length > 0) {
          content += `        - Supporting Insights:\n`;
          supportingInsights.forEach((insight: any) => {
            const insightName = insight.category;
            content += `          - ${insightName}\n`;
          });
        }
      });
    } else {
      content += `      - Spiky POV Truth 1: [To be developed based on research findings]\n`;
    }
    content += `    - Myths\n`;
    if (myths.length > 0) {
      myths.forEach((myth: any, index: number) => {
        const statement = myth.statement || myth.content || myth;
        const reasoning = myth.reasoning || '';
        const supportingInsights = safeArray(myth.supporting_insights || []);
        
        content += `      - Spiky POV Myth ${index + 1}: ${statement}\n`;
        if (reasoning) {
          content += `        - Reasoning: ${reasoning}\n`;
        }
        if (supportingInsights.length > 0) {
          content += `        - Supporting Insights:\n`;
          supportingInsights.forEach((insight: any) => {
            const insightName = insight.category;
            content += `          - ${insightName}\n`;
          });
        }
      });
    } else {
      content += `      - Spiky POV Myth 1: [To be developed based on research findings]\n`;
    }
    content += `\n`;

    // DOK3 Insights section
    content += `  - DOK3 Insights\n`;
    if (insights.length > 0) {
      insights.forEach((insight: any, index: number) => {
        // Extract insight text and supporting sources
        let insightText = '';
        let supportingSources = '';
        
        if (insight && typeof insight === 'object') {
          // Get the insight text
          insightText = insight.insight_text || insight.insight || insight.content || insight.summary || insight.text || insight.description || '';
          
          // Get supporting sources as CSV of titles
          if (insight.sources && Array.isArray(insight.sources)) {
            const sourceTitles = insight.sources
              .map((source: any) => source.title || source.name || source.url || String(source))
              .filter(Boolean)
              .join(', ');
            supportingSources = sourceTitles ? ` Supporting sources: ${sourceTitles}` : '';
          }
        } else if (typeof insight === 'string') {
          insightText = insight;
        } else {
          insightText = String(insight);
        }
        
        content += `    - Insight ${index + 1}: ${insightText}${supportingSources}\n`;
      });
    } else {
      content += `    - Insight 1: [Novel insights to be extracted from source analysis]\n`;
      content += `    - Insight 2: [Contrarian learnings from research findings]\n`;
    }
    content += `\n`;

    // DOK2 Knowledge Tree section
    content += `  - DOK2 Knowledge Tree\n`;
    if (knowledgeTree.length > 0) {
      // Group by category
      const categories = knowledgeTree.reduce((acc: any, item: any) => {
        const category = item.category || 'General Knowledge';
        if (!acc[category]) {
          acc[category] = [];
        }
        acc[category].push(item);
        return acc;
      }, {});

      Object.entries(categories).forEach(([categoryName, items]: [string, any]) => {
        content += `    - ${categoryName}\n`;
        content += `      - Summary: ${items[0]?.summary || 'Knowledge category summary'}\n`;
        
        // Group by subcategory within category
        const subcategories = items.reduce((acc: any, item: any) => {
          const subcategory = item.subcategory || 'General';
          if (!acc[subcategory]) {
            acc[subcategory] = [];
          }
          acc[subcategory].push(item);
          return acc;
        }, {});

        Object.entries(subcategories).forEach(([subcategoryName, subItems]: [string, any]) => {
          // Check if this subcategory has any sources before displaying it
          const hasAnySources = subItems.some((subItem: any) => subItem.sources && subItem.sources.length > 0);
          
          if (hasAnySources) {
            content += `      - ${subcategoryName}\n`;
            content += `        - Sources:\n`;
            
            // Get sources from subcategory items
            subItems.forEach((subItem: any) => {
              if (subItem.sources && subItem.sources.length > 0) {
              subItem.sources.forEach((source: any) => { // Show all sources in subcategory
                const sourceName = source.title || source.name || 'Research Source';
                content += `          - ${sourceName}\n`;
                
                // Look up the actual source summary using source_id
                const sourceId = source.source_id || source.id;
                const sourceSummary = summaryLookup.get(sourceId);
                
                const dok1Facts = sourceSummary?.dok1_facts || source.facts || 'Key factual information from source';
                const summaryText = sourceSummary?.summary || source.summary || source.description || source.content || '[Summary not available]';
                
                content += `            - DOK1 Facts: ${Array.isArray(dok1Facts) ? dok1Facts.join('; ') : dok1Facts}\n`;
                content += `            - Summary: ${summaryText}\n`;
                content += `            - Link: ${source.url || source.link || 'Source link'}\n`;
              });
            }
          });
          }
        });
      });
    } else {
      content += `    - Research Categories\n`;
      content += `      - Summary: Comprehensive knowledge structure to be developed\n`;
      content += `      - Primary Research\n`;
      content += `        - Sources:\n`;
      content += `          - Source 1\n`;
      content += `            - DOK1 Facts: [Factual information to be extracted]\n`;
      content += `            - Summary: [Summary not available]\n`;
      content += `            - Link: [Source link to be added]\n`;
    }

    return content;
  };

  const handleCopy = async () => {
    const content = generateBrainLiftContent();
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const handleDownload = () => {
    const content = generateBrainLiftContent();
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${taskTitle || 'research'}-brainlift.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Export to BrainLift</h2>
            <p className="text-sm text-gray-600 mt-1">
              Hierarchical bullet point format for BrainLift knowledge base
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="p-6 flex-1 overflow-y-auto">
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
                {generateBrainLiftContent()}
              </pre>
            </div>
          </div>

          {/* Actions */}
          <div className="border-t border-gray-200 p-6 flex items-center justify-between bg-gray-50">
            <div className="text-sm text-gray-600">
              Ready to copy to clipboard or download as text file
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={handleDownload}
                className="flex items-center space-x-2 px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </button>
              <button
                onClick={handleCopy}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    <span>Copy to Clipboard</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
