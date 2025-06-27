// API endpoint
const API_URL = window.location.protocol + '//' + window.location.hostname + ':12000';

// Task IDs
let taskIds = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Load tasks from local storage
    const storedTaskIds = localStorage.getItem('nexus_task_ids');
    if (storedTaskIds) {
        taskIds = JSON.parse(storedTaskIds);
        refreshTasks();
    }
    
    // Set up the form
    const form = document.getElementById('create-task-form');
    form.addEventListener('submit', createTask);
    
    // Set up the continuous mode checkbox
    const continuousModeCheckbox = document.getElementById('continuous-mode');
    continuousModeCheckbox.addEventListener('change', function() {
        const intervalContainer = document.getElementById('interval-container');
        intervalContainer.style.display = this.checked ? 'block' : 'none';
    });
    
    // Refresh tasks every 10 seconds
    setInterval(refreshTasks, 10000);
});

// Create a new task
async function createTask(event) {
    event.preventDefault();
    
    const title = document.getElementById('title').value;
    const description = document.getElementById('description').value;
    const continuousMode = document.getElementById('continuous-mode').checked;
    const interval = document.getElementById('interval').value;
    
    const data = {
        title,
        description,
        continuous_mode: continuousMode,
        continuous_interval_hours: continuousMode ? parseInt(interval) : null
    };
    
    try {
        const response = await fetch(`${API_URL}/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Add the task ID to the list
        taskIds.push(result.task_id);
        
        // Save the task IDs to local storage
        localStorage.setItem('nexus_task_ids', JSON.stringify(taskIds));
        
        // Refresh the tasks
        refreshTasks();
        
        // Reset the form
        document.getElementById('create-task-form').reset();
        document.getElementById('interval-container').style.display = 'none';
    } catch (error) {
        console.error('Error creating task:', error);
        alert('Error creating task: ' + error.message);
    }
}

// Refresh the tasks
async function refreshTasks() {
    const tasksContainer = document.getElementById('tasks-container');
    
    if (taskIds.length === 0) {
        tasksContainer.innerHTML = '<p>No tasks yet. Create one above!</p>';
        return;
    }
    
    // Clear the container
    tasksContainer.innerHTML = '';
    
    // Fetch each task
    for (const taskId of taskIds) {
        try {
            const response = await fetch(`${API_URL}/tasks/${taskId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const task = await response.json();
            
            // Create a card for the task
            const card = document.createElement('div');
            card.className = 'card task-card';
            
            // Create the card header
            const cardHeader = document.createElement('div');
            cardHeader.className = 'card-header';
            cardHeader.innerHTML = `
                <h5 class="card-title mb-0">${task.title}</h5>
            `;
            
            // Create the card body
            const cardBody = document.createElement('div');
            cardBody.className = 'card-body';
            cardBody.innerHTML = `
                <p><strong>ID:</strong> ${task.task_id}</p>
                <p><strong>Description:</strong> ${task.description}</p>
                <p><strong>Status:</strong> <span class="task-status status-${task.status}">${task.status}</span></p>
                <p><strong>Continuous Mode:</strong> ${task.continuous_mode ? 'Yes' : 'No'}</p>
                ${task.continuous_mode ? `<p><strong>Update Interval:</strong> ${task.continuous_interval_hours} hours</p>` : ''}
                <p><strong>Created:</strong> ${task.created_at || 'N/A'}</p>
                <p><strong>Updated:</strong> ${task.updated_at || 'N/A'}</p>
            `;
            
            // Add artifacts if any
            if (task.artifacts && task.artifacts.length > 0) {
                const artifactsSection = document.createElement('div');
                artifactsSection.innerHTML = '<h6>Artifacts:</h6>';
                
                const artifactsList = document.createElement('ul');
                for (const artifact of task.artifacts) {
                    const artifactItem = document.createElement('li');
                    artifactItem.innerHTML = `
                        <strong>${artifact.title}</strong> (${artifact.type})
                        <br>
                        <small>${artifact.filepath}</small>
                    `;
                    artifactsList.appendChild(artifactItem);
                }
                
                artifactsSection.appendChild(artifactsList);
                cardBody.appendChild(artifactsSection);
            }
            
            // Add the header and body to the card
            card.appendChild(cardHeader);
            card.appendChild(cardBody);
            
            // Add the card to the container
            tasksContainer.appendChild(card);
        } catch (error) {
            console.error(`Error fetching task ${taskId}:`, error);
            
            // Create an error card
            const errorCard = document.createElement('div');
            errorCard.className = 'card task-card';
            errorCard.innerHTML = `
                <div class="card-header">
                    <h5 class="card-title mb-0">Error</h5>
                </div>
                <div class="card-body">
                    <p>Error fetching task ${taskId}: ${error.message}</p>
                </div>
            `;
            
            tasksContainer.appendChild(errorCard);
        }
    }
}