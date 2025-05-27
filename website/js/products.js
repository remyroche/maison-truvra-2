// website/js/product.js
// Handles fetching and displaying products on listing and detail pages.

let allProducts = []; // Cache for all products, used for client-side filter// website/js/products.js

let allProducts = []; // Cache for all products, used for client-side filtering if implemented
let currentProductDetail = null; // Holds the data for the currently viewed product detail

/**
 * Fetches products from the API and displays them on the product listing page.// website/js/products.js

// Assumes API_BASE_URL, makeApiRequest, translate, currentLanguage, formatPrice, showGlobalMessage, getUser, isUserLoggedIn are available

let currentProductDetails = null; // To store details for review submission

async function loadProducts(category = 'all', searchTerm = '', sortBy = 'name_asc', page = 1, limit = 10) {
    const productsGrid = document.getElementById('products-grid');
    const loadingIndicator = document.getElementById('loading-products');
    const noProductsMessage = document.getElementById('no-products-message');
    // const paginationControls = document.getElementById('pagination-controls');

    if (!productsGrid || !loadingIndicator || !noProductsMessage) {
        console.error('Required product display elements not found.');
        return;
    }

    loadingIndicator.classList.remove('hidden');
    productsGrid.innerHTML = '';
    noProductsMessage.classList.add('hidden');
    // if (paginationControls) paginationControls.innerHTML = '';

    try {
        let url = `/api/products?page=${page}&limit=${limit}&sort_by=${sortBy}`;
        if (category !== 'all') {
            url += `&category_key=${category}`;
        }
        if (searchTerm) {
            url += `&search=${encodeURIComponent(searchTerm)}`;
        }
        
        const response = await makeApiRequest(url, 'GET');
        const products = response.products; // Assuming API returns { products: [], total_pages: X, current_page: Y }

        if (products && products.length > 0) {
            products.forEach(product => {
                const productCard = `
                    <div class="bg-white rounded-lg shadow-lg overflow-hidden transition-all duration-300 hover:shadow-xl group">
                        <a href="produit-detail.html?id=${product.id}" class="block">
                            <div class="w-full h-48 md:h-64 overflow-hidden">
                                <img src="${product.image_url_main || 'https://placehold.co/600x400/F5F0E6/4A3B31?text=' + encodeURIComponent(product[`name_${currentLanguage}`] || product.name_en)}" 
                                     alt="${product[`name_${currentLanguage}`] || product.name_en}" 
                                     class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                     onerror="this.onerror=null;this.src='https://placehold.co/600x400/F5F0E6/4A3B31?text=Image+Indisponible';">
                            </div>
                            <div class="p-4">
                                <h3 class="text-lg font-serif text-brand-primary group-hover:text-brand-accent truncate" title="${product[`name_${currentLanguage}`] || product.name_en}">
                                    ${product[`name_${currentLanguage}`] || product.name_en}
                                </h3>
                                <p class="text-sm text-brand-dark-taupe mt-1 h-10 overflow-hidden">
                                    ${(product[`short_description_${currentLanguage}`] || product.short_description_en || '').substring(0, 60)}...
                                </p>
                                <p class="text-xl font-semibold text-brand-accent mt-3">
                                    ${formatPrice(product.base_price, product.currency)}
                                </p>
                            </div>
                        </a>
                        <div class="p-4 border-t border-gray-200">
                             <button onclick="quickAddToCart(${product.id}, '${product[`name_${currentLanguage}`] || product.name_en}', ${product.base_price}, '${product.image_url_main}', 1, null)" 
                                    class="w-full bg-brand-primary hover:bg-brand-secondary text-white font-semibold py-2 px-4 rounded-md transition duration-150 text-sm flex items-center justify-center">
                                <i class="fas fa-cart-plus mr-2"></i> <span data-i18n="products.addToCart">${translate('products.addToCart')}</span>
                            </button>
                        </div>
                    </div>
                `;
                productsGrid.innerHTML += productCard;
            });
            // TODO: Implement pagination controls based on response.total_pages and response.current_page
        } else {
            noProductsMessage.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error loading products:', error);
        productsGrid.innerHTML = `<p class="text-red-500 col-span-full">${translate('products.errorLoading')}</p>`;
        noProductsMessage.classList.remove('hidden');
        noProductsMessage.textContent = translate('products.errorLoading');

    } finally {
        loadingIndicator.classList.add('hidden');
    }
}

async function loadProductDetail() {
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('id');

    if (!productId) {
        document.getElementById('product-detail-container').innerHTML = `<p class="text-red-500">${translate('productDetail.invalidProduct')}</p>`;
        return;
    }

    const loadingIndicator = document.getElementById('loading-product-detail');
    const productContainer = document.getElementById('product-detail-container');
    
    loadingIndicator.classList.remove('hidden');
    productContainer.classList.add('hidden');

    try {
        const product = await makeApiRequest(`/api/products/${productId}`, 'GET');
        currentProductDetails = product; // Store for review submission

        document.title = `${product[`name_${currentLanguage}`] || product.name_en} - Maison Trüvra`;
        
        document.getElementById('product-image').src = product.image_url_main || 'https://placehold.co/600x400/F5F0E6/4A3B31?text=Image+Indisponible';
        document.getElementById('product-image').alt = product[`name_${currentLanguage}`] || product.name_en;
        document.getElementById('product-name').textContent = product[`name_${currentLanguage}`] || product.name_en;
        document.getElementById('product-short-description').textContent = product[`short_description_${currentLanguage}`] || product.short_description_en;
        document.getElementById('product-long-description').innerHTML = product[`long_description_${currentLanguage}`] || product.long_description_en; // Use innerHTML if description contains HTML
        
        const priceElement = document.getElementById('product-price');
        priceElement.textContent = formatPrice(product.base_price, product.currency);

        const weightSelector = document.getElementById('product-weight-selector');
        const variants = product.variants || [];
        if (variants.length > 0) {
            weightSelector.innerHTML = `<label for="variant" class="block text-sm font-medium text-brand-dark-taupe mb-1" data-i18n="productDetail.selectWeight">${translate('productDetail.selectWeight')}:</label>`;
            const selectEl = document.createElement('select');
            selectEl.id = 'variant-select';
            selectEl.className = 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-brand-primary focus:border-brand-primary sm:text-sm rounded-md';
            
            // Add base product as an option if it has a weight/price
            if (product.weight_g && product.base_price) {
                 const baseOption = document.createElement('option');
                 baseOption.value = `base_${product.base_price}_${product.weight_g}`; // Store price and weight
                 baseOption.textContent = `${product.weight_g}g - ${formatPrice(product.base_price, product.currency)}`;
                 baseOption.dataset.price = product.base_price;
                 baseOption.dataset.weight = product.weight_g;
                 baseOption.dataset.variantId = "base"; // Special ID for base product
                 selectEl.appendChild(baseOption);
            }


            variants.forEach(variant => {
                const option = document.createElement('option');
                option.value = `variant_${variant.id}_${variant.price}_${variant.weight_g}`; // Store variant ID, price, and weight
                option.textContent = `${variant.weight_g}g (${variant.name_fr || variant.name_en}) - ${formatPrice(variant.price, product.currency)}`;
                option.dataset.price = variant.price;
                option.dataset.weight = variant.weight_g;
                option.dataset.variantId = variant.id;
                selectEl.appendChild(option);
            });
            weightSelector.appendChild(selectEl);

            selectEl.addEventListener('change', (event) => {
                const selectedOption = event.target.selectedOptions[0];
                const price = parseFloat(selectedOption.dataset.price);
                priceElement.textContent = formatPrice(price, product.currency);
            });
        } else {
            weightSelector.innerHTML = ''; // No variants
        }

        const addToCartButton = document.getElementById('add-to-cart-button');
        addToCartButton.onclick = () => {
            const quantity = parseInt(document.getElementById('quantity-input').value) || 1;
            let selectedVariantId = null;
            let currentPrice = product.base_price;
            let selectedWeightText = product.weight_g ? `${product.weight_g}g` : null;

            const variantSelect = document.getElementById('variant-select');
            if (variantSelect && variantSelect.value) {
                const selectedOption = variantSelect.selectedOptions[0];
                currentPrice = parseFloat(selectedOption.dataset.price);
                selectedVariantId = selectedOption.dataset.variantId === "base" ? null : parseInt(selectedOption.dataset.variantId);
                selectedWeightText = selectedOption.textContent.split(' - ')[0]; // e.g., "30g (Extra)"
            }
            
            quickAddToCart(
                product.id, 
                product[`name_${currentLanguage}`] || product.name_en, 
                currentPrice, 
                product.image_url_main, 
                quantity, 
                selectedVariantId,
                selectedWeightText // Pass the descriptive text of the variant/weight
            );
        };

        // Load reviews
        await loadProductReviews(productId);

        // Show/hide review form based on login status
        const reviewFormSection = document.getElementById('review-submission-form');
        const loginToReviewMessage = document.getElementById('login-to-review-message');
        if (isUserLoggedIn()) {
            reviewFormSection.classList.remove('hidden');
            loginToReviewMessage.classList.add('hidden');
        } else {
            reviewFormSection.classList.add('hidden');
            loginToReviewMessage.classList.remove('hidden');
        }


        productContainer.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading product detail:', error);
        productContainer.innerHTML = `<p class="text-red-500 col-span-full">${translate('productDetail.errorLoading')}</p>`;
        productContainer.classList.remove('hidden');
    } finally {
        loadingIndicator.classList.add('hidden');
    }
}


async function loadProductReviews(productId) {
    const reviewsContainer = document.getElementById('product-reviews-list');
    if (!reviewsContainer) return;

    try {
        const reviewsData = await makeApiRequest(`/api/products/${productId}/reviews`, 'GET');
        // Filter for approved reviews only on the frontend for now
        const approvedReviews = reviewsData.reviews ? reviewsData.reviews.filter(review => review.is_approved) : [];


        if (approvedReviews && approvedReviews.length > 0) {
            reviewsContainer.innerHTML = approvedReviews.map(review => `
                <div class="border-t border-gray-200 py-4">
                    <div class="flex items-center mb-1">
                        <div class="flex items-center">
                            ${[...Array(5)].map((_, i) => `<i class="fas fa-star ${i < review.rating ? 'text-yellow-400' : 'text-gray-300'}"></i>`).join('')}
                        </div>
                        <p class="ml-2 text-sm font-semibold text-brand-primary">${review.user_name || translate('productDetail.anonymousUser')}</p>
                    </div>
                    <p class="text-xs text-gray-500 mb-2">${new Date(review.created_at).toLocaleDateString(currentLanguage || 'fr-FR')}</p>
                    <p class="text-brand-dark-taupe text-sm">${review.comment}</p>
                </div>
            `).join('');
        } else {
            reviewsContainer.innerHTML = `<p class="text-sm text-gray-500" data-i18n="productDetail.noReviews">${translate('productDetail.noReviews')}</p>`;
        }
    } catch (error) {
        console.error('Error loading reviews:', error);
        reviewsContainer.innerHTML = `<p class="text-red-500 text-sm">${translate('productDetail.errorLoadingReviews')}</p>`;
    }
}

async function submitReview(event) {
    event.preventDefault();
    if (!currentProductDetails || !currentProductDetails.id) {
        showGlobalMessage(translate('productDetail.errorReviewNoProduct'), 'error');
        return;
    }
     if (!isUserLoggedIn()) {
        showGlobalMessage(translate('productDetail.mustBeLoggedInToReview'), 'error');
        return;
    }


    const rating = document.getElementById('review-rating').value;
    const comment = document.getElementById('review-comment').value;
    const reviewMessageDiv = document.getElementById('review-form-message');

    if (!rating || !comment) {
        reviewMessageDiv.textContent = translate('productDetail.ratingCommentRequired');
        reviewMessageDiv.className = 'text-red-600 mt-2 text-sm';
        return;
    }

    try {
        const response = await makeApiRequest(
            `/api/products/${currentProductDetails.id}/reviews`, 
            'POST', 
            { rating: parseInt(rating), comment: comment },
            true // Requires authentication
        );
        reviewMessageDiv.textContent = translate('productDetail.reviewSubmittedThanks');
        reviewMessageDiv.className = 'text-green-600 mt-2 text-sm';
        document.getElementById('review-form').reset();
        // Optionally, reload reviews or optimistically add the (unapproved) review to the list
        // For now, we'll just show the message. Admin will approve.
        showGlobalMessage(translate('productDetail.reviewSubmittedAdminApproval'), 'success');

    } catch (error) {
        console.error('Error submitting review:', error);
        reviewMessageDiv.textContent = error.message || translate('productDetail.errorSubmittingReview');
        reviewMessageDiv.className = 'text-red-600 mt-2 text-sm';
        showGlobalMessage(error.message || translate('productDetail.errorSubmittingReview'), 'error');
    }
}


// Quick add to cart function (simplified)
function quickAddToCart(productId, name, price, image, quantity = 1, variantId = null, variantDescription = null) {
    let cart = JSON.parse(localStorage.getItem('cart')) || [];
    
    // Create a unique ID for the cart item: productID + variantID (if exists)
    const cartItemId = variantId ? `${productId}-${variantId}` : `${productId}-base`;

    const existingItemIndex = cart.findIndex(item => item.cartItemId === cartItemId);

    if (existingItemIndex > -1) {
        cart[existingItemIndex].quantity += quantity;
    } else {
        cart.push({ 
            cartItemId, // Use this compound ID
            id: productId, // Original product ID
            name: name, 
            price: price, 
            image: image, 
            quantity: quantity,
            variantId: variantId, // Store variant ID
            variantDescription: variantDescription // Store descriptive text like "30g" or "50g (Extra)"
        });
    }
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartIcon(); // from ui.js
    showGlobalMessage(`${name} ${variantDescription ? '('+variantDescription+') ' : ''}${translate('products.addedToCart')}`, 'success');
}


// Initial setup for product listing page
if (document.getElementById('products-grid')) {
    document.addEventListener('DOMContentLoaded', () => {
        loadProducts(); // Load all products initially

        const categoryFilter = document.getElementById('category-filter');
        const searchInput = document.getElementById('search-input');
        const sortByFilter = document.getElementById('sort-by-filter');

        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => loadProducts(e.target.value, searchInput ? searchInput.value : '', sortByFilter ? sortByFilter.value : 'name_asc'));
        }
        if (searchInput) {
            searchInput.addEventListener('input', debounce((e) => loadProducts(categoryFilter ? categoryFilter.value : 'all', e.target.value, sortByFilter ? sortByFilter.value : 'name_asc'), 300));
        }
        if (sortByFilter) {
            sortByFilter.addEventListener('change', (e) => loadProducts(categoryFilter ? categoryFilter.value : 'all', searchInput ? searchInput.value : '', e.target.value));
        }
    });
}

// Initial setup for product detail page
if (document.getElementById('product-detail-container')) {
    document.addEventListener('DOMContentLoaded', () => {
        loadProductDetail();
        const reviewForm = document.getElementById('review-form');
        if (reviewForm) {
            reviewForm.addEventListener('submit', submitReview);
        }
    });
}

// Debounce utility
function debounce(func, delay) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}
