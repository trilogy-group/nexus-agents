'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '@/lib/store';
import { api } from '@/lib/api';
import { TaskDetails } from '@/components/TaskDetails';
import { LayoutWrapper } from '@/components/LayoutWrapper';
import { CreateProjectModal } from '@/components/CreateProjectModal';
import { CreateTaskForm } from '@/components/CreateTaskForm';
import { Plus } from 'lucide-react';
import Image from 'next/image';

export default function Home() {
  const { 
    selectedTaskId, 
    selectedProjectId,
    projects, 
    setProjects, 
    setProjectTasks,
    setProjectsLoading,
    getSelectedProject,
    getProjectTasks,
    setSelectedTask 
  } = useAppStore();
  
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Fetch all projects on mount
  const { data: projectsData, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await api.projects.list();
      return response.data;
    },
  });

  // Update store when projects are loaded
  useEffect(() => {
    if (projectsData) {
      setProjects(projectsData);
    }
  }, [projectsData, setProjects]);

  useEffect(() => {
    setProjectsLoading(projectsLoading);
  }, [projectsLoading, setProjectsLoading]);

  // Fetch tasks for each project
  useQuery({
    queryKey: ['all-tasks', projects],
    queryFn: async () => {
      const taskPromises = projects.map(async (project) => {
        const response = await api.projects.getTasks(project.id);
        return { projectId: project.id, tasks: response.data };
      });
      
      const results = await Promise.all(taskPromises);
      results.forEach(({ projectId, tasks }) => {
        setProjectTasks(projectId, tasks);
      });
      
      return results;
    },
    enabled: projects.length > 0,
  });

  if (selectedTaskId) {
    return (
      <LayoutWrapper>
        <TaskDetails taskId={selectedTaskId} />
      </LayoutWrapper>
    );
  }

  // Show project view with task creation form when project is selected
  if (selectedProjectId) {
    console.log('Selected project ID:', selectedProjectId);
    const selectedProject = getSelectedProject();
    console.log('Selected project object:', selectedProject);
    const projectTasks = getProjectTasks(selectedProjectId);
    
    return (
      <LayoutWrapper>
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">
                {selectedProject?.name || 'Project'}
              </h1>
              {selectedProject?.description && (
                <p className="text-gray-600 mt-1">{selectedProject.description}</p>
              )}
            </div>
            <div className="text-sm text-gray-500">
              {projectTasks.length} task{projectTasks.length !== 1 ? 's' : ''}
            </div>
          </div>

          <CreateTaskForm 
            projectId={selectedProjectId} 
            onTaskCreated={() => {
              // Task creation will trigger query invalidation automatically
              console.log('Task created successfully');
            }}
          />

          {projectTasks.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Research Tasks</h2>
              </div>
              <div className="divide-y divide-gray-200">
                {projectTasks.map((task) => (
                  <div key={task.task_id} className="p-6 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-gray-900 mb-2">
                          {task.title}
                        </h3>
                        <p className="text-gray-600 mb-3">{task.research_query}</p>
                        <div className="flex items-center gap-4 text-sm text-gray-500">
                          <span>Status: <span className={`font-medium ${
                            task.status === 'completed' ? 'text-green-600' :
                            task.status === 'failed' ? 'text-red-600' :
                            task.status === 'running' ? 'text-blue-600' :
                            'text-gray-600'
                          }`}>{task.status}</span></span>
                          <span>Created: {new Date(task.created_at).toLocaleDateString()}</span>
                          {task.research_type && (
                            <span>Type: {task.research_type.replace('_', ' ')}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => setSelectedTask(task.task_id)}
                        className="ml-4 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      >
                        View Details
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </LayoutWrapper>
    );
  }

  return (
    <LayoutWrapper>
      <div className="h-full flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="flex justify-center mb-6">
          <Image
            src="/nexus-agents-logo.png"
            alt="Nexus Agents Logo"
            width={530}
            height={400}
            className="w-[530px] h-[400px]"
          />
        </div>
        
        <h1 className="text-3xl font-semibold text-gray-900 mb-3">
          Welcome to Nexus Agents
        </h1>
        
        <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
          Multi-agent deep research system.
        </p>
        
        <div className="space-y-4">
          <p className="text-gray-500">
            Select a project from the sidebar to view its research tasks
          </p>
          
          <div className="flex flex-col gap-2 items-center">
            <p className="text-sm text-gray-400">or</p>
            <button 
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-800 transition-colors cursor-pointer"
            >
              Create New Project
            </button>
          </div>
        </div>
        
      </div>
    </div>
    
    <CreateProjectModal 
      isOpen={showCreateModal} 
      onClose={() => setShowCreateModal(false)} 
    />
    </LayoutWrapper>
  );
}
