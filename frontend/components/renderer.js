// Component renderer for HTML templates
export class ComponentRenderer {
    constructor() {
        // Component templates cache
        this.templates = {};
    }

    renderTaskCreationForm() {
        return `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Create Research Task</h5>
                </div>
                <div class="card-body">
                    <form id="create-task-form">
                        <div class="mb-3">
                            <label for="title" class="form-label">Title</label>
                            <input type="text" class="form-control" id="title" name="title" required>
                        </div>
                        <div class="mb-3">
                            <label for="description" class="form-label">Description</label>
                            <textarea 
                                class="form-control" 
                                id="description" 
                                name="description" 
                                rows="3" 
                                required></textarea>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="continuous-mode" name="continuous-mode">
                            <label class="form-check-label" for="continuous-mode">Continuous Mode</label>
                        </div>
                        <div class="mb-3" id="interval-container" style="display: none;">
                            <label for="interval" class="form-label">Update Interval (hours)</label>
                            <input type="number" class="form-control" id="interval" name="interval" value="24" min="1">
                        </div>
                        <button type="submit" class="btn btn-primary">
                            Create Task
                        </button>
                    </form>
                </div>
            </div>
        `;
    }

    renderTaskListContainer() {
        return `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Research Tasks</h5>
                </div>
                <div class="card-body">
                    <div id="taskListContainer">
                        <!-- Tasks will be loaded here -->
                        <div class="text-center py-4">
                            <div class="loading-spinner"></div>
                            <p class="mt-2 text-muted">Loading tasks...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderResearchReportModal() {
        return `
            <div class="modal fade" id="researchReportModal" tabindex="-1" aria-labelledby="researchReportModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="researchReportModalLabel">Research Report</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                            <div id="researchReportContent"></div>
                        </div>
                        <div class="modal-footer">
                            <div class="me-auto">
                                <small class="text-muted" id="reportMetadata"></small>
                            </div>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="downloadReport()">Download Report</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderTaskCard(task, taskDetails = null) {
        const statusClass = `status-${task.status}`;
        
        return `
            <div class="col-12 mb-4">
                <div class="card task-card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">${this.escapeHtml(task.title)}</h5>
                    </div>
                    <div class="card-body">
                        <div class="task-basic-info mb-3">
                            <p><strong>Task ID:</strong> <code>${task.task_id}</code></p>
                            <p><strong>Research Query:</strong> ${task.description || 'No query specified'}</p>
                            <p><strong>Status:</strong> <span class="task-status ${statusClass}">${task.status}</span></p>
                            <p><strong>Created:</strong> ${task.created_at || 'N/A'}</p>
                            <p><strong>Updated:</strong> ${task.updated_at || 'N/A'}</p>
                            ${task.continuous_mode ? `<p><strong>Continuous Mode:</strong> ${task.continuous_interval_hours} hours</p>` : ''}
                        </div>
                        
                        <!-- Workflow sections - will be populated by loadTaskWorkflowDetails -->
                        <div class="task-workflow-info mb-3">
                            <div class="workflow-section" id="decomposition-${task.task_id}" style="display: none;">
                                <h6 class="text-primary">Topic Decomposition</h6>
                                <div class="decomposition-content"></div>
                            </div>
                            <div class="workflow-section" id="agents-${task.task_id}" style="display: none;">
                                <h6 class="text-success">Executed Agents</h6>
                                <div class="agents-content"></div>
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
                        

                        ${taskDetails ? this.renderTaskWorkflowInfo(task.task_id, taskDetails) : ''}
                    </div>
                    
                    <!-- Evidence container -->
                    <div id="evidence-${task.task_id}" style="display: none;">
                        <div class="text-center py-2"><div class="spinner-border spinner-border-sm" role="status"></div> Loading evidence...</div>
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
                ${this.renderTimelineDisplay(taskDetails.operations)}
            </div>
        `;
    }

    renderTimelineDisplay(timeline) {
        if (!timeline || timeline.length === 0) {
            return '<p class="text-muted">No operations recorded yet.</p>';
        }

        let html = '<div class="timeline-container">';
        
        timeline.forEach((operation, index) => {
            const cardId = `timeline-${operation.operation_id}`;
            const statusClass = this.getStatusClass(operation.status);
            const duration = this.calculateDuration(operation.started_at, operation.completed_at);
            
            html += `
                <div class="card timeline-card mb-3 collapsed" id="${cardId}">
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
                    
                    <div class="timeline-content" style="display: none;">
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
                        <pre class="json-content">${this.escapeHtml(JSON.stringify(operation.input_data, null, 2))}</pre>
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
                        <pre class="json-content">${this.escapeHtml(JSON.stringify(operation.output_data, null, 2))}</pre>
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
                    <pre class="json-content">${this.escapeHtml(JSON.stringify(evidence.evidence_data, null, 2))}</pre>
                </div>
            </div>
        `;
    }

    renderLoadingSpinner(message = 'Loading...') {
        return `
            <div class="text-center py-4">
                <div class="loading-spinner"></div>
                <p class="mt-2 text-muted">${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    renderErrorMessage(message) {
        return `
            <div class="alert alert-danger" role="alert">
                <h4 class="alert-heading">Error</h4>
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    renderEmptyState(title, message) {
        return `
            <div class="alert alert-info" role="alert">
                <h4 class="alert-heading">${this.escapeHtml(title)}</h4>
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
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
        if (!text) return '';
        if (typeof text !== 'string') text = String(text);
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
