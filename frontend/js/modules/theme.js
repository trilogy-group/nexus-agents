// Theme management module
export class ThemeManager {
    constructor() {
        this.currentTheme = 'dark'; // Default to dark mode as requested
        this.themeToggle = null;
    }

    initialize() {
        // Get saved theme preference or default to dark
        const savedTheme = localStorage.getItem('nexus-theme') || 'dark';
        this.setTheme(savedTheme);
        
        // Initialize theme toggle button
        this.themeToggle = document.getElementById('themeToggle');
        if (this.themeToggle) {
            this.updateToggleButton();
        }
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    setTheme(theme) {
        this.currentTheme = theme;
        
        // Apply theme to document
        document.documentElement.setAttribute('data-theme', theme);
        
        // Save preference
        localStorage.setItem('nexus-theme', theme);
        
        // Update toggle button
        this.updateToggleButton();
        
        // Apply theme to JSON viewers
        this.applyThemeToJsonViewers();
    }

    updateToggleButton() {
        // Update theme icon exactly like original frontend
        const themeIcon = document.getElementById('themeIcon');
        if (themeIcon) {
            themeIcon.textContent = this.currentTheme === 'light' ? '🌙' : '☀️';
        }
    }

    // Apply theme to JSON viewers - recreate all JSON viewers to properly apply theme
    applyThemeToJsonViewers() {
        // First apply custom CSS to ensure JSON viewer component uses our theme variables
        this.applyJsonTreeStyles();
        
        // Then recreate all JSON viewers with the new theme
        const jsonViewers = document.querySelectorAll('json-viewer');
        jsonViewers.forEach(viewer => {
            const data = viewer.getAttribute('data');
            const viewerId = viewer.getAttribute('id');
            if (data && viewerId) {
                // Create new json-viewer element with current theme
                const newViewer = document.createElement('json-viewer');
                newViewer.setAttribute('id', viewerId);
                newViewer.setAttribute('data', data);
                newViewer.setAttribute('theme', this.currentTheme);
                
                // Replace the old viewer with the new one
                viewer.parentNode.replaceChild(newViewer, viewer);
            }
        });
    }
    
    // Apply CSS variables to JSON tree elements to ensure theme consistency
    applyJsonTreeStyles() {
        // Define dynamic style element if not exists
        let styleEl = document.getElementById('json-tree-theme-styles');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'json-tree-theme-styles';
            document.head.appendChild(styleEl);
        }
        
        // Update the custom properties for json-viewer elements to use our theme colors
        styleEl.textContent = `
            json-viewer {
                --string-color: var(--json-string-color) !important;
                --number-color: var(--json-number-color) !important;
                --boolean-color: var(--json-boolean-color) !important;
                --null-color: var(--json-null-color) !important;
                --key-color: var(--json-key-color) !important;
                --bracket-color: var(--json-brace-color) !important;
                --brace-color: var(--json-brace-color) !important;
                background-color: transparent !important;
            }
        `;
    }

    getCurrentTheme() {
        return this.currentTheme;
    }
}

