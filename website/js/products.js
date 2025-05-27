// website/js/product.js
// Handles fetching and displaying products on listing and detail pages.

let allProducts = []; // Cache for all products, used for client-side filter// website/js/products.js

let allProducts = []; // Cache for all products, used for client-side filtering if implemented
let currentProductDetail = null; // Holds the data for the currently viewed product detail

/**
 * Fetches products from the API and displays them on the product listing page.
 * @param {string} [category='all'] - The category to filter by. 'all' fetches all products.
 */
async function fetchAndDisplayProducts(category = 'all') {
    const productsGrid = document.getElementById('products-grid');
    const loadingMessageElement = document.getElementById('products-loading-message');

    if (!productsGrid || !loadingMessageElement) {
        console.error("Product grid or loading message elements not found for product listing.");
        return;
    }

    loadingMessageElement.textContent = t('Chargement_des_produits'); // i18n
    loadingMessageElement.style.display = 'block';
    productsGrid.innerHTML = ''; // Clear previous products

    try {
        // makeApiRequest from api.js, includes lang parameter by default
        const products = await makeApiRequest(
            category === 'all' ? '/products' : `/products?category=${encodeURIComponent(category)}`
        );

        if (category === 'all' && products && products.length > 0) {
            allProducts = products; // Cache all products if fetching all
        }

        const productsToDisplay = products || [];

        if (productsToDisplay.length === 0) {
            loadingMessageElement.textContent = t('Aucun_produit_trouve_dans_cette_categorie'); // i18n
            productsGrid.innerHTML = `<p class="col-span-full text-center text-brand-earth-brown py-8">${t('Aucun_produit_a_afficher')}</p>`; // i18n
        } else {
            loadingMessageElement.style.display = 'none';
            productsToDisplay.forEach(product => {
                const stock_quantity = product.stock_quantity !== undefined ? product.stock_quantity : 0;
                const stockMessage = stock_quantity > 5 ? t('En_stock') : (stock_quantity > 0 ? t('Stock_limite') : t('Epuise')); // i18n
                const stockClass = stock_quantity > 0 ? 'text-brand-deep-sage-green' : 'text-brand-truffle-burgundy';
                // product.name and product.short_description are assumed to be localized from the API
                const productCard = `
                    <div class="product-card">
                        <a href="produit-detail.html?id=${product.id}">
                            <img src="${product.image_url_main || 'https://placehold.co/400x300/F5EEDE/7D6A4F?text=Image+Indisponible'}" alt="${product.name}" class="w-full h-64 object-cover" onerror="this.onerror=null;this.src='https://placehold.co/400x300/F5EEDE/7D6A4F?text=Image+Error';">
                        </a>
                        <div class="product-card-content">
                            <h3 class="text-xl font-serif font-semibold text-brand-near-black mb-2">${product.name}</h3>
                            <p class="text-brand-earth-brown text-sm mb-3 h-16 overflow-hidden">${product.short_description || ''}</p>
                            <p class="text-lg font-semibold text-brand-truffle-burgundy mb-4">
                                ${product.starting_price !== "N/A" && product.starting_price !== null ? `${t('A_partir_de')} ${parseFloat(product.starting_price).toFixed(2)} €` : (product.base_price ? `${parseFloat(product.base_price).toFixed(2)} €` : t('Prix_sur_demande'))}
                            </p>
                             <p class="text-xs ${stockClass} mb-4">${stockMessage}</p>
                        </div>
                        <div class="product-card-footer p-4">
                            <a href="produit-detail.html?id=${product.id}" class="btn-primary block text-center text-sm py-2.5 ${stock_quantity <=0 ? 'opacity-50 cursor-not-allowed' : ''}">${stock_quantity <= 0 ? t('Epuise') : t('Voir_le_produit')}</a>
                        </div>
                    </div>
                `;
                productsGrid.insertAdjacentHTML('beforeend', productCard);
            });
        }
    } catch (error) {
        loadingMessageElement.textContent = t('Impossible_de_charger_les_produits'); // i18n
        productsGrid.innerHTML = `<p class="col-span-full text-center text-brand-truffle-burgundy py-8">${t('Impossible_de_charger_les_produits')}. ${error.message}</p>`; // i18n
        console.error("Error fetching and displaying products:", error);
    }
}

/**
 * Sets up event listeners for product category filter buttons.
 */
