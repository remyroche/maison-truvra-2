// website/js/ui.js
// UI helper functions for the frontend application

/**
 * Initializes the mobile menu toggle functionality.
 */
function initializeMobileMenu() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenuDropdown = document.getElementById('mobile-menu-dropdown');
    if (mobileMenuButton && mobileMenuDropdown) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenuDropdown.classList.toggle('hidden');
        });
    }
}

/**
 * Closes the mobile menu if it's open.
 */
function closeMobileMenu() {
    const mobileMenuDropdown = document.getElementById('mobile-menu-dropdown');
    if (mobileMenuDropdown && !mobileMenuDropdown.classList.contains('hidden')) {
        mobileMenuDropdown.classList.add('hidden');
    }
}

/**
 * Displays a global message toast or an inline message within a target element.
 * @param {object} options - Configuration for the message.
 * @param {string} options.message - The message to display.
 * @param {string} [options.type='success'] - The type of message ('success', 'error', 'info', 'warning').
 * @param {number} [options.duration=4000] - The duration to display the toast in milliseconds. Not used for inline messages.
 * @param {string|null} [options.targetElementId=null] - If provided, displays the message inside this element instead of a global toast.
 */
function showGlobalMessage({ message, type = 'success', duration = 4000, targetElementId = null }) {
    if (targetElementId) {
        const targetElement = document.getElementById(targetElementId);
        if (targetElement) {
            targetElement.textContent = message;
            targetElement.className = ''; // Clear existing classes
            targetElement.classList.add('message-inline', `message-${type}`); // e.g., message-error
            targetElement.setAttribute('role', 'alert');
            targetElement.style.display = 'block';
            return;
        } else {
            console.warn(`Target element with ID "${targetElementId}" not found for inline message. Falling back to global toast.`);
        }
    }

    const toastContainer = document.getElementById('global-toast-container'); // Changed ID
    const textElement = document.getElementById('global-toast-text'); // Changed ID

    if (!toastContainer || !textElement) {
        console.warn("Global toast elements ('global-toast-container', 'global-toast-text') not found. Fallback to alert.");
        alert(`${type.toUpperCase()}: ${message}`); // Fallback if toast elements are not in the HTML
        return;
    }

    textElement.textContent = message;
    // Base classes for the toast, specific styling classes are added below
    toastContainer.className = 'fixed bottom-5 right-5 p-4 rounded-lg shadow-md text-white z-50 transition-opacity duration-500 ease-in-out';
    toastContainer.setAttribute('role', 'alert');
    toastContainer.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');


    if (type === 'error') {
        toastContainer.classList.add('bg-brand-truffle-burgundy'); // Or your specific error color
    } else if (type === 'info') {
        toastContainer.classList.add('bg-brand-slate-blue-grey'); // Or your specific info color
    } else if (type === 'warning') {
        toastContainer.classList.add('bg-yellow-500'); // Example warning color
    } else { // success
        toastContainer.classList.add('bg-brand-deep-sage-green'); // Or your specific success color
    }
    
    toastContainer.style.display = 'block';
    toastContainer.style.opacity = '0'; // Start fully transparent

    // Force reflow before adding 'show' class for transition to work
    void toastContainer.offsetWidth; 
    
    toastContainer.style.opacity = '1'; // Fade in

    // Clear existing timeouts to prevent conflicts
    if (toastContainer.currentTimeout) clearTimeout(toastContainer.currentTimeout);
    if (toastContainer.hideTimeout) clearTimeout(toastContainer.hideTimeout);

    toastContainer.currentTimeout = setTimeout(() => {
        toastContainer.style.opacity = '0'; // Fade out
        // Wait for fade out transition to complete before hiding
        toastContainer.hideTimeout = setTimeout(() => {
            toastContainer.style.display = 'none';
        }, 500); // Match this duration with CSS transition duration
    }, duration);
}


/**
 * Opens a modal dialog.
 * @param {string} modalId - The ID of the modal element to open.
 * @param {string} [productName=''] - Optional product name for the add-to-cart modal.
 */
function openModal(modalId, productName = '') {
    const modal = document.getElementById(modalId);
    if (modal) {
        if (modalId === 'add-to-cart-modal' && productName) {
            const modalProductName = modal.querySelector('#modal-product-name');
            if (modalProductName) modalProductName.textContent = `${productName} ajouté au panier !`; // Consider using t() for translation
        }
        modal.classList.add('active');
        // Focus on the modal or its first focusable element for accessibility
        const firstFocusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (firstFocusable) {
            firstFocusable.focus();
        }
    }
}

/**
 * Closes a modal dialog.
 * @param {string} modalId - The ID of the modal element to close.
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

/**
 * Sets the active state for the current navigation link.
 */
