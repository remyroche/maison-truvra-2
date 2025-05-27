// website/js/cart.js
// Manages shopping cart functionality using localStorage.

/**
 * Retrieves the cart from localStorage.
 * @returns {Array<object>} The cart items array.
 */// website/js/cart.js

function getCart() {
    const cartString = localStorage.getItem('maisonTruvraCart');
    try {
        return cartString ? JSON.parse(cartString) : [];
    } catch (e) {// website/js/cart.js

/**
 * Retrieves the cart from localStorage.
 * @returns {Array<object>} The cart items array.
 */
function getCart() {
    const cartString = localStorage.getItem('maisonTruvraCart');
    try {
        return cartString ? JSON.parse(cartString) : [];
    } catch (e) {
        console.error(t('Erreur_parsing_panier_localStorage'), e); // i18n
        localStorage.removeItem('maisonTruvraCart'); // Clear corrupted cart
        return [];
    }
}

/**
 * Saves the cart to localStorage and updates relevant UI displays.
 * @param {Array<object>} cart - The cart items array to save.
 */
function saveCart(cart) {
    localStorage.setItem('maisonTruvraCart', JSON.stringify(cart));
    if (typeof updateCartCountDisplay === "function") updateCartCountDisplay();
    if (document.body.id === 'page-panier' && typeof displayCartItems === "function") {
        displayCartItems(); // Refresh cart page if currently viewed
    }
}

/**
 * Adds a product to the shopping cart or updates its quantity if it already exists.
 * @param {object} product - The product object (from API, should include localized name).
 * @param {number} quantity - The quantity to add.
 * @param {object|null} [selectedOptionDetails=null] - Details of the selected weight option, if any.
 * @returns {boolean} True if item was added/updated successfully, false otherwise (e.g., stock issue).
 */
function addToCart(product, quantity, selectedOptionDetails = null) {
    let cart = getCart();
    const productId = product.id;
    // Ensure cartItemId is a string for consistent matching
    const cartItemId = selectedOptionDetails ? `${productId}_${selectedOptionDetails.option_id}` : String(productId);

    const existingItemIndex = cart.findIndex(item => String(item.cartId) === cartItemId);
    const stockAvailable = selectedOptionDetails ? parseInt(selectedOptionDetails.stock) : parseInt(product.stock_quantity);
    const itemNameForMessage = product.name + (selectedOptionDetails ? ` (${selectedOptionDetails.weight_grams}g)` : ''); // product.name is already localized

    if (existingItemIndex > -1) {
        const newQuantity = cart[existingItemIndex].quantity + quantity;
        if (newQuantity > stockAvailable) {
            if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage(t('Stock_insuffisant_MAX_pour', { productName: itemNameForMessage, stock: stockAvailable }), "error");
            }
            return false;
        }
        cart[existingItemIndex].quantity = newQuantity;
    } else {
        if (quantity > stockAvailable) {
             if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: itemNameForMessage, stock: stockAvailable }), "error");
            }
            return false;
        }
        const cartItem = {
            cartId: cartItemId, // Store as string
            id: productId,
            name: product.name, // Assumed to be localized from product detail
            price: selectedOptionDetails ? parseFloat(selectedOptionDetails.price) : parseFloat(product.base_price),
            quantity: quantity,
            image: product.image_url_main || 'https://placehold.co/100x100/F5EEDE/7D6A4F?text=Img',
            variant: selectedOptionDetails ? `${selectedOptionDetails.weight_grams}g` : null,
            variant_option_id: selectedOptionDetails ? selectedOptionDetails.option_id : null,
            stock: stockAvailable // Store current stock for reference in cart
        };
        cart.push(cartItem);
    }
    saveCart(cart);
    return true;
}

/**
 * Handles adding a product to the cart from the product detail page.
 * Gathers selected quantity and weight option (if any).
 */
