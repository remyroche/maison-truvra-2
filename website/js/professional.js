// website/js/professional.js

document.addEventListener('DOMContentLoaded', () => {
    // This check ensures professional.js logic only runs if specifically on 'page-professionnels'
    // and main.js will call initializeProfessionalPage()
});

async function initializeProfessionalPage() {
    const proLoginForm = document.getElementById('pro-login-form');
    const proRegisterForm = document.getElementById('pro-register-form');
    const proLogoutButton = document.getElementById('pro-logout-button');
    const proShowUpdateFormButton = document.getElementById('pro-show-update-form-button');
    const proUpdateAccountForm = document.getElementById('pro-update-account-form');// website/js/professional.js

document.addEventListener('DOMContentLoaded', () => {
    // This check ensures professional.js logic only runs if specifically on 'page-professionnels'
    // and main.js will call initializeProfessionalPage()
});

async function initializeProfessionalPage() {
    const proLoginForm = document.getElementById('pro-login-form');
    const proRegisterForm = document.getElementById('pro-register-form');
    const proLogoutButton = document.getElementById('pro-logout-button');
    const proShowUpdateFormButton = document.getElementById('pro-show-update-form-button');
    const proUpdateAccountForm = document.getElementById('pro-update-account-form');
    const proCancelUpdateFormButton = document.getElementById('pro-cancel-update-form-button');

    // Forgot password elements
    const proForgotPasswordLink = document.getElementById('pro-forgot-password-link');
    const forgotPasswordModal = document.getElementById('forgot-password-modal'); // Assuming this ID for the modal
    const proForgotPasswordForm = document.getElementById('pro-forgot-password-form'); // Assuming this ID for the form inside modal
    const proCancelForgotPassword = document.getElementById('pro-cancel-forgot-password'); // Button to close modal

    if (proLoginForm) proLoginForm.addEventListener('submit', handleProLogin);
    if (proRegisterForm) proRegisterForm.addEventListener('submit', handleProRegister);
    if (proLogoutButton) proLogoutButton.addEventListener('click', handleProLogout);

    if (proShowUpdateFormButton && proUpdateAccountForm) {
        proShowUpdateFormButton.addEventListener('click', () => {
            proUpdateAccountForm.style.display = 'block';
            proShowUpdateFormButton.style.display = 'none';
            populateProUpdateForm();
        });
    }
    if (proCancelUpdateFormButton && proUpdateAccountForm && proShowUpdateFormButton) {
        proCancelUpdateFormButton.addEventListener('click', () => {
            proUpdateAccountForm.style.display = 'none';
            if (typeof clearFormErrors === 'function') clearFormErrors(proUpdateAccountForm);
            proShowUpdateFormButton.style.display = 'block';
        });
    }
    if (proUpdateAccountForm) proUpdateAccountForm.addEventListener('submit', handleProUpdateAccount);

    // --- Forgot Password Modal Logic ---
    if (proForgotPasswordLink && forgotPasswordModal) {
        proForgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            forgotPasswordModal.style.display = 'flex'; // Show modal
            const emailInput = document.getElementById('pro-forgot-email');
            const messageElement = document.getElementById('pro-forgot-password-message');
            if(emailInput) emailInput.value = '';
            if(messageElement) messageElement.textContent = '';
            if (proForgotPasswordForm && typeof clearFormErrors === 'function') clearFormErrors(proForgotPasswordForm);
        });
    }

    if (proCancelForgotPassword && forgotPasswordModal) {
        proCancelForgotPassword.addEventListener('click', () => {
            forgotPasswordModal.style.display = 'none';
        });
    }
    // Close modal if overlay is clicked
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
            messageElement.className = 'text-sm my-2'; // Reset class
            messageElement.textContent = '';
            if(typeof clearFormErrors === 'function') clearFormErrors(proForgotPasswordForm);

            if (!email || !validateEmail(email)) { // validateEmail from ui.js
                if(typeof setFieldError === 'function') setFieldError(emailInput, t('Veuillez_entrer_une_adresse_e-mail_valide'));
                return;
            }

            showGlobalMessage(t('Pro_Traitement_Demande_MDP'), 'info');
            try {
                const result = await makeApiRequest('/auth/forgot-password', 'POST', { email });
                // The backend now always returns success: true for forgot-password to prevent email enumeration
                // So we just display the generic "check your email" message.
                showGlobalMessage(t('Pro_Email_Reinitialisation_Envoye_Info'), 'success', 10000);
                messageElement.textContent = t('Pro_Email_Reinitialisation_Envoye_Info_Modal');
                messageElement.classList.add('text-green-600');
                // Optionally hide the modal after a delay
                // setTimeout(() => { if (forgotPasswordModal) forgotPasswordModal.style.display = 'none'; }, 7000);

            } catch (error) { // Should ideally not be reached if backend always returns success for this route
                showGlobalMessage(t('Erreur_serveur'), 'error');
                messageElement.textContent = error.message || t('Erreur_serveur');
                messageElement.classList.add('text-brand-truffle-burgundy');
            }
        });
    }
    // --- End Forgot Password Modal Logic ---

    checkProLoginState();
    if(typeof translatePageElements === 'function') translatePageElements();
}

