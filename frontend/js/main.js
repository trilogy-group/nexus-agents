// Main application entry point
import { ThemeManager } from './modules/theme.js';
import { TaskManager } from './modules/tasks.js';
import { PollingManager } from './modules/polling.js';
import { ComponentRenderer } from '../components/renderer.js';

// Initialize global managers
const themeManager = new ThemeManager();
const taskManager = new TaskManager();
const pollingManager = new PollingManager(taskManager);
const componentRenderer = new ComponentRenderer();

// Initialize the application
class NexusAgentsApp {
    constructor() {
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;

        // Initialize theme first
        themeManager.initialize();

        // Render initial components
        await this.renderInitialComponents();

        // Initialize task management
        await taskManager.initialize();

        // Start polling
        pollingManager.startSmartPolling();

        // Setup global event listeners
        this.setupGlobalEventListeners();

        this.initialized = true;
        console.log('Nexus Agents application initialized successfully');
    }

    async renderInitialComponents() {
        // Render task creation form
        const taskFormContainer = document.getElementById('taskCreationForm');
        if (taskFormContainer) {
            taskFormContainer.innerHTML = componentRenderer.renderTaskCreationForm();
        }

        // Render task list container
        const taskListContainer = document.getElementById('taskList');
        if (taskListContainer) {
            taskListContainer.innerHTML = componentRenderer.renderTaskListContainer();
        }

        // Render research report modal directly to the body
        const modalHtml = componentRenderer.renderResearchReportModal();
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    setupGlobalEventListeners() {
        // Global click handler for dynamic content
        document.addEventListener('click', (event) => {
            const target = event.target;

            // Handle task creation
            if (target.closest('#create-task-form button[type="submit"]')) {
                event.preventDefault();
                const taskForm = document.getElementById('create-task-form');
                const formEvent = {
                    preventDefault: () => {},
                    target: taskForm
                };
                taskManager.createTask(formEvent);
            
            }

            // Handle evidence toggle
            if (target.matches('[data-action="toggle-evidence"]')) {
                const taskId = target.dataset.taskId;
                taskManager.toggleEvidence(taskId, target);
            }

            // Handle task deletion
            if (target.matches('[data-action="delete-task"]')) {
                event.preventDefault();
                event.stopPropagation();
                const taskId = target.dataset.taskId;
                const taskTitle = target.dataset.taskTitle;
                taskManager.deleteTask(taskId, taskTitle);
            }

            // Handle timeline card toggle
            if (target.matches('[data-action="toggle-timeline"]')) {
                const cardId = target.dataset.cardId;
                taskManager.toggleTimelineCard(cardId);
            }

            // Handle report modal
            if (target.matches('[data-action="open-report"]')) {
                const taskId = target.dataset.taskId;
                taskManager.openReportModal(taskId);
            }

            // Handle theme toggle (fix to work with both button and icon)
            if (target.matches('#themeToggle') || target.matches('#themeIcon') || target.closest('#themeToggle')) {
                themeManager.toggleTheme();
            }
        });

        // Global form submission handler
        document.addEventListener('submit', (event) => {
            if (event.target.matches('#taskForm')) {
                event.preventDefault();
                taskManager.createTask(event);
            }
        });

        // Global modal event handlers will be setup after DOM content loads
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new NexusAgentsApp();
    app.init();
    
    // Add event listener for continuous mode checkbox
    document.addEventListener('change', (event) => {
        if (event.target.id === 'continuous-mode') {
            const intervalContainer = document.getElementById('interval-container');
            intervalContainer.style.display = event.target.checked ? 'block' : 'none';
        }
    });
});

// Expose global functions for event handlers
window.toggleTheme = () => themeManager.toggleTheme();
window.taskManager = taskManager;
window.themeManager = themeManager;

// Global state for timeline card expansion
let timelineCardStates = {};

// Toggle timeline card expansion
window.toggleTimelineCard = function(cardId) {
    console.log('Attempting to toggle card:', cardId);
    const card = document.getElementById(cardId);
    console.log('Found card element:', card);
    
    if (card) {
        const wasExpanded = card.classList.contains('expanded');
        console.log('Card was expanded:', wasExpanded);
        
        const isExpanded = card.classList.toggle('expanded');
        console.log('Card is now expanded:', isExpanded);
        
        timelineCardStates[cardId] = isExpanded;
        
        // Update the toggle arrow
        const toggle = card.querySelector('.timeline-card-toggle');
        console.log('Found toggle element:', toggle);
        if (toggle) {
            toggle.textContent = isExpanded ? '▼' : '▶';
            console.log('Updated toggle to:', toggle.textContent);
        }
        
        // Check if card body is showing
        const cardBody = card.querySelector('.timeline-card-body');
        console.log('Card body element:', cardBody);
        if (cardBody) {
            console.log('Card body display style:', window.getComputedStyle(cardBody).display);
        }
        
        // If expanding, expand all JSON viewers in this card
        if (isExpanded) {
            setTimeout(() => {
                const jsonViewers = card.querySelectorAll('json-viewer');
                console.log('Found JSON viewers to expand:', jsonViewers.length);
                jsonViewers.forEach(viewer => {
                    if (viewer.expandAll && typeof viewer.expandAll === 'function') {
                        viewer.expandAll();
                    }
                });
            }, 50); // Small delay to ensure DOM is rendered
        }
    } else {
        console.error('Could not find timeline card with ID:', cardId);
        // Try to find it by looking for all timeline cards
        const allCards = document.querySelectorAll('.timeline-card');
        console.log('All timeline cards found:', allCards.length);
        allCards.forEach((card, index) => {
            console.log(`Card ${index}: id="${card.id}", classes="${card.className}"`);
        });
    }
};

// Restore timeline card states after DOM update
window.restoreTimelineCardStates = function() {
    for (const [cardId, isExpanded] of Object.entries(timelineCardStates)) {
        const card = document.getElementById(cardId);
        if (card && isExpanded) {
            card.classList.add('expanded');
            const toggle = card.querySelector('.timeline-card-toggle');
            if (toggle) {
                toggle.textContent = '▼';
            }
        }
    }
};

// Render JSON tree with theme support (copied from working original frontend with robust error handling)
window.renderJsonTree = function(obj) {
    const viewerId = 'json-viewer-' + Math.random().toString(36).substr(2, 9);
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    
    try {
        // Safely serialize JSON with custom replacer to handle problematic values
        const jsonString = JSON.stringify(obj, function(key, value) {
            // Handle potentially problematic values
            if (typeof value === 'string') {
                // Truncate extremely long strings that might cause issues
                if (value.length > 10000) {
                    return value.substring(0, 10000) + '... [truncated]';
                }
                // Replace problematic characters that break JSON parsing
                return value.replace(/[\u0000-\u001F\u007F-\u009F]/g, '');
            }
            return value;
        }, 2);
        
        // More comprehensive escaping for HTML attributes
        const escapedJson = jsonString
            .replace(/&/g, '&amp;')     // Escape ampersands first
            .replace(/'/g, '&#39;')     // Escape single quotes
            .replace(/"/g, '&quot;')    // Escape double quotes
            .replace(/</g, '&lt;')      // Escape less than
            .replace(/>/g, '&gt;');     // Escape greater than
            
        return `<json-viewer id="${viewerId}" data='${escapedJson}' theme="${currentTheme}"></json-viewer>`;
    } catch (error) {
        console.error('Error serializing JSON for viewer:', error, obj);
        return `<div class="alert alert-warning"><small>Unable to render JSON data: ${error.message}</small></div>`;
    }
};

window.pollingManager = pollingManager;
window.componentRenderer = componentRenderer;

// Export for global access if needed
window.NexusAgentsApp = NexusAgentsApp;

// Export individual managers for global access
window.createTask = (event) => taskManager.createTask(event);
window.deleteTask = (taskId, taskTitle) => taskManager.deleteTask(taskId, taskTitle);
window.toggleEvidence = (taskId, button) => taskManager.toggleEvidence(taskId, button);
window.openReportModal = (taskId) => taskManager.openReportModal(taskId);
window.downloadReport = () => taskManager.downloadReport();
window.toggleTimelineCard = (cardId) => taskManager.toggleTimelineCard(cardId);
