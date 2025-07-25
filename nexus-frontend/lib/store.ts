import { create } from 'zustand';
import { Project, ResearchTask } from './api';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface AppState {
  // Current selections
  selectedProjectId: string | null;
  selectedTaskId: string | null;
  
  // Data
  projects: Project[];
  tasks: Map<string, ResearchTask[]>; // Map of projectId -> tasks
  
  // UI state
  isProjectsLoading: boolean;
  isTasksLoading: boolean;
  sidebarCollapsed: boolean;
  toasts: Toast[];
  
  // Actions
  setSelectedProject: (projectId: string | null) => void;
  setSelectedTask: (taskId: string | null) => void;
  setProjects: (projects: Project[]) => void;
  setProjectTasks: (projectId: string, tasks: ResearchTask[]) => void;
  addTaskToProject: (projectId: string, task: ResearchTask) => void;
  toggleSidebar: () => void;
  setProjectsLoading: (loading: boolean) => void;
  setTasksLoading: (loading: boolean) => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  
  // Computed
  getSelectedProject: () => Project | undefined;
  getSelectedTask: () => ResearchTask | undefined;
  getProjectTasks: (projectId: string) => ResearchTask[];
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  selectedProjectId: null,
  selectedTaskId: null,
  projects: [],
  tasks: new Map(),
  isProjectsLoading: false,
  isTasksLoading: false,
  sidebarCollapsed: false,
  toasts: [],
  
  // Actions
  setSelectedProject: (projectId) => set({ selectedProjectId: projectId }),
  setSelectedTask: (taskId) => set({ selectedTaskId: taskId }),
  setProjects: (projects) => set({ projects }),
  setProjectTasks: (projectId, projectTasks) => 
    set((state) => {
      const newTasks = new Map(state.tasks);
      newTasks.set(projectId, projectTasks);
      return { tasks: newTasks };
    }),
  addTaskToProject: (projectId, task) => 
    set((state) => {
      const newTasks = new Map(state.tasks);
      const currentTasks = newTasks.get(projectId) || [];
      newTasks.set(projectId, [...currentTasks, task]);
      return { tasks: newTasks };
    }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setProjectsLoading: (loading) => set({ isProjectsLoading: loading }),
  setTasksLoading: (loading) => set({ isTasksLoading: loading }),
  addToast: (toast) => 
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id: Date.now().toString() + Math.random().toString(36).substr(2, 9) }]
    })),
  removeToast: (id) => 
    set((state) => ({
      toasts: state.toasts.filter(toast => toast.id !== id)
    })),
  
  // Computed
  getSelectedProject: () => {
    const state = get();
    return state.projects.find(p => p.id === state.selectedProjectId);
  },
  getSelectedTask: () => {
    const state = get();
    if (!state.selectedProjectId || !state.selectedTaskId) return undefined;
    const projectTasks = state.tasks.get(state.selectedProjectId) || [];
    return projectTasks.find(t => t.task_id === state.selectedTaskId);
  },
  getProjectTasks: (projectId) => {
    const state = get();
    return state.tasks.get(projectId) || [];
  },
}));
