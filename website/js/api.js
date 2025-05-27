// website/js/api.js
// Handles API communication for the frontend application

/**
 * Makes an API request to the backend.
 * @param {string} endpoint - The API endpoint (e.g., '/products').
 * @param {string} [method='GET'] - The HTTP method.
 * @param {object|null} [body=null] - The request body for POST/PUT requests.
 * @param {boolean} [requiresAuth=false] - Whether the request requires an authentication token.// website/js/api.js
// Assumes API_BASE_URL is from config.js and getCurrentLang is from i18n.js

async function makeApiRequest(endpoint, method = 'GET', body = null, requiresAuth = false) {
    const headers = { 'Content-Type': 'application/json' };
    const lang = typeof getCurrentLang === 'function' ? getCurrentLang() : 'fr'; // Get current language

    if (requiresAuth) {
        const token = getAuthToken(); // Assumes getAuthToken is available (from auth.js)
        if (!token) {
            if(typeof showGlobalMessage === 'function' && typeof t === 'function') showGlobalMessage(t('Vous_netes_pas_authentifie'), "error");
            else console.error("User not authenticated and showGlobalMessage or t is not available.");
            throw new Error("Authentification requise.");
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

    // Add lang parameter to GET requests
    let url = `<span class="math-inline">\{API\_BASE\_URL\}</span>{endpoint}`;
    if (method === 'GET') {
        url += (url.includes('?') ? '&' : '?') + `lang=${lang}`;
    }

    try {
        const response = await fetch(url, config);
        if (!response.ok) {
            const errorResult = await response.json().catch(() => ({ message: t('Erreur_de_communication_avec_le_serveur') || "Erreur de communication avec le serveur." }));
            throw new Error(errorResult.message || `${t('Erreur_HTTP') || 'HTTP Error:'} ${response.status}`);
        }
        if (response.status === 204) {
            return { success: true, message: "Opération réussie (pas de contenu)." };
        }
        return await response.json();
    } catch (error) {
        console.error(`${t('Erreur_API_pour') || 'API Error for'} ${method} <span class="math-inline">\{API\_BASE\_URL\}</span>{endpoint}:`, error);
        if(typeof showGlobalMessage === 'function' && typeof t === 'function') {
            showGlobalMessage(error.message || t('Une_erreur_reseau_est_survenue'), "error");
        } else {
             console.error(error.message || "A network error occurred.");
        }
        throw error;
    }
}
