// website/js/i18n.js
let currentTranslations = {};
let currentLang = localStorage.getItem('maisonTruvraLang') || 'fr'; // Default to French

async function loadTranslations(lang = 'fr') {
    try {
        const response = await fetch(`js/locales/<span class="math-inline">\{lang\}\.json?v\=</span>{new Date().getTime()}`); // Cache buster
        if (!response.ok) {
            console.error(`Could not load ${lang}.json. Status: ${response.status}`);
            // Fallback to French if English fails or vice-versa, or load default empty
            if (lang !== 'fr') return loadTranslations('fr'); // Attempt to load default
            currentTranslations = {}; // Load empty if default also fails
            return;
        }
        currentTranslations = await response.json();
        currentLang = lang;
        localStorage.setItem('maisonTruvraLang', lang);
        document.documentElement.lang = currentLang; // Set lang attribute on <html>
        translatePageElements();
    } catch (error) {
        console.error("Error loading translations for " + lang + ":", error);
        if (lang !== 'fr') { // Avoid infinite loop if fr.json is missing
            console.warn("Falling back to French translations.");
            await loadTranslations('fr');
        } else {
            currentTranslations = {}; // Ensure it's an object
        }
    }
}

function t(key, replacements = {}) {
    let translation = currentTranslations[key] || key;
    for (const placeholder in replacements) {
        translation = translation.replace(new RegExp(`{${placeholder}}`, 'g'), replacements[placeholder]);
    }
    return translation;
}

function translatePageElements() {
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        if (key) {
            const translatedText = t(key);
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                if (element.type === 'submit' || element.type === 'button') {
                    element.value = translatedText;
                } else {
                    element.placeholder = translatedText;
                }
            } else if (element.hasAttribute('title')) {
                 element.title = translatedText;
            }
            else {
                element.innerHTML = translatedText; // Use innerHTML to allow for simple HTML in translations if needed
            }
        }
    });
    // Special handling for page titles if needed
    const pageTitleKey = document.body.getAttribute('data-page-title-key');
    if (pageTitleKey) {
        document.title = t(pageTitleKey);
    }
}

// Function to change language and reload translations
async function setLanguage(lang) {
    await loadTranslations(lang);
    // Potentially re-initialize parts of the page that depend on language
    // For example, if product lists are already loaded, they might need to be re-fetched or re-rendered.
    // This depends on how your dynamic content loading is structured.
    // A simple approach for now is that dynamic content fetching should already include language.
    if (typeof updateLoginState === "function") updateLoginState(); // To update "Mon Compte (Prénom)"
    if (document.body.id === 'page-nos-produits' && typeof fetchAndDisplayProducts === "function") {
        const activeFilter = document.querySelector('#product-categories-filter button.filter-active');
        fetchAndDisplayProducts(activeFilter ? activeFilter.dataset.category : 'all');
    }
    if (document.body.id === 'page-produit-detail' && typeof loadProductDetail === "function") {
        loadProductDetail();
    }
    if (document.body.id === 'page-panier' && typeof displayCartItems === "function") {
        displayCartItems(); // Re-render cart items if text like "Remove" needs translation
    }
     if (document.body.id === 'page-compte' && typeof displayAccountDashboard === "function") {
        displayAccountDashboard();
    }
}

// Expose functions to global scope if needed, or handle through event listeners in main.js
window.setLanguage = setLanguage;
window.t = t;
window.loadTranslations = loadTranslations;
window.translatePageElements = translatePageElements;
window.getCurrentLang = () => currentLang;
