// API client module
export class ApiClient {
    constructor() {
        // Use backend port 12000, not frontend port
        const protocol = window.location.protocol;
        const hostname = window.location.hostname;
        this.baseUrl = `${protocol}//${hostname}:12000`;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, mergedOptions);
            return response;
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    async get(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'GET',
            ...options,
        });
    }

    async post(endpoint, data = null, options = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: data ? JSON.stringify(data) : null,
            ...options,
        });
    }

    async put(endpoint, data = null, options = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: data ? JSON.stringify(data) : null,
            ...options,
        });
    }

    async delete(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'DELETE',
            ...options,
        });
    }

    async patch(endpoint, data = null, options = {}) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: data ? JSON.stringify(data) : null,
            ...options,
        });
    }
}
