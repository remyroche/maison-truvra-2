// website/admin/js/admin_auth.js
// Handles admin login authentication.

document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Auth JS Loaded");

    const loginForm = document.getElementById('admin-login-form');
    const emailInput = document.getElementById('admin-email');
    const passwordInput = document.getElementById('admin-password');
    const messageElement = document.getElementById('admin-login-message');

    // Ensure API_ADMIN_BASE_URL is available (expected from config.js or admin_config.js)
    // If not, provide a fallback or throw an error.
    // For admin pages, it's likely ADMIN_API_BASE_URL from js/admin_config.js if it exists,
    // or API_BASE_URL from ../js/config.js
    const ADMIN_AUTH_API_URL = (window.ADMIN_API_BASE_URL || window.API_BASE_URL || '/api') + '/auth/login';


    // Function to show toast messages (can be moved to a global admin_ui.js if used across multiple admin pages)
    // For now, keeping it here as it was part of the original login page script.
    // If admin_ui.js and its showAdminToast is loaded before this, this can be removed.
    if (!window.showAdminToast) {
        console.warn("showAdminToast not found globally, using local version for admin_auth.js.");
        window.showAdminToast = function(message, type = 'info', duration = 3000) {
            const toast = document.getElementById('admin-message-toast'); // Assumes this element exists on the page
            const textElement = document.getElementById('admin-message-text'); // Assumes this element exists
            if (!toast || !textElement) {
                // Fallback to simple alert if toast elements are not on the page
                alert(`${type.toUpperCase()}: ${message}`);
                return;
            }
            textElement.textContent = message;
            toast.className = ''; // Reset classes
            toast.classList.add(type); // Add type class for styling (e.g., 'success', 'error')
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, duration);
        };
    }


    if (loginForm) {
        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const email = emailInput.value.trim();
            const password = passwordInput.value.trim();
            
            if(messageElement) messageElement.textContent = ''; // Clear previous messages

            if (!email || !password) {
                if(messageElement) messageElement.textContent = 'Veuillez remplir tous les champs.';
                return;
            }

            try {
                const response = await fetch(ADMIN_AUTH_API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const result = await response.json();

                if (response.ok && result.success && result.user && result.user.is_admin) {
                    // Store token and user info (use sessionStorage for session-only, localStorage for persistence)
                    sessionStorage.setItem('adminAuthToken', result.token);
                    sessionStorage.setItem('adminUser', JSON.stringify(result.user));
                    
                    window.showAdminToast('Connexion réussie. Redirection...', 'success');
                    // Redirect to the admin dashboard (ensure this path is correct)
                    window.location.href = 'admin_dashboard.html'; 
                } else if (response.ok && result.success && result.user && !result.user.is_admin) {
                    if(messageElement) messageElement.textContent = 'Accès refusé. Ce compte n\'est pas un administrateur.';
                    window.showAdminToast('Accès administrateur requis.', 'error');
                } else {
                    if(messageElement) messageElement.textContent = result.message || 'E-mail ou mot de passe incorrect.';
                    window.showAdminToast(result.message || 'Échec de la connexion.', 'error');
                }
            } catch (error) {
                console.error('Erreur de connexion admin:', error);
                if(messageElement) messageElement.textContent = 'Erreur de communication avec le serveur.';
                window.showAdminToast('Erreur de connexion.', 'error');
            }
        });
    }

    // Optional: Redirect if already logged in as admin
    // This check should ideally be in admin_main.js or a script that runs on all protected admin pages.
    // If placing it here, ensure it doesn't cause redirect loops if already on the login page.
    const currentPath = window.location.pathname.split('/').pop();
    if (currentPath === 'admin_login.html') { // Only run redirect check if on login page
        const token = sessionStorage.getItem('adminAuthToken');
        const adminUserString = sessionStorage.getItem('adminUser');
        if (token && adminUserString) {
            try {
                const adminUser = JSON.parse(adminUserString);
                if (adminUser && adminUser.is_admin) {
                    console.log("Admin already logged in, redirecting to dashboard from login page.");
                    // No, do not redirect from login page itself if already logged in, user might want to log in as different admin.
                    // The check for authentication should happen on protected pages, redirecting TO login if not auth.
                    // For now, we'll leave this commented out or remove it, as admin_main.js should handle protection.
                    // window.location.href = 'admin_dashboard.html'; 
                }
            } catch (e) {
                console.error("Error parsing admin user from sessionStorage", e);
                sessionStorage.removeItem('adminAuthToken');
                sessionStorage.removeItem('adminUser');
            }
        }
    }
    console.log("Admin Auth JS Initialized for login page.");
});
