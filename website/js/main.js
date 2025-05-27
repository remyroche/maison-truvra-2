// website/js/main.js
// Main script for initializing the frontend application and page-specific logic.

document.addEventListener('DOMContentLoaded', () => {
    // --- Global Initializations ---
    initializeMobileMenu();     // From ui.js
    initializeNewsletterForm(); // From newsletter.js
    setActiveNavLink();         // From ui.js
    updateLoginState();         // From auth.js
    updateCartCountDisplay();   // From cart.js// website/js/main.js
// Ensure i18n.js is loaded before main.js in your HTML files:
// <script src="js/i18n.js"></script>
// <script src="js/main.js"></script>

document.addEventListener('DOMContentLoaded', async () => {
    // --- Global Initializations ---
    await loadTranslations(localStorage.getItem('maisonTruvraLang') || 'fr'); // Load translations first
    initializeMobileMenu();     // From ui.js
    initializeNewsletterForm(); // From newsletter.js
    setActiveNavLink();         // From ui.js
    updateLoginState();         // From auth.js
    updateCartCountDisplay();   // From cart.js

    // Update language display in switcher
    const currentLangInitial = getCurrentLang(); // from i18n.js
    const langDisplay = document.getElementById('current-lang-display');
    const langDisplayMobile = document.getElementById('current-lang-display-mobile');
    if (langDisplay) langDisplay.textContent = currentLangInitial.toUpperCase();
    if (langDisplayMobile) langDisplayMobile.textContent = currentLangInitial.toUpperCase();


    const currentYearEl = document.getElementById('currentYear');
    if (currentYearEl) {
        currentYearEl.textContent = new Date().getFullYear();
    }

    const bodyId = document.body.id;

    if (bodyId === 'page-nos-produits') {
        if (typeof fetchAndDisplayProducts === 'function') fetchAndDisplayProducts('all');
        if (typeof setupCategoryFilters === 'function') setupCategoryFilters();
    } else if (bodyId === 'page-produit-detail') {
        if (typeof loadProductDetail === 'function') loadProductDetail();
        const addToCartDetailButton = document.getElementById('add-to-cart-button');
        if (addToCartDetailButton && typeof handleAddToCartFromDetail === 'function') {
            addToCartDetailButton.addEventListener('click', (event) => {
                event.preventDefault();
                handleAddToCartFromDetail();
            });
        }
        const quantityControls = document.getElementById('quantity-select-controls');
        if (quantityControls) {
            const decreaseButton = quantityControls.querySelector('button:first-child');
            const increaseButton = quantityControls.querySelector('button:last-child');
            if(decreaseButton && typeof updateDetailQuantity === 'function') decreaseButton.addEventListener('click', () => updateDetailQuantity(-1));
            if(increaseButton && typeof updateDetailQuantity === 'function') increaseButton.addEventListener('click', () => updateDetailQuantity(1));
        }
    } else if (bodyId === 'page-panier') {
        if (typeof displayCartItems === 'function') displayCartItems();
    } else if (bodyId === 'page-compte') {
        if (typeof displayAccountDashboard === 'function') displayAccountDashboard();
        const loginForm = document.getElementById('login-form');
        if (loginForm && typeof handleLogin === 'function') {
            loginForm.addEventListener('submit', handleLogin);
        }
        const createAccountButton = document.querySelector('#login-register-section button.btn-secondary'); // More specific selector
        if(createAccountButton && typeof showGlobalMessage === 'function'){
            createAccountButton.addEventListener('click', (e) => {
                e.preventDefault();
                showGlobalMessage(t('Feature_not_implemented_contact_admin'), 'info'); // Example of using t()
            });
        }
    } else if (bodyId === 'page-paiement') {
        if (typeof initializeCheckoutPage === 'function') initializeCheckoutPage();
    } else if (bodyId === 'page-confirmation-commande') {
        if (typeof initializeConfirmationPage === 'function') initializeConfirmationPage();
    }


    document.querySelectorAll('.modal-overlay').forEach(modalOverlay => {
        modalOverlay.addEventListener('click', function(event) {
            if (event.target === modalOverlay && typeof closeModal === 'function') {
                closeModal(modalOverlay.id);
            }
        });
    });
    document.querySelectorAll('.modal-close-button').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal-overlay');
            if (modal && typeof closeModal === 'function') {
                closeModal(modal.id);
            }
        });
    });

    // Load header and footer, then translate them if translatePageElements wasn't called yet or needs re-run for dynamic parts
    await Promise.all([loadHeader(), loadFooter()]);
    // Re-translate after header/footer are loaded to catch their keys
    if(window.translatePageElements) window.translatePageElements();


}); // End DOMContentLoaded


async function loadHeader() {
    const headerPlaceholder = document.getElementById('header-placeholder');
    if (!headerPlaceholder) {
        console.error("L'élément #header-placeholder est introuvable.");
        return;
    }
    try {
        const response = await fetch('header.html');
        if (!response.ok) throw new Error(`Erreur de chargement du header: ${response.status}`);
        headerPlaceholder.innerHTML = await response.text();

        if (typeof initializeMobileMenu === 'function') initializeMobileMenu();
        if (typeof setActiveNavLink === 'function') setActiveNavLink();
        if (typeof updateLoginState === 'function') updateLoginState();
        if (typeof updateCartCountDisplay === 'function') updateCartCountDisplay();
        // Translate newly loaded header content
        if(window.translatePageElements) window.translatePageElements();
        // Update language display in switcher (as it's part of header.html)
        const currentLangInitial = getCurrentLang();
        const langDisplay = document.getElementById('current-lang-display');
        const langDisplayMobile = document.getElementById('current-lang-display-mobile');
        if (langDisplay) langDisplay.textContent = currentLangInitial.toUpperCase();
        if (langDisplayMobile) langDisplayMobile.textContent = currentLangInitial.toUpperCase();

    } catch (error) {
        console.error("Impossible de charger l'en-tête:", error);
    }
}

async function loadFooter() {
    const footerPlaceholder = document.getElementById('footer-placeholder');
    if (!footerPlaceholder) {
        console.error("L'élément #footer-placeholder est introuvable.");
        return;
    }
    try {
        const response = await fetch('footer.html');
        if (!response.ok) throw new Error(`Erreur de chargement du footer: ${response.status}`);
        footerPlaceholder.innerHTML = await response.text();

        if (typeof initializeNewsletterForm === 'function' && footerPlaceholder.querySelector('#newsletter-form')) {
            initializeNewsletterForm();
        }
        const currentYearEl = footerPlaceholder.querySelector('#currentYear');
        if (currentYearEl) currentYearEl.textContent = new Date().getFullYear();
        // Translate newly loaded footer content
        if(window.translatePageElements) window.translatePageElements();
    } catch (error) {
        console.error("Impossible de charger le pied de page:", error);
    }
}
