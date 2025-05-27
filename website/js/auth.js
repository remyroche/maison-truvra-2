// website/js/auth.js

function getAuthToken() {
    return sessionStorage.getItem('authToken');
}

function setAuthToken(token) {
    if (token) sessionStorage.setItem('authToken', token);
    else sessionStorage.removeItem('authToken');
}// website/js/auth.js

/**
 * Retrieves the authentication token from session storage.
 * @returns {string|null} The auth token or null if not found.
 */
function getAuthToken() {
    return sessionStorage.getItem('authToken');
}

/**
 * Sets the authentication token in session storage.
 * @param {string|null} token - The auth token to set, or null to remove.
 */
function setAuthToken(token) {
    if (token) {
        sessionStorage.setItem('authToken', token);
    } else {
        sessionStorage.removeItem('authToken');
    }
}

/**
 * Retrieves the current user data from session storage.
 * @returns {object|null} The user object or null if not found/error.
 */
function getCurrentUser() {
    const userString = sessionStorage.getItem('currentUser');
    if (userString) {
        try {
            return JSON.parse(userString);
        } catch (e) {
            console.error(t('Erreur_lors_du_parsing_des_donnees_utilisateur'), e); // i18n
            sessionStorage.removeItem('currentUser');
            sessionStorage.removeItem('authToken');
            return null;
        }
    }
    return null;
}

/**
 * Sets the current user data and token in session storage.
 * Updates UI elements related to login state and cart count.
 * @param {object|null} userData - The user object, or null to log out.
 * @param {string|null} [token=null] - The auth token.
 */
function setCurrentUser(userData, token = null) {
    if (userData) {
        sessionStorage.setItem('currentUser', JSON.stringify(userData));
        if (token) setAuthToken(token);
    } else {
        sessionStorage.removeItem('currentUser');
        sessionStorage.removeItem('authToken');
    }
    if (typeof updateLoginState === "function") updateLoginState();
    if (typeof updateCartCountDisplay === "function") updateCartCountDisplay();
}

/**
 * Logs out the current user.
 * Clears user data from session storage and updates UI.
 * Redirects to account page if on account or payment page.
 */
async function logoutUser() {
    // Optionally: Call a backend logout endpoint if it exists to invalidate server-side session/token
    // await makeApiRequest('/auth/logout', 'POST', null, true);
    setCurrentUser(null); // Clears session storage and updates UI
    if (typeof showGlobalMessage === "function" && typeof t === "function") {
        showGlobalMessage(t('Deconnecte_message'), "info");
    }

    if (document.body.id === 'page-compte' || document.body.id === 'page-paiement') {
        window.location.href = 'compte.html';
    } else if (document.body.id === 'page-professionnels') { // Also redirect B2B from their dashboard
        window.location.href = 'professionnels.html';
    } else {
        if (typeof updateLoginState === "function") updateLoginState(); // Re-update for other pages
        if (document.body.id === 'page-compte' && typeof displayAccountDashboard === "function") {
            displayAccountDashboard(); // Refresh account page view
        }
    }
}

/**
 * Updates the UI elements (account links in header/mobile menu) based on login state.
 */
