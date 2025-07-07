// Polling management module
export class PollingManager {
    constructor(taskManager) {
        this.taskManager = taskManager;
        this.pollInterval = null;
        this.pollFrequency = 5000; // 5 seconds for active tasks
        this.lastTaskStates = {};
        this.completedReports = new Set(); // Track reports we've already loaded
        this.pollingTasks = new Map(); // Track which tasks are being polled
    }

    startSmartPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        // Start polling
        this.pollInterval = setInterval(() => {
            this.refreshTasksIntelligently();
        }, this.pollFrequency);

        console.log(`Smart polling started with ${this.pollFrequency}ms interval`);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
            console.log('Polling stopped');
        }
    }

    async refreshTasksIntelligently() {
        try {
            // Only poll for active tasks (not completed or failed)
            const activeTasks = Array.from(this.pollingTasks.values()).filter(task => 
                task.status !== 'completed' && task.status !== 'failed'
            );
            
            if (activeTasks.length === 0) {
                console.log('No active tasks to poll');
                return;
            }
            
            // Poll individual task statuses and operations for active tasks only
            for (const task of activeTasks) {
                await this.pollTaskStatus(task.task_id);
                await this.pollTaskOperations(task.task_id);
            }
            
            // Poll for completed task reports that haven't been loaded yet
            const completedTasks = Array.from(this.pollingTasks.values()).filter(task => 
                task.status === 'completed' && !this.completedReports.has(task.task_id)
            );
            
            // Debug logging to understand polling behavior
            if (completedTasks.length > 0) {
                console.log(`Polling reports for ${completedTasks.length} completed tasks:`, 
                    completedTasks.map(t => `${t.task_id} (${t.status})`));
            }
            
            for (const task of completedTasks) {
                console.log(`Attempting to poll report for completed task: ${task.task_id}`);
                await this.pollTaskReport(task.task_id);
            }
            
        } catch (error) {
            console.error('Error during intelligent polling:', error);
        }
    }
    
    async pollTaskStatus(taskId) {
        try {
            const response = await this.taskManager.apiClient.get(`/tasks/${taskId}`);
            if (!response.ok) return;
            
            const task = await response.json();
            const previousTask = this.pollingTasks.get(taskId);
            
            // Update our tracking
            this.pollingTasks.set(taskId, task);
            
            // Update UI if status changed
            if (!previousTask || previousTask.status !== task.status) {
                console.log(`Task ${taskId} status changed: ${previousTask?.status || 'new'} -> ${task.status}`);
                await this.taskManager.updateTaskCard(task);
            }
        } catch (error) {
            console.error(`Error polling task ${taskId} status:`, error);
        }
    }
    
    async pollTaskOperations(taskId) {
        try {
            const response = await this.taskManager.apiClient.get(`/tasks/${taskId}/operations`);
            if (!response.ok) return;
            
            const operations = await response.json();
            this.taskManager.displayExecutedAgents(taskId, operations.operations || operations.timeline || []);
        } catch (error) {
            console.error(`Error polling task ${taskId} operations:`, error);
        }
    }
    
    async pollTaskReport(taskId) {
        try {
            const response = await this.taskManager.apiClient.get(`/tasks/${taskId}/report`);
            if (response.ok) {
                console.log(`Report available for task ${taskId}`);
                this.taskManager.fetchAndDisplayResearchReport(taskId);
                this.completedReports.add(taskId);
            }
        } catch (error) {
            // Report not ready yet, will retry next poll
        }
    }

    // Initialize polling with current tasks
    initializeWithTasks(tasks) {
        this.pollingTasks.clear();
        this.completedReports.clear();
        
        tasks.forEach(task => {
            this.pollingTasks.set(task.task_id, task);
            // Mark completed reports as already loaded if they exist
            if (task.status === 'completed' && task.has_report) {
                this.completedReports.add(task.task_id);
            }
        });
    }
    
    // Add a new task to polling
    addTask(task) {
        console.log(`Adding new task to polling: ${task.task_id} with status: ${task.status}`);
        this.pollingTasks.set(task.task_id, task);
        
        // Ensure new tasks are not marked as having reports
        if (task.status !== 'completed') {
            this.completedReports.delete(task.task_id);
        }
    }
    
    // Update task status in polling tracker
    updateTaskStatus(taskId, status) {
        const task = this.pollingTasks.get(taskId);
        if (task) {
            task.status = status;
        }
    }

    setPollFrequency(frequency) {
        this.pollFrequency = frequency;
        if (this.pollInterval) {
            this.stopPolling();
            this.startSmartPolling();
        }
    }

    getPollFrequency() {
        return this.pollFrequency;
    }
}
