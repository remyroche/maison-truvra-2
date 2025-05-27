// website/js/checkout.js
// Handles the checkout process and payment page logic.

/**
 * Handles the checkout form submission.
 * @param {Event} event - The form submission event.
 */
async function handleCheckout(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form); // Assumes clearFormErrors is in ui.js
    const cart = getCart(); // Assumes getCart is in cart.js
    const currentUser = getCurrentUser(); // Assumes getCurrentUser is in auth.js

    if (cart.length === 0) {
        showGlobalMessage("Votre panier est vide. Impossible de procéder au paiement.", "error"); // Assumes showGlobalMessage is in ui.js
        return;
    }

    let isValid = true;
    // Define required fields and their validation
    const requiredFields = [
        { id: 'checkout-email', validator: validateEmail, message: "E-mail invalide." }, // validateEmail from ui.js
        { id: 'checkout-firstname', message: "Prénom requis." },
        { id: 'checkout-lastname', message: "Nom requis." },
        { id: 'checkout-address', message: "Adresse requise." },
        { id: 'checkout-zipcode', message: "Code postal requis." },
        { id: 'checkout-city', message: "Ville requise." },
        { id: 'checkout-country', message: "Pays requis." }
    ];

    requiredFields.forEach(fieldInfo => {
        const fieldElement = form.querySelector(`#${fieldInfo.id}`);
        if (fieldElement) { // Field might not exist if user is logged in and info is pre-filled (e.g. email)
            const value = fieldElement.value.trim();
            if (!value || (fieldInfo.validator && !fieldInfo.validator(value))) {
                setFieldError(fieldElement, fieldInfo.message); // setFieldError from ui.js
                isValid = false;
            }
        }
    });
    
    // Basic presence check for payment fields. Actual validation would be via Stripe.js or similar.
    const paymentFields = ['card-number', 'card-expiry', 'card-cvc', 'cardholder-name'];
    paymentFields.forEach(id => {
        const field = form.querySelector(`#${id}`); // Assuming these IDs exist on paiement.html
        if(field && !field.value.trim()){ // Check if field exists before accessing value
            setFieldError(field, "Ce champ de paiement est requis.");
            isValid = false;
        }
    });

    if (!isValid) {
        showGlobalMessage("Veuillez corriger les erreurs dans le formulaire de paiement.", "error");
        return;
    }

    const customerEmail = currentUser ? currentUser.email : form.querySelector('#checkout-email').value;
    const shippingAddress = {
        firstname: form.querySelector('#checkout-firstname').value,
        lastname: form.querySelector('#checkout-lastname').value,
        address: form.querySelector('#checkout-address').value,
        apartment: form.querySelector('#checkout-apartment') ? form.querySelector('#checkout-apartment').value : '',
        zipcode: form.querySelector('#checkout-zipcode').value,
        city: form.querySelector('#checkout-city').value,
        country: form.querySelector('#checkout-country').value,
        phone: form.querySelector('#checkout-phone') ? form.querySelector('#checkout-phone').value : ''
    };
    
    const orderData = {
        customerEmail: customerEmail,
        shippingAddress: shippingAddress,
        cartItems: cart.map(item => ({ 
            id: item.id, 
            name: item.name, 
            quantity: item.quantity, 
            price: item.price, 
            variant: item.variant,
            variant_option_id: item.variant_option_id
        })),
        userId: currentUser ? currentUser.id : null
    };

    showGlobalMessage("Traitement de la commande...", "info", 60000); // Long timeout

    try {
        // makeApiRequest from api.js, API_BASE_URL from config.js
        const result = await makeApiRequest('/orders/checkout', 'POST', orderData, !!currentUser); 
        if (result.success) {
            showGlobalMessage(`Commande ${result.orderId} passée avec succès! Montant total: ${parseFloat(result.totalAmount).toFixed(2)} €`, "success", 10000);
            saveCart([]); // Clear cart (saveCart from cart.js)
            sessionStorage.setItem('lastOrderDetails', JSON.stringify(result)); // Store for confirmation page
            window.location.href = 'confirmation-commande.html'; 
        } else {
            showGlobalMessage(result.message || "Échec de la commande.", "error");
        }
    } catch (error) {
        // Error message is already shown by makeApiRequest's catch block
        console.error("Erreur lors du checkout:", error);
    }
}

/**
 * Populates the checkout page with user and cart summary information.
 * To be called on DOMContentLoaded if on the 'page-paiement'.
 */
