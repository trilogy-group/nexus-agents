// JSON tree rendering module using json-viewer component
export class JsonTreeRenderer {
    constructor() {
        this.viewerCount = 0;
    }

    renderJsonTree(data) {
        if (!data) return '<p class="text-muted">No data available</p>';

        // Generate unique ID for this viewer
        const viewerId = `json-viewer-${++this.viewerCount}`;
        
        // Create json-viewer element
        const viewerHtml = `<json-viewer id="${viewerId}"></json-viewer>`;
        
        // Schedule data binding after DOM insertion
        setTimeout(() => {
            const viewer = document.getElementById(viewerId);
            if (viewer) {
                try {
                    // Set the data
                    viewer.data = data;
                    
                    // Apply theme colors
                    this.applyThemeToViewer(viewer);
                } catch (error) {
                    console.error('Error setting JSON viewer data:', error);
                    // Fallback to pre-formatted JSON
                    viewer.outerHTML = `<pre class="json-fallback">${this.escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
                }
            }
        }, 10);
        
        return viewerHtml;
    }

    applyThemeToViewer(viewer) {
        // The theme colors are already set via CSS variables in variables.css
        // The json-viewer component will automatically pick them up
        
        // Ensure the viewer respects the current theme
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        viewer.setAttribute('data-theme', currentTheme);
    }

    expandAllViewersInContainer(container) {
        if (!container) return;
        
        const viewers = container.querySelectorAll('json-viewer');
        viewers.forEach(viewer => {
            if (viewer.expandAll) {
                try {
                    viewer.expandAll();
                } catch (error) {
                    console.error('Error expanding JSON viewer:', error);
                }
            }
        });
    }

    expandViewer(viewerId) {
        const viewer = document.getElementById(viewerId);
        if (viewer && viewer.expandAll) {
            try {
                viewer.expandAll();
            } catch (error) {
                console.error('Error expanding specific JSON viewer:', error);
            }
        }
    }

    collapseViewer(viewerId) {
        const viewer = document.getElementById(viewerId);
        if (viewer && viewer.collapseAll) {
            try {
                viewer.collapseAll();
            } catch (error) {
                console.error('Error collapsing specific JSON viewer:', error);
            }
        }
    }

    escapeHtml(text) {
        if (typeof text !== 'string') {
            text = String(text);
        }
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Update all viewers when theme changes
    updateViewersForTheme(theme) {
        const viewers = document.querySelectorAll('json-viewer');
        viewers.forEach(viewer => {
            viewer.setAttribute('data-theme', theme);
        });
    }
}
