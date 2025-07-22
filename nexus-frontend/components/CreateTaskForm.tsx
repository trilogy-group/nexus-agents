'use client';

import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';

interface CreateTaskFormProps {
  projectId: string;
  onTaskCreated?: () => void;
}

export function CreateTaskForm({ projectId, onTaskCreated }: CreateTaskFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [researchType, setResearchType] = useState('analytical_report');
  const queryClient = useQueryClient();

  const createTaskMutation = useMutation({
    mutationFn: async (taskData: {
      title: string;
      research_query: string;
      research_type: string;
      project_id: string;
      user_id?: string | null;
      data_aggregation_config?: any | null;
    }) => {
      const response = await api.tasks.create(taskData);
      return response.data;
    },
    onSuccess: (data) => {
      console.log('Task created successfully:', data);
      
      // Reset form
      setTitle('');
      setDescription('');
      setResearchType('analytical_report');
      
      // Invalidate and refetch project tasks to show the new task immediately
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['project-tasks', projectId] });
      
      // Call the callback
      onTaskCreated?.();
      
      // Show success message
      alert('Research task created successfully!');
    },
    onError: (error) => {
      console.error('Error creating task:', error);
      alert(`Failed to create task: ${error.message}`);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title.trim() || !description.trim()) {
      alert('Please fill in all required fields');
      return;
    }

    console.log('Creating task with project_id:', projectId);
    
    createTaskMutation.mutate({
      title: title.trim(),
      research_query: description.trim(),
      research_type: researchType,
      project_id: projectId,
      user_id: null,
      data_aggregation_config: null
    });
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Create Research Task</h3>
        <p className="text-sm text-gray-600 mt-1">
          Start a new research investigation within this project
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="task-title" className="block text-sm font-medium text-gray-700 mb-1">
            Title
          </label>
          <input
            type="text"
            id="task-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter task title..."
          />
        </div>

        <div>
          <label htmlFor="task-description" className="block text-sm font-medium text-gray-700 mb-1">
            Inquiry
          </label>
          <textarea
            id="task-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            placeholder="Describe what you want to research..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Research Type
          </label>
          <div className="space-y-2">
            <label className="flex items-start space-x-3">
              <input
                type="radio"
                name="research-type"
                value="analytical_report"
                checked={researchType === 'analytical_report'}
                onChange={(e) => setResearchType(e.target.value)}
                className="mt-1 w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
              />
              <div>
                <div className="text-sm font-medium text-gray-900">Analytical Report</div>
                <div className="text-xs text-gray-500">Comprehensive research with DOK taxonomy analysis</div>
              </div>
            </label>
            
            <label className="flex items-start space-x-3">
              <input
                type="radio"
                name="research-type"
                value="data_aggregation"
                checked={researchType === 'data_aggregation'}
                onChange={(e) => setResearchType(e.target.value)}
                className="mt-1 w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
              />
              <div>
                <div className="text-sm font-medium text-gray-900">Data Aggregation</div>
                <div className="text-xs text-gray-500">Structured data collection and synthesis</div>
              </div>
            </label>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <button
            type="submit"
            disabled={createTaskMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
          >
            {createTaskMutation.isPending ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                Creating Task...
              </>
            ) : (
              'Create Task'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