function checkProLoginState() {
    const currentUser = getCurrentUser(); // from auth.js
    const loggedOutView = document.getElementById('pro-logged-out-view');
    const dashboardView = document.getElementById('pro-dashboard-view');

    if (currentUser && currentUser.user_type === 'b2b') {
        if (loggedOutView) loggedOutView.style.display = 'none';
        if (dashboardView) dashboardView.style.display = 'block';
        displayProDashboard(currentUser);
    } else {
        if (loggedOutView) loggedOutView.style.display = 'block'; // Or 'grid' based on your layout
        if (dashboardView) dashboardView.style.display = 'none';
    }
}

async function handleProLogin(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);
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
        if (result.success && result.user && result.user.user_type === 'b2b') {
            setCurrentUser(result.user, result.token);
            showGlobalMessage(t('Connexion_reussie'), 'success');
            checkProLoginState();
        } else if (result.success && result.user && result.user.user_type !== 'b2b') {
            messageElement.textContent = t('Pro_Compte_non_professionnel');
            showGlobalMessage(t('Pro_Compte_non_professionnel_long'), 'error');
            setCurrentUser(null);
        }
        else {
            messageElement.textContent = result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants');
            showGlobalMessage(result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants'), 'error');
        }
    } catch (error) {
        messageElement.textContent = error.message || t('Erreur_de_connexion_au_serveur');
        showGlobalMessage(error.message || t('Erreur_de_connexion_au_serveur'), 'error');
    }
}

async function handleProRegister(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);
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
    if (!company_name) { setFieldError(form.querySelector('#pro-register-company-name'), t('Nom_entreprise_requis')); isValid = false; }
    if (!prenom) { setFieldError(form.querySelector('#pro-register-prenom'), t('Prenom_contact_requis')); isValid = false; }
    if (!nom) { setFieldError(form.querySelector('#pro-register-nom'), t('Nom_contact_requis')); isValid = false; }
    if (!email || !validateEmail(email)) { setFieldError(form.querySelector('#pro-register-email'), t('E-mail_invalide')); isValid = false; }
    if (password.length < 8) { setFieldError(form.querySelector('#pro-register-password'), t('Mot_de_passe_8_caracteres')); isValid = false; }
    if (password !== confirm_password) { setFieldError(form.querySelector('#pro-register-confirm-password'), t('Mots_de_passe_ne_correspondent_pas')); isValid = false; }

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
            showGlobalMessage(result.message || t('Compte_professionnel_cree_succes'), 'success');
            form.reset();
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
    setCurrentUser(null);
    showGlobalMessage(t('Deconnecte_message'), 'info');
    checkProLoginState();
}

function displayProDashboard(userData) {
    document.getElementById('pro-dashboard-company-name').textContent = userData.company_name || 'N/A';
    document.getElementById('pro-dashboard-contact-name').textContent = `${userData.prenom || ''} ${userData.nom || ''}`.trim() || 'N/A';
    document.getElementById('pro-dashboard-email').textContent = userData.email || 'N/A';
    document.getElementById('pro-dashboard-phone').textContent = userData.phone_number || 'N/A';
    fetchProInvoices();
}

function populateProUpdateForm() {
    const currentUser = getCurrentUser();
    if (!currentUser || currentUser.user_type !== 'b2b') return;

    document.getElementById('pro-update-company-name').value = currentUser.company_name || '';
    document.getElementById('pro-update-prenom').value = currentUser.prenom || '';
    document.getElementById('pro-update-nom').value = currentUser.nom || '';
    document.getElementById('pro-update-email').value = currentUser.email || '';
    document.getElementById('pro-update-phone').value = currentUser.phone_number || '';
    document.getElementById('pro-update-current-password').value = '';
    document.getElementById('pro-update-new-password').value = '';
    document.getElementById('pro-update-confirm-password').value = '';
}