function handleAddToCartFromDetail() {
    if (!currentProductDetail) { // currentProductDetail from product.js
        if (typeof showGlobalMessage === "function" && typeof t === "function") {
            showGlobalMessage(t('Details_du_produit_non_charges'), "error");
        }
        return;
    }
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) {
        console.error("Element 'quantity-select' not found on product detail page.");
        if (typeof showGlobalMessage === "function" && typeof t === "function") {
             showGlobalMessage(t('Erreur_configuration_page'), "error"); // Generic error
        }
        return;
    }
    const quantity = parseInt(quantityInput.value);
    const weightOptionsSelect = document.getElementById('weight-options-select');
    let selectedOptionDetails = null;
    const productNameForMessage = currentProductDetail.name; // Already localized

    if (currentProductDetail.weight_options && currentProductDetail.weight_options.length > 0) {
        if (!weightOptionsSelect) {
            console.error("Element 'weight-options-select' not found.");
             if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage(t('Erreur_configuration_page'), "error");
            }
            return;
        }
        const selectedRawOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];
        if (!selectedRawOption || selectedRawOption.disabled) {
             if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage(t('Veuillez_selectionner_une_option_de_poids_valide_et_en_stock'), "error");
            }
            return;
        }
        selectedOptionDetails = {
            option_id: selectedRawOption.value,
            price: selectedRawOption.dataset.price,
            weight_grams: selectedRawOption.dataset.weightGrams,
            stock: parseInt(selectedRawOption.dataset.stock)
        };
        if (selectedOptionDetails.stock < quantity) {
            if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: `${productNameForMessage} (${selectedOptionDetails.weight_grams}g)`, stock: selectedOptionDetails.stock }), "error");
            }
            return;
        }
    } else { // Simple product (no weight options)
        if (currentProductDetail.stock_quantity < quantity) {
            if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: productNameForMessage, stock: currentProductDetail.stock_quantity }), "error");
            }
            return;
        }
    }

    const addedSuccessfully = addToCart(currentProductDetail, quantity, selectedOptionDetails);
    if (addedSuccessfully && typeof openModal === "function") {
        openModal('add-to-cart-modal', productNameForMessage); // openModal from ui.js
    }
}

/**
 * Updates the quantity of an item in the cart. Removes item if quantity <= 0.
 * Prevents quantity from exceeding available stock.
 * @param {string} cartItemId - The unique ID of the cart item.
 * @param {number} newQuantity - The new quantity for the item.
 */
function updateCartItemQuantity(cartItemId, newQuantity) {
    let cart = getCart();
    const itemIndex = cart.findIndex(item => String(item.cartId) === String(cartItemId));
    if (itemIndex > -1) {
        if (newQuantity <= 0) {
            cart.splice(itemIndex, 1); // Remove item
        } else if (newQuantity > cart[itemIndex].stock) {
            if (typeof showGlobalMessage === "function" && typeof t === "function") {
                showGlobalMessage(t('Quantite_maximale_de_ atteinte_pour', { stock: cart[itemIndex].stock, productName: cart[itemIndex].name }), "info");
            }
            cart[itemIndex].quantity = cart[itemIndex].stock; // Set to max available
        } else {
            cart[itemIndex].quantity = newQuantity;
        }
        saveCart(cart);
    }
}

/**
 * Removes an item completely from the cart.
 * @param {string} cartItemId - The unique ID of the cart item to remove.
 */
function removeCartItem(cartItemId) {
    let cart = getCart();
    cart = cart.filter(item => String(item.cartId) !== String(cartItemId));
    saveCart(cart);
}

/**
 * Updates the cart item count display in the header.
 */
function updateCartCountDisplay() {
    const cart = getCart();
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    const cartCountDesktop = document.getElementById('cart-item-count');
    const cartCountMobile = document.getElementById('mobile-cart-item-count');

    if (cartCountDesktop) cartCountDesktop.textContent = totalItems;
    if (cartCountMobile) cartCountMobile.textContent = totalItems;
}

/**
 * Displays cart items on the cart page.
 * Handles empty cart message and summary display.
 */
