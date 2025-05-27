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
    const proUpdateAccountForm = document.getElementById('pro-update-account-form');
    const proCancelUpdateFormButton = document.getElementById('pro-cancel-update-form-button');
    const proForgotPasswordLink = document.getElementById('pro-forgot-password-link');


    if (proLoginForm) proLoginForm.addEventListener('submit', handleProLogin);
    if (proRegisterForm) proRegisterForm.addEventListener('submit', handleProRegister);
    if (proLogoutButton) proLogoutButton.addEventListener('click', handleProLogout);

    if (proShowUpdateFormButton) {
        proShowUpdateFormButton.addEventListener('click', () => {
            proUpdateAccountForm.style.display = 'block';
            proShowUpdateFormButton.style.display = 'none';
            populateProUpdateForm(); // Populate with current details
        });
    }
    if (proCancelUpdateFormButton) {
        proCancelUpdateFormButton.addEventListener('click', () => {
            proUpdateAccountForm.style.display = 'none';
            clearFormErrors(proUpdateAccountForm);
            proShowUpdateFormButton.style.display = 'block';
        });
    }
    if (proUpdateAccountForm) proUpdateAccountForm.addEventListener('submit', handleProUpdateAccount);

    if (proForgotPasswordLink) {
        proForgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            // Implement "Forgot Password" modal or redirect
            showGlobalMessage(t('Fonctionnalite_Mot_de_passe_oublie_B2B_TODO'), 'info'); // Add to locales
        });
    }


    checkProLoginState();
    // Translate static elements on this page if not already done by main.js
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
        // If a B2C user lands here, or non-logged-in, they see login/register
        // If a B2C user is logged in and lands here, they should still see login/register for B2B.
        // Or redirect them to B2C account or homepage. For now, just show B2B login.
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
        messageElement.textContent = t('Email_et_mot_de_passe_requis'); // Add to locales
        return;
    }
    showGlobalMessage(t('Connexion_en_cours'), 'info');
    try {
        const result = await makeApiRequest('/auth/login', 'POST', { email, password });
        if (result.success && result.user && result.user.user_type === 'b2b') {
            setCurrentUser(result.user, result.token); // from auth.js
            showGlobalMessage(t('Connexion_reussie'), 'success');
            checkProLoginState(); // Refresh view to show dashboard
        } else if (result.success && result.user && result.user.user_type !== 'b2b') {
            messageElement.textContent = t('Pro_Compte_non_professionnel'); // Add to locales
            showGlobalMessage(t('Pro_Compte_non_professionnel_long'), 'error'); // Add to locales
            setCurrentUser(null); // Log out if B2C user tried to log in here
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
    if (!company_name) { setFieldError(form.querySelector('#pro-register-company-name'), t('Nom_entreprise_requis')); isValid = false; } // Add
    if (!prenom) { setFieldError(form.querySelector('#pro-register-prenom'), t('Prenom_contact_requis')); isValid = false; } // Add
    if (!nom) { setFieldError(form.querySelector('#pro-register-nom'), t('Nom_contact_requis')); isValid = false; } // Add
    if (!email || !validateEmail(email)) { setFieldError(form.querySelector('#pro-register-email'), t('E-mail_invalide')); isValid = false; }
    if (password.length < 8) { setFieldError(form.querySelector('#pro-register-password'), t('Mot_de_passe_8_caracteres')); isValid = false; }
    if (password !== confirm_password) { setFieldError(form.querySelector('#pro-register-confirm-password'), t('Mots_de_passe_ne_correspondent_pas')); isValid = false; }

    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire'), "error");
        return;
    }

    showGlobalMessage(t('Creation_compte_pro_en_cours'), 'info'); // Add
    try {
        const result = await makeApiRequest('/auth/register-professional', 'POST', {
            email, password, company_name, nom, prenom, phone_number
        });
        if (result.success) {
            showGlobalMessage(result.message || t('Compte_professionnel_cree_succes'), 'success'); // Add
            form.reset();
            // Optionally auto-login or prompt to login
        } else {
            messageElement.textContent = result.message || t('Erreur_creation_compte_pro'); // Add
            showGlobalMessage(result.message || t('Erreur_creation_compte_pro'), 'error');
        }
    } catch (error) {
        messageElement.textContent = error.message || t('Erreur_serveur');
        showGlobalMessage(error.message || t('Erreur_serveur'), 'error');
    }
}

