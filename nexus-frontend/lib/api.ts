// API configuration and client
import axios from 'axios';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:12000';

// Create axios instance with default config
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API endpoints
export const api = {
  // Projects
  projects: {
    list: (userId?: string) => 
      apiClient.get('/projects', { params: { user_id: userId } }),
    
    get: (projectId: string) => 
      apiClient.get(`/projects/${projectId}`),
    
    create: (data: { name: string; description?: string; user_id?: string }) => 
      apiClient.post('/projects', data),
    
    update: (projectId: string, data: { name?: string; description?: string }) => 
      apiClient.put(`/projects/${projectId}`, data),
    
    delete: (projectId: string) => 
      apiClient.delete(`/projects/${projectId}`),
    
    getTasks: (projectId: string) => 
      apiClient.get(`/projects/${projectId}/tasks`),
    
    createTask: (projectId: string, data: any) => 
      apiClient.post(`/projects/${projectId}/tasks`, data),
    
    getKnowledgeGraph: (projectId: string) => 
      apiClient.get(`/projects/${projectId}/knowledge`),
    
    updateKnowledgeGraph: (projectId: string, data: any) => 
      apiClient.put(`/projects/${projectId}/knowledge`, data),
    
    getProjectEntities: (projectId: string) => 
      apiClient.get(`/projects/${projectId}/entities`),
  },
  
  // Tasks
  tasks: {
    list: (project_id?: string) => 
      apiClient.get('/tasks', { params: { project_id } }),
    
    create: (data: {
      title: string;
      research_query: string;
      research_type: string;
      project_id: string;
      user_id?: string | null;
      data_aggregation_config?: any | null;
    }) => 
      apiClient.post('/tasks', data),
    
    get: (taskId: string) => 
      apiClient.get(`/tasks/${taskId}`),
    
    getTimeline: (taskId: string) => 
      apiClient.get(`/tasks/${taskId}/timeline`),
    
    getReport: (taskId: string) => 
      apiClient.get(`/tasks/${taskId}/report`),
    
    delete: (taskId: string) => 
      apiClient.delete(`/tasks/${taskId}`),
    
    exportCSV: (taskId: string) => 
      apiClient.get(`/tasks/${taskId}/export/csv`, { responseType: 'blob' }),
  },
};

// Types
export interface Project {
  id: string;
  name: string;
  description?: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ResearchTask {
  task_id: string;
  title: string;
  description?: string;
  research_query: string;
  status: string;
  project_id?: string;
  user_id?: string;
  research_type?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface TaskTimeline {
  task: ResearchTask;
  timeline: any[];
  artifacts: any[];
  statistics: {
    total_operations: number;
    completed_operations: number;
    failed_operations: number;
    total_evidence_items: number;
    total_artifacts: number;
    search_providers_used: string[];
  };
}
