// File: website/admin/js/admin_api.js

const API_BASE_URL = 'http://127.0.0.1:5000/api/admin'; // Your backend admin API base URL
const AUTH_BASE_URL = 'http://127.0.0.1:5000/auth'; // Your backend auth API base URL

const adminApi = {
    /**
     * Helper function to make authenticated API requests.
     * @param {string} endpoint - The API endpoint (e.g., '/products').
     * @param {string} method - HTTP method (GET, POST, PUT, DELETE).
     * @param {object|FormData|null} [body=null] - Request body for POST/PUT.
     * @param {boolean} [isFormData=false] - Set to true if body is FormData.
     * @returns {Promise<object>} - The JSON response from the API.
     */
    async request(endpoint, method = 'GET', body = null, isFormData = false) {
        const token = getAdminAuthToken(); // Function from admin_auth.js
        // Allow requests to login/auth endpoints without a token
        const isAuthEndpoint = endpoint.startsWith(AUTH_BASE_URL) || (API_BASE_URL + endpoint).includes('/login');


        if (!token && !isAuthEndpoint) {
            console.error('Admin token not found for non-auth endpoint.');
            // This should ideally be handled by ensureAdminAuthenticated on page load
            // but as a fallback:
            if (typeof ensureAdminAuthenticated === 'function') {
                 ensureAdminAuthenticated(); // Attempt to redirect
            }
            throw new Error('Authentication required. Please log in again.');
        }

        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        if (!isFormData && body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            headers['Content-Type'] = 'application/json';
        }

        const config = {
            method: method,
            headers: headers,
        };

        if (body) {
            config.body = isFormData ? body : JSON.stringify(body);
        }
        
        const fullUrl = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;


        try {
            const response = await fetch(fullUrl, config);
            let responseData;

            if (response.status === 401 && !isAuthEndpoint) {
                console.error('Admin token expired or invalid.');
                if (typeof clearAdminAuthToken === 'function') clearAdminAuthToken();
                if (typeof ensureAdminAuthenticated === 'function') ensureAdminAuthenticated(); // Will redirect
                throw new Error('Your session has expired. Please log in again.');
            }

            const responseText = await response.text();
            try {
                responseData = responseText ? JSON.parse(responseText) : {}; // Default to empty object if no text
            } catch (e) {
                // If parsing fails but response is OK, it might be an intentional empty response or non-JSON
                if (response.ok && !responseText) { // Successful empty response
                    return { message: "Operation successful." };
                } else if (response.ok && responseText) { // Successful non-JSON response
                     return { message: responseText };
                }
                // If parsing fails and response is not OK
                console.error("Failed to parse JSON response:", responseText);
                throw new Error(`Server returned non-JSON error. Status: ${response.status} - ${response.statusText}. Response: ${responseText.substring(0,150)}...`);
            }

            if (!response.ok) {
                // Prefer specific error message from backend if available
                const errorMessage = responseData.error || responseData.message || `Request failed with status ${response.status}.`;
                console.error(`API Error (${response.status}):`, errorMessage, responseData);
                throw new Error(errorMessage);
            }
            
            // Ensure a message field for successful operations if none is provided by backend
            if(response.ok && !responseData.message && Object.keys(responseData).length === 0 && (method === 'POST' || method === 'PUT' || method === 'DELETE')) {
                 // For successful POST/PUT/DELETE that might return 200 OK with empty body or just data
                 // and we want to provide a default success message if the calling function expects one.
                 // However, usually the calling function will craft its own success message based on context.
                 // So, it's better to return the data as is.
            }


            return responseData;

        } catch (error) {
            console.error(`API Request Failed: ${method} ${fullUrl}`, error);
            // Standardize network errors
            if (error.message.toLowerCase().includes("failed to fetch")) {
                throw new Error("Network error: Could not connect to the server. Please check your internet connection and try again.");
            }
            // Re-throw other errors (already processed or specific)
            throw error;
        }
    },

    // --- Authentication (Example, move to authApi if separating further) ---
    async adminLogin(email, password) {
        // Note: Login endpoint might be different from API_BASE_URL
        return this.request(`${AUTH_BASE_URL}/admin/login`, 'POST', { email, password });
    },

    // --- Dashboard ---
    async getDashboardStats() {
        return this.request('/dashboard/stats', 'GET');
    },

    // --- Categories ---
    async getCategories(searchTerm = '', page = 1, limit = 100) {
        let query = `/categories?page=${page}&limit=${limit}`;
        if (searchTerm) query += `&search=${encodeURIComponent(searchTerm)}`;
        return this.request(query, 'GET');
    },
    async getCategoryById(categoryId) {
        return this.request(`/categories/${categoryId}`, 'GET');
    },
    async addCategory(categoryData) {
        return this.request('/categories', 'POST', categoryData);
    },
    async updateCategory(categoryId, categoryData) {
        return this.request(`/categories/${categoryId}`, 'PUT', categoryData);
    },
    async deleteCategory(categoryId) {
        return this.request(`/categories/${categoryId}`, 'DELETE');
    },

    // --- Products ---
    async getProducts(searchTerm = '', page = 1, limit = 10) {
        let query = `/products?page=${page}&limit=${limit}`;
        if (searchTerm) query += `&search=${encodeURIComponent(searchTerm)}`;
        return this.request(query, 'GET');
    },
    async getProductById(productId) {
        return this.request(`/products/${productId}`, 'GET');
    },
    async addProduct(formData) {
        return this.request('/products', 'POST', formData, true);
    },
    async updateProduct(productId, formData) {
        return this.request(`/products/${productId}`, 'PUT', formData, true);
    },
    async deleteProduct(productId) {
        return this.request(`/products/${productId}`, 'DELETE');
    },

    // --- Users ---
    async getUsers(searchTerm = '', page = 1, limit = 10) {
        let query = `/users?page=${page}&limit=${limit}`;
        if (searchTerm) query += `&search=${encodeURIComponent(searchTerm)}`;
        return this.request(query, 'GET');
    },
    async getUserById(userId) {
        return this.request(`/users/${userId}`, 'GET');
    },
    async updateUser(userId, userData) {
        return this.request(`/users/${userId}`, 'PUT', userData);
    },

    // --- Reviews ---
    async getReviews(searchTerm = '', page = 1, limit = 10) {
        let query = `/reviews?page=${page}&limit=${limit}`;
        if (searchTerm) query += `&search=${encodeURIComponent(searchTerm)}`;
        return this.request(query, 'GET');
    },
    async getReviewById(reviewId) {
        return this.request(`/reviews/${reviewId}`, 'GET');
    },
    async updateReview(reviewId, reviewData) {
        return this.request(`/reviews/${reviewId}`, 'PUT', reviewData);
    },
    async deleteReview(reviewId) {
        return this.request(`/reviews/${reviewId}`, 'DELETE');
    },

    // --- Orders ---
    async getOrders(searchTerm = '', page = 1, limit = 10, status = '') {
        let query = `/orders?page=${page}&limit=${limit}`;
        if (searchTerm) query += `&search=${encodeURIComponent(searchTerm)}`;
        if (status) query += `&status=${encodeURIComponent(status)}`;
        return this.request(query, 'GET');
    },
    async getOrderById(orderId) {
        return this.request(`/orders/${orderId}`, 'GET');
    },
    async updateOrderStatus(orderId, statusData) {
        return this.request(`/orders/${orderId}/status`, 'PUT', statusData);
    },

    // --- Invoices ---
    async getInvoices(searchTerm = '', page = 1, limit = 10) {
        let query = `/invoices?page=${page}&limit=${limit}`;
        if (searchTerm) query += `&search=${encodeURIComponent(searchTerm)}`;
        return this.request(query, 'GET');
    },
    async generateInvoiceForOrder(orderId) {
        return this.request(`/invoices/order/${orderId}`, 'POST');
    },
    async getInvoiceById(invoiceId) {
        return this.request(`/invoices/${invoiceId}`, 'GET');
    },
    getInvoicePdfUrl(invoiceId) {
        const token = getAdminAuthToken();
        // If your backend /download route for PDFs is protected by JWT in query param
        return token ? `${API_BASE_URL}/invoices/${invoiceId}/download?token=${token}` : `${API_BASE_URL}/invoices/${invoiceId}/download`;
        // If protected by Authorization header, direct <a> link won't work easily.
        // You might need to fetch the blob and create an object URL for download.
        // For now, assume direct link or backend handles auth redirection.
    },
    async updateInvoiceStatus(invoiceId, statusData) {
        return this.request(`/invoices/${invoiceId}/status`, 'PUT', statusData);
    },
    async deleteInvoice(invoiceId) {
        return this.request(`/invoices/${invoiceId}`, 'DELETE');
    }
};

// Ensure these are available globally or imported if admin_auth.js is a module
// These are placeholders if admin_auth.js isn't loaded or structured as expected.
// It's better to rely on admin_auth.js to provide these.
if (typeof getAdminAuthToken === 'undefined') {
    window.getAdminAuthToken = function() {
        return localStorage.getItem('adminAuthToken');
    };
}
if (typeof clearAdminAuthToken === 'undefined') {
    window.clearAdminAuthToken = function() {
        localStorage.removeItem('adminAuthToken');
    };
}
if (typeof ensureAdminAuthenticated === 'undefined') {
    window.ensureAdminAuthenticated = function() {
        // Basic check, actual redirection logic is in admin_auth.js
        if (!getAdminAuthToken() && !window.location.pathname.endsWith('admin_login.html')) {
            console.warn("ensureAdminAuthenticated called from admin_api.js fallback: Redirecting (ensure admin_auth.js is loaded).");
            // window.location.href = 'admin_login.html'; // Simplified
            return false;
        }
        return true;
    };
}
