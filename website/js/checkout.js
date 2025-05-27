// website/js/checkout.js
// Assumes ui.js (showGlobalMessage, clearFormErrors, setFieldError, validateEmail, showButtonLoading, hideButtonLoading) is loaded
// Assumes cart.js (getCart, saveCart) is loaded
// Assumes auth.js (getUser) is loaded
// Assumes i18n.js (t, getCurrentLang) is loaded
// Assumes api.js (makeApiRequest, ApiError) is loaded

/**
 * Handles the checkout form submission.
 * Validates form fields, prepares order data, and sends it to the backend.
 * @param {Event} event - The form submission event.
 */
async function handleCheckout(event) {
    event.preventDefault();
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');

    if (typeof clearFormErrors === "function") clearFormErrors(form);
    const cart = typeof getCart === "function" ? getCart() : [];
    const currentUser = typeof getUser === "function" ? getUser() : null;

    if (cart.length === 0) {
        if (typeof showGlobalMessage === "function" && typeof t === "function") {
            showGlobalMessage({ message: t('checkout.cartEmptyError'), type: "error" });
        }
        return;
    }

    let isValid = true;
    // Define required fields and their validation messages (using i18n keys)
    const requiredFields = [
        { id: 'checkout-email', validator: typeof validateEmail === "function" ? validateEmail : null, messageKey: "checkout.validation.emailInvalid" },
        { id: 'checkout-firstname', messageKey: "checkout.validation.firstNameRequired" },
        { id: 'checkout-lastname', messageKey: "checkout.validation.lastNameRequired" },
        { id: 'checkout-address', messageKey: "checkout.validation.addressRequired" },
        { id: 'checkout-zipcode', messageKey: "checkout.validation.zipCodeRequired" },
        { id: 'checkout-city', messageKey: "checkout.validation.cityRequired" },
        { id: 'checkout-country', messageKey: "checkout.validation.countryRequired" }
    ];

    requiredFields.forEach(fieldInfo => {
        const fieldElement = form.querySelector(`#${fieldInfo.id}`);
        if (fieldElement) {
            const value = fieldElement.value.trim();
            let fieldError = false;
            if (!value) {
                fieldError = true;
            } else if (fieldInfo.validator && !fieldInfo.validator(value)) {
                fieldError = true;
            }
            
            if (fieldError) {
                if (typeof setFieldError === "function" && typeof t === "function") {
                    setFieldError(fieldElement, t(fieldInfo.messageKey));
                }
                isValid = false;
            }
        }
    });

    // Basic presence check for mock payment fields
    const paymentFields = ['card-number', 'card-expiry', 'card-cvc', 'cardholder-name'];
    paymentFields.forEach(id => {
        const field = form.querySelector(`#${id}`);
        if (field && !field.value.trim()) {
            if (typeof setFieldError === "function" && typeof t === "function") {
                setFieldError(field, t('checkout.validation.paymentFieldRequired'));
            }
            isValid = false;
        }
    });

    if (!isValid) {
        if (typeof showGlobalMessage === "function" && typeof t === "function") {
            showGlobalMessage({ message: t('checkout.validation.formErrors'), type: "error" });
        }
        return;
    }

    if (submitButton && typeof showButtonLoading === "function") {
        showButtonLoading(submitButton, t('checkout.processingOrder'));
    }

    // Prepare order data
    const customerEmail = currentUser ? currentUser.email : form.querySelector('#checkout-email').value;
    const shippingAddress = {
        firstname: form.querySelector('#checkout-firstname').value,
        lastname: form.querySelector('#checkout-lastname').value,
        address_line1: form.querySelector('#checkout-address').value, // Assuming single line for now
        address_line2: form.querySelector('#checkout-apartment') ? form.querySelector('#checkout-apartment').value : '',
        postal_code: form.querySelector('#checkout-zipcode').value,
        city: form.querySelector('#checkout-city').value,
        country_code: form.querySelector('#checkout-country').value, // Assuming country is a code e.g., 'FR'
        phone: form.querySelector('#checkout-phone') ? form.querySelector('#checkout-phone').value : ''
    };
    
    // Billing address - assuming same as shipping for now if not provided separately
    const useDifferentBilling = form.querySelector('#different-billing-address') && form.querySelector('#different-billing-address').checked;
    let billingAddress = shippingAddress; // Default to same
    if (useDifferentBilling) {
        // TODO: Collect billing address fields if different billing is enabled
        // For now, this part is conceptual as HTML for different billing is not shown
        console.warn("Different billing address selected but fields not implemented in this example.");
    }


    const orderData = {
        customer_email: customerEmail, // Ensure backend expects these keys
        shipping_address: shippingAddress,
        billing_address: billingAddress, // Add billing address
        items: cart.map(item => ({ // Ensure backend expects 'items' not 'cartItems'
            product_id: item.id, // Send product_id
            variant_option_id: item.variant_option_id || null, // and variant_option_id
            quantity: item.quantity,
            price_at_purchase: item.price, // Price at time of adding to cart
            // name: item.name, // Name can be fetched server-side based on ID
            // currency: item.currency // Currency should be part of the order total or global
        })),
        user_id: currentUser ? currentUser.id : null,
        lang: typeof getCurrentLang === "function" ? getCurrentLang() : 'fr',
        // Payment details are usually tokenized by a payment provider, not sent directly like this.
        // This is a mock:
        payment_details_mock: {
            cardNumber: form.querySelector('#card-number').value.slice(-4), // Only last 4 for mock
            cardHolder: form.querySelector('#cardholder-name').value
        }
    };

    try {
        // Endpoint for creating an order: e.g., /orders
        const result = await makeApiRequest('/orders', 'POST', orderData, !!currentUser); 
        
        if (result.success || result.id) { // Check for success flag or order ID
            if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage({ 
                    message: t('checkout.orderSuccess', { orderId: result.orderId || result.id, totalAmount: parseFloat(result.total_amount || 0).toFixed(2) }), 
                    type: "success", 
                    duration: 10000 
                });
            }
            if (typeof saveCart === "function") saveCart([]); // Clear cart
            sessionStorage.setItem('lastOrderDetails', JSON.stringify(result));
            window.location.href = 'confirmation-commande.html';
        } else {
            // makeApiRequest should throw an ApiError, which is caught below.
            // This 'else' might not be reached if makeApiRequest is robust.
            if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage({ message: result.message || t('checkout.orderFailed'), type: "error" });
            }
        }
    } catch (error) {
        // ApiError message is already shown by makeApiRequest's global handler.
        // If specific handling is needed here, check error.errorCode etc.
        console.error("Checkout error:", error.message);
        // Optionally, provide more specific feedback based on error.errorCode
        // if (typeof showGlobalMessage === "function" && typeof t === "function") {
        //     showGlobalMessage({ message: error.message || t('checkout.orderFailed'), type: "error" });
        // }
    } finally {
        if (submitButton && typeof hideButtonLoading === "function") {
            hideButtonLoading(submitButton);
        }
    }
}