async function handleProUpdateAccount(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);
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

    if (newPassword) {
        if (newPassword.length < 8) {
            setFieldError(form.querySelector('#pro-update-new-password'), t('Mot_de_passe_8_caracteres')); return;
        }
        if (newPassword !== confirmPassword) {
            setFieldError(form.querySelector('#pro-update-confirm-password'), t('Mots_de_passe_ne_correspondent_pas')); return;
        }
        if (!currentPassword && newPassword) { // Require current password only if attempting to change password
            setFieldError(form.querySelector('#pro-update-current-password'), t('Pro_Mot_de_passe_actuel_requis_pour_changement')); return;
        }
        if (currentPassword) updateData.current_password = currentPassword; // Send only if provided
        updateData.new_password = newPassword;
    }
    
    const finalUpdateData = {};
    for (const key in updateData) {
        if (updateData[key] !== null && updateData[key] !== undefined) { 
             if (typeof updateData[key] === 'string' && updateData[key].trim() === '' && key !== 'phone_number') continue; // Don't send empty strings except for phone
            finalUpdateData[key] = updateData[key];
        }
    }
    if (Object.keys(finalUpdateData).length === 0 ) { // Check if any data to update
        messageElement.textContent = t('Pro_Aucun_changement_detecte');
        return;
    }


    showGlobalMessage(t('Pro_Mise_a_jour_en_cours'), 'info');
    try {
        const result = await makeApiRequest('/professional/account', 'PUT', finalUpdateData, true);
        if (result.success) {
            showGlobalMessage(t('Pro_Compte_mis_a_jour_succes'), 'success');
            setCurrentUser(result.user, getAuthToken());
            displayProDashboard(result.user);
            form.style.display = 'none';
            clearFormErrors(form);
            document.getElementById('pro-show-update-form-button').style.display = 'block';
            form.querySelector('#pro-update-current-password').value = '';
            form.querySelector('#pro-update-new-password').value = '';
            form.querySelector('#pro-update-confirm-password').value = '';

        } else {
            messageElement.textContent = result.message || t('Pro_Erreur_mise_a_jour_compte');
            showGlobalMessage(result.message || t('Pro_Erreur_mise_a_jour_compte'), 'error');
        }
    } catch (error) {
        messageElement.textContent = error.message || t('Erreur_serveur');
        showGlobalMessage(error.message || t('Erreur_serveur'), 'error');
    }
}


async function fetchProInvoices() {
    const container = document.getElementById('pro-invoices-list-container');
    container.innerHTML = `<p class="text-brand-warm-taupe italic">${t('Pro_Chargement_Factures')}</p>`;
    try {
        const result = await makeApiRequest('/professional/invoices', 'GET', null, true);
        if (result.success && result.invoices) {
            if (result.invoices.length === 0) {
                container.innerHTML = `<p class="text-brand-warm-taupe italic" data-translate-key="Pro_Aucune_facture">${t('Pro_Aucune_facture')}</p>`;
                return;
            }
            let html = '<ul class="space-y-3">';
            result.invoices.forEach(invoice => {
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString(getCurrentLang() || 'fr-FR');
                // The download_url is already constructed by the backend and includes the necessary API base
                const downloadUrl = `${API_BASE_URL}/professional/invoices/${invoice.invoice_id}/download`; // Construct full URL

                html += `
                    <li class="p-3 border border-brand-warm-taupe/30 rounded-md flex justify-between items-center">
                        <div>
                            <span class="font-semibold text-brand-near-black">${invoice.invoice_number}</span>
                            <span class="text-xs text-brand-warm-taupe ml-2">(${invoiceDate})</span>
                        </div>
                        <div class="flex items-center">
                            <span class="text-brand-earth-brown mr-4">${parseFloat(invoice.total_amount_ttc).toFixed(2)} €</span>
                            <a href="${downloadUrl}" 
                               target="_blank" 
                               class="btn-secondary text-xs py-1 px-2" data-translate-key="Telecharger">
                                ${t('Telecharger')}
                            </a>
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

window.initializeProfessionalPage = initializeProfessionalPage;
