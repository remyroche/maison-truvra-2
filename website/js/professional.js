// website/js/professional.js

document.addEventListener('DOMContentLoaded', () => {
    // This check ensures professional.js logic only runs if specifically on 'page-professionnels'
    // and main.js will call initializeProfessionalPage()
});

// --- Password Strength Checker (Client-side feedback) ---
const PASSWORD_POLICY = {
    minLength: 10, // Keep in sync with backend (auth/routes.py)
    requireUppercase: true,
    requireLowercase: true,
    requireDigit: true,
    requireSpecial: true
};

function checkPasswordStrength(password) {
    let strength = 0;
    let messages = [];

    if (password.length >= PASSWORD_POLICY.minLength) strength++; else messages.push(t('Pro_MDP_Min_Longueur', {length: PASSWORD_POLICY.minLength}));
    if (PASSWORD_POLICY.requireUppercase && /[A-Z]/.test(password)) strength++; else if (PASSWORD_POLICY.requireUppercase) messages.push(t('Pro_MDP_Majuscule'));
    if (PASSWORD_POLICY.requireLowercase && /[a-z]/.test(password)) strength++; else if (PASSWORD_POLICY.requireLowercase) messages.push(t('Pro_MDP_Minuscule'));
    if (PASSWORD_POLICY.requireDigit && /\d/.test(password)) strength++; else if (PASSWORD_POLICY.requireDigit) messages.push(t('Pro_MDP_Chiffre'));
    if (PASSWORD_POLICY.requireSpecial && /[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++; else if (PASSWORD_POLICY.requireSpecial) messages.push(t('Pro_MDP_Special'));
    
    let strengthText = '';
    let strengthClass = '';

    if (strength < 3) {
        strengthText = t('Pro_MDP_Faible');
        strengthClass = 'strength-weak';
    } else if (strength < 5) {
        strengthText = t('Pro_MDP_Moyen');
        strengthClass = 'strength-medium';
    } else {
        strengthText = t('Pro_MDP_Fort');
        strengthClass = 'strength-strong';
    }
    
    if (password.length === 0) { // No feedback if field is empty
        return { text: '', class: '', messages: [], meetsPolicy: false };
    }
    
    const meetsPolicy = messages.length === 0; // Meets policy if no error messages
    return { text: strengthText, class: strengthClass, messages, meetsPolicy };
}

function displayPasswordStrength(passwordFieldId, strengthDisplayId) {
    const passwordInput = document.getElementById(passwordFieldId);
    const strengthDisplay = document.getElementById(strengthDisplayId);

    if (passwordInput && strengthDisplay) {
        passwordInput.addEventListener('input', () => {
            const password = passwordInput.value;
            const { text, class: strengthClass, messages } = checkPasswordStrength(password);
            strengthDisplay.textContent = text;
            strengthDisplay.className = `password-strength ${strengthClass}`;

            // Display detailed messages if any (optional)
            // For example, you could have another div to show the 'messages' array.
            // For now, the color/text indicates strength.
            // The form validation will show specific errors on submit.
        });
    }
}


async function initializeProfessionalPage() {
    const proLoginForm = document.getElementById('pro-login-form');
    const proRegisterForm = document.getElementById('pro-register-form');
    const proLogoutButton = document.getElementById('pro-logout-button');
    const proShowUpdateFormButton = document.getElementById('pro-show-update-form-button');
    const proUpdateAccountForm = document.getElementById('pro-update-account-form');
    const proCancelUpdateFormButton = document.getElementById('pro-cancel-update-form-button');

    // Forgot password elements
    const proForgotPasswordLink = document.getElementById('pro-forgot-password-link');
    const forgotPasswordModal = document.getElementById('forgot-password-modal');
    const proForgotPasswordForm = document.getElementById('pro-forgot-password-form');
    const proCancelForgotPassword = document.getElementById('pro-cancel-forgot-password');

    if (proLoginForm) proLoginForm.addEventListener('submit', handleProLogin);
    if (proRegisterForm) proRegisterForm.addEventListener('submit', handleProRegister);
    if (proLogoutButton) proLogoutButton.addEventListener('click', handleProLogout);

    if (proShowUpdateFormButton && proUpdateAccountForm) {
        proShowUpdateFormButton.addEventListener('click', () => {
            proUpdateAccountForm.style.display = 'block';
            proShowUpdateFormButton.style.display = 'none';
            populateProUpdateForm();
            // Initialize password strength checker for update form
            displayPasswordStrength('pro-update-new-password', 'pro-update-password-strength');
        });
    }
    if (proCancelUpdateFormButton && proUpdateAccountForm && proShowUpdateFormButton) {
        proCancelUpdateFormButton.addEventListener('click', () => {
            proUpdateAccountForm.style.display = 'none';
            if (typeof clearFormErrors === 'function') clearFormErrors(proUpdateAccountForm);
            document.getElementById('pro-update-password-strength').textContent = ''; // Clear strength message
            proShowUpdateFormButton.style.display = 'block';
        });
    }
    if (proUpdateAccountForm) proUpdateAccountForm.addEventListener('submit', handleProUpdateAccount);

    // Initialize password strength checker for registration form
    displayPasswordStrength('pro-register-password', 'pro-register-password-strength');


    // --- Forgot Password Modal Logic ---
    if (proForgotPasswordLink && forgotPasswordModal) {
        proForgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            forgotPasswordModal.style.display = 'flex';
            const emailInput = document.getElementById('pro-forgot-email');
            const messageElement = document.getElementById('pro-forgot-password-message');
            if(emailInput) emailInput.value = '';
            if(messageElement) {
                messageElement.textContent = '';
                messageElement.className = 'text-sm my-2 min-h-[1.25rem]'; // Reset class
            }
            if (proForgotPasswordForm && typeof clearFormErrors === 'function') clearFormErrors(proForgotPasswordForm);
        });
    }

    if (proCancelForgotPassword && forgotPasswordModal) {
        proCancelForgotPassword.addEventListener('click', () => {
            forgotPasswordModal.style.display = 'none';
        });
    }
    if (forgotPasswordModal) {
        forgotPasswordModal.addEventListener('click', function(event) {
            if (event.target === forgotPasswordModal) {
                forgotPasswordModal.style.display = 'none';
            }
        });
    }

    if (proForgotPasswordForm) {
        proForgotPasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const emailInput = document.getElementById('pro-forgot-email');
            const email = emailInput.value;
            const messageElement = document.getElementById('pro-forgot-password-message');
            messageElement.className = 'text-sm my-2 min-h-[1.25rem]';
            messageElement.textContent = '';
            if(typeof clearFormErrors === 'function') clearFormErrors(proForgotPasswordForm);

            if (!email || (typeof validateEmail === 'function' && !validateEmail(email))) {
                if(typeof setFieldError === 'function') setFieldError(emailInput, t('Veuillez_entrer_une_adresse_e-mail_valide'));
                return;
            }

            showGlobalMessage(t('Pro_Traitement_Demande_MDP'), 'info');
            try {
                // Backend /auth/forgot-password always returns success to prevent email enumeration.
                // The actual email sending is conditional on user existence.
                await makeApiRequest('/auth/forgot-password', 'POST', { email });
                showGlobalMessage(t('Pro_Email_Reinitialisation_Envoye_Info'), 'success', 10000);
                messageElement.textContent = t('Pro_Email_Reinitialisation_Envoye_Info_Modal');
                messageElement.classList.add('text-green-600');
                // Optionally hide the modal after a delay
                // setTimeout(() => { if (forgotPasswordModal) forgotPasswordModal.style.display = 'none'; }, 7000);
            } catch (error) { // Should ideally not be reached if backend always returns success for this route
                // This catch is more for network errors or unexpected issues with makeApiRequest
                showGlobalMessage(t('Erreur_serveur'), 'error');
                messageElement.textContent = error.message || t('Erreur_serveur');
                messageElement.classList.add('text-brand-truffle-burgundy');
            }
        });
    }
    // --- End Forgot Password Modal Logic ---

    checkProLoginState(); // This will also call displayProDashboard if logged in
    if(typeof translatePageElements === 'function') translatePageElements();
}

