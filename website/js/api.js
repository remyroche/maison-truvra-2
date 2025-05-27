// website/js/api.js
// Handles API communication for the frontend application
// Assumes API_BASE_URL is from config.js
// Assumes getCurrentLang and t (translate) are from i18n.js
// Assumes showGlobalMessage is from ui.js
// Assumes getAuthToken is from auth.js

// Custom Error class for API responses
class ApiError extends Error {
    constructor(message, status, errorCode = null, details = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.errorCode = errorCode;
        this.details = details;
    }
}

async function makeApiRequest(endpoint, method = 'GET', body = null, requiresAuth = false) {
    const headers = { 'Content-Type': 'application/json' };
    const lang = typeof getCurrentLang === 'function' ? getCurrentLang() : 'fr'; // Get current language

    if (requiresAuth) {
        const token = getAuthToken(); 
        if (!token) {
            const authRequiredMsg = typeof t === 'function' ? t('authentication_required') : "Authentication required.";
            // Do not show global message here, let the caller decide if it's a page-blocking error
            // For example, checkAuth will handle redirection or UI update.
            // Other calls might just need to inform the user to log in without a global toast.
            console.error("User not authenticated for a protected route:", endpoint);
            throw new ApiError(authRequiredMsg, 401, 'AUTH_REQUIRED');
        }
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        method: method,
        headers: headers,
    };

    if (body) {
        config.body = JSON.stringify(body);
    }

    let url = `${API_BASE_URL}${endpoint}`; // Ensure API_BASE_URL is correctly defined
    if (method === 'GET' && lang) { // Add lang parameter to GET requests if available
        url += (url.includes('?') ? '&' : '?') + `lang=${lang}`;
    }

    try {
        const response = await fetch(url, config);
        let responseData;

        try {
            // Try to parse JSON, but handle cases where response might be empty (e.g., 204 No Content)
            // or non-JSON (though API should ideally always return JSON for errors)
            const text = await response.text();
            if (text) {
                responseData = JSON.parse(text);
            } else if (response.status === 204) {
                return { success: true, message: typeof t === 'function' ? t('operation_successful_no_content') : "Operation successful (no content).", status: 204 };
            } else if (response.ok) { // OK status but empty body not 204
                 return { success: true, message: typeof t === 'function' ? t('operation_successful') : "Operation successful.", status: response.status };
            }
        } catch (e) {
            // Failed to parse JSON. If response was not OK, this is an issue.
            if (!response.ok) {
                console.error(`Failed to parse JSON error response from ${method} ${url}. Status: ${response.status}. Response text: ${await response.text().catch(() => '')}`);
                const serverErrorMsg = typeof t === 'function' ? t('server_returned_invalid_error_format') : "Server returned an invalid error format.";
                throw new ApiError(serverErrorMsg, response.status, 'INVALID_JSON_RESPONSE');
            }
            // If response was OK but JSON parsing failed (e.g. malformed JSON from an endpoint that should return it)
            // This case should be rare if API is consistent.
            console.warn(`Successfully fetched from ${method} ${url} but failed to parse supposedly JSON response. Status: ${response.status}.`);
            // Treat as success if status code was 2xx, but return raw text or a warning.
            // For now, let's assume if it's OK, and not 204, it should have parseable JSON or it's an API design issue.
            // If it was meant to be non-JSON, the caller should handle it.
        }


        if (!response.ok) {
            const errorMessage = responseData?.message || responseData?.error || (typeof t === 'function' ? t('error_http_status', { status: response.status }) : `HTTP Error: ${response.status}`);
            const errorCode = responseData?.error_code || responseData?.errorCode || null;
            const errorDetails = responseData?.details || null;
            
            console.error(`API Error for ${method} ${url}: Status ${response.status}`, responseData);
            throw new ApiError(errorMessage, response.status, errorCode, errorDetails);
        }
        
        // If responseData is undefined here (e.g. successful 200 with empty body that wasn't 204)
        // and we expect data, this might be an issue. For now, we return it as is.
        // The backend should ideally return 204 for no content, or an empty JSON object/array for 200.
        return responseData || { success: true, status: response.status }; // Ensure something is returned for .then()

    } catch (error) {
        // Handle network errors (fetch itself failed) or errors thrown from above
        if (error instanceof ApiError) {
            // If it's already an ApiError, re-throw it for the caller to handle.
            // Global message display can be decided by the caller or a higher-level handler.
            // However, for general API errors not caught specifically, a global message might be useful.
            // Let's show a global message for non-auth errors here as a default.
            if (error.status !== 401) { // Don't show global for 401 as it's often handled by redirection
                 if (typeof showGlobalMessage === 'function') {
                    showGlobalMessage({ message: error.message, type: 'error' });
                }
            }
            throw error;
        }

        console.error(`Network or other error for ${method} ${url}:`, error);
        const networkErrorMsg = typeof t === 'function' ? t('network_error_occurred') : "A network error occurred. Please check your connection.";
        if (typeof showGlobalMessage === 'function') {
            showGlobalMessage({ message: networkErrorMsg, type: 'error' });
        }
        throw new ApiError(networkErrorMsg, 0, 'NETWORK_ERROR', { originalError: error.message }); // Status 0 for network errors
    }
}
