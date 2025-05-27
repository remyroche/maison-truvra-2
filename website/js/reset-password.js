// website/js/reset-password.js

document.addEventListener('DOMContentLoaded', () => {
    const resetPasswordForm = document.getElementById('reset-password-form');
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const email = urlParams.get('email');

    const tokenField = document.getElementById('reset-token');
    const emailField = document.getElementById('reset-email');// website/js/reset-password.js

document.addEventListener('DOMContentLoaded', () => {
    const resetPasswordForm = document.getElementById('reset-password-form');
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const email = urlParams.get('email');

    const tokenField = document.getElementById('reset-token');
    const emailField = document.getElementById('reset-email');

    if (tokenField) tokenField.value = token || '';
    if (emailField) emailField.value = email || '';

    if (!token || !email) {
        const messageElement = document.getElementById('reset-password-message');
        if (messageElement) {
            // Ensure t() is available, might need to load translations specifically for this page if main.js doesn't cover it early enough
            messageElement.textContent = typeof t === 'function' ? t('Pro_Token_Ou_Email_Manquant_URL') : "Token or email missing. Cannot proceed.";
            messageElement.className = 'text-sm my-2 text-brand-truffle-burgundy';
        }
        if (resetPasswordForm) {
            const submitButton = resetPasswordForm.querySelector('button[type="submit"]');
            if(submitButton) submitButton.disabled = true;
        }
    }

    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const currentToken = document.getElementById('reset-token').value;
            const currentEmail = document.getElementById('reset-email').value;
            const newPassword = document.getElementById('new-password').value;
            const confirmNewPassword = document.getElementById('confirm-new-password').value;
            const messageElement = document.getElementById('reset-password-message');
            messageElement.className = 'text-sm my-2'; // Reset class
            messageElement.textContent = '';
            if (typeof clearFormErrors === 'function') clearFormErrors(resetPasswordForm);

            if (!currentToken || !currentEmail) {
                messageElement.textContent = typeof t === 'function' ? t('Pro_Token_Ou_Email_Manquant_Impossible_Reinitialiser') : "Invalid token or email. Cannot reset.";
                messageElement.classList.add('text-brand-truffle-burgundy');
                return;
            }
            if (newPassword.length < 8) {
                if (typeof setFieldError === 'function') setFieldError(document.getElementById('new-password'), typeof t === 'function' ? t('Mot_de_passe_8_caracteres') : "Password too short.");
                return;
            }
            if (newPassword !== confirmNewPassword) {
                if (typeof setFieldError === 'function') setFieldError(document.getElementById('confirm-new-password'), typeof t === 'function' ? t('Mots_de_passe_ne_correspondent_pas') : "Passwords do not match.");
                return;
            }

            if (typeof showGlobalMessage === 'function') showGlobalMessage(typeof t === 'function' ? t('Pro_Reinitialisation_En_Cours') : "Resetting password...", 'info');
            try {
                const result = await makeApiRequest('/auth/reset-password', 'POST', {
                    token: currentToken,
                    email: currentEmail,
                    new_password: newPassword
                });

                if (result.success) {
                    if (typeof showGlobalMessage === 'function') showGlobalMessage(result.message || (typeof t === 'function' ? t('Pro_MDP_Reinitialise_Succes_Connectez_Vous') : "Password reset!"), 'success', 8000);
                    messageElement.textContent = result.message || (typeof t === 'function' ? t('Pro_MDP_Reinitialise_Succes_Connectez_Vous_Modal') : "Password reset! Redirecting...");
                    messageElement.classList.add('text-green-600');
                    resetPasswordForm.reset();
                     if (resetPasswordForm.querySelector('button[type="submit"]')) resetPasswordForm.querySelector('button[type="submit"]').disabled = true;
                    setTimeout(() => {
                        window.location.href = 'professionnels.html'; // Redirect to B2B login
                    }, 4000);
                } else {
                    messageElement.textContent = result.message || (typeof t === 'function' ? t('Pro_Erreur_Reinitialisation_MDP') : "Error resetting password.");
                    messageElement.classList.add('text-brand-truffle-burgundy');
                    if (typeof showGlobalMessage === 'function') showGlobalMessage(result.message || (typeof t === 'function' ? t('Pro_Erreur_Reinitialisation_MDP') : "Error resetting password."), 'error');
                }
            } catch (error) {
                messageElement.textContent = error.message || (typeof t === 'function' ? t('Erreur_serveur') : "Server error.");
                messageElement.classList.add('text-brand-truffle-burgundy');
                if (typeof showGlobalMessage === 'function') showGlobalMessage(error.message || (typeof t === 'function' ? t('Erreur_serveur') : "Server error."), 'error');
            }
        });
    }
    // Initial translation of the page elements
    // This ensures that even if main.js hasn't fully initialized translations yet,
    // this page tries to translate itself.
    if (typeof loadTranslations === 'function') {
        loadTranslations(localStorage.getItem('maisonTruvraLang') || 'fr').then(() => {
            if (typeof translatePageElements === 'function') {
                translatePageElements();
            }
        });
    } else if (typeof translatePageElements === 'function') {
        translatePageElements();
    } else {
         console.warn("Translation functions not available on reset-password page early load.");
    }
});
