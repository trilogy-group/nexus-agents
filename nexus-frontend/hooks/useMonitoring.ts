'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export interface MonitoringEvent {
  event_id: string;
  ts: string;
  event_type: string;
  
  // Task/project identifiers
  project_id?: string;
  parent_task_id?: string;
  task_id?: string;
  task_type?: string;
  phase?: string;
  
  // Worker information
  worker_id?: number;
  
  // Task execution details
  retry_count?: number;
  status?: string;
  duration_ms?: number;
  
  // Aggregated data
  counts?: Record<string, number>;
  queue?: Record<string, number>;
  
  // Messages and errors
  message?: string;
  error?: string;
  
  // Additional metadata
  meta?: Record<string, any>;
}

export interface TaskEvent extends MonitoringEvent {
  task_id: string;
  task_type: string;
  status: string;
}

export interface PhaseEvent extends MonitoringEvent {
  phase: string;
  parent_task_id: string;
  message: string;
}

export interface WorkerEvent extends MonitoringEvent {
  worker_id: number;
}

export interface StatsSnapshot extends MonitoringEvent {
  queue?: Record<string, number>;
  counts?: Record<string, number>;
}

export interface MonitoringState {
  isConnected: boolean;
  events: MonitoringEvent[];
  taskEvents: TaskEvent[];
  phaseEvents: PhaseEvent[];
  workerEvents: WorkerEvent[];
  statsSnapshots: StatsSnapshot[];
  queueStats: Record<string, number>;
  taskCounts: Record<string, number>;
  taskStatusById: Record<string, string>; // current status per task_id for accurate breakdown
  activeWorkers: Set<number>;
  // Throughput metrics
  throughputWindowMin: number; // rolling window in minutes (default 15)
  throughputPerMin: number; // tasks/min over the selected window
  completedTimestamps: number[]; // ring buffer of last 500 completion timestamps (ms)
  error: string | null;
}

const MAX_EVENTS = 1000; // Keep last 1000 events

