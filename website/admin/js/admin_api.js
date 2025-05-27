// website/admin/js/admin_api.js
// Handles API communication for the Admin Panel.

/**
 * Makes an API request to the admin backend.
 * @param {string} endpoint - The API endpoint (e.g., '/products').
 * @param {string} [method='GET'] - The HTTP method.
 * @param {object|null} [body=null] - The request body for POST/PUT requests.
 * @returns {Promise<object>} - A promise that resolves with the JSON response from the API.
 * @throws {Error} - Throws an error if the API request fails or authentication is required but missing.
 */
async function adminApiRequest(endpoint, method = 'GET', body = null) {
    const token = getAdminAuthToken(); // Assumes getAdminAuthToken is available (from admin_auth.js)
    if (!token) {
        showAdminToast("Session expirée ou invalide. Veuillez vous reconnecter.", "error"); // Assumes showAdminToast is available (from admin_ui.js)
        window.location.href = 'admin_login.html'; // Redirect to login
        throw new Error("Token administrateur manquant.");
    }

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };

    const config = {
        method: method,
        headers: headers,
    };

    if (body) {
        config.body = JSON.stringify(body);
    }

    try {
        // Assumes API_ADMIN_BASE_URL is available (from admin_config.js)
        const response = await fetch(`${API_ADMIN_BASE_URL}${endpoint}`, config);
        const responseData = await response.json().catch(() => ({})); // Handle cases where response might be empty but still ok (e.g. 204)

        if (!response.ok) {
            const errorMessage = responseData.message || `Erreur HTTP: ${response.status}`;
            showAdminToast(errorMessage, "error");
            if (response.status === 401 || response.status === 403) { // Unauthorized or Forbidden
                sessionStorage.removeItem('adminAuthToken');
                sessionStorage.removeItem('adminUser');
                window.location.href = 'admin_login.html';
            }
            throw new Error(errorMessage);
        }
        return responseData;
    } catch (error) {
        console.error(`Erreur API Admin pour ${method} ${API_ADMIN_BASE_URL}${endpoint}:`, error);
        // Avoid double-toasting if already handled by HTTP status check
        if (!error.message.startsWith("Erreur HTTP") && !error.message.includes("Token administrateur manquant")) {
            showAdminToast(error.message || "Une erreur réseau est survenue.", "error");
        }
        throw error; // Re-throw to be caught by calling function if needed
    }
}
