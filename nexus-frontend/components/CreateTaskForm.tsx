'use client';

import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';

interface CreateTaskFormProps {
  projectId: string;
  onTaskCreated?: () => void;
}

interface DataAggregationConfig {
  entities: string[];
  attributes: string[];
  search_space: string;
  domain_hint?: string;
}

export function CreateTaskForm({ projectId, onTaskCreated }: CreateTaskFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [researchType, setResearchType] = useState('analytical_report');
  
  // Data aggregation config states
  const [entities, setEntities] = useState('');
  const [attributes, setAttributes] = useState('');
  const [searchSpace, setSearchSpace] = useState('');
  const [domainHint, setDomainHint] = useState('');
  
  const queryClient = useQueryClient();
  const { addTaskToProject, addToast } = useAppStore();

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
      
      // Add the new task to the Zustand store immediately for instant UI update
      addTaskToProject(projectId, data);
      
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
      
      // Show success toast
      addToast({
        type: 'success',
        title: 'Research Task Created',
        message: `"${data.title}" has been added to your project`,
        duration: 4000
      });
    },
    onError: (error) => {
      console.error('Error creating task:', error);
      addToast({
        type: 'error',
        title: 'Failed to Create Task',
        message: error.message || 'An unexpected error occurred',
        duration: 6000
      });
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title.trim() || !description.trim()) {
      addToast({
        type: 'warning',
        title: 'Missing Information',
        message: 'Please fill in both title and description fields',
        duration: 4000
      });
      return;
    }

    // Validate data aggregation config if selected
    let dataAggregationConfig = null;
    if (researchType === 'data_aggregation') {
      if (!entities.trim() || !attributes.trim() || !searchSpace.trim()) {
        addToast({
          type: 'warning',
          title: 'Missing Data Aggregation Configuration',
          message: 'Please fill in all data aggregation fields',
          duration: 4000
        });
        return;
      }
      
      dataAggregationConfig = {
        entities: entities.split(',').map(e => e.trim()).filter(e => e),
        attributes: attributes.split(',').map(a => a.trim()).filter(a => a),
        search_space: searchSpace.trim(),
        domain_hint: domainHint.trim() || undefined
      };
    }

    console.log('Creating task with project_id:', projectId);
    
    createTaskMutation.mutate({
      title: title.trim(),
      research_query: description.trim(),
      research_type: researchType,
      project_id: projectId,
      user_id: null,
      data_aggregation_config: dataAggregationConfig
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

        {researchType === 'data_aggregation' && (
          <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
            <h4 className="text-md font-medium text-gray-800">Data Aggregation Configuration</h4>
            
            <div>
              <label htmlFor="entities" className="block text-sm font-medium text-gray-700 mb-1">
                Entities
              </label>
              <input
                type="text"
                id="entities"
                value={entities}
                onChange={(e) => setEntities(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., private schools, hospitals, companies"
              />
              <p className="text-xs text-gray-500 mt-1">Comma-separated list of entities to aggregate data for</p>
            </div>
            
            <div>
              <label htmlFor="attributes" className="block text-sm font-medium text-gray-700 mb-1">
                Attributes
              </label>
              <input
                type="text"
                id="attributes"
                value={attributes}
                onChange={(e) => setAttributes(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., name, address, website, enrollment, tuition"
              />
              <p className="text-xs text-gray-500 mt-1">Comma-separated list of attributes to extract for each entity</p>
            </div>
            
            <div>
              <label htmlFor="search-space" className="block text-sm font-medium text-gray-700 mb-1">
                Search Space
              </label>
              <input
                type="text"
                id="search-space"
                value={searchSpace}
                onChange={(e) => setSearchSpace(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., in California, in the US, in New York City"
              />
              <p className="text-xs text-gray-500 mt-1">Geographic or categorical constraint for the search</p>
            </div>
            
            <div>
              <label htmlFor="domain-hint" className="block text-sm font-medium text-gray-700 mb-1">
                Domain Hint (Optional)
              </label>
              <input
                type="text"
                id="domain-hint"
                value={domainHint}
                onChange={(e) => setDomainHint(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., education.private_schools, healthcare.hospitals"
              />
              <p className="text-xs text-gray-500 mt-1">Domain-specific hint to optimize data extraction</p>
            </div>
          </div>
        )}

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