function initializeCheckoutPage() {
    const checkoutForm = document.getElementById('checkout-form'); 
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', handleCheckout);
    }
    
    const currentUser = getCurrentUser(); // from auth.js
    const checkoutEmailField = document.getElementById('checkout-email');
    const checkoutFirstname = document.getElementById('checkout-firstname');
    const checkoutLastname = document.getElementById('checkout-lastname');

    if(currentUser && checkoutEmailField) {
        checkoutEmailField.value = currentUser.email;
        checkoutEmailField.readOnly = true; 
        checkoutEmailField.classList.add('bg-gray-100', 'cursor-not-allowed'); // Style for readonly
    }
    if(currentUser && checkoutFirstname && currentUser.prenom) {
        checkoutFirstname.value = currentUser.prenom;
    }
    if(currentUser && checkoutLastname && currentUser.nom) {
        checkoutLastname.value = currentUser.nom;
    }

    // Display cart summary on checkout page
    const cart = getCart(); // from cart.js
    const checkoutCartSummary = document.getElementById('checkout-cart-summary'); // Ensure this ID exists in paiement.html
    if(checkoutCartSummary && cart.length > 0){
        let summaryHtml = '<h3 class="text-lg font-serif text-brand-near-black mb-4">Récapitulatif de votre commande</h3><ul class="space-y-2 mb-4">';
        let subtotal = 0;
        cart.forEach(item => {
            summaryHtml += `<li class="flex justify-between text-sm"><span>${item.name} ${item.variant ? '('+item.variant+')' : ''} x ${item.quantity}</span> <span>${(item.price * item.quantity).toFixed(2)}€</span></li>`;
            subtotal += item.price * item.quantity;
        });
        const shipping = subtotal > 0 && subtotal < 75 ? 7.50 : 0; // Example shipping
        const total = subtotal + shipping;
        summaryHtml += `</ul>
            <div class="border-t border-brand-warm-taupe/30 pt-4 space-y-1">
                <p class="flex justify-between text-sm"><span>Sous-total:</span> <span>${subtotal.toFixed(2)}€</span></p>
                <p class="flex justify-between text-sm"><span>Livraison:</span> <span>${shipping > 0 ? shipping.toFixed(2)+'€' : 'Gratuite'}</span></p>
                <p class="flex justify-between text-lg font-semibold text-brand-near-black"><span>Total:</span> <span>${total.toFixed(2)}€</span></p>
            </div>
        `;
        checkoutCartSummary.innerHTML = summaryHtml;
    } else if (checkoutCartSummary) {
        checkoutCartSummary.innerHTML = '<p>Votre panier est vide.</p>';
        const proceedButton = document.querySelector('#checkout-form button[type="submit"]');
        if(proceedButton) proceedButton.disabled = true; // Disable checkout if cart is empty
    }
}

/**
 * Initializes the order confirmation page with details from sessionStorage.
 * To be called on DOMContentLoaded if on 'page-confirmation-commande'.
 */
function initializeConfirmationPage() {
    const orderDetailsString = sessionStorage.getItem('lastOrderDetails');
    const confirmationOrderIdEl = document.getElementById('confirmation-order-id');
    const confirmationTotalAmountEl = document.getElementById('confirmation-total-amount');
    const confirmationMessageEl = document.getElementById('confirmation-message'); // For displaying messages

    if (orderDetailsString && confirmationOrderIdEl && confirmationTotalAmountEl) {
        try {
            const orderDetails = JSON.parse(orderDetailsString);
            confirmationOrderIdEl.textContent = orderDetails.orderId;
            confirmationTotalAmountEl.textContent = parseFloat(orderDetails.totalAmount).toFixed(2);
            // Clear details from session storage after displaying
            // sessionStorage.removeItem('lastOrderDetails'); // Keep for refresh, or clear on new navigation
        } catch (e) {
            console.error("Erreur parsing des détails de commande:", e);
            if(confirmationMessageEl) confirmationMessageEl.textContent = "Erreur lors de l'affichage des détails de la commande.";
        }
    } else if (confirmationMessageEl) {
        confirmationMessageEl.textContent = "Détails de la commande non trouvés. Veuillez vérifier vos e-mails ou contacter le support.";
        if(confirmationOrderIdEl) confirmationOrderIdEl.textContent = "N/A";
        if(confirmationTotalAmountEl) confirmationTotalAmountEl.textContent = "N/A";
    }
}
