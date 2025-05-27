// File: website/admin/js/admin_api.js

// Ensure API_BASE_URL and AUTH_BASE_URL are defined (e.g., from admin_config.js or a global config)
// These fallbacks are illustrative; a proper config setup is better.
const ADMIN_API_BASE_URL = window.ADMIN_API_BASE_URL || 'http://127.0.0.1:5000/api/admin';
const ADMIN_AUTH_BASE_URL = window.ADMIN_AUTH_BASE_URL || 'http://127.0.0.1:5000/auth';

// Custom Error class for Admin API responses
class AdminApiError extends Error {
    constructor(message, status, errorCode = null, details = null) {
        super(message);
        this.name = 'AdminApiError';
        this.status = status;
        this.errorCode = errorCode;
        this.details = details;
    }
}

const adminApi = {
    /**
     * Helper function to make authenticated API requests for the admin panel.
     * @param {string} endpoint - The API endpoint (e.g., '/products').
     * @param {string} method - HTTP method (GET, POST, PUT, DELETE, PATCH).
     * @param {object|FormData|null} [body=null] - Request body for POST/PUT/PATCH.
     * @param {boolean} [isFormData=false] - Set to true if body is FormData.
     * @returns {Promise<object>} - The JSON response from the API.
     * @throws {AdminApiError} - For API or network errors.
     */
    async request(endpoint, method = 'GET', body = null, isFormData = false) {
        const token = typeof getAdminAuthToken === 'function' ? getAdminAuthToken() : localStorage.getItem('adminAuthToken');
        
        // Determine if the endpoint is for authentication (login, refresh token etc.)
        // These might not require a token or have different auth handling.
        const isAuthEndpoint = endpoint.startsWith(ADMIN_AUTH_BASE_URL) || 
                               (ADMIN_API_BASE_URL + endpoint).includes('/login') ||
                               (ADMIN_API_BASE_URL + endpoint).includes('/refresh'); // Add other auth endpoints if any

        if (!token && !isAuthEndpoint) {
            console.error('Admin token not found for non-auth endpoint:', endpoint);
            if (typeof ensureAdminAuthenticated === 'function') {
                 ensureAdminAuthenticated(); // Attempt to redirect
            }
            const authRequiredMsg = typeof t === 'function' ? t('admin_auth_required_redirecting') : 'Authentication required. Please log in again.';
            // No global message here, redirection should handle it.
            throw new AdminApiError(authRequiredMsg, 401, 'ADMIN_AUTH_REQUIRED');
        }

        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        if (!isFormData && body && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
            headers['Content-Type'] = 'application/json';
        }
        // For GET requests, Content-Type is usually not needed.

        const config = {
            method: method.toUpperCase(),
            headers: headers,
        };

        if (body) {
            config.body = isFormData ? body : JSON.stringify(body);
        }
        
        const fullUrl = endpoint.startsWith('http') ? endpoint : `${ADMIN_API_BASE_URL}${endpoint}`;

        try {
            const response = await fetch(fullUrl, config);
            let responseData;
            const responseText = await response.text();

            if (response.status === 401 && !isAuthEndpoint) {
                console.error('Admin token expired or invalid for:', fullUrl);
                if (typeof clearAdminAuthToken === 'function') clearAdminAuthToken();
                if (typeof ensureAdminAuthenticated === 'function') ensureAdminAuthenticated(); // Will redirect
                const sessionExpiredMsg = typeof t === 'function' ? t('admin_session_expired') : 'Your session has expired. Please log in again.';
                throw new AdminApiError(sessionExpiredMsg, 401, 'ADMIN_SESSION_EXPIRED');
            }

            try {
                if (responseText) {
                    responseData = JSON.parse(responseText);
                } else if (response.status === 204) { // No Content
                    return { success: true, message: typeof t === 'function' ? t('admin_operation_successful_no_content') : "Operation successful (no content).", status: 204 };
                } else if (response.ok) { // OK status but empty body not 204
                    return { success: true, message: typeof t === 'function' ? t('admin_operation_successful') : "Operation successful.", status: response.status };
                }
            } catch (e) {
                if (!response.ok) {
                    console.error(`Failed to parse JSON error response from ${method} ${fullUrl}. Status: ${response.status}. Response: ${responseText.substring(0, 200)}`);
                    const serverErrorMsg = typeof t === 'function' ? t('admin_server_invalid_error_format') : "Server returned an invalid error format.";
                    throw new AdminApiError(serverErrorMsg, response.status, 'ADMIN_INVALID_JSON_RESPONSE');
                }
                // If response.ok but parsing failed (e.g. successful HTML page returned instead of JSON)
                console.warn(`Successfully fetched from ${method} ${fullUrl} (Status: ${response.status}) but failed to parse expected JSON response. Response: ${responseText.substring(0,200)}`);
                // This could be an issue with the endpoint or an unexpected response.
                // Let's assume for admin, if it's 2xx and not 204, it should be JSON.
                const parseFailMsg = typeof t === 'function' ? t('admin_api_unexpected_response_format') : "API returned an unexpected response format.";
                throw new AdminApiError(parseFailMsg, response.status, 'ADMIN_UNEXPECTED_FORMAT');
            }

            if (!response.ok) {
                const errorMessage = responseData?.message || responseData?.error || (typeof t === 'function' ? t('admin_error_http_status', { status: response.status }) : `Request failed with status ${response.status}.`);
                const errorCode = responseData?.error_code || responseData?.errorCode || null;
                const errorDetails = responseData?.details || null;
                console.error(`Admin API Error (${response.status}) for ${method} ${fullUrl}:`, errorMessage, responseData);
                throw new AdminApiError(errorMessage, response.status, errorCode, errorDetails);
            }
            
            return responseData || { success: true, status: response.status };

        } catch (error) {
            if (error instanceof AdminApiError) {
                // If it's already an AdminApiError, show message and re-throw.
                // Avoid double-messaging for auth errors handled by redirection.
                if (error.errorCode !== 'ADMIN_AUTH_REQUIRED' && error.errorCode !== 'ADMIN_SESSION_EXPIRED') {
                    if (typeof showGlobalMessage === 'function') { // Assumes ui.js is available
                        showGlobalMessage({ message: error.message, type: 'error' });
                    } else {
                        console.error("showGlobalMessage not available. Admin API Error:", error.message);
                    }
                }
                throw error;
            }

            // Network errors or other unexpected errors
            console.error(`Admin API Request Failed: ${method} ${fullUrl}`, error);
            let networkErrorMessage = typeof t === 'function' ? t('admin_network_error') : "Network error: Could not connect to the server. Please check your internet connection.";
            if (error.message && !error.message.toLowerCase().includes("failed to fetch")) {
                // If it's not a typical "failed to fetch", it might be another JS error during the request process.
                networkErrorMessage = typeof t === 'function' ? t('admin_unexpected_error_during_request') : "An unexpected error occurred while making the request.";
            }
            
            if (typeof showGlobalMessage === 'function') {
                showGlobalMessage({ message: networkErrorMessage, type: 'error' });
            } else {
                console.error("showGlobalMessage not available. Network/Request Error:", networkErrorMessage);
            }
            throw new AdminApiError(networkErrorMessage, 0, 'ADMIN_NETWORK_ERROR', { originalError: error.message });
        }
    },

    // --- Authentication ---
    async adminLogin(email, password) {
        // Login endpoint might be different from ADMIN_API_BASE_URL
        return this.request(`${ADMIN_AUTH_BASE_URL}/admin/login`, 'POST', { email, password });
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
    async addProduct(formData) { // formData is FormData
        return this.request('/products', 'POST', formData, true);
    },
    async updateProduct(productId, formData) { // formData is FormData
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
     async createUser(userData) { // Added for admin user creation
        return this.request('/users', 'POST', userData);
    },
    async deleteUser(userId) { // Added for admin user deletion
        return this.request(`/users/${userId}`, 'DELETE');
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
    async updateOrderStatus(orderId, statusData) { // statusData should be { status: "new_status" }
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
        const token = typeof getAdminAuthToken === 'function' ? getAdminAuthToken() : localStorage.getItem('adminAuthToken');
        // If your backend /download route for PDFs is protected by JWT in query param
        // This is generally less secure than Authorization header.
        // Consider fetching as blob if header auth is strict.
        return token ? `${ADMIN_API_BASE_URL}/invoices/${invoiceId}/download?token=${token}` : `${ADMIN_API_BASE_URL}/invoices/${invoiceId}/download`;
    },
    async updateInvoiceStatus(invoiceId, statusData) { // statusData should be { status: "new_status" }
        return this.request(`/invoices/${invoiceId}/status`, 'PUT', statusData);
    },
    async deleteInvoice(invoiceId) {
        return this.request(`/invoices/${invoiceId}`, 'DELETE');
    }
};

// Fallback definitions for auth helper functions if admin_auth.js isn't loaded or structured as expected.
// It's much better to ensure admin_auth.js provides these globally or they are imported as modules.
if (typeof getAdminAuthToken === 'undefined') {
    console.warn("getAdminAuthToken is not defined globally. Using fallback from admin_api.js.");
    window.getAdminAuthToken = function() {
        return sessionStorage.getItem('adminAuthToken') || localStorage.getItem('adminAuthToken'); // Check both
    };
}
if (typeof clearAdminAuthToken === 'undefined') {
    console.warn("clearAdminAuthToken is not defined globally. Using fallback from admin_api.js.");
    window.clearAdminAuthToken = function() {
        sessionStorage.removeItem('adminAuthToken');
        localStorage.removeItem('adminAuthToken');
    };
}
// ensureAdminAuthenticated should ideally be in admin_main.js or a dedicated auth guard script.
if (typeof ensureAdminAuthenticated === 'undefined') {
    console.warn("ensureAdminAuthenticated is not defined globally. Using fallback from admin_api.js.");
    window.ensureAdminAuthenticated = function() {
        if (!getAdminAuthToken() && !window.location.pathname.endsWith('admin_login.html')) {
            console.warn("Fallback ensureAdminAuthenticated: Redirecting to admin_login.html (ensure admin_auth.js or admin_main.js handles this properly).");
            window.location.href = 'admin_login.html'; 
            return false;
        }
        return true;
    };
}
