// website/js/reset-password.js

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
            messageElement.textContent = t('Pro_Token_Ou_Email_Manquant_URL'); // Add key
            messageElement.className = 'text-sm my-2 text-brand-truffle-burgundy';
        }
        if (resetPasswordForm) resetPasswordForm.querySelector('button[type="submit"]').disabled = true;
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
            clearFormErrors(resetPasswordForm); // Assumes clearFormErrors is in ui.js

            if (!currentToken || !currentEmail) {
                messageElement.textContent = t('Pro_Token_Ou_Email_Manquant_Impossible_Reinitialiser'); // Add key
                messageElement.classList.add('text-brand-truffle-burgundy');
                return;
            }
            if (newPassword.length < 8) {
                setFieldError(document.getElementById('new-password'), t('Mot_de_passe_8_caracteres'));
                return;
            }
            if (newPassword !== confirmNewPassword) {
                setFieldError(document.getElementById('confirm-new-password'), t('Mots_de_passe_ne_correspondent_pas'));
                return;
            }

            showGlobalMessage(t('Pro_Reinitialisation_En_Cours'), 'info'); // Add key
            try {
                const result = await makeApiRequest('/auth/reset-password', 'POST', {
                    token: currentToken,
                    email: currentEmail,
                    new_password: newPassword
                });

                if (result.success) {
                    showGlobalMessage(result.message || t('Pro_MDP_Reinitialise_Succes_Connectez_Vous'), 'success', 8000); // Add key
                    messageElement.textContent = result.message || t('Pro_MDP_Reinitialise_Succes_Connectez_Vous_Modal'); // Add key
                    messageElement.classList.add('text-green-600');
                    resetPasswordForm.reset();
                    // Redirect to login page after a delay
                    setTimeout(() => {
                        // Determine if it was a B2B or B2C reset based on context or add a type to token/url
                        window.location.href = 'professionnels.html'; // Assuming B2B reset
                    }, 5000);
                } else {
                    messageElement.textContent = result.message || t('Pro_Erreur_Reinitialisation_MDP'); // Add key
                    messageElement.classList.add('text-brand-truffle-burgundy');
                    showGlobalMessage(result.message || t('Pro_Erreur_Reinitialisation_MDP'), 'error');
                }
            } catch (error) {
                messageElement.textContent = error.message || t('Erreur_serveur');
                messageElement.classList.add('text-brand-truffle-burgundy');
                showGlobalMessage(error.message || t('Erreur_serveur'), 'error');
            }
        });
    }
    // Initial translation of the page elements
    if (typeof translatePageElements === 'function') {
        translatePageElements();
    } else {
        console.warn("translatePageElements function not available on reset-password page.");
    }
});