function updateLoginState() {
    const currentUser = getCurrentUser();
    const accountLinkTextDesktop = document.getElementById('account-link-text-desktop');
    const accountLinkTextMobile = document.getElementById('account-link-text-mobile');
    const accountLinkDesktopContainer = document.querySelector('header nav a[href="compte.html"]');
    const accountLinkMobileContainer = document.querySelector('#mobile-menu-dropdown a[href="compte.html"]');

    const desktopTextElement = accountLinkTextDesktop || (accountLinkDesktopContainer ? accountLinkDesktopContainer.querySelector('span.text-xs') : null);
    const mobileTextElement = accountLinkTextMobile || accountLinkMobileContainer;

    if (currentUser) {
        const userName = currentUser.prenom || t('Mon_Compte');
        if (desktopTextElement) {
            desktopTextElement.textContent = userName;
        } else if (accountLinkDesktopContainer) { // Fallback if span not found, reconstruct
             accountLinkDesktopContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7 text-brand-classic-gold"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> <span id="account-link-text-desktop" class="ml-1 text-xs">${userName}</span>`;
        }
        if (mobileTextElement) mobileTextElement.textContent = `${t('Mon_Compte_Menu')} (${userName})`;

    } else {
        if (desktopTextElement) {
            desktopTextElement.textContent = t('Mon_Compte_Menu');
        } else if (accountLinkDesktopContainer) { // Fallback if span not found
            accountLinkDesktopContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> <span id="account-link-text-desktop" class="ml-1 text-xs">${t('Mon_Compte_Menu')}</span>`;
        }
        if (mobileTextElement) mobileTextElement.textContent = t('Mon_Compte_Menu');
    }
}


/**
 * Handles the B2C login form submission.
 * @param {Event} event - The form submission event.
 */
async function handleLogin(event) {
    event.preventDefault();
    const loginForm = event.target;
    if (typeof clearFormErrors === "function") clearFormErrors(loginForm);
    const emailField = loginForm.querySelector('#login-email');
    const passwordField = loginForm.querySelector('#login-password');
    const email = emailField.value;
    const password = passwordField.value;
    const loginMessageElement = document.getElementById('login-message');

    let isValid = true;
    if (loginMessageElement) loginMessageElement.textContent = '';

    if (!email || !validateEmail(email)) { // validateEmail from ui.js
        if (typeof setFieldError === "function") setFieldError(emailField, t('Veuillez_entrer_une_adresse_e-mail_valide'));
        isValid = false;
    }
    if (!password) {
        if (typeof setFieldError === "function") setFieldError(passwordField, t('Veuillez_entrer_votre_mot_de_passe'));
        isValid = false;
    }
    if (!isValid) {
        if (typeof showGlobalMessage === "function") showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire'), "error");
        return;
    }

    if (typeof showGlobalMessage === "function") showGlobalMessage(t('Connexion_en_cours'), "info", 60000);

    try {
        const result = await makeApiRequest('/auth/login', 'POST', { email, password }); // makeApiRequest from api.js
        if (result.success && result.user && result.token) {
            // Ensure B2C users are not trying to log in via B2B specific forms and vice-versa if needed.
            // For a general login form, this check might be less strict or handled by UI context.
            setCurrentUser(result.user, result.token);
            if (typeof showGlobalMessage === "function") showGlobalMessage(result.message || t('Connexion_reussie'), "success");
            loginForm.reset();
            if (typeof displayAccountDashboard === "function") displayAccountDashboard();
        } else {
            setCurrentUser(null); // Clear any partial login state
            const generalErrorMessage = result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants');
            if (typeof showGlobalMessage === "function") showGlobalMessage(generalErrorMessage, "error");
            if (loginMessageElement) loginMessageElement.textContent = generalErrorMessage;
            if (typeof setFieldError === "function") {
                setFieldError(emailField, " "); // Mark field as potentially incorrect without specific message
                setFieldError(passwordField, generalErrorMessage); // Show general error on password or a specific field
            }
        }
    } catch (error) {
        setCurrentUser(null);
        if (loginMessageElement) loginMessageElement.textContent = error.message || t('Erreur_de_connexion_au_serveur');
        // showGlobalMessage might have already displayed the error from makeApiRequest
    }
}

/**
 * Handles the B2C registration form submission.
 * @param {Event} event - The form submission event.
 */
async function handleRegistrationForm(event) {
    event.preventDefault();
    const form = event.target;
    if (typeof clearFormErrors === "function") clearFormErrors(form);

    const emailField = form.querySelector('#register-email');
    const passwordField = form.querySelector('#register-password');
    const confirmPasswordField = form.querySelector('#register-confirm-password');
    const nomField = form.querySelector('#register-nom');
    const prenomField = form.querySelector('#register-prenom');
    const messageElement = document.getElementById('register-message'); // For form-specific messages
    if (messageElement) messageElement.textContent = '';


    let isValid = true;
    if (!emailField || !emailField.value || !validateEmail(emailField.value)) {
        if (typeof setFieldError === "function" && emailField) setFieldError(emailField, t('E-mail_invalide'));
        isValid = false;
    }
    if (!nomField || !nomField.value.trim()) {
        if (typeof setFieldError === "function" && nomField) setFieldError(nomField, t('Nom_requis'));
        isValid = false;
    }
    if (!prenomField || !prenomField.value.trim()) {
        if (typeof setFieldError === "function" && prenomField) setFieldError(prenomField, t('Prenom_requis'));
        isValid = false;
    }
    if (!passwordField || passwordField.value.length < 8) {
        if (typeof setFieldError === "function" && passwordField) setFieldError(passwordField, t('Mot_de_passe_8_caracteres'));
        isValid = false;
    }
    if (!confirmPasswordField || passwordField.value !== confirmPasswordField.value) {
        if (typeof setFieldError === "function" && confirmPasswordField) setFieldError(confirmPasswordField, t('Mots_de_passe_ne_correspondent_pas'));
        isValid = false;
    }

    if (!isValid) {
        if (typeof showGlobalMessage === "function") showGlobalMessage(t('Veuillez_corriger_les_erreurs_formulaire_inscription'), "error");
        return;
    }

    if (typeof showGlobalMessage === "function") showGlobalMessage(t('Creation_du_compte'), "info");
    try {
        const result = await makeApiRequest('/auth/register', 'POST', {
            email: emailField.value,
            password: passwordField.value,
            nom: nomField.value,
            prenom: prenomField.value
        });
        if (result.success) {
            if (typeof showGlobalMessage === "function") showGlobalMessage(result.message || t('Compte_cree_avec_succes_Veuillez_vous_connecter'), "success");
            form.reset();
            // Optionally switch to login view
            const loginForm = document.getElementById('login-form');
            const registerForm = document.getElementById('register-form');
            const newCustomerSection = document.getElementById('new-customer-section');
            if(loginForm) loginForm.style.display = 'block';
            if(registerForm) registerForm.style.display = 'none';
            if(newCustomerSection) newCustomerSection.style.display = 'block';


        } else {
            if (typeof showGlobalMessage === "function") showGlobalMessage(result.message || t('Erreur_lors_de_linscription'), "error");
            if (messageElement) messageElement.textContent = result.message || t('Erreur_lors_de_linscription');
        }
    } catch (error) {
        // Error message likely shown by makeApiRequest
        if (messageElement) messageElement.textContent = error.message || t('Erreur_serveur');
        console.error("Erreur d'inscription:", error);
    }
}

/**
 * Displays the B2C user account dashboard.
 * Hides login/register forms and shows user info and order history.
 */
function displayAccountDashboard() {
    const loginRegisterSection = document.getElementById('login-register-section');
    const accountDashboardSection = document.getElementById('account-dashboard-section');
    const currentUser = getCurrentUser();

    if (currentUser && loginRegisterSection && accountDashboardSection) {
        loginRegisterSection.style.display = 'none';
        accountDashboardSection.style.display = 'block';
        const dashboardUsername = document.getElementById('dashboard-username');
        const dashboardEmail = document.getElementById('dashboard-email');

        if (dashboardUsername) dashboardUsername.textContent = `${currentUser.prenom || ''} ${currentUser.nom || ''}`;
        if (dashboardEmail) dashboardEmail.textContent = currentUser.email;

        const logoutButton = document.getElementById('logout-button');
        if (logoutButton) {
            logoutButton.removeEventListener('click', logoutUser); // Avoid multiple listeners
            logoutButton.addEventListener('click', logoutUser);
        }
        if (typeof loadOrderHistory === "function") loadOrderHistory();
    } else if (loginRegisterSection) {
        loginRegisterSection.style.display = 'block';
        if (accountDashboardSection) accountDashboardSection.style.display = 'none';
    }
    // Translate static parts of the dashboard if they use data-translate-key
    if(window.translatePageElements) translatePageElements();
}

/**
 * Loads and displays the B2C user's order history.
 */
async function loadOrderHistory() {
    const orderHistoryContainer = document.getElementById('order-history-container');
    if (!orderHistoryContainer) return;

    const currentUser = getCurrentUser();
    if (!currentUser) {
        orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Veuillez_vous_connecter_pour_voir_votre_historique')}</p>`;
        return;
    }

    orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Chargement_de_lhistorique_des_commandes')}</p>`;
    try {
        const ordersData = await makeApiRequest('/orders/history', 'GET', null, true); // Requires auth
        if (ordersData.success && ordersData.orders) {
            if (ordersData.orders.length === 0) {
                orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Vous_navez_aucune_commande_pour_le_moment')}</p>`;
            } else {
                let html = '<ul class="space-y-4">';
                // Implement pagination here if ordersData.pagination exists
                // For now, displaying all returned orders
                ordersData.orders.forEach(order => {
                    const orderDate = new Date(order.order_date).toLocaleDateString(getCurrentLang() || 'fr-FR');
                    const statusText = t(order.status) || order.status; // Translate status if key exists
                    html += `
                        <li class="p-4 border border-brand-warm-taupe/50 rounded-md bg-white">
                            <div class="flex justify-between items-center mb-2">
                                <p class="font-semibold text-brand-near-black">${t('Commande_')} #${order.order_id}</p>
                                <span class="px-2 py-1 text-xs font-semibold rounded-full ${getOrderStatusClass(order.status)}">${statusText}</span>
                            </div>
                            <p class="text-sm"><strong>${t('Date')}:</strong> ${orderDate}</p>
                            <p class="text-sm"><strong>${t('Total')}:</strong> ${parseFloat(order.total_amount).toFixed(2)} €</p>
                            <button class="text-sm text-brand-classic-gold hover:underline mt-2" onclick="viewOrderDetail('${order.order_id}')" data-translate-key="Voir_details">${t('Voir_details')}</button>
                        </li>`;
                });
                html += '</ul>';
                // Add pagination controls here based on ordersData.pagination
                orderHistoryContainer.innerHTML = html;
            }
        } else {
            orderHistoryContainer.innerHTML = `<p class="text-sm text-red-600 italic">${ordersData.message || t('Impossible_de_charger_lhistorique_des_commandes')}</p>`;
        }
    } catch (error) {
        orderHistoryContainer.innerHTML = `<p class="text-sm text-red-600 italic">${t('Impossible_de_charger_lhistorique_des_commandes')} ${error.message}</p>`;
        console.error("Error loading order history:", error);
    }
}

/**
 * Placeholder for viewing order details (B2C).
 * @param {string|number} orderId - The ID of the order to view.
 */
function viewOrderDetail(orderId) {
    // This would typically navigate to a new page or open a modal with order details
    // For now, it shows a global message.
    if (typeof showGlobalMessage === "function" && typeof t === "function") {
        showGlobalMessage(`${t('Detail_commande_')} #${orderId} (${t('Fonctionnalite_a_implementer')}).`, 'info');
    }
    console.log("Voir détails pour commande B2C:", orderId);
}
