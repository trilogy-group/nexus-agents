'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '@/lib/api';

interface TaskReportProps {
  taskId: string;
  taskStatus: string;
}

export function TaskReport({ taskId, taskStatus }: TaskReportProps) {
  // Fetch task report
  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['task-report', taskId],
    queryFn: async () => {
      const response = await api.tasks.getReport(taskId);
      return response.data as string;
    },
    enabled: taskStatus === 'completed',
  });

  if (reportLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-full mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-5/6 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-2/3 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-full mb-4"></div>
      </div>
    );
  }

  if (!report && taskStatus === 'completed') {
    return (
      <div className="text-center py-8">
        <div className="text-gray-500 mb-2">No report available</div>
        <div className="text-sm text-gray-400">
          The research task completed but no report was generated.
        </div>
      </div>
    );
  }

  if (!report && taskStatus !== 'completed') {
    return (
      <div className="text-center py-8">
        <div className="text-gray-500 mb-2">Report not yet available</div>
        <div className="text-sm text-gray-400">
          The report will be generated when the research task is completed.
        </div>
        <div className="mt-4">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            taskStatus === 'running' ? 'bg-blue-100 text-blue-800' :
            taskStatus === 'failed' ? 'bg-red-100 text-red-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            Status: {taskStatus}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full overflow-hidden min-w-0" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
      {/* Report Header */}
      <div className="mb-6 pb-4 border-b border-gray-200">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-lg font-semibold text-gray-900 break-all">Research Report</h2>
          <div className="flex items-center space-x-2 flex-wrap">
            <span className="text-sm text-gray-500">
              {report ? `${report.length.toLocaleString()} characters` : ''}
            </span>
            {report && (
              <button
                onClick={() => {
                  const blob = new Blob([report], { type: 'text/markdown' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `research-report-${taskId}.md`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  URL.revokeObjectURL(url);
                }}
                className="inline-flex items-center px-3 py-1 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Download Report
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Rendered Markdown Report */}
      <div className="w-full max-w-none overflow-hidden break-words min-w-0" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          components={{
            // Custom styling for markdown elements
            h1: ({ children }) => <h1 className="text-3xl font-bold text-gray-900 mb-6 break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</h1>,
            h2: ({ children }) => <h2 className="text-2xl font-semibold text-gray-900 mb-4 mt-8 break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</h2>,
            h3: ({ children }) => <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6 break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</h3>,
            h4: ({ children }) => <h4 className="text-lg font-semibold text-gray-900 mb-2 mt-4 break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</h4>,
            p: ({ children }) => <p className="text-gray-700 mb-4 leading-relaxed break-all whitespace-pre-wrap" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</p>,
            ul: ({ children }) => <ul className="list-disc list-inside mb-4 space-y-1 break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-inside mb-4 space-y-1 break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</ol>,
            li: ({ children }) => <li className="text-gray-700 break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</li>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-blue-500 pl-4 py-2 mb-4 bg-blue-50 text-gray-700 italic break-all whitespace-pre-wrap" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                {children}
              </blockquote>
            ),
            code: ({ children, className }) => {
              const isInline = !className;
              if (isInline) {
                return <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-gray-800 break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</code>;
              }
              return (
                <pre className="bg-gray-100 p-4 rounded-lg mb-4 overflow-hidden" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                  <code className="text-sm font-mono text-gray-800 whitespace-pre-wrap break-all" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</code>
                </pre>
              );
            },
            table: ({ children }) => (
              <div className="w-full overflow-x-auto mb-4 min-w-0">
                <table className="w-full border-collapse border border-gray-300" style={{ tableLayout: 'fixed' }}>{children}</table>
              </div>
            ),
            th: ({ children }) => (
              <th className="border border-gray-300 px-4 py-2 bg-gray-100 font-semibold text-left break-all max-w-xs" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</th>
            ),
            td: ({ children }) => (
              <td className="border border-gray-300 px-4 py-2 break-all max-w-xs" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{children}</td>
            ),
            a: ({ children, href }) => (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline break-all"
                style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}
              >
                {children}
              </a>
            ),
          }}
        >
          {report || ''}
        </ReactMarkdown>
      </div>
    </div>
  );
}
