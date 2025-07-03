// Polling management module
export class PollingManager {
    constructor(taskManager) {
        this.taskManager = taskManager;
        this.pollInterval = null;
        this.pollFrequency = 30000; // 30 seconds
        this.lastTaskStates = {};
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
            const response = await this.taskManager.apiClient.get('/tasks');
            if (!response.ok) {
                console.error('Failed to refresh tasks during polling');
                return;
            }

            const tasks = await response.json();
            
            // Check if we need to update the display
            const needsUpdate = this.checkIfUpdateNeeded(tasks);
            
            if (needsUpdate) {
                console.log('Task states changed, updating display');
                
                // Save current timeline card states before refresh
                const currentStates = { ...this.taskManager.timelineCardStates };
                
                // Refresh the display
                await this.taskManager.displayTasks(tasks);
                
                // Restore timeline card states after a short delay
                setTimeout(() => {
                    this.taskManager.timelineCardStates = currentStates;
                    this.taskManager.restoreTimelineCardStates();
                }, 100);
            }
            
            // Update last known states
            this.updateLastTaskStates(tasks);
            
        } catch (error) {
            console.error('Error during intelligent polling:', error);
        }
    }

    checkIfUpdateNeeded(tasks) {
        // Check if number of tasks changed
        const currentTaskIds = new Set(tasks.map(t => t.task_id));
        const lastTaskIds = new Set(Object.keys(this.lastTaskStates));
        
        if (currentTaskIds.size !== lastTaskIds.size) {
            return true;
        }
        
        // Check if any task status changed
        for (const task of tasks) {
            const lastState = this.lastTaskStates[task.task_id];
            if (!lastState || 
                lastState.status !== task.status || 
                lastState.updated_at !== task.updated_at) {
                return true;
            }
        }
        
        return false;
    }

    updateLastTaskStates(tasks) {
        this.lastTaskStates = {};
        tasks.forEach(task => {
            this.lastTaskStates[task.task_id] = {
                status: task.status,
                updated_at: task.updated_at
            };
        });
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