function displayCartItems() {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartSummaryContainer = document.getElementById('cart-summary-container');

    if (!cartItemsContainer || !cartSummaryContainer) {
        console.error("Cart items or summary container not found on cart page.");
        return;
    }

    cartItemsContainer.innerHTML = ''; // Clear previous items
    const cart = getCart();

    if (cart.length === 0) {
        cartItemsContainer.innerHTML = `<p id="empty-cart-message" class="text-center text-brand-earth-brown py-8">${t('Votre_panier_est_actuellement_vide')} <a href="nos-produits.html" class="text-brand-classic-gold hover:underline" data-translate-key="Continuer_mes_achats">${t('Continuer_mes_achats')}</a></p>`;
        cartSummaryContainer.style.display = 'none';
    } else {
        cartSummaryContainer.style.display = 'block'; // Or 'flex' depending on layout
        cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            const cartItemHTML = `
                <div class="cart-item" data-cart-item-id="${item.cartId}">
                    <div class="flex items-center flex-grow">
                        <img src="${item.image}" alt="${item.name}" class="cart-item-image" onerror="this.onerror=null;this.src='https://placehold.co/80x80/F5EEDE/7D6A4F?text=ImgErr';">
                        <div>
                            <h3 class="text-md font-semibold text-brand-near-black">${item.name}</h3>
                            ${item.variant ? `<p class="text-xs text-brand-warm-taupe">${item.variant}</p>` : ''}
                            <p class="text-sm text-brand-classic-gold">${parseFloat(item.price).toFixed(2)} €</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2 sm:space-x-3">
                        <div class="quantity-input-controls flex items-center">
                            <button onclick="changeCartItemQuantity('${item.cartId}', -1)" class="px-2 py-0.5 border border-brand-warm-taupe/50 text-brand-near-black hover:bg-brand-warm-taupe/20 text-sm rounded-l">-</button>
                            <input type="number" value="${item.quantity}" min="1" max="${item.stock}" class="quantity-input cart-item-quantity-input w-10 sm:w-12 text-center border-y border-brand-warm-taupe/50 py-1 text-sm appearance-none" readonly data-id="${item.cartId}">
                            <button onclick="changeCartItemQuantity('${item.cartId}', 1)" class="px-2 py-0.5 border border-brand-warm-taupe/50 text-brand-near-black hover:bg-brand-warm-taupe/20 text-sm rounded-r">+</button>
                        </div>
                        <p class="text-md font-semibold text-brand-near-black w-20 text-right">${itemTotal.toFixed(2)} €</p>
                        <button onclick="removeCartItem('${item.cartId}')" title="${t('Supprimer_larticle')}" class="text-brand-truffle-burgundy hover:text-red-700">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                    </div>
                </div>`;
            cartItemsContainer.insertAdjacentHTML('beforeend', cartItemHTML);
        });
        if (typeof updateCartSummary === "function") updateCartSummary();
    }
}

/**
 * Helper function to change item quantity from cart page controls.
 * @param {string} cartItemId - The ID of the cart item.
 * @param {number} change - The amount to change the quantity by (+1 or -1).
 */
function changeCartItemQuantity(cartItemId, change) {
    const inputElement = document.querySelector(`.cart-item-quantity-input[data-id="${cartItemId}"]`);
    if (inputElement) {
        let currentQuantity = parseInt(inputElement.value);
        updateCartItemQuantity(cartItemId, currentQuantity + change);
        // displayCartItems() will be called by saveCart() to re-render the specific item or whole list
    }
}

/**
 * Updates the cart summary section (subtotal, shipping, total) on the cart page.
 */
function updateCartSummary() {
    const cart = getCart();
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    // Example shipping logic: Free over 75€, otherwise 7.50€.
    // This could be more complex, fetched from an API, or based on weight/destination.
    const shipping = subtotal > 0 && subtotal < 75 ? 7.50 : 0;
    const total = subtotal + shipping;

    const subtotalEl = document.getElementById('cart-subtotal');
    const shippingEl = document.getElementById('cart-shipping');
    const totalEl = document.getElementById('cart-total');

    if (subtotalEl) subtotalEl.textContent = `${subtotal.toFixed(2)} €`;
    if (shippingEl) {
        if (subtotal > 0) {
            shippingEl.textContent = shipping > 0 ? `${shipping.toFixed(2)} €` : t('Gratuite');
        } else {
            shippingEl.textContent = t('N_A'); // Not Applicable or a dash
        }
    }
    if (totalEl) totalEl.textContent = `${total.toFixed(2)} €`;

    // Ensure summary container visibility is correct based on cart contents
    const cartSummaryContainer = document.getElementById('cart-summary-container');
    if (cartSummaryContainer) {
        cartSummaryContainer.style.display = cart.length > 0 ? 'block' : 'none'; // Or 'flex' based on layout
    }
}
