# Frontend Refactoring Plan: Nexus Agents UI

This document outlines the refactoring of the monolithic `index.html` into a modern, component-based JavaScript application. This new structure improves maintainability, scalability, and separation of concerns.

## Project Structure

The new frontend codebase is organized into two main directories: `public` and `src`.

*   **`public/`**: Contains static assets that are served directly to the browser, such as the main `index.html` and CSS files.
*   **`src/`**: Contains the JavaScript source code, organized by function into components and services.

```
.
├── public/
│   ├── css/
│   │   └── style.css
│   └── index.html
└── src/
    ├── components/
    │   ├── CreateTaskForm.js
    │   ├── TaskCard.js
    │   └── TaskList.js
    ├── services/
    │   ├── api.js
    │   └── state.js
    └── main.js
```

---

## File Contents

### 1. `public/index.html`

This is the main HTML entry point. It has been stripped down to a basic shell. It includes the necessary meta tags, links to Bootstrap CSS and our local stylesheet, and a single `<div id="app">` where the entire application will be dynamically rendered by JavaScript. The main script, `main.js`, is loaded as a module.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Agents</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div id="app" class="container">
        <!-- App content will be rendered here by JavaScript -->
    </div>
    <script type="module" src="../src/main.js"></script>
</body>
</html>
```

### 2. `public/css/style.css`

This file contains all the custom CSS styles that were previously in a `<style>` tag in the original `index.html`.

```css
body {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.task-card {
    margin-bottom: 1rem;
}
.task-status {
    font-weight: bold;
}
.status-created { color: #6c757d; }
.status-planning { color: #17a2b8; }
.status-searching { color: #007bff; }
.status-summarizing { color: #fd7e14; }
.status-reasoning { color: #6f42c1; }
.status-generating_artifacts { color: #e83e8c; }
.status-completed { color: #28a745; }
.status-failed { color: #dc3545; }
```

### 3. `src/services/api.js`

This service module abstracts all communication with the backend API. It centralizes API endpoints and fetch logic, making it easy to manage and update.

```javascript
const API_URL = window.location.protocol + '//' + window.location.hostname + ':12000';

/**
 * Creates a new task on the server.
 * @param {object} taskData - The data for the new task.
 * @returns {Promise<object>} The created task object.
 */
export async function createTask(taskData) {
    const response = await fetch(`${API_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskData)
    });
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

/**
 * Fetches a single task by its ID.
 * @param {string} taskId - The ID of the task to fetch.
 * @returns {Promise<object>} The task object.
 */
export async function getTask(taskId) {
    const response = await fetch(`${API_URL}/tasks/${taskId}`);
    if (!response.ok) {
        // We don't throw here for a single task failure, so other tasks can still render.
        // The caller will handle the non-ok response.
        console.error(`Error fetching task ${taskId}: ${response.statusText}`);
        return null;
    }
    return response.json();
}
```

### 4. `src/services/state.js`

This module manages the application's state, specifically the list of task IDs. It handles loading from and saving to `localStorage`, providing a single source of truth for which tasks the client is tracking.

```javascript
const STORAGE_KEY = 'nexus_task_ids';
let taskIds = [];

/**
 * Loads task IDs from localStorage into memory.
 */
function loadTaskIds() {
    const storedTaskIds = localStorage.getItem(STORAGE_KEY);
    if (storedTaskIds) {
        taskIds = JSON.parse(storedTaskIds);
    }
}

/**
 * Saves the current list of task IDs to localStorage.
 */
function saveTaskIds() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(taskIds));
}

/**
 * Gets the current list of task IDs.
 * @returns {string[]} An array of task IDs.
 */
export function getTaskIds() {
    return [...taskIds];
}

/**
 * Adds a new task ID to the list and saves to localStorage.
 * @param {string} taskId - The new task ID to add.
 */
export function addTask(taskId) {
    if (!taskIds.includes(taskId)) {
        taskIds.push(taskId);
        saveTaskIds();
    }
}

// Initial load when the module is imported.
loadTaskIds();
```

### 5. `src/components/CreateTaskForm.js`

This component is responsible for rendering the "Create Research Task" form and handling its submission logic. When a task is successfully created, it dispatches a custom `taskCreated` event to notify other parts of the application (like the `TaskList`) to update.

```javascript
import { createTask } from '../services/api.js';
import { addTask } from '../services/state.js';

const formTemplate = `
    <div class="card">
        <div class="card-header">
            <h5 class="card-title mb-0">Create Research Task</h5>
        </div>
        <div class="card-body">
            <form id="create-task-form">
                <div class="mb-3">
                    <label for="title" class="form-label">Title</label>
                    <input type="text" class="form-control" id="title" required>
                </div>
                <div class="mb-3">
                    <label for="description" class="form-label">Description</label>
                    <textarea class="form-control" id="description" rows="3" required></textarea>
                </div>
                <div class="mb-3 form-check">
                    <input type="checkbox" class="form-check-input" id="continuous-mode">
                    <label class="form-check-label" for="continuous-mode">Continuous Mode</label>
                </div>
                <div class="mb-3" id="interval-container" style="display: none;">
                    <label for="interval" class="form-label">Update Interval (hours)</label>
                    <input type="number" class="form-control" id="interval" value="24" min="1">
                </div>
                <button type="submit" class="btn btn-primary">Create Task</button>
            </form>
        </div>
    </div>
`;

export function renderCreateTaskForm(container) {
    container.innerHTML = formTemplate;

    const form = container.querySelector('#create-task-form');
    const continuousModeCheckbox = container.querySelector('#continuous-mode');
    const intervalContainer = container.querySelector('#interval-container');

    continuousModeCheckbox.addEventListener('change', function() {
        intervalContainer.style.display = this.checked ? 'block' : 'none';
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const title = container.querySelector('#title').value;
        const description = container.querySelector('#description').value;
        const continuousMode = continuousModeCheckbox.checked;
        const interval = container.querySelector('#interval').value;

        const data = {
            title,
            description,
            continuous_mode: continuousMode,
            continuous_interval_hours: continuousMode ? parseInt(interval) : null
        };

        try {
            const result = await createTask(data);
            addTask(result.task_id);
            document.dispatchEvent(new CustomEvent('taskCreated', { detail: result }));
            form.reset();
            intervalContainer.style.display = 'none';
        } catch (error) {
            console.error('Error creating task:', error);
            alert('Error creating task: ' + error.message);
        }
    });
}
```

### 6. `src/components/TaskCard.js`

A pure presentation component. It takes a task object and returns a DOM element representing the task card. This isolates the card's structure and makes it easy to modify.

```javascript
export function createTaskCard(task) {
    if (!task) {
        return null;
    }

    const card = document.createElement('div');
    card.className = 'card task-card';
    
    const artifactsHtml = (task.artifacts && task.artifacts.length > 0)
        ? `<h6>Artifacts:</h6>
           <ul>
             ${task.artifacts.map(artifact => `
               <li>
                 <strong>${artifact.title}</strong> (${artifact.type})
                 <br>
                 <small>${artifact.filepath}</small>
               </li>`).join('')}
           </ul>`
        : '';

    card.innerHTML = `
        <div class="card-header">
            <h5 class="card-title mb-0">${task.title}</h5>
        </div>
        <div class="card-body">
            <p><strong>ID:</strong> ${task.task_id}</p>
            <p><strong>Description:</strong> ${task.description}</p>
            <p><strong>Status:</strong> <span class="task-status status-${task.status}">${task.status}</span></p>
            <p><strong>Continuous Mode:</strong> ${task.continuous_mode ? 'Yes' : 'No'}</p>
            ${task.continuous_mode ? `<p><strong>Update Interval:</strong> ${task.continuous_interval_hours} hours</p>` : ''}
            <p><strong>Created:</strong> ${new Date(task.created_at).toLocaleString() || 'N/A'}</p>
            <p><strong>Updated:</strong> ${new Date(task.updated_at).toLocaleString() || 'N/A'}</p>
            ${artifactsHtml}
        </div>
    `;
    return card;
}

export function createTaskErrorCard(taskId, error) {
    const card = document.createElement('div');
    card.className = 'card task-card';
    card.innerHTML = `
        <div class="card-header bg-danger text-white">
            <h5 class="card-title mb-0">Error</h5>
        </div>
        <div class="card-body">
            <p>Error fetching task <strong>${taskId}</strong>: ${error.message}</p>
        </div>
    `;
    return card;
}
```

### 7. `src/components/TaskList.js`

This component manages the display of the list of tasks. It fetches task data, uses `TaskCard.js` to render each task, and handles the periodic refresh. It listens for the `taskCreated` event to update the list immediately when a new task is added.

```javascript
import { getTaskIds } from '../services/state.js';
import { getTask } from '../services/api.js';
import { createTaskCard, createTaskErrorCard } from './TaskCard.js';

let tasksContainer;

async function refreshTasks() {
    const taskIds = getTaskIds();
    
    if (!tasksContainer) return;

    if (taskIds.length === 0) {
        tasksContainer.innerHTML = '<p>No tasks yet. Create one above!</p>';
        return;
    }
    
    tasksContainer.innerHTML = ''; // Clear previous content
    
    const taskPromises = taskIds.map(id => getTask(id).catch(err => ({ error: err, taskId: id })));
    
    for (const taskPromise of taskPromises) {
        try {
            const task = await taskPromise;
            let card;
            if (task && !task.error) {
                card = createTaskCard(task);
            } else {
                // Handle case where getTask returns null or an error object
                const error = task ? task.error : new Error('Task not found or failed to load.');
                const taskId = task ? task.taskId : 'Unknown ID';
                card = createTaskErrorCard(taskId, error);
            }
            if (card) {
                tasksContainer.appendChild(card);
            }
        } catch (error) {
            console.error('Error processing task promise:', error);
        }
    }
}

export function renderTaskList(container) {
    container.innerHTML = `
        <h2>Research Tasks</h2>
        <div id="tasks-container">
            <p>Loading tasks...</p>
        </div>
    `;
    tasksContainer = container.querySelector('#tasks-container');
    
    // Initial refresh
    refreshTasks();
    
    // Refresh every 10 seconds
    setInterval(refreshTasks, 10000);

    // Listen for new tasks to trigger an immediate refresh
    document.addEventListener('taskCreated', () => {
        console.log('New task created, refreshing list...');
        refreshTasks();
    });
}
```

### 8. `src/main.js`

This is the main entry point for the application. It orchestrates the rendering of the different components into the main `#app` container in `index.html`.

```javascript
import { renderCreateTaskForm } from './components/CreateTaskForm.js';
import { renderTaskList } from './components/TaskList.js';

document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');

    // Create main layout containers
    const header = document.createElement('h1');
    header.className = 'mb-4';
    header.textContent = 'Nexus Agents';

    const formRow = document.createElement('div');
    formRow.className = 'row mb-4';
    const formCol = document.createElement('div');
    formCol.className = 'col-md-12';
    formRow.appendChild(formCol);

    const tasksRow = document.createElement('div');
    tasksRow.className = 'row';
    const tasksCol = document.createElement('div');
    tasksCol.className = 'col-md-12';
    tasksRow.appendChild(tasksCol);

    // Append layout to the app container
    app.appendChild(header);
    app.appendChild(formRow);
    app.appendChild(tasksRow);

    // Render components into their containers
    renderCreateTaskForm(formCol);
    renderTaskList(tasksCol);
});
```