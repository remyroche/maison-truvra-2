// website/js/cart.js
// Manages shopping cart functionality using localStorage.

/**
 * Retrieves the cart from localStorage.
 * @returns {Array<object>} The cart items array.
 */
function getCart() {
    const cartString = localStorage.getItem('maisonTruvraCart');
    try {
        return cartString ? JSON.parse(cartString) : [];
    } catch (e) {
        console.error("Erreur parsing du panier depuis localStorage:", e);
        localStorage.removeItem('maisonTruvraCart'); // Clear corrupted cart
        return [];
    }
}

/**
 * Saves the cart to localStorage and updates UI elements.
 * @param {Array<object>} cart - The cart items array to save.
 */
function saveCart(cart) {
    localStorage.setItem('maisonTruvraCart', JSON.stringify(cart));
    updateCartCountDisplay();
    // If on the cart page, refresh the displayed items
    if (document.body.id === 'page-panier') {
        displayCartItems();
    }
}

/**
 * Adds a product to the shopping cart or updates its quantity if it already exists.
 * @param {object} product - The product object from product details.
 * @param {number} quantity - The quantity to add.
 * @param {object|null} [selectedOptionDetails=null] - Details of the selected weight option, if any.
 * @returns {boolean} True if the item was added/updated successfully, false otherwise (e.g. stock issue).
 */
function addToCart(product, quantity, selectedOptionDetails = null) {
    let cart = getCart();
    const productId = product.id;
    // Create a unique ID for the cart item, especially if there are variants
    const cartItemId = selectedOptionDetails ? `${productId}_${selectedOptionDetails.option_id}` : productId.toString();

    const existingItemIndex = cart.findIndex(item => item.cartId === cartItemId);
    
    const stockAvailable = selectedOptionDetails ? parseInt(selectedOptionDetails.stock) : parseInt(product.stock_quantity);
    const itemName = product.name + (selectedOptionDetails ? ` (${selectedOptionDetails.weight_grams}g)` : '');

    if (existingItemIndex > -1) {
        const newQuantity = cart[existingItemIndex].quantity + quantity;
        if (newQuantity > stockAvailable) {
            showGlobalMessage(`Stock insuffisant. Max: ${stockAvailable} pour ${itemName}.`, "error");
            return false;
        }
        cart[existingItemIndex].quantity = newQuantity;
    } else {
        if (quantity > stockAvailable) {
            showGlobalMessage(`Stock insuffisant pour ${itemName}. Disponible: ${stockAvailable}`, "error");
            return false;
        }
        const cartItem = {
            cartId: cartItemId, // Unique identifier for the cart line item
            id: productId,      // Original product ID
            name: product.name,
            price: selectedOptionDetails ? parseFloat(selectedOptionDetails.price) : parseFloat(product.base_price),
            quantity: quantity,
            image: product.image_url_main || 'https://placehold.co/100x100/F5EEDE/7D6A4F?text=Img',
            variant: selectedOptionDetails ? `${selectedOptionDetails.weight_grams}g` : null,
            variant_option_id: selectedOptionDetails ? selectedOptionDetails.option_id : null,
            stock: stockAvailable // Store current stock for validation in cart
        };
        cart.push(cartItem);
    }
    saveCart(cart);
    return true;
}

/**
 * Handles adding a product to the cart from the product detail page.
 * Gathers product details, selected quantity, and variant options.
 */
function handleAddToCartFromDetail() {
    // currentProductDetail is expected to be a global or module-scoped variable from product.js
    if (!currentProductDetail) {
        showGlobalMessage("Détails du produit non chargés.", "error");
        return;
    }
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) {
        console.error("Élément 'quantity-select' non trouvé.");
        return;
    }
    const quantity = parseInt(quantityInput.value);
    const weightOptionsSelect = document.getElementById('weight-options-select');
    let selectedOptionDetails = null;

    if (currentProductDetail.weight_options && currentProductDetail.weight_options.length > 0) {
        if (!weightOptionsSelect) {
            console.error("Élément 'weight-options-select' non trouvé pour produit avec options.");
            showGlobalMessage("Erreur de configuration de la page.", "error");
            return;
        }
        const selectedRawOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];
        if (!selectedRawOption || selectedRawOption.disabled) {
            showGlobalMessage("Veuillez sélectionner une option de poids valide et en stock.", "error");
            return;
        }
        selectedOptionDetails = {
            option_id: selectedRawOption.value,
            price: selectedRawOption.dataset.price,
            weight_grams: selectedRawOption.dataset.weightGrams,
            stock: parseInt(selectedRawOption.dataset.stock)
        };
        if (selectedOptionDetails.stock < quantity) {
            showGlobalMessage(`Stock insuffisant pour ${currentProductDetail.name} (${selectedOptionDetails.weight_grams}g). Max: ${selectedOptionDetails.stock}`, "error");
            return;
        }
    } else { // Product without weight options
        if (currentProductDetail.stock_quantity < quantity) {
            showGlobalMessage(`Stock insuffisant pour ${currentProductDetail.name}. Max: ${currentProductDetail.stock_quantity}`, "error");
            return;
        }
    }
    
    const addedSuccessfully = addToCart(currentProductDetail, quantity, selectedOptionDetails);
    if (addedSuccessfully) {
        openModal('add-to-cart-modal', currentProductDetail.name); // Assumes openModal is in ui.js
    }
}

