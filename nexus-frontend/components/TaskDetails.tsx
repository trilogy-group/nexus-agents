'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Clock, CheckCircle, XCircle, FileText, BarChart, AlertCircle, Trash2, Download } from 'lucide-react';
import { api, ResearchTask } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { TaskTimeline } from './TaskTimeline';
import { TaskReport } from './TaskReport';
import { DOKTaxonomySection } from './DOKTaxonomySection';
import { ConfirmationModal } from './ConfirmationModal';

interface TaskDetailsProps {
  taskId: string;
}

export function TaskDetails({ taskId }: TaskDetailsProps) {
  const [activeTab, setActiveTab] = useState<'timeline' | 'report' | 'knowledge' | 'entities' | 'export'>('timeline');
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const { setSelectedTask } = useAppStore();
  const queryClient = useQueryClient();

  // Delete task mutation
  const deleteTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      const response = await api.tasks.delete(taskId);
      return response.data;
    },
    onSuccess: () => {
      // Close the confirmation modal and clear the selected task
      setShowDeleteConfirmation(false);
      setSelectedTask(null);
      // Invalidate queries to refresh the UI
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['all-tasks'] });
    },
    onError: (error) => {
      console.error('Failed to delete task:', error);
      // Keep modal open but show error state
    },
  });

  const handleDeleteTask = () => {
    setShowDeleteConfirmation(true);
  };

  const confirmDeleteTask = () => {
    deleteTaskMutation.mutate(taskId);
  };

  const cancelDeleteTask = () => {
    setShowDeleteConfirmation(false);
  };

  // Fetch task details
  const { data: task, isLoading: taskLoading } = useQuery({
    queryKey: ['task', taskId],
    queryFn: async () => {
      const response = await api.tasks.get(taskId);
      return response.data as ResearchTask;
    },
  });

  if (taskLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Task not found</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 overflow-hidden min-w-0">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{task.research_query}</h1>
            <div className="flex items-center space-x-4 mt-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                task.status === 'completed' ? 'bg-green-100 text-green-800' :
                task.status === 'running' ? 'bg-blue-100 text-blue-800' :
                task.status === 'failed' ? 'bg-red-100 text-red-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {task.status === 'completed' && <CheckCircle className="w-3 h-3 mr-1" />}
                {task.status === 'running' && <Clock className="w-3 h-3 mr-1" />}
                {task.status === 'failed' && <XCircle className="w-3 h-3 mr-1" />}
                {task.status}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Created {new Date(task.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
          <div className="flex space-x-2">
            {task.research_type === 'data_aggregation' && task.status === 'completed' && (
              <button
                onClick={async () => {
                  try {
                    const response = await api.tasks.exportCSV(taskId);
                    const url = window.URL.createObjectURL(new Blob([response.data]));
                    const link = document.createElement('a');
                    link.href = url;
                    link.setAttribute('download', `${taskId}_data.csv`);
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                    window.URL.revokeObjectURL(url);
                  } catch (error) {
                    console.error('Error downloading CSV:', error);
                  }
                }}
                className="inline-flex items-center px-3 py-2 border border-green-300 text-sm font-medium rounded-md text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-gray-800 dark:border-green-600 dark:text-green-400 dark:hover:bg-green-900/20"
                title="Download CSV Export"
              >
                <Download className="w-4 h-4 mr-2" />
                Download CSV
              </button>
            )}
            <button
              onClick={handleDeleteTask}
              disabled={deleteTaskMutation.isPending}
              className="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-gray-800 dark:border-red-600 dark:text-red-400 dark:hover:bg-red-900/20"
              title="Delete this task"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              {deleteTaskMutation.isPending ? 'Deleting...' : 'Delete Task'}
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8 px-6">
          {task.research_type === 'data_aggregation' ? (
            [
              { id: 'timeline', label: 'Processing Timeline', icon: BarChart },
              { id: 'entities', label: 'Extracted Entities', icon: FileText },
              { id: 'export', label: 'Export Data', icon: Download },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </button>
            ))
          ) : (
            [
              { id: 'timeline', label: 'Timeline', icon: BarChart },
              { id: 'report', label: 'Report', icon: FileText },
              { id: 'knowledge', label: 'DOK Taxonomy', icon: AlertCircle },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </button>
            ))
          )}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-6 min-w-0">
        <div className="w-full max-w-full overflow-hidden">
          {task.research_type === 'data_aggregation' ? (
            <>
              {activeTab === 'timeline' && <TaskTimeline taskId={taskId} />}
              {activeTab === 'entities' && <TaskReport taskId={taskId} taskStatus={task.status} />}
              {activeTab === 'export' && (
                <div className="flex flex-col items-center justify-center h-full">
                  <h2 className="text-xl font-semibold mb-4">Export Data</h2>
                  <p className="text-gray-600 dark:text-gray-300 mb-6">
                    Download the aggregated data as a CSV file
                  </p>
                  <button
                    onClick={async () => {
                      try {
                        const response = await api.tasks.exportCSV(taskId);
                        const url = window.URL.createObjectURL(new Blob([response.data]));
                        const link = document.createElement('a');
                        link.href = url;
                        link.setAttribute('download', `${taskId}_data.csv`);
                        document.body.appendChild(link);
                        link.click();
                        link.remove();
                        window.URL.revokeObjectURL(url);
                      } catch (error) {
                        console.error('Error downloading CSV:', error);
                      }
                    }}
                    className="inline-flex items-center px-4 py-2 border border-green-300 text-sm font-medium rounded-md text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-gray-800 dark:border-green-600 dark:text-green-400 dark:hover:bg-green-900/20"
                    title="Download CSV Export"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download CSV
                  </button>
                </div>
              )}
            </>
          ) : (
            <>
              {activeTab === 'timeline' && <TaskTimeline taskId={taskId} />}
              {activeTab === 'report' && <TaskReport taskId={taskId} taskStatus={task.status} />}
              {activeTab === 'knowledge' && <DOKTaxonomySection taskId={taskId} taskTitle={task.title || task.research_query} />}
            </>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={showDeleteConfirmation}
        title="Delete Research Task"
        message={`Are you sure you want to delete the task "${task?.title || 'this task'}"? This action cannot be undone.`}
        confirmText="Delete Task"
        cancelText="Cancel"
        onConfirm={confirmDeleteTask}
        onClose={cancelDeleteTask}
        isDestructive={true}
        isLoading={deleteTaskMutation.isPending}
      />
    </div>
  );
}
