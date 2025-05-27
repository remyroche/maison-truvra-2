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
// <script src="js/main.js"></script>// website/js/main.js
// Main script for initializing the frontend application, including B2C and B2B page-specific logic.

/**
 * Loads header.html content into the #header-placeholder div.
 * Initializes header-specific functionalities like mobile menu, nav links, login state, and cart display.
 * Translates the loaded header content.
 */
async function loadHeader() {
    const headerPlaceholder = document.getElementById('header-placeholder');
    if (!headerPlaceholder) {
        console.error("L'élément #header-placeholder est introuvable.");
        return;
    }
    try {
        const response = await fetch('header.html'); // Ensure header.html is in the same directory or adjust path
        if (!response.ok) {
            throw new Error(`Erreur de chargement du header: ${response.status} ${response.statusText}`);
        }
        headerPlaceholder.innerHTML = await response.text();

        // Initialize header components
        if (typeof initializeMobileMenu === 'function') initializeMobileMenu();
        if (typeof setActiveNavLink === 'function') setActiveNavLink(); // Sets active class on nav links
        if (typeof updateLoginState === 'function') updateLoginState(); // Updates account link based on login
        if (typeof updateCartCountDisplay === 'function') updateCartCountDisplay(); // Updates cart item count

        // Translate newly loaded header content
        if (typeof translatePageElements === 'function') translatePageElements();

        // Update language display in switcher (as it's part of header.html)
        const currentLangHeader = typeof getCurrentLang === 'function' ? getCurrentLang() : 'fr';
        const langDisplayDesktop = document.getElementById('current-lang-display');
        const langDisplayMobile = document.getElementById('current-lang-display-mobile');
        if (langDisplayDesktop) langDisplayDesktop.textContent = currentLangHeader.toUpperCase();
        if (langDisplayMobile) langDisplayMobile.textContent = currentLangHeader.toUpperCase();

    } catch (error) {
        console.error("Impossible de charger l'en-tête:", error);
        headerPlaceholder.innerHTML = "<p class='text-center text-red-500'>Erreur: L'en-tête n'a pas pu être chargé.</p>";
    }
}

/**
 * Loads footer.html content into the #footer-placeholder div.
 * Initializes footer-specific functionalities like the newsletter form and current year.
 * Translates the loaded footer content.
 */
async function loadFooter() {
    const footerPlaceholder = document.getElementById('footer-placeholder');
    if (!footerPlaceholder) {
        console.error("L'élément #footer-placeholder est introuvable.");
        return;
    }
    try {
        const response = await fetch('footer.html'); // Ensure footer.html is in the same directory or adjust path
        if (!response.ok) {
            throw new Error(`Erreur de chargement du footer: ${response.status} ${response.statusText}`);
        }
        footerPlaceholder.innerHTML = await response.text();

        // Initialize footer components
        if (typeof initializeNewsletterForm === 'function' && footerPlaceholder.querySelector('#newsletter-form')) {
            initializeNewsletterForm();
        }
        const currentYearElFooter = footerPlaceholder.querySelector('#currentYear');
        if (currentYearElFooter) {
            currentYearElFooter.textContent = new Date().getFullYear();
        }
        // Translate newly loaded footer content
        if (typeof translatePageElements === 'function') translatePageElements();
    } catch (error) {
        console.error("Impossible de charger le pied de page:", error);
        footerPlaceholder.innerHTML = "<p class='text-center text-red-500'>Erreur: Le pied de page n'a pas pu être chargé.</p>";
    }
}


