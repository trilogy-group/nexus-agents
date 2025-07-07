// DOK Taxonomy module for bibliography and knowledge management
import { ApiClient } from './api.js';

export class DOKTaxonomyManager {
    constructor() {
        this.apiClient = new ApiClient();
    }

    // DOK Taxonomy API calls
    async getDOKStats(taskId) {
        try {
            const response = await this.apiClient.get(`/api/dok/tasks/${taskId}/stats`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error(`Failed to get DOK stats: ${response.status}`);
        } catch (error) {
            console.error('Error fetching DOK stats:', error);
            return null;
        }
    }

    async getKnowledgeTree(taskId) {
        try {
            const response = await this.apiClient.get(`/api/dok/tasks/${taskId}/knowledge-tree`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error(`Failed to get knowledge tree: ${response.status}`);
        } catch (error) {
            console.error('Error fetching knowledge tree:', error);
            return [];
        }
    }

    async getInsights(taskId) {
        try {
            const response = await this.apiClient.get(`/api/dok/tasks/${taskId}/insights`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error(`Failed to get insights: ${response.status}`);
        } catch (error) {
            console.error('Error fetching insights:', error);
            return [];
        }
    }

    async getSpikyPOVs(taskId) {
        try {
            const response = await this.apiClient.get(`/api/dok/tasks/${taskId}/spiky-povs`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error(`Failed to get spiky POVs: ${response.status}`);
        } catch (error) {
            console.error('Error fetching spiky POVs:', error);
            return { truth: [], myth: [] };
        }
    }

    async getSourceSummaries(taskId) {
        try {
            const response = await this.apiClient.get(`/api/dok/tasks/${taskId}/source-summaries`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error(`Failed to get source summaries: ${response.status}`);
        } catch (error) {
            console.error('Error fetching source summaries:', error);
            return [];
        }
    }

    async getBibliography(taskId) {
        try {
            const response = await this.apiClient.get(`/api/dok/tasks/${taskId}/bibliography`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error(`Failed to get bibliography: ${response.status}`);
        } catch (error) {
            console.error('Error fetching bibliography:', error);
            return [];
        }
    }

    async getCompleteDOKData(taskId) {
        try {
            const response = await this.apiClient.get(`/api/dok/tasks/${taskId}/complete`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error(`Failed to get complete DOK data: ${response.status}`);
        } catch (error) {
            console.error('Error fetching complete DOK data:', error);
            return null;
        }
    }

    // UI Rendering Methods
    renderDOKStatsCard(stats) {
        if (!stats) {
            return '<div class="alert alert-warning">DOK taxonomy data not available</div>';
        }

        return `
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">📊 DOK Taxonomy Statistics</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="stat-item">
                                <div class="stat-number">${stats.knowledge_tree_nodes || 0}</div>
                                <div class="stat-label">Knowledge Nodes</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-item">
                                <div class="stat-number">${stats.total_insights || 0}</div>
                                <div class="stat-label">Insights</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-item">
                                <div class="stat-number">${stats.spiky_povs_truths || 0}</div>
                                <div class="stat-label">Truths</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-item">
                                <div class="stat-number">${stats.spiky_povs_myths || 0}</div>
                                <div class="stat-label">Myths</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderKnowledgeTree(knowledgeTree) {
        // Ensure knowledgeTree is always an array
        let treeArray = [];
        if (Array.isArray(knowledgeTree)) {
            treeArray = knowledgeTree;
        } else if (knowledgeTree && typeof knowledgeTree === 'object') {
            // If it's an object, try to extract an array from common properties
            if (knowledgeTree.nodes && Array.isArray(knowledgeTree.nodes)) {
                treeArray = knowledgeTree.nodes;
            } else if (knowledgeTree.tree && Array.isArray(knowledgeTree.tree)) {
                treeArray = knowledgeTree.tree;
            } else {
                // Convert single object to array
                treeArray = [knowledgeTree];
            }
        }
        
        if (!treeArray || treeArray.length === 0) {
            return '<div class="alert alert-info">No knowledge tree data available</div>';
        }

        const treeHtml = treeArray.map(node => `
            <div class="knowledge-node mb-3">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <span class="badge bg-primary me-2">DOK ${node.dok_level}</span>
                            ${node.category}
                            ${node.subcategory ? `<span class="text-muted"> / ${node.subcategory}</span>` : ''}
                        </h6>
                    </div>
                    <div class="card-body">
                        <p class="card-text">${node.summary}</p>
                        ${node.sources && node.sources.length > 0 ? `
                            <div class="sources-section">
                                <small class="text-muted">Sources (${node.source_count}):</small>
                                <div class="sources-list">
                                    ${node.sources.map(source => `
                                        <div class="mb-1">
                                            <a href="${source.url || '#'}" target="_blank" class="badge bg-secondary text-decoration-none" title="${source.title}">
                                                ${source.title.substring(0, 50)}${source.title.length > 50 ? '...' : ''}
                                            </a>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');

        return `
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">🌳 Knowledge Tree (DOK 1-2)</h5>
                </div>
                <div class="card-body">
                    ${treeHtml}
                </div>
            </div>
        `;
    }

    renderInsights(insights) {
        // Ensure insights is always an array
        let insightsArray = [];
        if (Array.isArray(insights)) {
            insightsArray = insights;
        } else if (insights && typeof insights === 'object') {
            // If it's an object, try to extract an array from common properties
            if (insights.insights && Array.isArray(insights.insights)) {
                insightsArray = insights.insights;
            } else if (insights.items && Array.isArray(insights.items)) {
                insightsArray = insights.items;
            } else {
                // Convert single object to array
                insightsArray = [insights];
            }
        }
        
        if (!insightsArray || insightsArray.length === 0) {
            return '<div class="alert alert-info">No insights available</div>';
        }

        const insightsHtml = insightsArray.map(insight => `
            <div class="insight-item mb-3">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <span class="badge bg-success me-2">DOK 3</span>
                            ${insight.category}
                            <span class="badge bg-light text-dark ms-2">${Math.round(insight.confidence_score * 100)}% confidence</span>
                        </h6>
                    </div>
                    <div class="card-body">
                        <p class="card-text">${insight.insight_text}</p>
                        ${insight.supporting_sources && insight.supporting_sources.length > 0 ? `
                            <div class="sources-section">
                                <small class="text-muted">Supporting Sources:</small>
                                <div class="sources-list">
                                    ${insight.supporting_sources.map(source => `
                                        <div class="mb-1">
                                            <a href="${source.url || '#'}" target="_blank" class="badge bg-info text-decoration-none" title="${source.title}">
                                                ${source.title ? source.title.substring(0, 50) : 'Unknown'}${source.title && source.title.length > 50 ? '...' : ''}
                                            </a>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');

        return `
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">💡 Insights (DOK 3)</h5>
                </div>
                <div class="card-body">
                    ${insightsHtml}
                </div>
            </div>
        `;
    }

    renderSpikyPOVs(spikyPOVs) {
        // Ensure spikyPOVs has the expected structure
        let normalizedPOVs = { truth: [], myth: [] };
        
        if (spikyPOVs && typeof spikyPOVs === 'object') {
            // Handle different possible data structures
            if (Array.isArray(spikyPOVs)) {
                // If it's an array, separate by type
                spikyPOVs.forEach(pov => {
                    if (pov.pov_type === 'truth') {
                        normalizedPOVs.truth.push(pov);
                    } else if (pov.pov_type === 'myth') {
                        normalizedPOVs.myth.push(pov);
                    }
                });
            } else {
                // If it's an object, use existing structure or extract arrays
                normalizedPOVs.truth = Array.isArray(spikyPOVs.truth) ? spikyPOVs.truth : [];
                normalizedPOVs.myth = Array.isArray(spikyPOVs.myth) ? spikyPOVs.myth : [];
                
                // Handle alternative property names
                if (spikyPOVs.truths && Array.isArray(spikyPOVs.truths)) {
                    normalizedPOVs.truth = spikyPOVs.truths;
                }
                if (spikyPOVs.myths && Array.isArray(spikyPOVs.myths)) {
                    normalizedPOVs.myth = spikyPOVs.myths;
                }
            }
        }
        
        if (normalizedPOVs.truth.length === 0 && normalizedPOVs.myth.length === 0) {
            return '<div class="alert alert-info">No spiky POVs available</div>';
        }

        const renderPOVList = (povs, type, badgeClass) => {
            if (povs.length === 0) return '';
            
            return `
                <div class="pov-section mb-4">
                    <h6 class="text-${badgeClass}">${type.toUpperCase()}S</h6>
                    ${povs.map(pov => `
                        <div class="pov-item mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h6 class="mb-0">
                                        <span class="badge bg-${badgeClass} me-2">DOK 4</span>
                                        ${type.charAt(0).toUpperCase() + type.slice(1)}
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <blockquote class="blockquote">
                                        <p class="mb-2">"${pov.statement}"</p>
                                    </blockquote>
                                    <p class="card-text"><strong>Reasoning:</strong> ${pov.reasoning}</p>
                                    ${pov.supporting_insights && pov.supporting_insights.length > 0 ? `
                                        <div class="insights-section">
                                            <small class="text-muted">Supporting Insights:</small>
                                            <div class="insights-list">
                                                ${pov.supporting_insights.map(insight => `
                                                    <span class="badge bg-success me-1" title="${insight.insight_text}">
                                                        ${insight.category}
                                                    </span>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        };

        return `
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">🎯 Spiky POVs (DOK 4)</h5>
                </div>
                <div class="card-body">
                    ${renderPOVList(normalizedPOVs.truth, 'truth', 'success')}
                    ${renderPOVList(normalizedPOVs.myth, 'myth', 'danger')}
                </div>
            </div>
        `;
    }

    renderBibliography(bibliography) {
        // Ensure bibliography is always an array
        let bibliographyArray = [];
        if (Array.isArray(bibliography)) {
            bibliographyArray = bibliography;
        } else if (bibliography && typeof bibliography === 'object') {
            // If it's an object, try to extract an array from common properties
            if (bibliography.sources && Array.isArray(bibliography.sources)) {
                bibliographyArray = bibliography.sources;
            } else if (bibliography.bibliography && Array.isArray(bibliography.bibliography)) {
                bibliographyArray = bibliography.bibliography;
            } else {
                // Convert single object to array
                bibliographyArray = [bibliography];
            }
        }
        
        if (!bibliographyArray || bibliographyArray.length === 0) {
            return '<div class="alert alert-info">No bibliography available</div>';
        }

        const bibliographyHtml = bibliographyArray.map(source => {
            // Use title if available, otherwise fall back to URL or "Untitled Source"
            const title = source.title || (source.url ? new URL(source.url).hostname : 'Untitled Source');
            
            return `
                <div class="bibliography-item mb-2">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title">${title}</h6>
                            ${source.url ? `<p class="card-text"><a href="${source.url}" target="_blank" class="text-decoration-none">${source.url}</a></p>` : ''}
                            ${source.provider ? `<span class="badge bg-secondary">${source.provider}</span>` : ''}
                            ${source.usage_count ? `<span class="badge bg-primary ms-2">Used ${source.usage_count} times</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">📚 Bibliography</h5>
                </div>
                <div class="card-body">
                    ${bibliographyHtml}
                </div>
            </div>
        `;
    }

    // Main DOK Taxonomy Panel Renderer
    async renderDOKTaxonomyPanel(taskId) {
        try {
            // Fetch all DOK taxonomy data
            const [stats, knowledgeTree, insights, spikyPOVs, bibliography] = await Promise.all([
                this.getDOKStats(taskId),
                this.getKnowledgeTree(taskId),
                this.getInsights(taskId),
                this.getSpikyPOVs(taskId),
                this.getBibliography(taskId)
            ]);

            return `
                <div class="dok-taxonomy-panel">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h4 class="mb-0">📖 DOK Taxonomy & Bibliography</h4>
                            <small class="text-muted">Webb's Depth of Knowledge Analysis</small>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-12">
                                    ${this.renderDOKStatsCard(stats)}
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-lg-6">
                                    ${this.renderKnowledgeTree(knowledgeTree)}
                                    ${this.renderInsights(insights)}
                                </div>
                                <div class="col-lg-6">
                                    ${this.renderSpikyPOVs(spikyPOVs)}
                                    ${this.renderBibliography(bibliography)}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error rendering DOK taxonomy panel:', error);
            return `
                <div class="alert alert-danger">
                    <h5>Error Loading DOK Taxonomy Data</h5>
                    <p>Unable to load DOK taxonomy and bibliography information. Please try again later.</p>
                    <small class="text-muted">Error: ${error.message}</small>
                </div>
            `;
        }
    }
}
