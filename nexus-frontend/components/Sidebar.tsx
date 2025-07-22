'use client';

import React, { useState, useEffect, useRef } from 'react';
import { ChevronRight, ChevronDown, Folder, FileText, Plus, MoreVertical, PanelLeftClose, PanelLeftOpen, Trash2 } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { api, Project, ResearchTask } from '@/lib/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { CreateProjectModal } from './CreateProjectModal';
import { ConfirmationModal } from './ConfirmationModal';

interface ProjectItemProps {
  project: Project;
  tasks: ResearchTask[];
  isExpanded: boolean;
  onToggle: () => void;
  isSelected: boolean;
  onSelectProject: () => void;
  onSelectTask: (taskId: string) => void;
  selectedTaskId: string | null;
  onCreateTask: (projectId: string) => void;
  onDeleteTask: (taskId: string, taskTitle: string) => void;
}

function ProjectItem({ 
  project, 
  tasks, 
  isExpanded, 
  onToggle, 
  isSelected,
  onSelectProject,
  onSelectTask,
  selectedTaskId,
  onCreateTask,
  onDeleteTask
}: ProjectItemProps) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };

    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showMenu]);

  return (
    <div className="mb-1">
      <div 
        className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-100 group ${
          isSelected ? "bg-gray-100" : ""
        }`}
      >
        <button 
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          className="p-0.5 hover:bg-gray-200 rounded"
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-700" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-700" />
          )}
        </button>
        
        <Folder className="w-4 h-4 text-gray-700" />
        
        <span 
          className="flex-1 text-sm font-medium truncate text-gray-900 cursor-pointer"
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
            onSelectProject();
          }}
        >
          {project.name}
        </span>
        
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button 
            className="p-1 hover:bg-gray-200 rounded"
            onClick={(e) => {
              e.stopPropagation();
              onCreateTask(project.id);
            }}
          >
            <Plus className="w-3.5 h-3.5 text-gray-700" />
          </button>
          
          <button 
            className="p-1 hover:bg-gray-200 rounded"
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
          >
            <MoreVertical className="w-3.5 h-3.5 text-gray-700" />
          </button>
        </div>
        
        {/* Project Actions Menu */}
        {showMenu && (
          <div 
            ref={menuRef}
            className="absolute right-0 top-8 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-[120px]"
          >
            <button 
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2 dropdown-menu-item"
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(false);
                onCreateTask(project.id);
              }}
            >
              <Plus className="w-3.5 h-3.5" />
              New Task
            </button>
            <button 
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 text-red-600"
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(false);
                // TODO: Implement project deletion
                console.log('Delete project:', project.id);
              }}
            >
              Delete Project
            </button>
          </div>
        )}
      </div>
      
      {isExpanded && (
        <div className="ml-4 mt-1">
          {tasks.length === 0 ? (
            <div className="px-4 py-2 text-sm text-gray-500 italic">
              No research tasks yet
            </div>
          ) : (
            tasks.map((task, taskIndex) => (
              <div
                key={`task-${task.task_id}-${taskIndex}`}
                className={`group flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer hover:bg-gray-100 ${
                  selectedTaskId === task.task_id ? "bg-gray-100" : ""
                }`}
                onClick={() => onSelectTask(task.task_id)}
              >
                <FileText className="w-4 h-4 text-gray-500" />
                <span className="text-sm truncate text-gray-900 flex-1">{task.title}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  task.status === 'completed' ? "bg-green-100 text-green-700" :
                  task.status === 'failed' ? "bg-red-100 text-red-700" :
                  task.status === 'pending' ? "bg-yellow-100 text-yellow-700" :
                  task.status === 'running' ? "bg-blue-100 text-blue-700" : ""
                }`}>
                  {task.status}
                </span>
                <button
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-opacity"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteTask(task.task_id, task.title);
                  }}
                  title="Delete task"
                >
                  <Trash2 className="w-3.5 h-3.5 text-red-600" />
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function Sidebar() {
  const { 
    projects, 
    selectedProjectId, 
    selectedTaskId, 
    setSelectedProject, 
    setSelectedTask,
    sidebarCollapsed,
    toggleSidebar,
    setProjects
  } = useAppStore();
  
  const tasks = useAppStore((state) => state.tasks);
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    isOpen: boolean;
    taskId: string;
    taskTitle: string;
  }>({ isOpen: false, taskId: '', taskTitle: '' });
  const queryClient = useQueryClient();

  const handleCreateProject = () => {
    setShowCreateModal(true);
  };

  // Get tasks for a specific project
  const getProjectTasks = (projectId: string) => {
    return tasks.get(projectId) || [];
  };

  const toggleProject = (projectId: string) => {
    const newExpanded = new Set(expandedProjects);
    if (newExpanded.has(projectId)) {
      newExpanded.delete(projectId);
    } else {
      newExpanded.add(projectId);
    }
    setExpandedProjects(newExpanded);
  };

  // Delete task mutation
  const deleteTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      const response = await api.tasks.delete(taskId);
      return response.data;
    },
    onSuccess: () => {
      // Close the confirmation modal
      setDeleteConfirmation({ isOpen: false, taskId: '', taskTitle: '' });
      // Invalidate and refetch all relevant queries
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['all-tasks'] });
    },
    onError: (error) => {
      console.error('Failed to delete task:', error);
      // Keep modal open but show error state
    },
  });

  const handleDeleteTask = (taskId: string, taskTitle: string) => {
    setDeleteConfirmation({ isOpen: true, taskId, taskTitle });
  };

  const confirmDeleteTask = () => {
    // If the task being deleted is currently selected, clear the selection
    if (selectedTaskId === deleteConfirmation.taskId) {
      setSelectedTask(null);
    }
    deleteTaskMutation.mutate(deleteConfirmation.taskId);
  };

  const cancelDeleteTask = () => {
    setDeleteConfirmation({ isOpen: false, taskId: '', taskTitle: '' });
  };

  if (sidebarCollapsed) {
    return (
      <>
        <aside className="fixed left-0 top-20 bottom-0 w-16 bg-white border-r border-gray-200 z-30">
          <div className="p-4 space-y-2">
            <button 
              className="p-2 hover:bg-gray-100 rounded-lg w-full"
              onClick={toggleSidebar}
              title="Expand Sidebar"
            >
              <PanelLeftOpen className="w-5 h-5 text-gray-700" />
            </button>
            <button 
              className="p-2 hover:bg-gray-100 rounded-lg"
              onClick={handleCreateProject}
              title="Create New Project"
            >
              <Folder className="w-5 h-5 text-gray-700" />
            </button>
          </div>
        </aside>
        
        <CreateProjectModal 
          isOpen={showCreateModal} 
          onClose={() => setShowCreateModal(false)} 
        />
      </>
    );
  }

  return (
    <aside className="fixed left-0 top-20 bottom-0 w-80 bg-white border-r border-gray-200 z-30 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900">Projects</h2>
          <button 
            onClick={toggleSidebar}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            title="Collapse Sidebar"
          >
            <PanelLeftClose className="w-5 h-5 text-gray-700" />
          </button>
        </div>
        <button 
          onClick={handleCreateProject}
          className="flex items-center gap-2 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-800 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">

        
        {projects.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Folder className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">No projects yet</p>
            <p className="text-xs mt-1">Create your first project to get started</p>
          </div>
        ) : (
          projects.map((project, index) => (
            <ProjectItem
              key={`project-${project.id}-${index}`}
              project={project}
              tasks={getProjectTasks(project.id)}
              isExpanded={expandedProjects.has(project.id)}
              onToggle={() => toggleProject(project.id)}
              isSelected={selectedProjectId === project.id}
              onSelectProject={() => setSelectedProject(project.id)}
              onSelectTask={(taskId) => {
                setSelectedProject(project.id);
                setSelectedTask(taskId);
              }}
              selectedTaskId={selectedTaskId}
              onCreateTask={(projectId) => {
                setSelectedProject(projectId);
                setSelectedTask(null); // Clear task selection to show create form
              }}
              onDeleteTask={handleDeleteTask}
            />
          ))
        )}
      </div>
      
      <CreateProjectModal 
        isOpen={showCreateModal} 
        onClose={() => setShowCreateModal(false)} 
      />
      
      <ConfirmationModal
        isOpen={deleteConfirmation.isOpen}
        onClose={cancelDeleteTask}
        onConfirm={confirmDeleteTask}
        title="Delete Task"
        message={`Are you sure you want to delete the task "${deleteConfirmation.taskTitle}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        isLoading={deleteTaskMutation.isPending}
      />
    </aside>
  );
}