// Main DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Load translations first - this is crucial
    // Assumes loadTranslations, getCurrentLang are defined in i18n.js
    if (typeof loadTranslations === 'function') {
        await loadTranslations(localStorage.getItem('maisonTruvraLang') || 'fr');
    } else {
        console.error("loadTranslations function not found. Ensure i18n.js is loaded before main.js.");
        // Fallback: try to proceed without full i18n if t() is globally available but loadTranslations isn't
        if (typeof t !== 'function') {
             window.t = (key) => key; // Dummy t function
        }
    }

    // 2. Load Header and Footer (they contain elements that need translation)
    await Promise.all([loadHeader(), loadFooter()]);
    // loadHeader and loadFooter should call translatePageElements internally after content is loaded.
    // If not, call it here: if (typeof translatePageElements === 'function') translatePageElements();

    // 3. Initialize global UI components that might use translated text
    if (typeof initializeMobileMenu === 'function') initializeMobileMenu(); // From ui.js
    if (typeof initializeNewsletterForm === 'function') {
        // Check if newsletter form is NOT in footer, otherwise it's handled by loadFooter
        if (!document.getElementById('footer-placeholder')?.querySelector('#newsletter-form')) {
            initializeNewsletterForm(); // From newsletter.js
        }
    }
    if (typeof setActiveNavLink === 'function') setActiveNavLink(); // From ui.js
    if (typeof updateLoginState === 'function') updateLoginState(); // From auth.js - updates based on B2C/B2B
    if (typeof updateCartCountDisplay === 'function') updateCartCountDisplay(); // From cart.js

    // Update language display in switcher (if not already handled by loadHeader)
    const currentLangInitial = typeof getCurrentLang === 'function' ? getCurrentLang() : 'fr';
    const langDisplay = document.getElementById('current-lang-display');
    const langDisplayMobile = document.getElementById('current-lang-display-mobile');
    if (langDisplay && langDisplay.textContent !== currentLangInitial.toUpperCase()) langDisplay.textContent = currentLangInitial.toUpperCase();
    if (langDisplayMobile && langDisplayMobile.textContent !== currentLangInitial.toUpperCase()) langDisplayMobile.textContent = currentLangInitial.toUpperCase();


    // Display current year in footer (if not handled by loadFooter)
    const globalCurrentYearEl = document.getElementById('currentYear');
    if (globalCurrentYearEl && !document.getElementById('footer-placeholder')?.querySelector('#currentYear')) {
         globalCurrentYearEl.textContent = new Date().getFullYear();
    }

    // 4. Page-Specific Initializations
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
            const decreaseButton = quantityControls.querySelector('button:first-child'); // More robust selector
            const increaseButton = quantityControls.querySelector('button:last-child'); // More robust selector
            if(decreaseButton && typeof updateDetailQuantity === 'function') decreaseButton.addEventListener('click', () => updateDetailQuantity(-1));
            if(increaseButton && typeof updateDetailQuantity === 'function') increaseButton.addEventListener('click', () => updateDetailQuantity(1));
        }
    } else if (bodyId === 'page-panier') {
        if (typeof displayCartItems === 'function') displayCartItems();
    } else if (bodyId === 'page-compte') { // B2C Account Page
        if (typeof displayAccountDashboard === 'function') displayAccountDashboard(); // B2C dashboard
        const loginForm = document.getElementById('login-form'); // B2C login form
        if (loginForm && typeof handleLogin === 'function') {
            loginForm.addEventListener('submit', handleLogin); // B2C login handler
        }
        // B2C create account button (assuming it's the secondary button in this section)
        const createAccountButtonB2C = document.querySelector('#login-register-section button.btn-secondary');
        if(createAccountButtonB2C && typeof showGlobalMessage === 'function' && typeof t === 'function'){
            createAccountButtonB2C.addEventListener('click', (e) => {
                e.preventDefault();
                // This should ideally show a registration form or modal for B2C
                showGlobalMessage(t('Feature_not_implemented_contact_admin'), 'info');
            });
        }
    } else if (bodyId === 'page-professionnels') { // B2B Professionals Page
        if (typeof initializeProfessionalPage === 'function') {
            initializeProfessionalPage(); // Defined in professional.js
        } else {
            console.error("initializeProfessionalPage function not found. Ensure professional.js is loaded.");
        }
    } else if (bodyId === 'page-paiement') { // B2C Checkout
        if (typeof initializeCheckoutPage === 'function') initializeCheckoutPage();
    } else if (bodyId === 'page-confirmation-commande') { // B2C Order Confirmation
        if (typeof initializeConfirmationPage === 'function') initializeConfirmationPage();
    }
    // Add other page-specific initializations here

    // 5. Global Modal Event Listeners (if any)
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

    // Final translation pass for any elements that might have been missed or added dynamically by other scripts
    if (typeof translatePageElements === 'function') translatePageElements();
});
