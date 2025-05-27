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
        showGlobalMessage(t('Votre_panier_est_vide_Impossible_de_proceder_au_paiement'), "error"); // i18n
        return;
    }

    let isValid = true;
    const requiredFields = [
        { id: 'checkout-email', validator: validateEmail, messageKey: "E-mail_invalide" },
        { id: 'checkout-firstname', messageKey: "Prenom_requis" },
        { id: 'checkout-lastname', messageKey: "Nom_requis" },
        { id: 'checkout-address', messageKey: "Adresse_requise" },
        { id: 'checkout-zipcode', messageKey: "Code_postal_requis" },
        { id: 'checkout-city', messageKey: "Ville_requise" },
        { id: 'checkout-country', messageKey: "Pays_requis" }
    ];

    requiredFields.forEach(fieldInfo => {
        const fieldElement = form.querySelector(`#${fieldInfo.id}`);
        if (fieldElement) {
            const value = fieldElement.value.trim();
            if (!value || (fieldInfo.validator && !fieldInfo.validator(value))) {
                setFieldError(fieldElement, t(fieldInfo.messageKey)); // i18n
                isValid = false;
            }
        }
    });

    const paymentFields = ['card-number', 'card-expiry', 'card-cvc', 'cardholder-name'];
    paymentFields.forEach(id => {
        const field = form.querySelector(`#${id}`);
        if(field && !field.value.trim()){
            setFieldError(field, t('Ce_champ_de_paiement_est_requis')); // i18n
            isValid = false;
        }
    });

    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire_de_paiement'), "error"); // i18n
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
            name: item.name, // Name is already localized in the cart
            quantity: item.quantity,
            price: item.price,
            variant: item.variant,
            variant_option_id: item.variant_option_id
        })),
        userId: currentUser ? currentUser.id : null,
        lang: getCurrentLang() // Send language with order for confirmation email, etc.
    };

    showGlobalMessage(t('Traitement_de_la_commande'), "info", 60000); // i18n

    try {
        const result = await makeApiRequest('/orders/checkout', 'POST', orderData, !!currentUser);
        if (result.success) {
            showGlobalMessage(t('Commande_passee_avec_succes_Montant_total', { orderId: result.orderId, totalAmount: parseFloat(result.totalAmount).toFixed(2) }), "success", 10000); // i18n
            saveCart([]);
            sessionStorage.setItem('lastOrderDetails', JSON.stringify(result));
            window.location.href = 'confirmation-commande.html';
        } else {
            showGlobalMessage(result.message || t('Echec_de_la_commande'), "error"); // i18n
        }
    } catch (error) {
        // Error message shown by makeApiRequest
        console.error("Erreur lors du checkout:", error);
    }
}

/**
 * Populates the checkout page.
 */
function initializeCheckoutPage() {
    const checkoutForm = document.getElementById('checkout-form');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', handleCheckout);
    }

    const currentUser = getCurrentUser();
    const checkoutEmailField = document.getElementById('checkout-email');
    const checkoutFirstname = document.getElementById('checkout-firstname');
    const checkoutLastname = document.getElementById('checkout-lastname');

    if(currentUser && checkoutEmailField) {
        checkoutEmailField.value = currentUser.email;
        checkoutEmailField.readOnly = true;
        checkoutEmailField.classList.add('bg-gray-100', 'cursor-not-allowed');
    }
    if(currentUser && checkoutFirstname && currentUser.prenom) {
        checkoutFirstname.value = currentUser.prenom;
    }
    if(currentUser && checkoutLastname && currentUser.nom) {
        checkoutLastname.value = currentUser.nom;
    }

    const cart = getCart();
    const checkoutCartSummary = document.getElementById('checkout-cart-summary');
    if(checkoutCartSummary && cart.length > 0){
        let summaryHtml = `<h3 class="text-lg font-serif text-brand-near-black mb-4" data-translate-key="Recapitulatif_de_votre_commande">${t('Recapitulatif_de_votre_commande')}</h3><ul class="space-y-2 mb-4">`;
        let subtotal = 0;
        cart.forEach(item => {
            summaryHtml += `<li class="flex justify-between text-sm"><span>${item.name} ${item.variant ? '('+item.variant+')' : ''} x ${item.quantity}</span> <span>${(item.price * item.quantity).toFixed(2)}€</span></li>`;
            subtotal += item.price * item.quantity;
        });
        const shipping = subtotal > 0 && subtotal < 75 ? 7.50 : 0;
        const total = subtotal + shipping;
        summaryHtml += `</ul>
            <div class="border-t border-brand-warm-taupe/30 pt-4 space-y-1">
                <p class="flex justify-between text-sm"><span data-translate-key="Sous-total">${t('Sous-total')}</span> <span>${subtotal.toFixed(2)}€</span></p>
                <p class="flex justify-between text-sm"><span data-translate-key="Livraison">${t('Livraison')}</span> <span>${shipping > 0 ? shipping.toFixed(2)+'€' : t('Gratuite')}</span></p>
                <p class="flex justify-between text-lg font-semibold text-brand-near-black"><span data-translate-key="Total">${t('Total')}</span> <span>${total.toFixed(2)}€</span></p>
            </div>
        `;
        checkoutCartSummary.innerHTML = summaryHtml;
    } else if (checkoutCartSummary) {
        checkoutCartSummary.innerHTML = `<p data-translate-key="Votre_panier_est_actuellement_vide">${t('Votre_panier_est_actuellement_vide')}</p>`;
        const proceedButton = document.querySelector('#checkout-form button[type="submit"]');
        if(proceedButton) proceedButton.disabled = true;
    }
     // Translate static parts of the form if not done by translatePageElements
    if(window.translatePageElements) translatePageElements();
}

/**
 * Initializes the order confirmation page.
 */
function initializeConfirmationPage() {
    const orderDetailsString = sessionStorage.getItem('lastOrderDetails');
    const confirmationOrderIdEl = document.getElementById('confirmation-order-id');
    const confirmationTotalAmountEl = document.getElementById('confirmation-total-amount');
    const confirmationMessageEl = document.getElementById('confirmation-message');

    if (orderDetailsString && confirmationOrderIdEl && confirmationTotalAmountEl) {
        try {
            const orderDetails = JSON.parse(orderDetailsString);
            confirmationOrderIdEl.textContent = orderDetails.orderId;
            confirmationTotalAmountEl.textContent = parseFloat(orderDetails.totalAmount).toFixed(2);
        } catch (e) {
            console.error("Erreur parsing des détails de commande:", e);
            if(confirmationMessageEl) confirmationMessageEl.textContent = t('Erreur_affichage_details_commande'); // Add key
        }
    } else if (confirmationMessageEl) {
        confirmationMessageEl.textContent = t('Details_de_la_commande_non_trouves'); // i18n
        if(confirmationOrderIdEl) confirmationOrderIdEl.textContent = "N/A";
        if(confirmationTotalAmountEl) confirmationTotalAmountEl.textContent = "N/A";
    }
    if(window.translatePageElements) translatePageElements();
}
