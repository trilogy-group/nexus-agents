// Task management module
import { ApiClient } from './api.js';

export class TaskManager {
    constructor() {
        this.apiClient = new ApiClient();
        this.timelineCardStates = {};
        this.currentReportData = null;
        this.lastTaskStates = {};
        this.jsonViewerCount = 0;
    }

    async initialize() {
        // Load tasks initially
        await this.refreshTasks();
    }

    async createTask(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const title = formData.get('title');
        const description = formData.get('description');
        const continuousMode = formData.get('continuous-mode') === 'on';
        const interval = formData.get('interval');
        
        if (!title.trim() || !description.trim()) {
            alert('Please fill in all required fields');
            return;
        }

        // Show loading state
        const submitButton = event.target.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="loading-spinner"></span> Creating Task...';

        try {
            const response = await this.apiClient.post('/tasks', {
                title: title.trim(),
                description: description.trim(),
                continuous_mode: continuousMode,
                continuous_interval_hours: continuousMode ? parseInt(interval) : null
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Task created:', result);
                
                // Clear form
                event.target.reset();
                document.getElementById('interval-container').style.display = 'none';
                
                // Refresh tasks to show the new one
                await this.refreshTasks();
            } else {
                const error = await response.json();
                alert(`Failed to create task: ${error.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error creating task:', error);
            alert('Failed to create task. Please try again.');
        } finally {
            // Restore button state
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    async refreshTasks() {
        try {
            const response = await this.apiClient.get('/tasks');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const tasks = await response.json();
            await this.displayTasks(tasks);
        } catch (error) {
            console.error('Error fetching tasks:', error);
            this.displayError('Failed to load tasks. Please refresh the page.');
        }
    }

    async displayTasks(tasks) {
        const taskListContainer = document.getElementById('taskListContainer');
        if (!taskListContainer) return;

        if (!tasks || tasks.length === 0) {
            taskListContainer.innerHTML = `
                <div class="alert alert-info" role="alert">
                    <h4 class="alert-heading">No Research Tasks</h4>
                    <p>You haven't created any research tasks yet. Use the form above to start your first research task.</p>
                </div>
            `;
            return;
        }

        let html = '<div class="row">';
        
        for (const task of tasks) {
            html += this.renderTaskCard(task);
        }
        
        html += '</div>';
        taskListContainer.innerHTML = html;
        
        // Load detailed workflow information after rendering
        for (const task of tasks) {
            setTimeout(() => this.loadTaskWorkflowDetails(task.task_id), 100);
        }
        
        // Restore timeline card states after DOM update
        setTimeout(() => this.restoreTimelineCardStates(), 100);
    }

    async loadTaskWorkflowDetails(taskId) {
        try {
            const [taskResponse, operationsResponse] = await Promise.all([
                this.apiClient.get(`/tasks/${taskId}`),
                this.apiClient.get(`/tasks/${taskId}/operations`)
            ]);

            const task = taskResponse.ok ? await taskResponse.json() : null;
            const operations = operationsResponse.ok ? await operationsResponse.json() : null;

            // Always display Executed Agents if operations are available (match original frontend)
            if (operations && operations.operations && Array.isArray(operations.operations)) {
                this.displayExecutedAgents(taskId, operations.operations);
            } else if (operations && Array.isArray(operations.timeline)) {
                this.displayExecutedAgents(taskId, operations.timeline);
            }
            
            // Auto-load Research Report for completed tasks
            if (task && task.status === 'completed') {
                this.fetchAndDisplayResearchReport(taskId);
            }

            return {
                task: task,
                operations: operations?.timeline || []
            };
        } catch (error) {
            console.error(`Error loading details for task ${taskId}:`, error);
            return { task: null, operations: [] };
        }
    }

    renderTaskCard(task, taskDetails) {
        const statusClass = `status-${task.status}`;
        
        return `
            <div class="col-12 mb-4">
                <div class="card task-card">
                    <div class="card-header" data-bs-toggle="collapse" data-bs-target="#card-body-${task.task_id}" style="cursor: pointer;">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">${this.escapeHtml(task.title)}</h5>
                            <div class="d-flex align-items-center">
                                <span class="task-status ${statusClass} me-3">${task.status}</span>
                                <i class="fas fa-chevron-down"></i>
                            </div>
                        </div>
                    </div>
                    <div class="collapse" id="card-body-${task.task_id}">
                        <div class="card-body">
                            <div class="task-basic-info mb-3">
                                <p><strong>Task ID:</strong> <code>${task.task_id}</code></p>
                                <p><strong>Research Query:</strong> ${task.description || task.research_query || 'No query specified'}</p>
                            <p><strong>Created:</strong> ${task.created_at ? new Date(task.created_at).toLocaleString() : 'N/A'} | <strong>Updated:</strong> ${task.updated_at ? new Date(task.updated_at).toLocaleString() : 'N/A'}</p>
                            ${task.continuous_mode ? `<p><strong>Continuous Mode:</strong> ${task.continuous_interval_hours} hours</p>` : ''}
                        </div>
                        
                        <!-- Workflow sections - will be populated by loadTaskWorkflowDetails -->
                        <div class="task-workflow-info mb-3">
                            <div class="workflow-section" id="decomposition-${task.task_id}" style="display: none;">
                                <h6 class="text-primary">Topic Decomposition</h6>
                                <div class="decomposition-content"></div>
                            </div>
                            
                            <!-- Always show Executed Agents section, but initially with empty placeholder -->
                            <div class="workflow-section" id="agents-${task.task_id}">
                                <h6 class="text-success mb-2">Executed Agents</h6>
                                <div class="agents-content">
                                    <div class="alert alert-light p-2">
                                        <div class="mb-2"><strong>Agents:</strong> <em class="text-muted">Waiting...</em></div>
                                        <div><strong>Providers:</strong> <em class="text-muted">Waiting...</em></div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="workflow-section" id="report-${task.task_id}" style="display: none;">
                                <h6 class="text-info">Research Report</h6>
                                <div class="report-content"></div>
                            </div>
                        </div>
                        
                        <!-- Action buttons -->
                        <div class="mb-3">
                            <button class="btn btn-primary btn-sm me-2" onclick="window.taskManager.toggleEvidence('${task.task_id}', this)">
                                Show Research Evidence
                            </button>
                            <button class="btn btn-danger btn-sm" onclick="window.taskManager.deleteTask('${task.task_id}', '${this.escapeHtml(task.title)}')">
                                <i class="fas fa-trash"></i> Delete Task
                            </button>
                        </div>
                        

                        ${this.renderTaskWorkflowInfo(task.task_id, taskDetails)}
                        </div>
                    </div>
                    
                    <!-- Evidence container -->
                    <div id="evidence-${task.task_id}" style="display: none;">
                        <div class="text-center py-2">
                            <div class="spinner-border spinner-border-sm" role="status"></div>
                            Loading evidence...
                        </div>
                    </div>
                </div>
            </div>
        `;
    }



    renderTaskWorkflowInfo(taskId, taskDetails) {
        if (!taskDetails?.operations?.length) return '';

        return `
            <div class="mt-4">
                <h6>Research Timeline</h6>
                ${this.buildTimelineDisplay(taskDetails.operations)}
            </div>
        `;
    }

    buildTimelineDisplay(timeline) {
        if (!timeline || timeline.length === 0) {
            return '<p class="text-muted">No operations recorded yet.</p>';
        }

        let html = '<div class="timeline-container">';
        
        timeline.forEach((operation, index) => {
            const cardId = `timeline-${operation.operation_id}`;
            const isExpanded = this.timelineCardStates[cardId] || false;
            const statusClass = this.getStatusClass(operation.status);
            const duration = this.calculateDuration(operation.started_at, operation.completed_at);
            
            html += `
                <div class="card timeline-card mb-3 ${isExpanded ? 'expanded' : 'collapsed'}" id="${cardId}">
                    <div class="timeline-header" 
                         data-action="toggle-timeline" 
                         data-card-id="${cardId}">
                        <div class="d-flex align-items-center">
                            <span class="timeline-toggle-icon me-2">▶</span>
                            <div>
                                <strong>${this.escapeHtml(operation.operation_type || 'Operation')}</strong>
                                <span class="status-badge ${statusClass} ms-2">${operation.status}</span>
                                ${duration ? `<small class="text-muted ms-2">(${duration})</small>` : ''}
                            </div>
                        </div>
                    </div>
                    
                    <div class="timeline-content" style="display: ${isExpanded ? 'block' : 'none'};">
                        ${this.renderOperationDetails(operation)}
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }

    renderOperationDetails(operation) {
        let html = '<div class="row">';
        
        // Input section
        if (operation.input_data) {
            html += `
                <div class="col-md-4">
                    <h6>Input</h6>
                    <div class="json-tree">
                        ${this.renderJsonTree(operation.input_data)}
                    </div>
                </div>
            `;
        }
        
        // Output section
        if (operation.output_data) {
            html += `
                <div class="col-md-4">
                    <h6>Output</h6>
                    <div class="json-tree">
                        ${this.renderJsonTree(operation.output_data)}
                    </div>
                </div>
            `;
        }
        
        // Evidence section
        if (operation.evidence && operation.evidence.length > 0) {
            html += `
                <div class="col-md-4">
                    <h6>Evidence (${operation.evidence.length} items)</h6>
                    ${operation.evidence.map(evidence => this.renderEvidenceItem(evidence)).join('')}
                </div>
            `;
        }
        
        html += '</div>';
        return html;
    }

    renderEvidenceItem(evidence) {
        return `
            <div class="evidence-item">
                <div class="evidence-header">
                    ${evidence.provider ? `<span class="badge bg-primary">${evidence.provider}</span>` : ''}
                    ${evidence.evidence_type || 'Evidence'}
                </div>
                <div class="evidence-metadata">
                    ${evidence.created_at ? `Created: ${new Date(evidence.created_at).toLocaleString()}` : ''}
                </div>
                <div class="json-tree">
                    ${this.renderJsonTree(evidence.evidence_data)}
                </div>
            </div>
        `;
    }

    toggleTimelineCard(cardId) {
        const card = document.getElementById(cardId);
        if (!card) return;

        const content = card.querySelector('.timeline-content');
        const icon = card.querySelector('.timeline-toggle-icon');
        
        if (!content || !icon) return;

        const isExpanded = !card.classList.contains('expanded');
        
        // Update visual state
        if (isExpanded) {
            card.classList.add('expanded');
            card.classList.remove('collapsed');
            content.style.display = 'block';
            icon.textContent = '▼';
            
            // Expand JSON viewers in this card after a small delay
            setTimeout(() => {
                const jsonViewers = content.querySelectorAll('json-viewer');
                jsonViewers.forEach(viewer => {
                    if (viewer.expandAll) {
                        viewer.expandAll();
                    }
                });
            }, 50);
        } else {
            card.classList.add('collapsed');
            card.classList.remove('expanded');
            content.style.display = 'none';
            icon.textContent = '▶';
        }
        
        // Save state
        this.timelineCardStates[cardId] = isExpanded;
    }

    restoreTimelineCardStates() {
        Object.keys(this.timelineCardStates).forEach(cardId => {
            if (this.timelineCardStates[cardId]) {
                this.toggleTimelineCard(cardId);
            }
        });
    }

    async toggleEvidence(taskId, button) {
        const evidenceContainer = document.getElementById(`evidence-${taskId}`);
        if (!evidenceContainer) {
            console.error(`Evidence container not found for task: ${taskId}`);
            return;
        }

        if (evidenceContainer.style.display === 'none' || evidenceContainer.style.display === '') {
            // Show evidence
            button.innerHTML = '⏳ Loading Evidence...';
            
            try {
                await this.loadTaskEvidence(taskId);
                evidenceContainer.style.display = 'block';
                button.textContent = 'Hide Research Evidence';
            } catch (error) {
                console.error('Error loading evidence:', error);
                evidenceContainer.innerHTML = '<div class="alert alert-danger">Failed to load evidence</div>';
                evidenceContainer.style.display = 'block';
                button.textContent = 'Hide Research Evidence';
            }
        } else {
            // Hide evidence
            evidenceContainer.style.display = 'none';
            button.textContent = 'Show Research Evidence';
        }
    }

    async loadTaskEvidence(taskId) {
        const evidenceContainer = document.getElementById(`evidence-${taskId}`);
        if (!evidenceContainer) {
            console.error(`Evidence container not found for task: ${taskId}`);
            return;
        }

        try {
            // Use fetch directly to avoid potential apiClient issues
            const response = await fetch(`http://localhost:12000/tasks/${taskId}/operations`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const operations = await response.json();
            
            // Additionally fetch evidence statistics for Evidence Items and Search Providers counts
            const evidenceResponse = await fetch(`http://localhost:12000/tasks/${taskId}/evidence`);
            let evidenceStats = null;
            if (evidenceResponse.ok) {
                const evidenceData = await evidenceResponse.json();
                evidenceStats = evidenceData.statistics;
            }
            
            // Build evidence display using the timeline renderer
            const evidenceHTML = this.buildEvidenceDisplayFromOperations(operations, evidenceStats, taskId);
            evidenceContainer.innerHTML = evidenceHTML;
            
            // Display executed agents section
            this.displayExecutedAgents(taskId, operations);
            
            // Fetch and display research report
            this.fetchAndDisplayResearchReport(taskId);
            
            // Add event delegation for timeline card toggles
            setTimeout(() => {
                const timelineHeaders = evidenceContainer.querySelectorAll('.timeline-card-header[data-card-id]');
                timelineHeaders.forEach(header => {
                    header.addEventListener('click', function() {
                        const cardId = this.getAttribute('data-card-id');
                        
                        // Call toggle function directly
                        const card = document.getElementById(cardId);
                        if (card) {
                            const isExpanded = card.classList.toggle('expanded');
                            
                            // Update the toggle arrow
                            const toggle = card.querySelector('.timeline-card-toggle');
                            if (toggle) {
                                toggle.textContent = isExpanded ? '▼' : '▶';
                            }
                            
                            // If expanding, expand JSON viewers
                            if (isExpanded) {
                                setTimeout(() => {
                                    const jsonViewers = card.querySelectorAll('json-viewer');
                                    jsonViewers.forEach(viewer => {
                                        if (viewer.expandAll && typeof viewer.expandAll === 'function') {
                                            viewer.expandAll();
                                        }
                                    });
                                }, 50);
                            }
                        }
                    });
                });
                
                // Restore timeline card states after rendering
                if (window.restoreTimelineCardStates) {
                    window.restoreTimelineCardStates();
                }
            }, 100);
            
        } catch (error) {
            console.error('Error fetching evidence:', error);
            evidenceContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <small>Unable to load research evidence: ${error.message}</small>
                </div>
            `;
        }
    }

    // Build evidence display HTML with timeline from operations
    buildEvidenceDisplayFromOperations(operations, evidenceStats = null, taskId = null) {
        // Handle different possible response structures
        let operationsArray = operations;
        if (operations && operations.operations) {
            operationsArray = operations.operations;
        } else if (!Array.isArray(operations)) {
            console.log('Operations is not an array:', typeof operations, operations);
            operationsArray = [];
        }
        
        if (!operationsArray || operationsArray.length === 0) {
            return `
                <div class="mt-3">
                    <h6>Research Evidence Summary</h6>
                    <div class="alert alert-info" role="alert">
                        <small>No research operations recorded yet.</small>
                    </div>
                </div>
            `;
        }
        
        // Display statistics
        const totalOperations = operationsArray.length;
        const completedOperations = operationsArray.filter(op => op.status === 'completed').length;
        
        let html = `
            <div class="mt-3">
                <h6>Research Evidence Summary</h6>
                
                <!-- Statistics -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">${totalOperations}</div>
                        <div class="text-muted">Operations</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${completedOperations}</div>
                        <div class="text-muted">Completed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${evidenceStats ? evidenceStats.total_evidence_items : 0}</div>
                        <div class="text-muted">Evidence Items</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${evidenceStats ? evidenceStats.search_providers_used.length : 0}</div>
                        <div class="text-muted">Search Providers</div>
                    </div>
                </div>
        `;
        
        // Add search providers used - use evidenceStats if available for correct provider names
        const providersToShow = evidenceStats ? evidenceStats.search_providers_used : searchProviders;
        if (providersToShow.length > 0) {
            html += `
                <div class="mb-3">
                    <strong>Search Providers:</strong> 
                    ${providersToShow.map(provider => `<span class="badge bg-secondary me-1">${provider}</span>`).join('')}
                </div>
            `;
        }
        
        const timelineHtml = this.buildTimelineDisplay(operationsArray, taskId);
        
        // Schedule state restoration after DOM update
        setTimeout(() => {
            if (window.restoreTimelineCardStates) {
                window.restoreTimelineCardStates();
            }
        }, 100);
        
        return html + timelineHtml + '</div>';
    }
    
    // Build timeline display HTML with collapsible cards (from original)
    buildTimelineDisplay(timeline, taskId = null) {
        if (!timeline || timeline.length === 0) {
            return '<p class="text-muted">No research operations recorded yet.</p>';
        }
        
        let html = `
            <h6 class="mt-4 mb-3">Research Timeline</h6>
            <div class="timeline-container">
        `;
        
        timeline.forEach((operation, index) => {
            const statusClass = operation.status || 'pending';
            const durationSeconds = operation.duration_ms ? (operation.duration_ms / 1000).toFixed(1) : 
                                  operation.duration_seconds ? operation.duration_seconds : 'N/A';
            const cardId = taskId ? `timeline-card-${taskId}-${index}` : `timeline-card-${index}`;
            
            // Create status indicator with color
            const statusIndicator = {
                'completed': '✅',
                'failed': '❌',
                'running': '⏳',
                'pending': '⏸️'
            }[statusClass] || '●';
            
            html += `
                <div class="timeline-card" id="${cardId}">
                    <div class="timeline-card-header" data-card-id="${cardId}" style="cursor: pointer;">
                        <div class="d-flex align-items-center">
                            <span class="timeline-card-toggle me-2">▶</span>
                            <span class="me-2">${statusIndicator}</span>
                            <strong>${operation.operation_name || operation.operation_type}</strong>
                            <span class="badge bg-primary ms-2">${operation.operation_type}</span>
                            ${operation.agent_type ? `<span class="badge bg-info ms-1">${operation.agent_type}</span>` : ''}
                        </div>
                        <div class="text-end">
                            <small class="text-muted">
                                Status: <span class="text-${statusClass === 'completed' ? 'success' : statusClass === 'failed' ? 'danger' : 'primary'}">${statusClass}</span> | 
                                Duration: ${durationSeconds}s
                            </small>
                        </div>
                    </div>
                    <div class="timeline-card-body">
            `;
            
            // Add input data if available
            if (operation.input_data) {
                html += `
                    <div class="mb-3">
                        <h6 class="text-primary">Input:</h6>
                        <div class="json-tree">${window.renderJsonTree(operation.input_data)}</div>
                    </div>
                `;
            }
            
            // Add output data if available
            if (operation.output_data) {
                html += `
                    <div class="mb-3">
                        <h6 class="text-success">Output:</h6>
                        <div class="json-tree">${window.renderJsonTree(operation.output_data)}</div>
                    </div>
                `;
            }
            
            // Add error message if operation failed
            if (operation.error_message) {
                html += `
                    <div class="alert alert-danger mb-3">
                        <h6 class="alert-heading">Error:</h6>
                        <p class="mb-0">${operation.error_message}</p>
                    </div>
                `;
            }
            
            // Add evidence items
            if (operation.evidence && operation.evidence.length > 0) {
                html += `
                    <div class="mb-3">
                        <h6 class="text-info">Evidence (${operation.evidence.length} items):</h6>
                `;
                
                operation.evidence.forEach((evidence, evidenceIndex) => {
                    html += `
                        <div class="card mb-2">
                            <div class="card-header py-2">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>${evidence.evidence_type}</strong>
                                        ${evidence.provider ? `<span class="badge bg-secondary ms-1">${evidence.provider}</span>` : ''}
                                    </div>
                                    ${evidence.source_url ? `<a href="${evidence.source_url}" target="_blank" class="btn btn-sm btn-outline-primary">View Source</a>` : ''}
                                </div>
                            </div>
                    `;
                    
                    if (evidence.evidence_data) {
                        html += `
                            <div class="card-body py-2">
                                <div class="json-tree">${window.renderJsonTree(evidence.evidence_data)}</div>
                            </div>
                        `;
                    }
                    
                    html += '</div>';
                });
                
                html += '</div>';
            }
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += `
            </div>
        `;
        
        return html;
    }

    // Expand JSON viewers in a timeline card
    expandJsonViewersInCard(card) {
        setTimeout(() => {
            const viewers = card.querySelectorAll('json-viewer'); 
            viewers.forEach(viewer => {
                if (viewer.expandAll) {
                    viewer.expandAll();
                }
            });
        }, 50);
    }

    // Display executed search agents/providers (copied from original frontend)
    displayExecutedAgents(taskId, operations) {
        const agentsSection = document.getElementById(`agents-${taskId}`);
        if (!agentsSection) return;
        const agentsContent = agentsSection.querySelector('.agents-content');
        if (!agentsContent) return;
        
        if (operations && operations.length > 0) {
            // Extract unique agents and providers from operations
            const agents = new Set();
            const providers = new Set();
            
            operations.forEach(op => {
                if (op.agent_type) agents.add(op.agent_type);
                if (op.operation_type === 'search' && op.output_data && op.output_data.provider) {
                    providers.add(op.output_data.provider);
                }
            });
            
            let html = '<div class="alert alert-light p-2">';
            
            if (agents.size > 0) {
                html += '<div class="mb-2"><strong>Agents:</strong> ';
                html += Array.from(agents).map(agent => 
                    `<span class="badge bg-success me-1">${agent}</span>`
                ).join('');
                html += '</div>';
            }
            
            if (providers.size > 0) {
                html += '<div><strong>Providers:</strong> ';
                html += Array.from(providers).map(provider => 
                    `<span class="badge bg-info me-1">${provider}</span>`
                ).join('');
                html += '</div>';
            }
            
            html += '</div>';
            agentsContent.innerHTML = html;
            agentsSection.style.display = 'block';
        }
    }

    // Fetch and display research report helper function
    async fetchAndDisplayResearchReport(taskId) {
        try {
            const response = await fetch(`http://localhost:12000/api/research/tasks/${taskId}/report`);
            if (response.ok) {
                const reportMarkdown = await response.text();
                this.displayResearchReport(taskId, reportMarkdown);
            }
        } catch (error) {
            console.log('Research report not available for task:', taskId);
        }
    }

    // Display research report section (copied from original frontend)
    displayResearchReport(taskId, reportMarkdown) {
        const reportSection = document.getElementById(`report-${taskId}`);
        const reportContent = reportSection.querySelector('.report-content');
        
        if (reportMarkdown) {
            // Store report data for download functionality
            window.currentReportData = {
                taskId: taskId,
                markdown: reportMarkdown
            };
            
            // Create a button to open the modal instead of inline content
            const html = `
                <div class="alert alert-success p-3">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>Research Report Available</strong>
                            <div class="mt-1">
                                <small class="text-muted">Report length: ${reportMarkdown.length} characters</small>
                            </div>
                        </div>
                        <button type="button" class="btn btn-primary" onclick="window.taskManager.openReportModal('${taskId}')">
                            <i class="bi bi-file-text"></i> View Report
                        </button>
                    </div>
                </div>
            `;
            
            reportContent.innerHTML = html;
            reportSection.style.display = 'block';
        }
    }

    // Open report in modal (copied from original frontend)
    openReportModal(taskId) {
        if (!window.currentReportData || window.currentReportData.taskId !== taskId) {
            // Fetch the report if not already loaded
            fetch(`http://localhost:12000/api/research/tasks/${taskId}/report`)
                .then(response => {
                    if (response.ok) {
                        return response.text();
                    }
                    throw new Error('Report not found');
                })
                .then(markdown => {
                    window.currentReportData = {
                        taskId: taskId,
                        markdown: markdown
                    };
                    this.showReportModal(markdown);
                })
                .catch(error => {
                    console.error('Error fetching report:', error);
                    alert('Unable to load research report');
                });
        } else {
            this.showReportModal(window.currentReportData.markdown);
        }
    }

    // Show report modal with markdown content
    showReportModal(markdown) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('reportModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.innerHTML = `
                <div class="modal fade" id="reportModal" tabindex="-1">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Research Report</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div id="reportContent" class="report-content"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // Set the content and show the modal
        const reportContent = document.getElementById('reportContent');
        reportContent.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">${this.escapeHtml(markdown)}</pre>`;
        
        const bootstrapModal = new bootstrap.Modal(document.getElementById('reportModal'));
        bootstrapModal.show();
    }

    buildEvidenceDisplay(evidence) {
        if (!evidence.timeline || evidence.timeline.length === 0) {
            return '<div class="card-body"><p class="text-muted">No evidence available</p></div>';
        }

        let html = '<div class="card-body">';
        html += `<h6>Research Evidence Summary</h6>`;
        html += `<p><strong>Total Operations:</strong> ${evidence.statistics.total_operations}</p>`;
        html += `<p><strong>Evidence Items:</strong> ${evidence.statistics.total_evidence_items}</p>`;
        
        if (evidence.statistics.search_providers_used.length > 0) {
            html += `<p><strong>Search Providers:</strong> ${evidence.statistics.search_providers_used.join(', ')}</p>`;
        }

        html += '<hr>';
        
        evidence.timeline.forEach(operation => {
            if (operation.evidence && operation.evidence.length > 0) {
                html += `<h6>${operation.operation_type || 'Operation'}</h6>`;
                operation.evidence.forEach(evidenceItem => {
                    html += this.renderEvidenceItem(evidenceItem);
                });
            }
        });
        
        html += '</div>';
        return html;
    }

    async openReportModal(taskId) {
        try {
            const response = await this.apiClient.get(`/api/research/tasks/${taskId}/report`);
            if (response.ok) {
                const reportData = await response.json();
                
                // Handle different possible API response structures
                let reportContent = reportData.report_markdown || reportData.report || reportData.markdown || reportData.content || reportData;
                
                // If reportContent is still an object, try to stringify it
                if (typeof reportContent === 'object') {
                    reportContent = JSON.stringify(reportContent, null, 2);
                }
                
                if (reportContent && reportContent.trim()) {
                    this.showReportInModal(reportContent, taskId);
                } else {
                    console.error('No report content found in API response');
                    alert('Report content is empty or not available.');
                }
            } else {
                console.error('API response not ok:', response.status, response.statusText);
                alert('Research report not found or not ready yet.');
            }
        } catch (error) {
            console.error('Error loading report:', error);
            alert('Failed to load research report.');
        }
    }

    showReportInModal(reportMarkdown, taskId) {
        this.currentReportData = { markdown: reportMarkdown, taskId: taskId };
        
        const modalElement = document.getElementById('researchReportModal');
        if (!modalElement) {
            console.error('Modal element not found');
            alert('Modal not available. Please refresh the page.');
            return;
        }
        
        const modalTitle = document.getElementById('researchReportModalLabel');
        const modalContent = document.getElementById('researchReportContent');
        const modalMetadata = document.getElementById('reportMetadata');
        
        if (modalTitle) modalTitle.textContent = `Research Report - Task ${taskId.substring(0, 8)}`;
        if (modalContent) {
            // Convert markdown to HTML with better formatting
            const htmlContent = reportMarkdown
                .replace(/^### (.*$)/gim, '<h5 class="mt-4 mb-2">$1</h5>')
                .replace(/^## (.*$)/gim, '<h4 class="mt-4 mb-3">$1</h4>')
                .replace(/^# (.*$)/gim, '<h3 class="mt-4 mb-3">$1</h3>')
                .replace(/^\* (.*$)/gim, '<li>$1</li>')
                .replace(/^- (.*$)/gim, '<li>$1</li>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`([^`]+)`/g, '<code class="bg-light px-1 rounded">$1</code>')
                .replace(/\n\n/g, '</p><p class="mb-3">')
                .replace(/\n/g, '<br>');
            
            modalContent.innerHTML = `<div class="report-content"><p class="mb-3">${htmlContent}</p></div>`;
        }
        if (modalMetadata) {
            modalMetadata.textContent = `Report length: ${reportMarkdown.length} characters | Generated: ${new Date().toLocaleString()}`;
        }
        
        // Show the modal using Bootstrap 5 syntax
        try {
            const modal = new bootstrap.Modal(modalElement, {
                backdrop: true,
                keyboard: true,
                focus: true
            });
            modal.show();
        } catch (error) {
            console.error('Error showing modal:', error);
            // Fallback: try to show modal using data attributes
            modalElement.classList.add('show');
            modalElement.style.display = 'block';
            document.body.classList.add('modal-open');
        }
    }

    downloadReport() {
        if (!this.currentReportData) {
            alert('No report available for download');
            return;
        }

        const blob = new Blob([this.currentReportData.markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `research-report-${this.currentReportData.taskId}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    closeModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('researchReportModal'));
        if (modal) {
            modal.hide();
        }
    }

    async deleteTask(taskId, taskTitle) {
        // Create modal if it doesn't exist
        let confirmModal = document.getElementById('task-delete-confirm-modal');
        
        if (!confirmModal) {
            const modalHtml = `
                <div class="modal fade" id="task-delete-confirm-modal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Confirm Deletion</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <p>Are you sure you want to delete this task?</p>
                                <p>This will permanently delete:</p>
                                <ul>
                                    <li>The research task</li>
                                    <li>All associated operations and evidence</li>
                                    <li>The final research report</li>
                                </ul>
                                <p class="text-danger">This action cannot be undone.</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-danger" id="confirm-delete-btn">Delete</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = modalHtml;
            document.body.appendChild(modalContainer.firstElementChild);
            confirmModal = document.getElementById('task-delete-confirm-modal');
        }
        
        // Set up the confirmation modal
        const modal = new bootstrap.Modal(confirmModal);
        const deleteBtn = confirmModal.querySelector('#confirm-delete-btn');
        
        // Update modal content with task name
        confirmModal.querySelector('.modal-body p:first-child').textContent = 
            `Are you sure you want to delete the task "${taskTitle}"?`;
        
        // Remove old event listeners if any
        const newDeleteBtn = deleteBtn.cloneNode(true);
        deleteBtn.parentNode.replaceChild(newDeleteBtn, deleteBtn);
        
        // Show the modal and wait for user decision
        return new Promise((resolve) => {
            newDeleteBtn.addEventListener('click', async () => {
                modal.hide();
                
                try {
                    const response = await this.apiClient.delete(`/tasks/${taskId}`);
                    if (response.ok) {
                        await this.refreshTasks();
                        resolve(true);
                    } else {
                        const error = await response.json();
                        this.displayError(`Failed to delete task: ${error.detail || 'Unknown error'}`);
                        resolve(false);
                    }
                } catch (error) {
                    console.error('Error deleting task:', error);
                    this.displayError('Failed to delete task. Please try again.');
                    resolve(false);
                }
            });
            
            // Handle cancel
            confirmModal.addEventListener('hidden.bs.modal', () => {
                resolve(false);
            }, { once: true });
            
            modal.show();
        });
    }

    renderJsonTree(data) {
        if (!data) return '<p class="text-muted">No data available</p>';

        // Generate unique ID for this viewer
        const viewerId = `json-viewer-${++this.jsonViewerCount}`;
        
        // Create json-viewer element
        const viewerHtml = `<json-viewer id="${viewerId}"></json-viewer>`;
        
        // Schedule data binding after DOM insertion
        setTimeout(() => {
            const viewer = document.getElementById(viewerId);
            if (viewer) {
                try {
                    // Set the data
                    viewer.data = data;
                } catch (error) {
                    console.error('Error setting JSON viewer data:', error);
                    // Fallback to pre-formatted JSON
                    viewer.outerHTML = `<pre class="json-fallback">${this.escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
                }
            }
        }, 10);
        
        return viewerHtml;
    }

    // Utility methods
    getStatusClass(status) {
        const statusMap = {
            'completed': 'status-completed',
            'failed': 'status-failed',
            'pending': 'status-pending',
            'running': 'status-running'
        };
        return statusMap[status] || 'status-pending';
    }

    getStatusText(status) {
        const statusMap = {
            'completed': 'Completed',
            'failed': 'Failed',
            'pending': 'Pending',
            'running': 'Running'
        };
        return statusMap[status] || 'Unknown';
    }

    calculateDuration(startTime, endTime) {
        if (!startTime || !endTime) return null;
        
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diffMs = end - start;
        const diffSeconds = Math.round(diffMs / 1000);
        
        if (diffSeconds < 60) {
            return `${diffSeconds}s`;
        } else if (diffSeconds < 3600) {
            return `${Math.round(diffSeconds / 60)}m`;
        } else {
            return `${Math.round(diffSeconds / 3600)}h`;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    displayError(message) {
        const taskListContainer = document.getElementById('taskListContainer');
        if (taskListContainer) {
            taskListContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <h4 class="alert-heading">Error</h4>
                    <p>${this.escapeHtml(message)}</p>
                </div>
            `;
        }
    }
}