function checkProLoginState() {
    const currentUser = getCurrentUser(); // from auth.js
    const loggedOutView = document.getElementById('pro-logged-out-view');
    const dashboardView = document.getElementById('pro-dashboard-view');

    if (currentUser && currentUser.user_type === 'b2b') {
        if (loggedOutView) loggedOutView.style.display = 'none';
        if (dashboardView) dashboardView.style.display = 'block';
        displayProDashboard(currentUser); // Pass the full user object
    } else {
        if (loggedOutView) loggedOutView.style.display = 'block';
        if (dashboardView) dashboardView.style.display = 'none';
    }
}

async function handleProLogin(event) {
    event.preventDefault();
    const form = event.target;
    if(typeof clearFormErrors === 'function') clearFormErrors(form);
    const email = form.querySelector('#pro-login-email').value;
    const password = form.querySelector('#pro-login-password').value;
    const messageElement = document.getElementById('pro-login-message');
    messageElement.textContent = '';

    if (!email || !password) {
        messageElement.textContent = t('Email_et_mot_de_passe_requis');
        return;
    }
    showGlobalMessage(t('Connexion_en_cours'), 'info');
    try {
        const result = await makeApiRequest('/auth/login', 'POST', { email, password });
        if (result.success && result.user) {
            if (result.user.user_type === 'b2b') {
                if (result.user.status === 'active') {
                    setCurrentUser(result.user, result.token); // Store full user object
                    showGlobalMessage(t('Connexion_reussie'), 'success');
                    checkProLoginState(); // This will call displayProDashboard
                } else if (result.user.status === 'pending_approval') {
                    messageElement.textContent = t('Pro_Compte_En_Attente_Approbation');
                    showGlobalMessage(t('Pro_Compte_En_Attente_Approbation_Long'), 'warning', 7000);
                    setCurrentUser(null); // Clear any previous session
                } else if (result.user.status === 'suspended') {
                     messageElement.textContent = t('Pro_Compte_Suspendu');
                    showGlobalMessage(t('Pro_Compte_Suspendu_Long'), 'error', 7000);
                    setCurrentUser(null);
                } else { // Other statuses or unexpected
                    messageElement.textContent = t('Pro_Compte_Statut_Inconnu');
                    showGlobalMessage(t('Pro_Compte_Statut_Inconnu_Long'), 'error');
                    setCurrentUser(null);
                }
            } else { // Not a B2B user
                messageElement.textContent = t('Pro_Compte_non_professionnel');
                showGlobalMessage(t('Pro_Compte_non_professionnel_long'), 'error');
                setCurrentUser(null);
            }
        } else { // Login failed (e.g., wrong credentials, server error from API)
            messageElement.textContent = result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants');
            showGlobalMessage(result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants'), 'error');
        }
    } catch (error) { // Network error or issue with makeApiRequest
        messageElement.textContent = error.message || t('Erreur_de_connexion_au_serveur');
        showGlobalMessage(error.message || t('Erreur_de_connexion_au_serveur'), 'error');
    }
}

async function handleProRegister(event) {
    event.preventDefault();
    const form = event.target;
    if(typeof clearFormErrors === 'function') clearFormErrors(form);
    const messageElement = document.getElementById('pro-register-message');
    messageElement.textContent = '';

    const company_name = form.querySelector('#pro-register-company-name').value;
    const prenom = form.querySelector('#pro-register-prenom').value;
    const nom = form.querySelector('#pro-register-nom').value;
    const email = form.querySelector('#pro-register-email').value;
    const phone_number = form.querySelector('#pro-register-phone').value;
    const password = form.querySelector('#pro-register-password').value;
    const confirm_password = form.querySelector('#pro-register-confirm-password').value;

    let isValid = true;
    if (!company_name) { if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-register-company-name'), t('Nom_entreprise_requis')); isValid = false; }
    if (!prenom) { if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-register-prenom'), t('Prenom_contact_requis')); isValid = false; }
    if (!nom) { if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-register-nom'), t('Nom_contact_requis')); isValid = false; }
    if (!email || (typeof validateEmail === 'function' && !validateEmail(email))) { if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-register-email'), t('E-mail_invalide')); isValid = false; }
    
    const { meetsPolicy, messages: strengthMessages } = checkPasswordStrength(password);
    if (!meetsPolicy) {
        if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-register-password'), strengthMessages.join(' '));
        isValid = false;
    }
    if (password !== confirm_password) { if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-register-confirm-password'), t('Mots_de_passe_ne_correspondent_pas')); isValid = false; }

    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire'), "error");
        return;
    }

    showGlobalMessage(t('Creation_compte_pro_en_cours'), 'info');
    try {
        const result = await makeApiRequest('/auth/register-professional', 'POST', {
            email, password, company_name, nom, prenom, phone_number
        });
        if (result.success) {
            // Backend now sends "Compte professionnel créé. Il est en attente d'approbation..."
            showGlobalMessage(result.message || t('Compte_professionnel_cree_attente_approbation'), 'success', 10000);
            form.reset();
            document.getElementById('pro-register-password-strength').textContent = ''; // Clear strength message
        } else {
            messageElement.textContent = result.message || t('Erreur_creation_compte_pro');
            showGlobalMessage(result.message || t('Erreur_creation_compte_pro'), 'error');
        }
    } catch (error) {
        messageElement.textContent = error.message || t('Erreur_serveur');
        showGlobalMessage(error.message || t('Erreur_serveur'), 'error');
    }
}

function handleProLogout() {
    // Optimistic UI update: clear dashboard immediately
    const loggedOutView = document.getElementById('pro-logged-out-view');
    const dashboardView = document.getElementById('pro-dashboard-view');
    if (loggedOutView) loggedOutView.style.display = 'block';
    if (dashboardView) dashboardView.style.display = 'none';
    
    setCurrentUser(null); // Clears from localStorage and updates auth state
    showGlobalMessage(t('Deconnecte_message'), 'info');
    // No need to call checkProLoginState() again if UI is already updated.
    // If there were backend calls for logout, handle their success/failure.
    // For JWT, logout is client-side (token removal).
}

function displayProDashboard(userData) {
    document.getElementById('pro-dashboard-company-name').textContent = userData.company_name || 'N/A';
    document.getElementById('pro-dashboard-contact-name').textContent = `${userData.prenom || ''} ${userData.nom || ''}`.trim() || 'N/A';
    document.getElementById('pro-dashboard-email').textContent = userData.email || 'N/A';
    document.getElementById('pro-dashboard-phone').textContent = userData.phone_number || 'N/A';
    
    const statusElement = document.getElementById('pro-dashboard-status');
    let statusText = userData.status || 'N/A';
    if (userData.status === 'pending_approval') statusText = t('Pro_Statut_En_Attente');
    else if (userData.status === 'active') statusText = t('Pro_Statut_Actif');
    else if (userData.status === 'suspended') statusText = t('Pro_Statut_Suspendu');
    statusElement.textContent = statusText;
    statusElement.className = `font-semibold status-${(userData.status || 'unknown').replace('_', '-')}`;


    fetchProInvoices();
}

function populateProUpdateForm() {
    const currentUser = getCurrentUser();
    if (!currentUser || currentUser.user_type !== 'b2b') return;

    document.getElementById('pro-update-company-name').value = currentUser.company_name || '';
    document.getElementById('pro-update-prenom').value = currentUser.prenom || '';
    document.getElementById('pro-update-nom').value = currentUser.nom || '';
    document.getElementById('pro-update-email').value = currentUser.email || ''; // Email update might need re-verification
    document.getElementById('pro-update-phone').value = currentUser.phone_number || '';
    document.getElementById('pro-update-current-password').value = '';
    document.getElementById('pro-update-new-password').value = '';
    document.getElementById('pro-update-confirm-password').value = '';
    document.getElementById('pro-update-password-strength').textContent = ''; // Clear strength message
}


async function handleProUpdateAccount(event) {
    event.preventDefault();
    const form = event.target;
    if(typeof clearFormErrors === 'function') clearFormErrors(form);
    const messageElement = document.getElementById('pro-update-message');
    messageElement.textContent = '';

    const updateData = {
        company_name: form.querySelector('#pro-update-company-name').value,
        prenom: form.querySelector('#pro-update-prenom').value,
        nom: form.querySelector('#pro-update-nom').value,
        email: form.querySelector('#pro-update-email').value,
        phone_number: form.querySelector('#pro-update-phone').value,
    };

    const currentPassword = form.querySelector('#pro-update-current-password').value;
    const newPassword = form.querySelector('#pro-update-new-password').value;
    const confirmPassword = form.querySelector('#pro-update-confirm-password').value;

    let isValid = true;
    if (newPassword) { // Only validate new password if provided
        const { meetsPolicy, messages: strengthMessages } = checkPasswordStrength(newPassword);
        if (!meetsPolicy) {
            if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-update-new-password'), strengthMessages.join(' '));
            isValid = false;
        }
        if (newPassword !== confirmPassword) {
            if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-update-confirm-password'), t('Mots_de_passe_ne_correspondent_pas'));
            isValid = false;
        }
        if (!currentPassword) { // Current password is required if new password is set
            if(typeof setFieldError === 'function') setFieldError(form.querySelector('#pro-update-current-password'), t('Pro_Mot_de_passe_actuel_requis_pour_changement'));
            isValid = false;
        }
    }
    if (!isValid) return;


    if (currentPassword && newPassword) { // Only include passwords if current one is provided for change
        updateData.current_password = currentPassword;
        updateData.new_password = newPassword;
    }
    
    // Filter out unchanged fields before sending (optional, backend can handle this too)
    const currentUser = getCurrentUser();
    const finalUpdateData = {};
    let hasChanges = false;
    for (const key in updateData) {
        if (key === 'current_password' || key === 'new_password') { // Always send password fields if present
             if (updateData[key]) { // Only if not empty
                finalUpdateData[key] = updateData[key];
                hasChanges = true;
             }
        } else if (updateData[key] !== (currentUser[key] || '')) { // Compare against current user data
            finalUpdateData[key] = updateData[key];
            hasChanges = true;
        }
    }
    
    if (!hasChanges && !(currentPassword && newPassword)) {
        messageElement.textContent = t('Pro_Aucun_changement_detecte');
        return;
    }

    // Optimistic UI: Prepare new user data for potential immediate update
    const optimisticUserData = { ...currentUser, ...finalUpdateData };
    delete optimisticUserData.current_password; // Don't store these in frontend
    delete optimisticUserData.new_password;

    showGlobalMessage(t('Pro_Mise_a_jour_en_cours'), 'info');
    try {
        const result = await makeApiRequest('/professional/account', 'PUT', finalUpdateData, true); // true for authenticated
        if (result.success && result.user) {
            showGlobalMessage(t('Pro_Compte_mis_a_jour_succes'), 'success');
            setCurrentUser(result.user, getAuthToken()); // Update with fresh data from server
            displayProDashboard(result.user); // Refresh dashboard with server data
            
            form.style.display = 'none';
            if(typeof clearFormErrors === 'function') clearFormErrors(form);
            document.getElementById('pro-show-update-form-button').style.display = 'block';
            form.querySelector('#pro-update-current-password').value = '';
            form.querySelector('#pro-update-new-password').value = '';
            form.querySelector('#pro-update-confirm-password').value = '';
            document.getElementById('pro-update-password-strength').textContent = '';
        } else {
            messageElement.textContent = result.message || t('Pro_Erreur_mise_a_jour_compte');
            showGlobalMessage(result.message || t('Pro_Erreur_mise_a_jour_compte'), 'error');
            // No optimistic revert here as the form stays open for correction.
        }
    } catch (error) {
        messageElement.textContent = error.message || t('Erreur_serveur');
        showGlobalMessage(error.message || t('Erreur_serveur'), 'error');
        // Could revert optimistic update here if one was made and form was hidden.
    }
}


async function fetchProInvoices() {
    const container = document.getElementById('pro-invoices-list-container');
    container.innerHTML = `<p class="text-brand-warm-taupe italic">${t('Pro_Chargement_Factures')}</p>`;
    try {
        const result = await makeApiRequest('/professional/invoices', 'GET', null, true); // Authenticated
        if (result.success && result.invoices) {
            if (result.invoices.length === 0) {
                container.innerHTML = `<p class="text-brand-warm-taupe italic" data-translate-key="Pro_Aucune_facture">${t('Pro_Aucune_facture')}</p>`;
                return;
            }
            let html = '<ul class="space-y-3">';
            result.invoices.forEach(invoice => {
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString(getCurrentLang() || 'fr-FR');
                // Backend now provides file_path, not full download_url for B2B list.
                // Construct download URL using API_BASE_URL and the specific download endpoint.
                const downloadUrl = `${API_BASE_URL}/professional/invoices/${invoice.invoice_id}/download`;

                // Determine status text and class
                let statusText = invoice.status || 'pending';
                let statusClass = `invoice-status-${statusText.replace('_', '-')}`;
                if (statusText === 'pending') statusText = t('Pro_Facture_Statut_EnAttente');
                else if (statusText === 'paid') statusText = t('Pro_Facture_Statut_Payee');
                else if (statusText === 'overdue') statusText = t('Pro_Facture_Statut_EnRetard');
                else if (statusText === 'cancelled') statusText = t('Pro_Facture_Statut_Annulee');


                html += `
                    <li class="p-3 border border-brand-warm-taupe/30 rounded-md flex justify-between items-center">
                        <div>
                            <span class="font-semibold text-brand-near-black">${invoice.invoice_number}</span>
                            <span class="text-xs text-brand-warm-taupe ml-2">(${invoiceDate})</span>
                            <span class="invoice-status-badge ${statusClass} ml-3">${statusText}</span>
                        </div>
                        <div class="flex items-center">
                            <span class="text-brand-earth-brown mr-4">${parseFloat(invoice.total_amount_ttc).toFixed(2)} €</span>
                            ${invoice.file_path ? `
                            <a href="${downloadUrl}" 
                               target="_blank" 
                               class="btn-secondary text-xs py-1 px-2" data-translate-key="Telecharger">
                                ${t('Telecharger')}
                            </a>` : '<span class="text-xs text-gray-400 italic">PDF N/A</span>'}
                        </div>
                    </li>
                `;
            });
            html += '</ul>';
            container.innerHTML = html;
        } else {
            container.innerHTML = `<p class="text-red-500 italic">${result.message || t('Pro_Erreur_chargement_factures')}</p>`;
        }
    } catch (error) {
        container.innerHTML = `<p class="text-red-500 italic">${t('Pro_Erreur_chargement_factures')}: ${error.message}</p>`;
    }
}

// Make sure this function is globally accessible if called from main.js
window.initializeProfessionalPage = initializeProfessionalPage;