export function useMonitoring() {
  const [state, setState] = useState<MonitoringState>({
    isConnected: false,
    events: [],
    taskEvents: [],
    phaseEvents: [],
    workerEvents: [],
    statsSnapshots: [],
    queueStats: {},
    taskCounts: {},
    taskStatusById: {},
    activeWorkers: new Set(),
    throughputWindowMin: 15,
    throughputPerMin: 0,
    completedTimestamps: [],
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const addEvent = useCallback((event: MonitoringEvent) => {
    setState(prev => {
      const newEvents = [...prev.events, event].slice(-MAX_EVENTS);
      
      // Categorize events
      const newTaskEvents = [...prev.taskEvents];
      const newPhaseEvents = [...prev.phaseEvents];
      const newWorkerEvents = [...prev.workerEvents];
      const newStatsSnapshots = [...prev.statsSnapshots];
      let newQueueStats = { ...prev.queueStats };
      let newTaskCounts = { ...prev.taskCounts };
      let newTaskStatusById = { ...prev.taskStatusById };
      let newActiveWorkers = new Set(prev.activeWorkers);
      let newCompletedTimestamps = [...prev.completedTimestamps];

      switch (event.event_type) {
        case 'task_enqueued':
        case 'task_started':
        case 'task_completed':
        case 'task_failed':
        case 'task_retry':
          newTaskEvents.push(event as TaskEvent);
          newTaskEvents.splice(0, Math.max(0, newTaskEvents.length - MAX_EVENTS));
          
          // Update current-status breakdown using per-task map
          const taskEvent = event as TaskEvent;
          const currentStatus = taskEvent.status;
          const taskId = taskEvent.task_id;
          if (taskId && currentStatus) {
            const prevStatus = newTaskStatusById[taskId];
            if (prevStatus !== currentStatus) {
              if (prevStatus) {
                newTaskCounts[prevStatus] = Math.max(0, (newTaskCounts[prevStatus] || 0) - 1);
              }
              newTaskCounts[currentStatus] = (newTaskCounts[currentStatus] || 0) + 1;
              newTaskStatusById[taskId] = currentStatus;
            }
          }

          // Update throughput ring buffer on completion
          if (event.event_type === 'task_completed') {
            const tsMs = Date.parse(event.ts);
            newCompletedTimestamps.push(Number.isFinite(tsMs) ? tsMs : Date.now());
            if (newCompletedTimestamps.length > 500) {
              newCompletedTimestamps.splice(0, newCompletedTimestamps.length - 500);
            }
          }
          break;

        case 'phase_started':
        case 'phase_completed':
          newPhaseEvents.push(event as PhaseEvent);
          newPhaseEvents.splice(0, Math.max(0, newPhaseEvents.length - MAX_EVENTS));
          break;

        case 'worker_started':
        case 'worker_stopped':
        case 'worker_heartbeat':
          newWorkerEvents.push(event as WorkerEvent);
          newWorkerEvents.splice(0, Math.max(0, newWorkerEvents.length - MAX_EVENTS));
          
          const workerEvent = event as WorkerEvent;
          if (event.event_type === 'worker_started' || event.event_type === 'worker_heartbeat') {
            if (workerEvent.worker_id) {
              newActiveWorkers.add(workerEvent.worker_id);
            }
          } else if (event.event_type === 'worker_stopped') {
            if (workerEvent.worker_id) {
              newActiveWorkers.delete(workerEvent.worker_id);
            }
          }
          break;

        case 'stats_snapshot':
          newStatsSnapshots.push(event as StatsSnapshot);
          newStatsSnapshots.splice(0, Math.max(0, newStatsSnapshots.length - MAX_EVENTS));
          
          const statsEvent = event as StatsSnapshot;
          if (statsEvent.queue) {
            newQueueStats = { ...statsEvent.queue };
          }
          // Do not merge counts from snapshots into taskCounts to avoid mixing
          // snapshot-based totals with live per-task status. If needed, we can
          // expose snapshot counts separately in the UI.
          break;
      }

      // Recompute throughput based on selected window
      const now = Date.now();
      const windowMs = prev.throughputWindowMin * 60_000;
      const inWindow = newCompletedTimestamps.filter(ts => now - ts <= windowMs).length;
      const newThroughputPerMin = prev.throughputWindowMin > 0 ? inWindow / prev.throughputWindowMin : 0;

      return {
        ...prev,
        events: newEvents,
        taskEvents: newTaskEvents,
        phaseEvents: newPhaseEvents,
        workerEvents: newWorkerEvents,
        statsSnapshots: newStatsSnapshots,
        queueStats: newQueueStats,
        taskCounts: newTaskCounts,
        taskStatusById: newTaskStatusById,
        activeWorkers: newActiveWorkers,
        completedTimestamps: newCompletedTimestamps,
        throughputPerMin: newThroughputPerMin,
      };
    });
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      // Get WebSocket URL from environment or use default
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const apiHost = process.env.NEXT_PUBLIC_API_HOST || 'localhost';
      const apiPort = process.env.NEXT_PUBLIC_API_PORT || '12000';
      const wsUrl = `${wsProtocol}//${apiHost}${apiPort ? `:${apiPort}` : ''}/ws/monitor`;

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('Monitoring WebSocket connected');
        setState(prev => ({ ...prev, isConnected: true, error: null }));
        reconnectAttempts.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Ignore keepalive or malformed messages lacking an event_type
          if (!data || typeof data !== 'object' || !('event_type' in data) || data.event_type === 'ping') {
            return;
          }
          addEvent(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('Monitoring WebSocket disconnected:', event.code, event.reason);
        setState(prev => ({ ...prev, isConnected: false, error: event.reason || prev.error }));

        // Attempt to reconnect if not a clean close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };

      wsRef.current.onerror = (event) => {
        // Avoid triggering Next.js error overlay; rely on onclose for details
        console.warn('Monitoring WebSocket error event');
        setState(prev => ({
          ...prev,
          error: prev.error || 'WebSocket error',
        }));
      };

    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setState(prev => ({ 
        ...prev, 
        error: 'Failed to create WebSocket connection',
        isConnected: false 
      }));
    }
  }, [addEvent]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounting');
      wsRef.current = null;
    }

    setState(prev => ({ ...prev, isConnected: false }));
  }, []);

  const clearEvents = useCallback(() => {
    setState(prev => ({
      ...prev,
      events: [],
      taskEvents: [],
      phaseEvents: [],
      workerEvents: [],
      statsSnapshots: [],
      taskCounts: {},
      taskStatusById: {},
      completedTimestamps: [],
      throughputPerMin: 0,
    }));
  }, []);

  const setThroughputWindow = useCallback((minutes: number) => {
    setState(prev => {
      const now = Date.now();
      const windowMs = minutes * 60_000;
      const inWindow = prev.completedTimestamps.filter(ts => now - ts <= windowMs).length;
      const perMin = minutes > 0 ? inWindow / minutes : 0;
      return {
        ...prev,
        throughputWindowMin: minutes,
        throughputPerMin: perMin,
      };
    });
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    clearEvents,
    setThroughputWindow,
    throughputPerMin: state.throughputPerMin,
    throughputWindowMin: state.throughputWindowMin,
  };
}