/**
 * Initializes the checkout page.
 * Sets up form submission listener and pre-fills user data if logged in.
 * Displays cart summary.
 */
function initializeCheckoutPage() {
    const checkoutForm = document.getElementById('checkout-form');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', handleCheckout);
    }

    const currentUser = typeof getUser === "function" ? getUser() : null;
    const checkoutEmailField = document.getElementById('checkout-email');
    const checkoutFirstname = document.getElementById('checkout-firstname');
    const checkoutLastname = document.getElementById('checkout-lastname');
    // Add other fields if you pre-fill them (address, phone etc.)

    if (currentUser) {
        if (checkoutEmailField) {
            checkoutEmailField.value = currentUser.email || '';
            checkoutEmailField.readOnly = true;
            checkoutEmailField.classList.add('bg-gray-100', 'cursor-not-allowed');
        }
        if (checkoutFirstname && (currentUser.name || currentUser.firstname)) { // Assuming 'name' might be full name or 'firstname'
             // Split name if it's a full name
            const nameParts = currentUser.name ? currentUser.name.split(' ') : [];
            checkoutFirstname.value = currentUser.firstname || nameParts[0] || '';
        }
        if (checkoutLastname && (currentUser.name || currentUser.lastname)) {
            const nameParts = currentUser.name ? currentUser.name.split(' ') : [];
            checkoutLastname.value = currentUser.lastname || (nameParts.length > 1 ? nameParts.slice(1).join(' ') : '') || '';
        }
        // Pre-fill other fields like phone, address if available in user object and desired
        // e.g., document.getElementById('checkout-address').value = currentUser.address_shipping || '';
    }

    displayCheckoutCartSummary();
    
    if (window.translatePageElements) translatePageElements(); // For static text
}

