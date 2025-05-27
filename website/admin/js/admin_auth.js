// website/admin/js/admin_auth.js
// Handles admin login authentication.

document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Auth JS Loaded");

    const loginForm = document.getElementById('admin-login-form');// website/admin/js/admin_auth.js
// Handles admin login authentication.
// Assumes adminApi.js (adminApi.adminLogin, AdminApiError) is loaded.
// Assumes ui.js (showGlobalMessage, showButtonLoading, hideButtonLoading) is loaded.
// Assumes i18n.js (t function) is available for translated messages.

document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Auth JS Loaded");

    const loginForm = document.getElementById('admin-login-form');
    const emailInput = document.getElementById('admin-email');
    const passwordInput = document.getElementById('admin-password');
    // Message element for inline feedback within the form area
    const loginMessageTargetId = 'admin-login-message'; // Ensure an element with this ID exists

    // Helper function for translation, with a fallback
    const translate = typeof t === 'function' ? t : (key, params) => {
        let str = key;
        if (params) {
            for (const pKey in params) {
                str = str.replace(new RegExp(`{${pKey}}`, 'g'), params[pKey]);
            }
        }
        return str;
    };

    // Function to store admin auth data
    function storeAdminAuth(token, user) {
        sessionStorage.setItem('adminAuthToken', token);
        sessionStorage.setItem('adminUser', JSON.stringify(user));
        // localStorage can be used for more persistent login, but sessionStorage is often preferred for admin panels.
    }
    
    // Function to get admin auth token (consistent with admin_api.js expectation)
    if (typeof getAdminAuthToken === 'undefined') {
        window.getAdminAuthToken = function() {
            return sessionStorage.getItem('adminAuthToken');
        };
    }
    // Function to clear admin auth token
     if (typeof clearAdminAuthToken === 'undefined') {
        window.clearAdminAuthToken = function() {
            sessionStorage.removeItem('adminAuthToken');
            sessionStorage.removeItem('adminUser');
        };
    }


    if (loginForm) {
        const submitButton = loginForm.querySelector('button[type="submit"]');

        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const email = emailInput.value.trim();
            const password = passwordInput.value.trim();
            
            // Clear previous inline messages
            const messageElement = document.getElementById(loginMessageTargetId);
            if(messageElement) messageElement.textContent = '';


            if (!email || !password) {
                if (typeof showGlobalMessage === 'function') {
                    showGlobalMessage({ 
                        message: translate('admin.auth.fillAllFields'), 
                        type: 'error',
                        targetElementId: loginMessageTargetId // Show inline if element exists
                    });
                } else {
                    if(messageElement) messageElement.textContent = 'Veuillez remplir tous les champs.';
                }
                return;
            }

            if (submitButton && typeof showButtonLoading === 'function') {
                showButtonLoading(submitButton, translate('admin.auth.loggingIn'));
            }

            try {
                // adminApi.adminLogin should be available from admin_api.js
                const result = await adminApi.adminLogin(email, password);

                if (result.success !== false && result.token && result.user && result.user.is_admin) { // Check for explicit success false
                    storeAdminAuth(result.token, result.user);
                    
                    if (typeof showGlobalMessage === 'function') {
                        showGlobalMessage({ message: translate('admin.auth.loginSuccessRedirecting'), type: 'success' });
                    }
                    // Redirect to the admin dashboard
                    window.location.href = 'admin_dashboard.html'; 
                } else if (result.user && !result.user.is_admin) {
                    const accessDeniedMsg = translate('admin.auth.accessDeniedNotAdmin');
                     if (typeof showGlobalMessage === 'function') {
                        showGlobalMessage({ message: accessDeniedMsg, type: 'error', targetElementId: loginMessageTargetId });
                    } else if (messageElement) {
                        messageElement.textContent = accessDeniedMsg;
                    }
                } else {
                    // Use message from API if available, otherwise a generic one
                    const loginFailedMsg = result.message || translate('admin.auth.loginFailedIncorrectCredentials');
                     if (typeof showGlobalMessage === 'function') {
                        showGlobalMessage({ message: loginFailedMsg, type: 'error', targetElementId: loginMessageTargetId });
                    } else if (messageElement) {
                        messageElement.textContent = loginFailedMsg;
                    }
                }
            } catch (error) {
                console.error('Admin login error:', error);
                let errorMessage = translate('admin.auth.loginErrorServerCommunication');
                if (error instanceof AdminApiError) { // Custom error from adminApi
                    errorMessage = error.message; // This message would have already been shown globally by adminApi if not auth related
                }
                // Show error message inline
                if (typeof showGlobalMessage === 'function') {
                    showGlobalMessage({ message: errorMessage, type: 'error', targetElementId: loginMessageTargetId });
                } else if (messageElement) {
                     messageElement.textContent = errorMessage;
                }
            } finally {
                if (submitButton && typeof hideButtonLoading === 'function') {
                    hideButtonLoading(submitButton);
                }
            }
        });
    }

    // Redirection check: If already logged in as admin and NOT on the login page, redirect to dashboard.
    // This should ideally be in a central script like admin_main.js that runs on all admin pages.
    // For admin_login.html itself, we don't auto-redirect away if already logged in,
    // as the user might want to log in as a different admin.
    // The protection for other admin pages (redirecting TO login if not authenticated) is more critical.
    
    // Example of how admin_main.js might protect pages:
    /*
    if (typeof ensureAdminAuthenticated === 'undefined' && !window.location.pathname.endsWith('admin_login.html')) {
        window.ensureAdminAuthenticated = function() {
            const token = getAdminAuthToken();
            const adminUserString = sessionStorage.getItem('adminUser');
            let isAdmin = false;
            if (adminUserString) {
                try {
                    const adminUser = JSON.parse(adminUserString);
                    isAdmin = adminUser && adminUser.is_admin;
                } catch (e) { console.error("Error parsing admin user from session."); }
            }

            if (!token || !isAdmin) {
                console.log("Admin not authenticated or not an admin, redirecting to login.");
                clearAdminAuthToken(); // Clear any partial/invalid auth data
                window.location.href = 'admin_login.html?redirect=' + encodeURIComponent(window.location.pathname + window.location.search);
                return false; // Indicate not authenticated
            }
            return true; // Authenticated
        };
        // Call it on page load for protected pages
        // if (!ensureAdminAuthenticated()) {
        //   // Potentially stop further script execution if redirecting
        // }
    }
    */

    console.log("Admin Auth JS Initialized for login page.");
});
