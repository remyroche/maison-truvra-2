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
    } catch (e) {
        console.error(t('Erreur_parsing_panier_localStorage'), e); // Add key
        localStorage.removeItem('maisonTruvraCart');
        return [];
    }
}

function saveCart(cart) {
    localStorage.setItem('maisonTruvraCart', JSON.stringify(cart));
    updateCartCountDisplay();
    if (document.body.id === 'page-panier') {
        displayCartItems();
    }
}

function addToCart(product, quantity, selectedOptionDetails = null) {
    let cart = getCart();
    const productId = product.id;
    const cartItemId = selectedOptionDetails ? `${productId}_${selectedOptionDetails.option_id}` : productId.toString();
    const existingItemIndex = cart.findIndex(item => item.cartId === cartItemId);
    const stockAvailable = selectedOptionDetails ? parseInt(selectedOptionDetails.stock) : parseInt(product.stock_quantity);
    const itemNameForMessage = product.name + (selectedOptionDetails ? ` (${selectedOptionDetails.weight_grams}g)` : ''); // product.name is localized

    if (existingItemIndex > -1) {
        const newQuantity = cart[existingItemIndex].quantity + quantity;
        if (newQuantity > stockAvailable) {
            showGlobalMessage(t('Stock_insuffisant_MAX_pour', { productName: itemNameForMessage, stock: stockAvailable }), "error");
            return false;
        }
        cart[existingItemIndex].quantity = newQuantity;
    } else {
        if (quantity > stockAvailable) {
            showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: itemNameForMessage, stock: stockAvailable }), "error");
            return false;
        }
        const cartItem = {
            cartId: cartItemId,
            id: productId,
            name: product.name, // Localized name
            price: selectedOptionDetails ? parseFloat(selectedOptionDetails.price) : parseFloat(product.base_price),
            quantity: quantity,
            image: product.image_url_main || 'https://placehold.co/100x100/F5EEDE/7D6A4F?text=Img',
            variant: selectedOptionDetails ? `${selectedOptionDetails.weight_grams}g` : null,
            variant_option_id: selectedOptionDetails ? selectedOptionDetails.option_id : null,
            stock: stockAvailable
        };
        cart.push(cartItem);
    }
    saveCart(cart);
    return true;
}

function handleAddToCartFromDetail() {
    if (!currentProductDetail) {
        showGlobalMessage(t('Details_du_produit_non_charges'), "error");
        return;
    }
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) {
        console.error("Element 'quantity-select' not found.");
        return;
    }
    const quantity = parseInt(quantityInput.value);
    const weightOptionsSelect = document.getElementById('weight-options-select');
    let selectedOptionDetails = null;
    const productNameForMessage = currentProductDetail.name; // Localized name

    if (currentProductDetail.weight_options && currentProductDetail.weight_options.length > 0) {
        // ... (rest of the logic, ensure messages use t())
        if (!weightOptionsSelect) {
            console.error("Element 'weight-options-select' not found.");
            showGlobalMessage(t('Erreur_configuration_page'), "error"); // Add to locales
            return;
        }
        const selectedRawOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];
        if (!selectedRawOption || selectedRawOption.disabled) {
            showGlobalMessage(t('Veuillez_selectionner_une_option_de_poids_valide_et_en_stock'), "error");
            return;
        }
        selectedOptionDetails = { /* ... */ };
         if (selectedOptionDetails.stock < quantity) {
            showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: `${productNameForMessage} (${selectedOptionDetails.weight_grams}g)`, stock: selectedOptionDetails.stock }), "error");
            return;
        }
    } else {
        if (currentProductDetail.stock_quantity < quantity) {
             showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: productNameForMessage, stock: currentProductDetail.stock_quantity }), "error");
            return;
        }
    }

    const addedSuccessfully = addToCart(currentProductDetail, quantity, selectedOptionDetails);
    if (addedSuccessfully) {
        openModal('add-to-cart-modal', productNameForMessage);
    }
}

function updateCartItemQuantity(cartItemId, newQuantity) {
    let cart = getCart();
    const itemIndex = cart.findIndex(item => item.cartId === cartItemId);
    if (itemIndex > -1) {
        if (newQuantity <= 0) {
            cart.splice(itemIndex, 1);
        } else if (newQuantity > cart[itemIndex].stock) {
            showGlobalMessage(t('Quantite_maximale_de_ atteinte_pour', {stock: cart[itemIndex].stock, productName: cart[itemIndex].name }), "info");
            cart[itemIndex].quantity = cart[itemIndex].stock;
        } else {
            cart[itemIndex].quantity = newQuantity;
        }
        saveCart(cart);
    }
}

function removeCartItem(cartItemId) {
    let cart = getCart();
    cart = cart.filter(item => item.cartId !== cartItemId);
    saveCart(cart);
}

function updateCartCountDisplay() {
    const cart = getCart();
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    const cartCountDesktop = document.getElementById('cart-item-count');
    const cartCountMobile = document.getElementById('mobile-cart-item-count');
    if(cartCountDesktop) cartCountDesktop.textContent = totalItems;
    if(cartCountMobile) cartCountMobile.textContent = totalItems;
}

function displayCartItems() {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartSummaryContainer = document.getElementById('cart-summary-container');
    if (!cartItemsContainer || !cartSummaryContainer) return;

    cartItemsContainer.innerHTML = '';
    const cart = getCart();

    if (cart.length === 0) {
        cartItemsContainer.innerHTML = `<p id="empty-cart-message" class="text-center text-brand-earth-brown py-8">${t('Votre_panier_est_actuellement_vide')} <a href="nos-produits.html" class="text-brand-classic-gold hover:underline" data-translate-key="Continuer_mes_achats">${t('Continuer_mes_achats')}</a></p>`;
        cartSummaryContainer.style.display = 'none';
    } else {
        cartSummaryContainer.style.display = 'block';
        cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            const cartItemHTML = `
                <div class="cart-item" data-cart-item-id="${item.cartId}">
                    <div class="flex items-center flex-grow">
                        <img src="${item.image}" alt="${item.name}" class="cart-item-image">
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
        updateCartSummary();
    }
}

function changeCartItemQuantity(cartItemId, change) {
    const inputElement = document.querySelector(`.cart-item-quantity-input[data-id="${cartItemId}"]`);
    if (inputElement) {
        let currentQuantity = parseInt(inputElement.value);
        updateCartItemQuantity(cartItemId, currentQuantity + change);
    }
}

function updateCartSummary() {
    const cart = getCart();
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const shipping = subtotal > 0 && subtotal < 75 ? 7.50 : 0;
    const total = subtotal + shipping;

    const subtotalEl = document.getElementById('cart-subtotal');
    const shippingEl = document.getElementById('cart-shipping');
    const totalEl = document.getElementById('cart-total');

    if (subtotalEl) subtotalEl.textContent = `${subtotal.toFixed(2)} €`;
    if (shippingEl) {
        if (subtotal > 0) shippingEl.textContent = shipping > 0 ? `${shipping.toFixed(2)} €` : t('Gratuite');
        else shippingEl.textContent = 'N/A';
    }
    if (totalEl) totalEl.textContent = `${total.toFixed(2)} €`;

    const cartSummaryContainer = document.getElementById('cart-summary-container');
    if(cartSummaryContainer) cartSummaryContainer.style.display = cart.length > 0 ? 'block' : 'none';
}