function displayCheckoutCartSummary() {
    const cart = typeof getCart === "function" ? getCart() : [];
    const checkoutCartSummary = document.getElementById('checkout-cart-summary');
    const tFunc = typeof t === 'function' ? t : (key) => key; // Fallback for t

    if (checkoutCartSummary && cart.length > 0) {
        let summaryHtml = `<h3 class="text-lg font-serif text-brand-near-black mb-4" data-translate-key="checkout.summaryTitle">${tFunc('checkout.summaryTitle')}</h3><ul class="space-y-2 mb-4">`;
        let subtotal = 0;
        cart.forEach(item => {
            const itemTotal = (item.price || 0) * (item.quantity || 0);
            summaryHtml += `<li class="flex justify-between text-sm"><span>${item.name} ${item.variant ? '(' + item.variant + ')' : ''} x ${item.quantity}</span> <span>${itemTotal.toFixed(2)}€</span></li>`;
            subtotal += itemTotal;
        });
        
        // Example shipping logic (replace with actual logic if available)
        const shippingCost = subtotal > 0 && subtotal < 75 ? 7.50 : 0; 
        const total = subtotal + shippingCost;

        summaryHtml += `</ul>
            <div class="border-t border-brand-warm-taupe/30 pt-4 space-y-1">
                <p class="flex justify-between text-sm"><span data-translate-key="checkout.subtotal">${tFunc('checkout.subtotal')}</span> <span>${subtotal.toFixed(2)}€</span></p>
                <p class="flex justify-between text-sm"><span data-translate-key="checkout.shipping">${tFunc('checkout.shipping')}</span> <span>${shippingCost > 0 ? shippingCost.toFixed(2) + '€' : tFunc('checkout.shippingFree')}</span></p>
                <p class="flex justify-between text-lg font-semibold text-brand-near-black"><span data-translate-key="checkout.total">${tFunc('checkout.total')}</span> <span>${total.toFixed(2)}€</span></p>
            </div>
        `;
        checkoutCartSummary.innerHTML = summaryHtml;
    } else if (checkoutCartSummary) {
        checkoutCartSummary.innerHTML = `<p data-translate-key="checkout.cartCurrentlyEmpty">${tFunc('checkout.cartCurrentlyEmpty')}</p>`;
        const proceedButton = document.querySelector('#checkout-form button[type="submit"]');
        if (proceedButton) {
            proceedButton.disabled = true;
            proceedButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }
}


/**
 * Initializes the order confirmation page.
 * Retrieves order details from session storage and displays them.
 */
function initializeConfirmationPage() {
    const orderDetailsString = sessionStorage.getItem('lastOrderDetails');
    const confirmationOrderIdEl = document.getElementById('confirmation-order-id');
    const confirmationTotalAmountEl = document.getElementById('confirmation-total-amount');
    const confirmationMessageEl = document.getElementById('confirmation-message'); 
    const tFunc = typeof t === 'function' ? t : (key) => key; // Fallback for t

    if (orderDetailsString && confirmationOrderIdEl && confirmationTotalAmountEl) {
        try {
            const orderDetails = JSON.parse(orderDetailsString);
            confirmationOrderIdEl.textContent = orderDetails.orderId || orderDetails.id || tFunc('confirmation.notAvailable');
            confirmationTotalAmountEl.textContent = parseFloat(orderDetails.total_amount || 0).toFixed(2);
            
            // Display a more detailed confirmation message
            if (confirmationMessageEl) {
                 confirmationMessageEl.innerHTML = `
                    <p class="text-lg text-brand-deep-sage-green font-semibold mb-2">${tFunc('confirmation.title')}</p>
                    <p>${tFunc('confirmation.thankYouMessage')}</p>
                    <p>${tFunc('confirmation.orderNumberLabel')} <strong class="text-brand-primary">${orderDetails.orderId || orderDetails.id}</strong>.</p>
                    <p>${tFunc('confirmation.emailSentMessage', { email: orderDetails.customer_email || tFunc('confirmation.yourEmailAddress') })}</p>
                    <p class="mt-4">${tFunc('confirmation.trackOrderPrompt')}</p>
                 `;
            }
            // sessionStorage.removeItem('lastOrderDetails'); // Consider removing after display
        } catch (e) {
            console.error(tFunc('confirmation.errorParsingDetails'), e);
            if (confirmationMessageEl) confirmationMessageEl.textContent = tFunc('confirmation.errorDisplayingDetails');
            if (confirmationOrderIdEl) confirmationOrderIdEl.textContent = tFunc('confirmation.notAvailable');
            if (confirmationTotalAmountEl) confirmationTotalAmountEl.textContent = tFunc('confirmation.notAvailable');
        }
    } else if (confirmationMessageEl) {
        confirmationMessageEl.textContent = tFunc('confirmation.orderDetailsNotFound');
        if (confirmationOrderIdEl) confirmationOrderIdEl.textContent = tFunc('confirmation.notAvailable');
        if (confirmationTotalAmountEl) confirmationTotalAmountEl.textContent = tFunc('confirmation.notAvailable');
    }
    
    if (window.translatePageElements) translatePageElements(); // For static text
}

// Make sure these are called appropriately, e.g., on DOMContentLoaded for relevant pages.
// Example for main.js or script tags in HTML:
// if (document.getElementById('checkout-form')) {
//   document.addEventListener('DOMContentLoaded', initializeCheckoutPage);
// }
// if (document.getElementById('confirmation-order-id')) {
//   document.addEventListener('DOMContentLoaded', initializeConfirmationPage);
// }
