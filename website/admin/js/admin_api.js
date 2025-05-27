// website/admin/js/admin_api.js
// Handles API communication for the Admin Panel.

/**
 * Makes an API request to the admin backend.
 * @param {string} endpoint - The API endpoint (e.g., '/products').
 * @param {string} [method='GET'] - The HTTP method.
 * @param {object|FormData|null} [body=null] - The request body for POST/PUT requests. Can be an object or FormData.
 * @returns {Promise<object>} - A promise that resolves with the JSON response from the API.
 * @throws {Error} - Throws an error if the API request fails or authentication is required but missing.
 */
async function adminApiRequest(endpoint, method = 'GET', body = null) {
    const token = getAdminAuthToken(); // Assumes getAdminAuthToken is available (from admin_auth.js)
    if (!token && endpoint !== '/auth/login') { // Allow login without token
        showAdminToast("Session expirée ou invalide. Veuillez vous reconnecter.", "error");
        // Do not redirect here, let the calling function handle it or specific auth checks do.
        // window.location.href = 'admin_login.html';
        throw new Error("Token administrateur manquant.");
    }

    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        method: method,
        headers: headers,
    };

    if (body) {
        if (body instanceof FormData) {
            // For FormData, don't set Content-Type header. Browser will do it with boundary.
            config.body = body;
        } else {
            // For JSON, set Content-Type and stringify
            headers['Content-Type'] = 'application/json';
            config.body = JSON.stringify(body);
        }
    }


    try {
        const response = await fetch(`${API_ADMIN_BASE_URL}${endpoint}`, config); // API_ADMIN_BASE_URL from admin_config.js
        
        // Try to parse JSON, but handle cases where response might be empty or not JSON
        let responseData = {};
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            responseData = await response.json();
        } else if (response.ok && response.status !== 204) { // 204 No Content is fine
            // If not JSON but still okay, create a success-like structure
            // Or handle text response if expected for some endpoints
            responseData = { success: true, data: await response.text() };
        }


        if (!response.ok) {
            const errorMessage = responseData.message || responseData.error || `Erreur HTTP: ${response.status} ${response.statusText}`;
            showAdminToast(errorMessage, "error");
            if ((response.status === 401 || response.status === 403) && endpoint !== '/auth/login') {
                // More specific handling for auth errors if needed
                // Consider redirecting to login if token is clearly invalid/expired for non-login routes
                // sessionStorage.removeItem('adminAuthToken');
                // sessionStorage.removeItem('adminUser');
                // window.location.href = 'admin_login.html';
            }
            throw new Error(errorMessage);
        }
        
        // If responseData is empty for a 200/201 but was expected to be JSON, it might be an issue.
        // But for now, if response.ok, we assume success.
        // If responseData is not structured as {success: ..., message: ...}, adapt or ensure backend sends it.
        // For a 204 No Content, responseData will be empty.
        if (response.status === 204) {
            return { success: true, message: "Opération réussie (pas de contenu)." };
        }
        
        return responseData; // This should now be the parsed JSON or the constructed success object

    } catch (error) {
        console.error(`Erreur API Admin pour ${method} ${API_ADMIN_BASE_URL}${endpoint}:`, error);
        // Avoid double-toasting if already handled by HTTP status check or specific error message
        if (error.message && !error.message.includes("Erreur HTTP") && !error.message.includes("Token administrateur manquant")) {
             showAdminToast(error.message || "Une erreur réseau est survenue.", "error");
        } else if (!error.message) { // Generic error if message is missing
            showAdminToast("Une erreur réseau est survenue.", "error");
        }
        throw error;
    }
}