function setupCategoryFilters() {
    const filterContainer = document.getElementById('product-categories-filter');
    if (filterContainer) {
        const buttons = filterContainer.querySelectorAll('button');
        buttons.forEach(button => {
            button.addEventListener('click', () => {
                buttons.forEach(btn => btn.classList.remove('filter-active', 'bg-brand-earth-brown', 'text-brand-cream'));
                button.classList.add('filter-active', 'bg-brand-earth-brown', 'text-brand-cream');
                const category = button.dataset.category;
                fetchAndDisplayProducts(category);
            });
        });
        // Ensure filter buttons themselves are translated if they use data-translate-key
        if (typeof translatePageElements === 'function') translatePageElements();
    }
}

/**
 * Loads and displays product details on the product detail page.
 * Also initializes review display and submission form.
 */
async function loadProductDetail() {
    const params = new URLSearchParams(window.location.search);
    const productId = params.get('id');
    const loadingDiv = document.getElementById('product-detail-loading');
    const contentDiv = document.getElementById('product-detail-content');

    if (!productId) {
        if (loadingDiv) loadingDiv.textContent = t('Aucun_produit_specifie'); // i18n
        if (contentDiv) contentDiv.style.display = 'none';
        return;
    }

    if (loadingDiv) {
        loadingDiv.textContent = t('Chargement_des_details_du_produit'); // i18n
        loadingDiv.style.display = 'block';
    }
    if (contentDiv) contentDiv.style.display = 'none';

    try {
        // API sends localized data based on 'lang' param in makeApiRequest
        const product = await makeApiRequest(`/products/${productId}`);
        currentProductDetail = product; // Cache for add to cart functionality

        document.getElementById('product-name').textContent = product.name;
        const mainImage = document.getElementById('main-product-image');
        mainImage.src = product.image_url_main || 'https://placehold.co/600x500/F5EEDE/7D6A4F?text=Image';
        mainImage.alt = product.name; // Alt text uses localized name
        mainImage.onerror = () => { mainImage.src = 'https://placehold.co/600x500/F5EEDE/7D6A4F?text=Image+Erreur'; };

        document.getElementById('product-short-description').textContent = product.short_description || '';

        const priceDisplay = document.getElementById('product-price-display');
        const priceUnit = document.getElementById('product-price-unit');
        const weightOptionsContainer = document.getElementById('weight-options-container');
        const weightOptionsSelect = document.getElementById('weight-options-select');
        const addToCartButton = document.getElementById('add-to-cart-button');
        addToCartButton.textContent = t('Ajouter_au_Panier'); // i18n

        if (product.weight_options && product.weight_options.length > 0) {
            weightOptionsContainer.classList.remove('hidden');
            weightOptionsSelect.innerHTML = ''; // Clear previous options
            product.weight_options.forEach(opt => {
                const optionElement = document.createElement('option');
                optionElement.value = opt.option_id;
                const stockText = opt.stock_quantity <= 0 ? `(${t('Epuise')})` : `(Stock: ${opt.stock_quantity})`; // i18n
                optionElement.textContent = `${opt.weight_grams}g - ${parseFloat(opt.price).toFixed(2)} € ${stockText}`;
                optionElement.dataset.price = opt.price;
                optionElement.dataset.stock = opt.stock_quantity;
                optionElement.dataset.weightGrams = opt.weight_grams;
                if (opt.stock_quantity <= 0) optionElement.disabled = true;
                weightOptionsSelect.appendChild(optionElement);
            });

            let firstEnabledIndex = -1;
            for (let i = 0; i < weightOptionsSelect.options.length; i++) {
                if (!weightOptionsSelect.options[i].disabled) { firstEnabledIndex = i; break; }
            }
            if (firstEnabledIndex !== -1) weightOptionsSelect.selectedIndex = firstEnabledIndex;
            else if (weightOptionsSelect.options.length > 0) weightOptionsSelect.selectedIndex = 0; // Default to first if all disabled

            updatePriceFromSelection(); // Update price and button state based on selection
            weightOptionsSelect.addEventListener('change', updatePriceFromSelection);
        } else if (product.base_price !== null) {
            priceDisplay.textContent = `${parseFloat(product.base_price).toFixed(2)} €`;
            priceUnit.textContent = '';
            weightOptionsContainer.classList.add('hidden');
            if (product.stock_quantity <= 0) {
                addToCartButton.textContent = t('Epuise'); // i18n
                addToCartButton.disabled = true;
                addToCartButton.classList.replace('btn-gold', 'btn-secondary');
                addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
        } else {
            priceDisplay.textContent = t('Prix_sur_demande'); // i18n
            priceUnit.textContent = '';
            weightOptionsContainer.classList.add('hidden');
            addToCartButton.textContent = t('Indisponible'); // i18n
            addToCartButton.disabled = true;
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        }

        // Populate other product details
        document.getElementById('product-species').textContent = product.species || t('N_A'); // i18n
        document.getElementById('product-origin').textContent = product.origin || t('N_A'); // i18n
        document.getElementById('product-seasonality').textContent = product.seasonality || t('N_A'); // i18n
        document.getElementById('product-uses').textContent = product.ideal_uses || t('N_A'); // i18n
        document.getElementById('product-sensory-description').innerHTML = product.long_description || product.sensory_description || t('Description_sensorielle_a_venir'); // i18n
        document.getElementById('product-pairing-suggestions').textContent = product.pairing_suggestions || t('Suggestions_daccords_a_venir'); // i18n

        // Thumbnail gallery
        const thumbnailGallery = document.getElementById('product-thumbnail-gallery');
        thumbnailGallery.innerHTML = ''; // Clear previous
        if (product.image_urls_thumb && Array.isArray(product.image_urls_thumb) && product.image_urls_thumb.length > 0) {
            product.image_urls_thumb.forEach(thumbUrl => {
                if (typeof thumbUrl === 'string') {
                    const img = document.createElement('img');
                    img.src = thumbUrl;
                    img.alt = t('thumbnail_alt_text', { productName: product.name }); // i18n for alt text
                    img.className = 'w-full h-24 object-cover rounded cursor-pointer hover:opacity-75 transition-opacity';
                    img.onclick = () => { document.getElementById('main-product-image').src = thumbUrl; };
                    img.onerror = () => { img.style.display = 'none'; }; // Hide broken thumbnails
                    thumbnailGallery.appendChild(img);
                }
            });
        }

        if (loadingDiv) loadingDiv.style.display = 'none';
        if (contentDiv) contentDiv.style.display = 'grid'; // Or 'block' depending on layout

        // Initialize reviews section
        displayProductReviews(productId);
        setupReviewForm(productId);

        // Translate any static text on this page if not covered by data-translate-key
        if (typeof translatePageElements === 'function') translatePageElements();

    } catch (error) {
        if (loadingDiv) loadingDiv.innerHTML = `<p class="text-brand-truffle-burgundy">${t('Impossible_de_charger_les_details_du_produit')} ${error.message}</p>`; // i18n
        if (contentDiv) contentDiv.style.display = 'none';
        console.error("Error loading product detail:", error);
    }
}

/**
 * Updates the displayed price and "Add to Cart" button state based on the selected weight option.
 */
function updatePriceFromSelection() {
    const weightOptionsSelect = document.getElementById('weight-options-select');
    const priceDisplay = document.getElementById('product-price-display');
    const priceUnit = document.getElementById('product-price-unit');
    const addToCartButton = document.getElementById('add-to-cart-button');

    if (!weightOptionsSelect || !priceDisplay || !priceUnit || !addToCartButton) return;

    const selectedOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];

    if (selectedOption && selectedOption.value && selectedOption.dataset.price) { // Ensure selected option is valid
        priceDisplay.textContent = `${parseFloat(selectedOption.dataset.price).toFixed(2)} €`;
        priceUnit.textContent = `/ ${selectedOption.dataset.weightGrams}g`;
        if (parseInt(selectedOption.dataset.stock) <= 0 || selectedOption.disabled) {
            addToCartButton.textContent = t('Epuise'); // i18n
            addToCartButton.disabled = true;
            addToCartButton.classList.replace('btn-gold', 'btn-secondary');
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            addToCartButton.textContent = t('Ajouter_au_Panier'); // i18n
            addToCartButton.disabled = false;
            addToCartButton.classList.replace('btn-secondary', 'btn-gold');
            addToCartButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    } else if (currentProductDetail && currentProductDetail.base_price === null && (!currentProductDetail.weight_options || currentProductDetail.weight_options.length === 0)) {
        // Case: No variants, no base price (should be rare for sellable items)
        addToCartButton.textContent = t('Indisponible'); // i18n
        addToCartButton.disabled = true;
    } else if (currentProductDetail && currentProductDetail.base_price !== null) {
        // Case: Simple product with base price, no variants selected/available
        if (currentProductDetail.stock_quantity <= 0) {
            addToCartButton.textContent = t('Epuise'); // i18n
            addToCartButton.disabled = true;
        } else {
            addToCartButton.textContent = t('Ajouter_au_Panier'); // i18n
            addToCartButton.disabled = false;
        }
    }
}

/**
 * Updates the quantity input field on the product detail page.
 * @param {number} change - The amount to change the quantity by (+1 or -1).
 */
function updateDetailQuantity(change) {
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) return;
    let currentValue = parseInt(quantityInput.value);
    currentValue += change;
    if (currentValue < 1) currentValue = 1;
    if (currentValue > 10) currentValue = 10; // Max quantity limit (can be dynamic)
    quantityInput.value = currentValue;
}