function handleProLogout() {
    setCurrentUser(null); // from auth.js
    showGlobalMessage(t('Deconnecte_message'), 'info');
    checkProLoginState(); // Refresh view to show login/register
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
        if (!currentPassword) { // Require current password only if changing password
            setFieldError(form.querySelector('#pro-update-current-password'), t('Pro_Mot_de_passe_actuel_requis_pour_changement')); return; // Add
        }
        updateData.current_password = currentPassword;
        updateData.new_password = newPassword;
    }
    // Filter out empty fields so they don't overwrite existing data with empty strings if not intended
    const finalUpdateData = {};
    for (const key in updateData) {
        if (updateData[key] || key === 'phone_number') { // Allow empty phone_number to clear it
             if (typeof updateData[key] === 'string' && updateData[key].trim() === '' && key !== 'phone_number') continue;
            finalUpdateData[key] = updateData[key];
        }
    }
    if (Object.keys(finalUpdateData).length === 0 && !newPassword) {
        messageElement.textContent = t('Pro_Aucun_changement_detecte'); // Add
        return;
    }


    showGlobalMessage(t('Pro_Mise_a_jour_en_cours'), 'info'); // Add
    try {
        const result = await makeApiRequest('/professional/account', 'PUT', finalUpdateData, true);
        if (result.success) {
            showGlobalMessage(t('Pro_Compte_mis_a_jour_succes'), 'success'); // Add
            setCurrentUser(result.user, getAuthToken()); // Update session storage
            displayProDashboard(result.user); // Refresh displayed info
            form.style.display = 'none';
            clearFormErrors(form);
            document.getElementById('pro-show-update-form-button').style.display = 'block';
            form.querySelector('#pro-update-current-password').value = '';
            form.querySelector('#pro-update-new-password').value = '';
            form.querySelector('#pro-update-confirm-password').value = '';

        } else {
            messageElement.textContent = result.message || t('Pro_Erreur_mise_a_jour_compte'); // Add
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
                container.innerHTML = `<p class="text-brand-warm-taupe italic" data-translate-key="Pro_Aucune_facture">${t('Pro_Aucune_facture')}</p>`; // Add
                return;
            }
            let html = '<ul class="space-y-3">';
            result.invoices.forEach(invoice => {
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString(getCurrentLang() || 'fr-FR');
                html += `
                    <li class="p-3 border border-brand-warm-taupe/30 rounded-md flex justify-between items-center">
                        <div>
                            <span class="font-semibold text-brand-near-black">${invoice.invoice_number}</span>
                            <span class="text-xs text-brand-warm-taupe ml-2">(${invoiceDate})</span>
                        </div>
                        <div class="flex items-center">
                            <span class="text-brand-earth-brown mr-4">${parseFloat(invoice.total_amount_ttc).toFixed(2)} €</span>
                            <a href="${API_BASE_URL}/professional/invoices/${invoice.invoice_id}/download?token=${getAuthToken()}" 
                               target="_blank" download="${invoice.invoice_number}.pdf"
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
            container.innerHTML = `<p class="text-red-500 italic">${result.message || t('Pro_Erreur_chargement_factures')}</p>`; // Add
        }
    } catch (error) {
        container.innerHTML = `<p class="text-red-500 italic">${t('Pro_Erreur_chargement_factures')}: ${error.message}</p>`;
    }
}

// Expose the initializer to be called from main.js
window.initializeProfessionalPage = initializeProfessionalPage;