function setActiveNavLink() {
    const currentPage = window.location.pathname.split("/").pop() || "index.html";
    const navLinks = document.querySelectorAll('header nav .nav-link, #mobile-menu-dropdown .nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        // Ensure href is not null or empty before trying to split
        const linkHref = link.getAttribute('href');
        if (linkHref) {
            const linkPage = linkHref.split("/").pop() || "index.html";
            if (linkPage === currentPage) {
                link.classList.add('active');
            }
        }
    });
}

/**
 * Validates an email address format.
 * @param {string} email - The email address to validate.
 * @returns {boolean} - True if the email is valid, false otherwise.
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

/**
 * Sets an error message for a form field and applies error styling.
 * @param {HTMLElement} field - The form field element.
 * @param {string} message - The error message to display.
 */
function setFieldError(field, message) {
    if (!field) return;
    const fieldId = field.id || `field-${Math.random().toString(36).substring(7)}`;
    if (!field.id) field.id = fieldId; // Ensure field has an ID
    
    field.classList.add('border-red-500', 'ring-red-500');
    field.setAttribute('aria-invalid', 'true');
    
    const errorId = `${fieldId}-error`;
    let errorElement = field.parentElement.querySelector(`.error-message[id="${errorId}"]`);
    
    if (!errorElement) {
        errorElement = document.createElement('p');
        errorElement.id = errorId;
        errorElement.classList.add('error-message', 'text-xs', 'text-red-600', 'mt-1');
        // Insert after the field, or at the end of parent if structure is complex
        if (field.nextSibling) {
            field.parentElement.insertBefore(errorElement, field.nextSibling);
        } else {
            field.parentElement.appendChild(errorElement);
        }
    }
    errorElement.textContent = message;
    field.setAttribute('aria-describedby', errorId);
}

/**
 * Clears all error messages and styling from a form.
 * @param {HTMLFormElement} form - The form element.
 */
function clearFormErrors(form) {
    if (!form) return;
    form.querySelectorAll('.border-red-500, .ring-red-500').forEach(el => {
        el.classList.remove('border-red-500', 'ring-red-500');
        el.removeAttribute('aria-invalid');
        el.removeAttribute('aria-describedby');
    });
    form.querySelectorAll('.error-message').forEach(el => el.remove());
}

/**
 * Gets the appropriate CSS class for an order status.
 * @param {string} status - The order status.
 * @returns {string} - The CSS class string.
 */
function getOrderStatusClass(status) {
    // Ensure status is a string and convert to lowercase for case-insensitive matching
    const lowerStatus = String(status || '').toLowerCase();
    switch (lowerStatus) {
        case 'paid': return 'bg-green-100 text-green-800';
        case 'processing': return 'bg-blue-100 text-blue-800'; // Added processing
        case 'shipped': return 'bg-blue-100 text-blue-800'; // Kept as is, can differentiate if needed
        case 'delivered': return 'bg-purple-100 text-purple-800';
        case 'pending': return 'bg-yellow-100 text-yellow-800';
        case 'cancelled': return 'bg-red-100 text-red-800';
        case 'refunded': return 'bg-gray-200 text-gray-700'; // Added refunded
        default: return 'bg-gray-100 text-gray-800';
    }
}


/**
 * Shows a loading state on a button.
 * @param {HTMLButtonElement} buttonElement - The button to update.
 * @param {string} [loadingText] - Text to display while loading. Defaults to translated 'Loading...'.
 */
function showButtonLoading(buttonElement, loadingText) {
    if (!buttonElement) return;
    const defaultLoadingText = typeof t === 'function' ? t('loading') : 'Loading...';
    const textToShow = loadingText || defaultLoadingText;

    buttonElement.dataset.originalText = buttonElement.innerHTML; // Store original content (could be text + icons)
    buttonElement.innerHTML = `
        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        ${textToShow}
    `;
    buttonElement.disabled = true;
    buttonElement.classList.add('opacity-75', 'cursor-not-allowed');
}

/**
 * Hides the loading state on a button and restores its original content.
 * @param {HTMLButtonElement} buttonElement - The button to update.
 */
function hideButtonLoading(buttonElement) {
    if (!buttonElement) return;
    if (buttonElement.dataset.originalText) {
        buttonElement.innerHTML = buttonElement.dataset.originalText;
    }
    buttonElement.disabled = false;
    buttonElement.classList.remove('opacity-75', 'cursor-not-allowed');
}

// Ensure the toast container is in your main HTML (e.g., in footer.html or index.html)
/*
Example HTML for the toast:
<div id="global-toast-container" style="display: none;" class="fixed bottom-5 right-5 p-4 rounded-lg shadow-md text-white z-50 transition-opacity duration-500 ease-in-out" role="alert">
    <span id="global-toast-text">Sample message</span>
</div>
*/