// --- Product Reviews ---

/**
 * Fetches and displays product reviews.
 * @param {string} productId - The ID of the product.
 */
async function displayProductReviews(productId) {
    const reviewsListDiv = document.getElementById('reviews-list');
    if (!reviewsListDiv) {
        console.warn("Reviews list container not found.");
        return;
    }
    reviewsListDiv.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Chargement_avis')}</p>`; // i18n

    try {
        const response = await makeApiRequest(`/products/${productId}/reviews`);
        if (response.success && response.reviews) {
            if (response.reviews.length === 0) {
                reviewsListDiv.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Aucun_avis_pour_le_moment')}</p>`; // i18n
            } else {
                reviewsListDiv.innerHTML = response.reviews.map(review => `
                    <div class="border-b border-brand-cream pb-3 mb-3">
                        <p class="font-semibold text-brand-near-black">
                            ${review.user_prenom || t('Utilisateur_anonyme')} 
                            <span class="text-xs text-brand-warm-taupe ml-2">- ${new Date(review.review_date).toLocaleDateString(getCurrentLang() || 'fr-FR')}</span>
                        </p>
                        <p class="text-yellow-500 my-1">${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}</p>
                        <p class="text-sm text-brand-earth-brown">${review.comment_text || ''}</p>
                    </div>
                `).join('');
            }
        } else {
            reviewsListDiv.innerHTML = `<p class="text-sm text-red-600">${response.message || t('Erreur_chargement_avis')}</p>`; // i18n
        }
    } catch (error) {
        reviewsListDiv.innerHTML = `<p class="text-sm text-red-600">${t('Erreur_chargement_avis')}</p>`; // i18n
        console.error("Error fetching reviews:", error);
    }
}

