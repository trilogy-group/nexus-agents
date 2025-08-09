'use client';

import React, { useState } from 'react';
import { 
  Activity, 
  BarChart3, 
  Clock, 
  AlertCircle, 
  CheckCircle, 
  XCircle, 
  Pause,
  Play,
  RotateCcw,
  Trash2,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useMonitoring, MonitoringEvent, TaskEvent, PhaseEvent, WorkerEvent, StatsSnapshot } from '@/hooks/useMonitoring';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'gray';
  subtitle?: string;
}

function MetricCard({ title, value, icon, color = 'blue', subtitle }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    red: 'bg-red-50 text-red-600 border-red-200',
    yellow: 'bg-yellow-50 text-yellow-600 border-yellow-200',
    gray: 'bg-gray-50 text-gray-600 border-gray-200',
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg border ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

interface EventListProps {
  events: MonitoringEvent[];
  title: string;
  maxHeight?: string;
}

function EventList({ events, title, maxHeight = 'max-h-96' }: EventListProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-500">{events.length} events</p>
      </div>
      <div className={`${maxHeight} overflow-y-auto`}>
        {events.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No events yet
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {events.slice().reverse().map((event, index) => (
              <EventItem key={`${event.ts}-${index}`} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EventItem({ event }: { event: MonitoringEvent }) {
  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'task_enqueued':
        return <Clock className="w-4 h-4 text-blue-600" />;
      case 'task_started':
        return <Play className="w-4 h-4 text-blue-600" />;
      case 'task_completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'task_failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'task_retry':
        return <RotateCcw className="w-4 h-4 text-yellow-600" />;
      case 'phase_started':
        return <Play className="w-4 h-4 text-purple-600" />;
      case 'phase_completed':
        return <CheckCircle className="w-4 h-4 text-purple-600" />;
      case 'worker_started':
        return <Activity className="w-4 h-4 text-green-600" />;
      case 'worker_stopped':
        return <Pause className="w-4 h-4 text-gray-600" />;
      case 'worker_heartbeat':
        return <Activity className="w-4 h-4 text-blue-600" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-600" />;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'task_completed':
      case 'phase_completed':
      case 'worker_started':
        return 'text-green-600';
      case 'task_failed':
        return 'text-red-600';
      case 'task_retry':
        return 'text-yellow-600';
      case 'task_started':
      case 'task_enqueued':
      case 'phase_started':
        return 'text-blue-600';
      case 'worker_heartbeat':
        return 'text-blue-500';
      case 'worker_stopped':
        return 'text-gray-600';
      default:
        return 'text-gray-600';
    }
  };

  const formatEventData = (event: MonitoringEvent) => {
    switch (event.event_type) {
      case 'task_enqueued':
      case 'task_started':
      case 'task_completed':
      case 'task_failed':
      case 'task_retry':
        const taskEvent = event as TaskEvent;
        return (
          <div className="text-sm">
            <span className="font-medium">{taskEvent.task_id}</span>
            {taskEvent.task_type && (
              <span className="text-gray-500"> ({taskEvent.task_type})</span>
            )}
            {taskEvent.worker_id !== undefined && (
              <span className="text-gray-500"> - Worker {taskEvent.worker_id}</span>
            )}
            {taskEvent.duration_ms && (
              <span className="text-gray-500"> - {taskEvent.duration_ms}ms</span>
            )}
            {taskEvent.error && (
              <div className="text-red-600 text-xs mt-1 truncate" title={taskEvent.error}>
                Error: {taskEvent.error}
              </div>
            )}
          </div>
        );

      case 'phase_started':
      case 'phase_completed':
        const phaseEvent = event as PhaseEvent;
        return (
          <div className="text-sm">
            <span className="font-medium">{phaseEvent.phase}</span>
            <span className="text-gray-500"> - {phaseEvent.parent_task_id}</span>
            {phaseEvent.counts && (
              <div className="text-xs text-gray-500 mt-1">
                {Object.entries(phaseEvent.counts).map(([key, value]) => (
                  <span key={key} className="mr-2">{key}: {value}</span>
                ))}
              </div>
            )}
            <div className="text-xs text-gray-500 mt-1">{phaseEvent.message}</div>
          </div>
        );

      case 'worker_started':
      case 'worker_stopped':
      case 'worker_heartbeat':
        const workerEvent = event as WorkerEvent;
        return (
          <div className="text-sm">
            <span className="font-medium">Worker {workerEvent.worker_id}</span>
            {workerEvent.status && (
              <span className="text-gray-500"> - {workerEvent.status}</span>
            )}
          </div>
        );

      case 'stats_snapshot':
        const statsEvent = event as StatsSnapshot;
        return (
          <div className="text-sm">
            {statsEvent.queue && (
              <div>
                Queue depths: {Object.entries(statsEvent.queue).map(([queue, depth]) => (
                  <span key={queue} className="mr-2">{queue}: {depth}</span>
                ))}
              </div>
            )}
            {statsEvent.counts && (
              <div>
                Task counts: {Object.entries(statsEvent.counts).map(([status, count]) => (
                  <span key={status} className="mr-2">{status}: {count}</span>
                ))}
              </div>
            )}
          </div>
        );

      default:
        return (
          <div className="text-sm">
            <pre className="text-xs text-gray-600 whitespace-pre-wrap">
              {JSON.stringify(event, null, 2)}
            </pre>
          </div>
        );
    }
  };

  return (
    <div className="px-6 py-4 hover:bg-gray-50">
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          {getEventIcon(event.event_type)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-sm font-medium ${getEventColor(event.event_type)}`}>
              {event.event_type.replace(/_/g, ' ').toUpperCase()}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(event.ts).toLocaleTimeString()}
            </span>
          </div>
          {formatEventData(event)}
        </div>
      </div>
    </div>
  );
}

export function MonitoringDashboard() {
  const {
    isConnected,
    events,
    taskEvents,
    phaseEvents,
    workerEvents,
    queueStats,
    taskCounts,
    activeWorkers,
    error,
    connect,
    disconnect,
    clearEvents,
  } = useMonitoring();

  const [activeTab, setActiveTab] = useState<'all' | 'tasks' | 'phases' | 'workers'>('all');

  const getFilteredEvents = () => {
    switch (activeTab) {
      case 'tasks':
        return taskEvents;
      case 'phases':
        return phaseEvents;
      case 'workers':
        return workerEvents;
      default:
        return events;
    }
  };

  const totalQueueDepth = Object.values(queueStats).reduce((sum, depth) => sum + depth, 0);
  const completedTasks = taskCounts.completed || 0;
  const failedTasks = taskCounts.failed || 0;
  const processingTasks = taskCounts.processing || 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">System Monitoring</h1>
          <p className="text-gray-600 mt-1">Real-time monitoring of Nexus Agents system</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
            isConnected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            <span className="text-sm font-medium">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          <button
            onClick={isConnected ? disconnect : connect}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              isConnected 
                ? 'bg-red-600 text-white hover:bg-red-700' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isConnected ? 'Disconnect' : 'Connect'}
          </button>
          
          <button
            onClick={clearEvents}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg text-sm font-medium hover:bg-gray-700"
          >
            <Trash2 className="w-4 h-4 inline mr-2" />
            Clear Events
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <span className="text-red-800 font-medium">Connection Error</span>
          </div>
          <p className="text-red-700 mt-1">{error}</p>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Active Workers"
          value={activeWorkers.size}
          icon={<Activity className="w-6 h-6" />}
          color="green"
          subtitle="Currently processing tasks"
        />
        
        <MetricCard
          title="Queue Depth"
          value={totalQueueDepth}
          icon={<BarChart3 className="w-6 h-6" />}
          color="blue"
          subtitle="Tasks waiting to be processed"
        />
        
        <MetricCard
          title="Completed Tasks"
          value={completedTasks}
          icon={<CheckCircle className="w-6 h-6" />}
          color="green"
          subtitle="Successfully completed"
        />
        
        <MetricCard
          title="Failed Tasks"
          value={failedTasks}
          icon={<XCircle className="w-6 h-6" />}
          color="red"
          subtitle="Tasks that failed"
        />
      </div>

      {/* Queue Stats */}
      {Object.keys(queueStats).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Queue Statistics</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(queueStats).map(([queueName, depth]) => (
              <div key={queueName} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-700">
                  {queueName.replace(/_/g, ' ').toUpperCase()}
                </span>
                <span className="text-lg font-bold text-gray-900">{depth}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Task Status Breakdown */}
      {Object.keys(taskCounts).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Task Status Breakdown</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(taskCounts).map(([status, count]) => {
              const getStatusColor = (status: string) => {
                switch (status) {
                  case 'completed': return 'text-green-600 bg-green-50';
                  case 'failed': return 'text-red-600 bg-red-50';
                  case 'processing': return 'text-blue-600 bg-blue-50';
                  case 'pending': return 'text-yellow-600 bg-yellow-50';
                  case 'retrying': return 'text-orange-600 bg-orange-50';
                  default: return 'text-gray-600 bg-gray-50';
                }
              };

              return (
                <div key={status} className={`p-3 rounded-lg ${getStatusColor(status)}`}>
                  <div className="text-sm font-medium capitalize">{status}</div>
                  <div className="text-2xl font-bold">{count}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Event Stream */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Event Stream</h3>
            
            {/* Event Type Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Filter:</span>
              <select
                value={activeTab}
                onChange={(e) => setActiveTab(e.target.value as any)}
                className="text-sm border border-gray-300 rounded-md px-3 py-1"
              >
                <option value="all">All Events</option>
                <option value="tasks">Task Events</option>
                <option value="phases">Phase Events</option>
                <option value="workers">Worker Events</option>
              </select>
            </div>
          </div>
        </div>
        
        <div className="max-h-96 overflow-y-auto">
          {getFilteredEvents().length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No {activeTab === 'all' ? '' : activeTab + ' '}events yet
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {getFilteredEvents().slice().reverse().map((event, index) => (
                <EventItem key={`${event.ts}-${index}`} event={event} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Phase Activity */}
      {phaseEvents.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Phase Activity</h3>
          <div className="space-y-3">
            {phaseEvents.slice(-5).reverse().map((event, index) => {
              const phaseEvent = event as PhaseEvent;
              return (
                <div key={`phase-${event.ts}-${index}`} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0">
                    {event.event_type === 'phase_started' ? (
                      <Play className="w-5 h-5 text-purple-600" />
                    ) : (
                      <CheckCircle className="w-5 h-5 text-purple-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 capitalize">{phaseEvent.phase}</span>
                      <span className="text-sm text-gray-500">
                        {event.event_type === 'phase_started' ? 'Started' : 'Completed'}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">{phaseEvent.message}</div>
                    {phaseEvent.counts && (
                      <div className="text-xs text-gray-500 mt-1">
                        {Object.entries(phaseEvent.counts).map(([key, value]) => (
                          <span key={key} className="mr-3">{key}: {value}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(event.ts).toLocaleTimeString()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}