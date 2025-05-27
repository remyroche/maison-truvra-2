// website/js/auth.js
// Handles user authentication, session management, and account display.

/**
 * Retrieves the authentication token from session storage.
 * @returns {string|null} The auth token or null if not found.
 */
function getAuthToken() {
    return sessionStorage.getItem('authToken');
}

/**
 * Sets or removes the authentication token in session storage.
 * @param {string|null} token - The token to set, or null to remove.
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
 * @returns {object|null} The user object or null if not found/invalid.
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
 * Sets the current user data in session storage and updates login state.
 * @param {object|null} userData - The user data object, or null to clear.
 * @param {string|null} [token=null] - The auth token, if setting a new user.
 */
function setCurrentUser(userData, token = null) {
    if (userData) {
        sessionStorage.setItem('currentUser', JSON.stringify(userData));
        if (token) setAuthToken(token);
    } else {
        sessionStorage.removeItem('currentUser');
        sessionStorage.removeItem('authToken');
    }
    updateLoginState();
    if (typeof updateCartCountDisplay === 'function') updateCartCountDisplay();
}

/**
 * Logs out the current user.
 */
async function logoutUser() {
    setCurrentUser(null);
    showGlobalMessage(t('Deconnecte_message'), "info"); // i18n

    if (document.body.id === 'page-compte' || document.body.id === 'page-paiement') {
        window.location.href = 'compte.html';
    } else {
        updateLoginState();
        if (document.body.id === 'page-compte') displayAccountDashboard();
    }
}

/**
 * Updates the UI elements (account links) based on the current login state.
 */