/**
 * Sets up the review submission form.
 * Shows form for logged-in users, prompt for guests. Handles form submission.
 * @param {string} productId - The ID of the product.
 */
function setupReviewForm(productId) {
    const reviewForm = document.getElementById('submit-review-form');
    const reviewLoginPrompt = document.getElementById('review-login-prompt');
    const currentUser = getCurrentUser(); // getCurrentUser from auth.js

    if (!reviewForm || !reviewLoginPrompt) {
        console.warn("Review form or login prompt not found.");
        return;
    }

    if (currentUser) {
        reviewForm.style.display = 'block';
        reviewLoginPrompt.style.display = 'none';
        reviewForm.onsubmit = async function(event) {
            event.preventDefault();
            const rating = document.getElementById('review-rating').value;
            const comment_text = document.getElementById('review-comment').value;
            const messageDiv = document.getElementById('review-form-message');
            if(messageDiv) messageDiv.textContent = '';

            try {
                // makeApiRequest from api.js, requiresAuth = true
                const result = await makeApiRequest(`/products/${productId}/reviews`, 'POST', { rating, comment_text }, true);
                if (result.success) {
                    if (typeof showGlobalMessage === "function") showGlobalMessage(result.message || t('Avis_soumis_succes'), 'success');
                    reviewForm.reset();
                    displayProductReviews(productId); // Refresh reviews list
                } else {
                    if(messageDiv) {
                        messageDiv.textContent = result.message || t('Erreur_soumission_avis');
                        messageDiv.className = 'text-sm mt-2 text-red-600';
                    } else {
                        if (typeof showGlobalMessage === "function") showGlobalMessage(result.message || t('Erreur_soumission_avis'), 'error');
                    }
                }
            } catch (error) {
                 if(messageDiv) {
                    messageDiv.textContent = error.message || t('Erreur_serveur');
                    messageDiv.className = 'text-sm mt-2 text-red-600';
                } else {
                    // Global message might have been shown by makeApiRequest
                }
                console.error("Error submitting review:", error);
            }
        };
    } else {
        reviewForm.style.display = 'none';
        reviewLoginPrompt.style.display = 'block';
    }
}