/**
 * Updates the quantity of an item in the cart. Removes if quantity is 0 or less.
 * @param {string} cartItemId - The unique ID of the cart item.
 * @param {number} newQuantity - The new quantity for the item.
 */
function updateCartItemQuantity(cartItemId, newQuantity) {
    let cart = getCart();
    const itemIndex = cart.findIndex(item => item.cartId === cartItemId);
    if (itemIndex > -1) {
        if (newQuantity <= 0) {
            cart.splice(itemIndex, 1); // Remove item if quantity is zero or less
        } else if (newQuantity > cart[itemIndex].stock) {
            showGlobalMessage(`Quantité maximale de ${cart[itemIndex].stock} atteinte pour ${cart[itemIndex].name}.`, "info");
            cart[itemIndex].quantity = cart[itemIndex].stock; // Set to max available stock
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
    cart = cart.filter(item => item.cartId !== cartItemId);
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
    
    if(cartCountDesktop) cartCountDesktop.textContent = totalItems;
    if(cartCountMobile) cartCountMobile.textContent = totalItems;
}

/**
 * Displays the cart items on the cart page.
 */
function displayCartItems() {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartSummaryContainer = document.getElementById('cart-summary-container'); // Ensure this ID exists

    if (!cartItemsContainer || !cartSummaryContainer) {
        console.error("Éléments du panier ou du résumé non trouvés pour l'affichage.");
        return;
    }
    
    cartItemsContainer.innerHTML = ''; // Clear previous items
    const cart = getCart();

    if (cart.length === 0) {
        cartItemsContainer.innerHTML = '<p id="empty-cart-message" class="text-center text-brand-earth-brown py-8">Votre panier est actuellement vide. <a href="nos-produits.html" class="text-brand-classic-gold hover:underline">Continuer vos achats</a></p>';
        cartSummaryContainer.style.display = 'none';
    } else {
        cartSummaryContainer.style.display = 'block'; // Or 'flex' depending on layout

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
                        <button onclick="removeCartItem('${item.cartId}')" title="Supprimer l'article" class="text-brand-truffle-burgundy hover:text-red-700">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                    </div>
                </div>
            `;
            cartItemsContainer.insertAdjacentHTML('beforeend', cartItemHTML);
        });
        updateCartSummary();
    }
}

/**
 * Changes the quantity of a cart item via input controls.
 * @param {string} cartItemId - The unique ID of the cart item.
 * @param {number} change - The amount to change the quantity by (+1 or -1).
 */
function changeCartItemQuantity(cartItemId, change) {
    const inputElement = document.querySelector(`.cart-item-quantity-input[data-id="${cartItemId}"]`);
    if (inputElement) {
        let currentQuantity = parseInt(inputElement.value);
        updateCartItemQuantity(cartItemId, currentQuantity + change);
        // displayCartItems will be called by saveCart if on cart page
    }
}

/**
 * Updates the cart summary (subtotal, shipping, total).
 */
function updateCartSummary() {
    const cart = getCart();
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    // Example shipping logic: free shipping over 75€, otherwise 7.50€
    const shipping = subtotal > 0 && subtotal < 75 ? 7.50 : 0; 
    const total = subtotal + shipping;

    const subtotalEl = document.getElementById('cart-subtotal');
    const shippingEl = document.getElementById('cart-shipping');
    const totalEl = document.getElementById('cart-total');

    if (subtotalEl) subtotalEl.textContent = `${subtotal.toFixed(2)} €`;
    if (shippingEl) {
        if (subtotal > 0) {
            shippingEl.textContent = shipping > 0 ? `${shipping.toFixed(2)} €` : 'Gratuite';
        } else {
            shippingEl.textContent = 'N/A';
        }
    }
    if (totalEl) totalEl.textContent = `${total.toFixed(2)} €`;
}