function updateLoginState() {
    const currentUser = getCurrentUser();
    const accountLinkTextDesktop = document.getElementById('account-link-text-desktop');
    const accountLinkTextMobile = document.getElementById('account-link-text-mobile'); // Assuming you added this ID

    // Fallback to querySelector if specific IDs aren't present (e.g. if header.html wasn't updated)
    const accountLinkDesktopContainer = document.querySelector('header nav a[href="compte.html"]');
    const accountLinkMobileContainer = document.querySelector('#mobile-menu-dropdown a[href="compte.html"]');


    const desktopTextElement = accountLinkTextDesktop || (accountLinkDesktopContainer ? accountLinkDesktopContainer.querySelector('span') : null);
    const mobileTextElement = accountLinkTextMobile || accountLinkMobileContainer;


    if (currentUser) {
        const userName = currentUser.prenom || t('Compte'); // i18n for "Compte"
        if (desktopTextElement) {
            desktopTextElement.textContent = userName;
            // Ensure SVG is present if we are only updating text of a span
            if (accountLinkDesktopContainer && !accountLinkDesktopContainer.querySelector('svg')) {
                 accountLinkDesktopContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7 text-brand-classic-gold"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> <span class="ml-1 text-xs">${userName}</span>`;
            }
        }
        if (mobileTextElement) mobileTextElement.textContent = `${t('Mon_Compte_Menu')} (${userName})`; // i18n
    } else {
        if (desktopTextElement) {
            desktopTextElement.textContent = t('Mon_Compte_Menu'); // i18n
             if (accountLinkDesktopContainer && !accountLinkDesktopContainer.querySelector('svg')) {
                 accountLinkDesktopContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> <span class="ml-1 text-xs">${t('Mon_Compte_Menu')}</span>`;
            }
        }
        if (mobileTextElement) mobileTextElement.textContent = t('Mon_Compte_Menu'); // i18n
    }
}


/**
 * Handles the login form submission.
 */
async function handleLogin(event) {
    event.preventDefault();
    const loginForm = event.target;
    clearFormErrors(loginForm);
    const emailField = loginForm.querySelector('#login-email');
    const passwordField = loginForm.querySelector('#login-password');
    const email = emailField.value;
    const password = passwordField.value;
    const loginMessageElement = document.getElementById('login-message');

    let isValid = true;
    if (loginMessageElement) loginMessageElement.textContent = '';

    if (!email || !validateEmail(email)) {
        setFieldError(emailField, t('Veuillez_entrer_une_adresse_e-mail_valide')); // i18n
        isValid = false;
    }
    if (!password) {
        setFieldError(passwordField, t('Veuillez_entrer_votre_mot_de_passe')); // i18n
        isValid = false;
    }
    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire'), "error"); // i18n
        return;
    }

    showGlobalMessage(t('Connexion_en_cours'), "info", 60000); // i18n

    try {
        const result = await makeApiRequest('/auth/login', 'POST', { email, password }); // makeApiRequest sends lang
        if (result.success && result.user && result.token) {
            setCurrentUser(result.user, result.token);
            showGlobalMessage(result.message || t('Connexion_reussie'), "success"); // i18n "Connexion_reussie"
            loginForm.reset();
            displayAccountDashboard();
        } else {
            setCurrentUser(null);
            const generalErrorMessage = result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants'); // i18n
            showGlobalMessage(generalErrorMessage, "error");
            if (loginMessageElement) loginMessageElement.textContent = generalErrorMessage;
            setFieldError(emailField, " ");
            setFieldError(passwordField, generalErrorMessage);
        }
    } catch (error) {
        setCurrentUser(null);
        if (loginMessageElement) loginMessageElement.textContent = error.message || t('Erreur_de_connexion_au_serveur'); // i18n
    }
}

/**
 * Handles the registration form submission.
 */
async function handleRegistrationForm(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);

    const emailField = form.querySelector('#register-email');
    const passwordField = form.querySelector('#register-password');
    const confirmPasswordField = form.querySelector('#register-confirm-password');
    const nomField = form.querySelector('#register-nom');
    const prenomField = form.querySelector('#register-prenom');

    let isValid = true;

    if (!emailField.value || !validateEmail(emailField.value)) {
        setFieldError(emailField, t('E-mail_invalide')); isValid = false; // i18n
    }
    if (!nomField.value.trim()) {
        setFieldError(nomField, t('Nom_requis')); isValid = false; // i18n
    }
    if (!prenomField.value.trim()) {
        setFieldError(prenomField, t('Prenom_requis')); isValid = false; // i18n
    }
    if (passwordField.value.length < 8) {
        setFieldError(passwordField, t('Mot_de_passe_8_caracteres')); isValid = false; // i18n + add key
    }
    if (passwordField.value !== confirmPasswordField.value) {
        setFieldError(confirmPasswordField, t('Mots_de_passe_ne_correspondent_pas')); isValid = false; // i18n + add key
    }

    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_formulaire_inscription'), "error"); // i18n + add key
        return;
    }

    showGlobalMessage(t('Creation_du_compte'), "info"); // i18n + add key
    try {
        const result = await makeApiRequest('/auth/register', 'POST', {
            email: emailField.value, password: passwordField.value,
            nom: nomField.value, prenom: prenomField.value
        });
        if (result.success) {
            showGlobalMessage(result.message || t('Compte_cree_avec_succes_Veuillez_vous_connecter'), "success"); // i18n
            form.reset();
        } else {
            showGlobalMessage(result.message || t('Erreur_lors_de_linscription'), "error"); // i18n
        }
    } catch (error) {
        // Error message shown by makeApiRequest
        console.error("Erreur d'inscription:", error);
    }
}

/**
 * Displays the account dashboard.
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
        if(dashboardUsername) dashboardUsername.textContent = `${currentUser.prenom || ''} ${currentUser.nom || ''}`;
        if(dashboardEmail) dashboardEmail.textContent = currentUser.email;

        const logoutButton = document.getElementById('logout-button');
        if (logoutButton) {
            logoutButton.removeEventListener('click', logoutUser);
            logoutButton.addEventListener('click', logoutUser);
        }
        loadOrderHistory();
    } else if (loginRegisterSection) {
        loginRegisterSection.style.display = 'block';
        if (accountDashboardSection) accountDashboardSection.style.display = 'none';
    }
    // Translate static parts of the dashboard if not done by translatePageElements on load
    if(window.translatePageElements) translatePageElements();
}

/**
 * Loads and displays the user's order history.
 */
async function loadOrderHistory() {
    const orderHistoryContainer = document.getElementById('order-history-container');
    if (!orderHistoryContainer) return;

    const currentUser = getCurrentUser();
    if (!currentUser) {
        orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Veuillez_vous_connecter_pour_voir_votre_historique')}</p>`; // i18n
        return;
    }

    orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Chargement_de_lhistorique_des_commandes')}</p>`; // i18n
    try {
        const ordersData = await makeApiRequest('/orders/history', 'GET', null, true); // makeApiRequest sends lang

        if (ordersData.success && ordersData.orders.length > 0) {
            let html = '<ul class="space-y-4">';
            ordersData.orders.forEach(order => {
                // Assuming order.status is a key that can be translated if needed, or backend sends localized status
                html += `
                    <li class="p-4 border border-brand-warm-taupe/50 rounded-md bg-white">
                        <div class="flex justify-between items-center mb-2">
                            <p class="font-semibold text-brand-near-black">${t('Commande_')} #${order.order_id || order.id}</p>
                            <span class="px-2 py-1 text-xs font-semibold rounded-full ${getOrderStatusClass(order.status)}">${t(order.status) || order.status}</span>
                        </div>
                        <p class="text-sm"><strong>${t('Date')}:</strong> ${new Date(order.order_date).toLocaleDateString(getCurrentLang())}</p>
                        <p class="text-sm"><strong>${t('Total')}:</strong> ${parseFloat(order.total_amount).toFixed(2)} €</p>
                        <button class="text-sm text-brand-classic-gold hover:underline mt-2" onclick="viewOrderDetail('${order.order_id || order.id}')" data-translate-key="Voir_details">${t('Voir_details')}</button>
                    </li>
                `; // Add Commande_, Date, Total, Voir_details to locales
            });
            html += '</ul>';
            orderHistoryContainer.innerHTML = html;
        } else {
            orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Vous_navez_aucune_commande_pour_le_moment')}</p>`; // i18n
        }
    } catch (error) {
        orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-truffle-burgundy italic">${t('Impossible_de_charger_lhistorique_des_commandes')} ${error.message}</p>`; // i18n
    }
}

/**
 * Placeholder function to view order details.
 * @param {string} orderId - The ID of the order.
 */
function viewOrderDetail(orderId) {
    showGlobalMessage(`${t('Detail_commande_')} #${orderId} (${t('Fonctionnalite_a_implementer')}).`, 'info'); // i18n
    console.log("Voir détails pour commande:", orderId);
}
