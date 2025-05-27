// website/js/product.js
// Handles fetching and displaying products on listing and detail pages.

let allProducts = []; // Cache for all products, used for client-side filtering if implemented
let currentProductDetail = null; // Holds the data for the currently viewed product detail

/**// website/js/product.js
// Handles fetching and displaying products on listing and detail pages.

let allProducts = []; // Cache for all products
let currentProductDetail = null; // Holds the data for the currently viewed product detail

/**
 * Fetches products from the API and displays them on the product listing page.
 * @param {string} [category='all'] - The category to filter by. 'all' fetches all products.
 */
async function fetchAndDisplayProducts(category = 'all') {
    const productsGrid = document.getElementById('products-grid');
    const loadingMessageElement = document.getElementById('products-loading-message');

    if (!productsGrid || !loadingMessageElement) {
        console.error("Product grid or loading message elements not found.");
        return;
    }

    loadingMessageElement.textContent = t('Chargement_des_produits');
    loadingMessageElement.style.display = 'block';
    productsGrid.innerHTML = '';

    try {
        const products = await makeApiRequest(
            category === 'all' ? '/products' : `/products?category=${encodeURIComponent(category)}`
        ); // makeApiRequest now sends 'lang'

        if (category === 'all' && products.length > 0) {
            allProducts = products;
        }

        const productsToDisplay = products; // API returns localized data

        if (productsToDisplay.length === 0) {
            loadingMessageElement.textContent = t('Aucun_produit_trouve_dans_cette_categorie');
            productsGrid.innerHTML = `<p class="col-span-full text-center text-brand-earth-brown py-8">${t('Aucun_produit_a_afficher')}</p>`;
        } else {
            loadingMessageElement.style.display = 'none';
            productsToDisplay.forEach(product => {
                const stock_quantity = product.stock_quantity !== undefined ? product.stock_quantity : 0;
                const stockMessage = stock_quantity > 5 ? t('En_stock') : (stock_quantity > 0 ? t('Stock_limite') : t('Epuise'));
                const stockClass = stock_quantity > 0 ? 'text-brand-deep-sage-green' : 'text-brand-truffle-burgundy';
                // product.name and product.short_description are now localized from the API
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
        loadingMessageElement.textContent = t('Impossible_de_charger_les_produits');
        productsGrid.innerHTML = `<p class="col-span-full text-center text-brand-truffle-burgundy py-8">${t('Impossible_de_charger_les_produits')}. ${error.message}</p>`;
    }
}

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
        if (typeof translatePageElements === 'function') translatePageElements(); // Translate filter buttons
    }
}

async function loadProductDetail() {
    const params = new URLSearchParams(window.location.search);
    const productId = params.get('id');
    const loadingDiv = document.getElementById('product-detail-loading');
    const contentDiv = document.getElementById('product-detail-content');

    if (!productId) {
        if(loadingDiv) loadingDiv.textContent = t('Aucun_produit_specifie');
        if(contentDiv) contentDiv.style.display = 'none';
        return;
    }

    if(loadingDiv) {
        loadingDiv.textContent = t('Chargement_des_details_du_produit');
        loadingDiv.style.display = 'block';
    }
    if(contentDiv) contentDiv.style.display = 'none';

    try {
        const product = await makeApiRequest(`/products/${productId}`); // API sends localized data
        currentProductDetail = product;

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
        addToCartButton.textContent = t('Ajouter_au_Panier');

        if (product.weight_options && product.weight_options.length > 0) {
            weightOptionsContainer.classList.remove('hidden');
            weightOptionsSelect.innerHTML = '';
            product.weight_options.forEach(opt => {
                const optionElement = document.createElement('option');
                optionElement.value = opt.option_id;
                const stockText = opt.stock_quantity <= 0 ? `(${t('Epuise')})` : `(Stock: ${opt.stock_quantity})`;
                optionElement.textContent = `${opt.weight_grams}g - ${parseFloat(opt.price).toFixed(2)} € ${stockText}`;
                optionElement.dataset.price = opt.price;
                optionElement.dataset.stock = opt.stock_quantity;
                optionElement.dataset.weightGrams = opt.weight_grams;
                if(opt.stock_quantity <= 0) optionElement.disabled = true;
                weightOptionsSelect.appendChild(optionElement);
            });

            let firstEnabledIndex = -1;
            for(let i=0; i<weightOptionsSelect.options.length; i++) {
                if(!weightOptionsSelect.options[i].disabled) { firstEnabledIndex = i; break; }
            }
            if(firstEnabledIndex !== -1) weightOptionsSelect.selectedIndex = firstEnabledIndex;

            updatePriceFromSelection();
            weightOptionsSelect.addEventListener('change', updatePriceFromSelection);
        } else if (product.base_price !== null) {
            priceDisplay.textContent = `${parseFloat(product.base_price).toFixed(2)} €`;
            priceUnit.textContent = '';
            weightOptionsContainer.classList.add('hidden');
             if (product.stock_quantity <= 0) {
                addToCartButton.textContent = t('Epuise');
                addToCartButton.disabled = true;
                addToCartButton.classList.replace('btn-gold','btn-secondary');
                addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
        } else {
            priceDisplay.textContent = t('Prix_sur_demande');
            priceUnit.textContent = '';
            weightOptionsContainer.classList.add('hidden');
            addToCartButton.textContent = t('Indisponible');
            addToCartButton.disabled = true;
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        }

        document.getElementById('product-species').textContent = product.species || 'N/A';
        document.getElementById('product-origin').textContent = product.origin || 'N/A';
        document.getElementById('product-seasonality').textContent = product.seasonality || 'N/A';
        document.getElementById('product-uses').textContent = product.ideal_uses || 'N/A';
        document.getElementById('product-sensory-description').innerHTML = product.long_description || product.sensory_description || t('Description_sensorielle_a_venir');
        document.getElementById('product-pairing-suggestions').textContent = product.pairing_suggestions || t('Suggestions_daccords_a_venir');
        document.getElementById('product-reviews').textContent = t('Aucun_avis_pour_le_moment');


        const thumbnailGallery = document.getElementById('product-thumbnail-gallery');
        thumbnailGallery.innerHTML = '';
        if (product.image_urls_thumb && Array.isArray(product.image_urls_thumb) && product.image_urls_thumb.length > 0) {
            product.image_urls_thumb.forEach(thumbUrl => {
                if (typeof thumbUrl === 'string') {
                    const img = document.createElement('img');
                    img.src = thumbUrl;
                    img.alt = `${product.name} miniature`; // Localized alt text
                    img.className = 'w-full h-24 object-cover rounded cursor-pointer hover:opacity-75 transition-opacity';
                    img.onclick = () => { document.getElementById('main-product-image').src = thumbUrl; };
                    img.onerror = () => { img.style.display='none'; };
                    thumbnailGallery.appendChild(img);
                }
            });
        }

        if(loadingDiv) loadingDiv.style.display = 'none';
        if(contentDiv) contentDiv.style.display = 'grid';
        // Translate any static text on this page if not covered by data-translate-key
        if (typeof translatePageElements === 'function') translatePageElements();
    } catch (error) {
        if(loadingDiv) loadingDiv.innerHTML = `<p class="text-brand-truffle-burgundy">${t('Impossible_de_charger_les_details_du_produit')} ${error.message}</p>`;
        if(contentDiv) contentDiv.style.display = 'none';
    }
}

function updatePriceFromSelection() {
    const weightOptionsSelect = document.getElementById('weight-options-select');
    const priceDisplay = document.getElementById('product-price-display');
    const priceUnit = document.getElementById('product-price-unit');
    const addToCartButton = document.getElementById('add-to-cart-button');

    if (!weightOptionsSelect || !priceDisplay || !priceUnit || !addToCartButton) return;

    const selectedOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];

    if (selectedOption && selectedOption.value) {
        priceDisplay.textContent = `${parseFloat(selectedOption.dataset.price).toFixed(2)} €`;
        priceUnit.textContent = `/ ${selectedOption.dataset.weightGrams}g`;
        if (parseInt(selectedOption.dataset.stock) <= 0 || selectedOption.disabled) {
            addToCartButton.textContent = t('Epuise');
            addToCartButton.disabled = true;
            addToCartButton.classList.replace('btn-gold','btn-secondary');
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            addToCartButton.textContent = t('Ajouter_au_Panier');
            addToCartButton.disabled = false;
            addToCartButton.classList.replace('btn-secondary','btn-gold');
            addToCartButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    } else if (currentProductDetail && currentProductDetail.base_price === null && (!currentProductDetail.weight_options || currentProductDetail.weight_options.length === 0)) {
        addToCartButton.textContent = t('Indisponible');
        addToCartButton.disabled = true;
    } else if (currentProductDetail && currentProductDetail.base_price !== null) {
        if (currentProductDetail.stock_quantity <= 0) {
            addToCartButton.textContent = t('Epuise');
            addToCartButton.disabled = true;
        } else {
            addToCartButton.textContent = t('Ajouter_au_Panier');
            addToCartButton.disabled = false;
        }
    }
}

function updateDetailQuantity(change) {
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) return;
    let currentValue = parseInt(quantityInput.value);
    currentValue += change;
    if (currentValue < 1) currentValue = 1;
    if (currentValue > 10) currentValue = 10;
    quantityInput.value = currentValue;
}
