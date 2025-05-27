// File: website/admin/js/admin_products.js

document.addEventListener('DOMContentLoaded', () => {
    // Ensure admin is authenticated (function from admin_auth.js)
    // This should be called on all admin pages that require login.
    // if (!ensureAdminAuthenticated()) { return; } // ensureAdminAuthenticated handles redirection

    // --- DOM Elements ---
    const addProductBtn = document.getElementById('addProductBtn');
    const productModal = document.getElementById('productModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const cancelModalBtn = document.getElementById('cancelModalBtn');
    const productForm = document.getElementById('productForm');
    const modalTitle = document.getElementById('modalTitle');
    const productsTableBody = document.getElementById('productsTableBody');
    const productSearchInput = document.getElementById('productSearchInput');
    const productImageInput = document.getElementById('productImage'); // Renamed for clarity
    const imagePreview = document.getElementById('imagePreview');
    const productCategorySelect = document.getElementById('productCategory');
    const formMessage = document.getElementById('formMessage'); // For messages inside the modal
    const paginationControls = document.getElementById('paginationControls');
    const saveProductBtn = document.getElementById('saveProductBtn');

    const productTypeSelect = document.getElementById('productType');
    const variableOptionsContainer = document.getElementById('variableOptionsContainer');
    const addWeightOptionBtn = document.getElementById('addWeightOptionBtn');
    const weightOptionsList = document.getElementById('weightOptionsList');

    // --- State ---
    let currentProducts = [];
    let editingProductId = null;
    let currentPage = 1;
    const productsPerPage = 10;

    // --- Modal Handling ---
    const openModal = (isEdit = false, product = null) => {
        clearFormMessage(); // Clear previous messages
        productForm.reset();
        imagePreview.classList.add('hidden');
        imagePreview.src = '#';
        weightOptionsList.innerHTML = '';
        productTypeSelect.value = 'simple'; // Default
        variableOptionsContainer.classList.add('hidden');
        saveProductBtn.disabled = false;
        saveProductBtn.textContent = 'Save Product';


        if (isEdit && product) {
            modalTitle.textContent = 'Edit Product';
            editingProductId = product.id;
            document.getElementById('productId').value = product.id;
            document.getElementById('productName').value = product.name;
            document.getElementById('productDescription').value = product.description;
            document.getElementById('productPrice').value = product.price;
            document.getElementById('productStock').value = product.stock_quantity;
            productCategorySelect.value = product.category_id; // Ensure categories are loaded before this
            productTypeSelect.value = product.type || 'simple';

            if (product.image_url) {
                // Construct absolute URL if image_url is relative
                const fullImageUrl = product.image_url.startsWith('http') ? product.image_url : `${API_BASE_URL.replace('/api/admin', '')}/${product.image_url.startsWith('/') ? product.image_url.substring(1) : product.image_url}`;
                imagePreview.src = fullImageUrl;
                imagePreview.classList.remove('hidden');
            }

            if (product.type === 'variable' && product.weight_options && product.weight_options.length > 0) {
                variableOptionsContainer.classList.remove('hidden');
                product.weight_options.forEach(opt => addWeightOptionToForm(opt.weight_grams, opt.price_modifier, opt.stock_quantity));
            } else {
                variableOptionsContainer.classList.add('hidden');
            }

        } else {
            modalTitle.textContent = 'Add New Product';
            editingProductId = null;
            document.getElementById('productId').value = '';
        }
        productModal.classList.remove('opacity-0', 'pointer-events-none');
        productModal.classList.add('opacity-100');
        document.body.classList.add('modal-active');
    };

    const closeModal = () => {
        productModal.classList.add('opacity-0');
        productModal.classList.remove('opacity-100');
        setTimeout(() => {
            productModal.classList.add('pointer-events-none');
            document.body.classList.remove('modal-active');
        }, 250);
    };

    if (addProductBtn) addProductBtn.addEventListener('click', () => openModal());
    if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeModal);

    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !productModal.classList.contains('pointer-events-none')) {
            closeModal();
        }
    });

    // --- Product Type Change (Simple/Variable) ---
    if (productTypeSelect) {
        productTypeSelect.addEventListener('change', (e) => {
            if (e.target.value === 'variable') {
                variableOptionsContainer.classList.remove('hidden');
                if (weightOptionsList.children.length === 0) {
                    addWeightOptionToForm();
                }
            } else {
                variableOptionsContainer.classList.add('hidden');
            }
        });
    }
    if (addWeightOptionBtn) addWeightOptionBtn.addEventListener('click', () => addWeightOptionToForm());

    function addWeightOptionToForm(weight = '', priceModifier = '', stock = '') {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'flex items-center space-x-2 mb-2 p-2 border rounded-md bg-gray-50'; // Added bg for distinction
        optionDiv.innerHTML = `
            <input type="number" placeholder="Weight (g)" value="${weight}" class="weight-grams mt-1 block w-1/3 px-2 py-1 border border-gray-300 rounded-md shadow-sm text-sm focus:ring-indigo-500 focus:border-indigo-500" required>
            <input type="number" step="0.01" placeholder="Price Mod (+/-)" value="${priceModifier}" class="price-modifier mt-1 block w-1/3 px-2 py-1 border border-gray-300 rounded-md shadow-sm text-sm focus:ring-indigo-500 focus:border-indigo-500" required>
            <input type="number" placeholder="Stock" value="${stock}" class="weight-stock mt-1 block w-1/3 px-2 py-1 border border-gray-300 rounded-md shadow-sm text-sm focus:ring-indigo-500 focus:border-indigo-500" required>
            <button type="button" class="remove-weight-option text-red-500 hover:text-red-700 p-1 rounded-full hover:bg-red-100 transition-colors" title="Remove option">&times;</button>
        `;
        weightOptionsList.appendChild(optionDiv);
        optionDiv.querySelector('.remove-weight-option').addEventListener('click', () => optionDiv.remove());
    }

    // --- Image Preview ---
    if (productImageInput) {
        productImageInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreview.classList.remove('hidden');
                }
                reader.readAsDataURL(file);
            } else {
                imagePreview.classList.add('hidden');
                imagePreview.src = '#';
            }
        });
    }

    // --- Load Categories for Select Dropdown ---
    const loadCategories = async () => {
        if (!productCategorySelect) return;
        productCategorySelect.innerHTML = '<option value="">Loading categories...</option>';
        try {
            const categories = await adminApi.getCategories(); // From admin_api.js
            productCategorySelect.innerHTML = '<option value="">Select a Category</option>';
            if (categories && categories.length > 0) {
                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category.id;
                    option.textContent = category.name;
                    productCategorySelect.appendChild(option);
                });
            } else {
                productCategorySelect.innerHTML = '<option value="">No categories found. Add one first.</option>';
            }
        } catch (error) {
            console.error('Failed to load categories:', error);
            productCategorySelect.innerHTML = '<option value="">Error loading categories</option>';
            // Use global message if available from admin_main.js
            if (typeof showGlobalUIMessage === 'function') {
                showGlobalUIMessage(`Error loading categories: ${error.message}`, 'error');
            } else {
                alert(`Error loading categories: ${error.message}`);
            }
        }
    };

    // --- Display Products in Table ---
    const renderProducts = (productsToRender) => {
        if (!productsTableBody) return;
        productsTableBody.innerHTML = '';
        if (!productsToRender || productsToRender.length === 0) {
            productsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">No products found.</td></tr>`;
            return;
        }

        productsToRender.forEach(product => {
            const row = productsTableBody.insertRow();
            row.className = 'hover:bg-gray-50 transition-colors duration-150';
            // Ensure API_BASE_URL is defined (typically in admin_api.js or a config file)
            const imageBase = API_BASE_URL.replace('/api/admin', ''); // Assuming static files served from backend root
            const imageUrl = product.image_url
                ? (product.image_url.startsWith('http') ? product.image_url : `${imageBase}/${product.image_url.startsWith('/') ? product.image_url.substring(1) : product.image_url}`)
                : 'https://placehold.co/60x60/e2e8f0/a0aec0?text=No+Img';

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <img src="${imageUrl}" alt="${product.name}" class="h-12 w-12 rounded-md object-cover shadow-sm border border-gray-200" onerror="this.src='https://placehold.co/60x60/e2e8f0/a0aec0?text=Error'; this.onerror=null;">
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">${product.name}</div>
                    <div class="text-xs text-gray-500">ID: ${product.id}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${product.category_name || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${parseFloat(product.price).toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${product.stock_quantity !== null ? product.stock_quantity : 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">${product.type || 'simple'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button class="edit-btn text-indigo-600 hover:text-indigo-800 transition-colors p-1 rounded hover:bg-indigo-100" data-id="${product.id}" title="Edit ${product.name}">
                        <i class="fas fa-pencil-alt fa-fw"></i>
                    </button>
                    <button class="delete-btn text-red-600 hover:text-red-800 transition-colors p-1 rounded hover:bg-red-100" data-id="${product.id}" title="Delete ${product.name}">
                        <i class="fas fa-trash-alt fa-fw"></i>
                    </button>
                </td>
            `;
        });

        document.querySelectorAll('.edit-btn').forEach(button => button.addEventListener('click', handleEditProduct));
        document.querySelectorAll('.delete-btn').forEach(button => button.addEventListener('click', handleDeleteProduct));
    };

    // --- Pagination ---
    const setupPagination = (totalProducts) => {
        if (!paginationControls) return;
        paginationControls.innerHTML = '';
        const totalPages = Math.ceil(totalProducts / productsPerPage);

        if (totalPages <= 1) return;

        const createPageButton = (text, pageNum, isDisabled = false, isActive = false) => {
            const button = document.createElement('button');
            button.innerHTML = text; // Use innerHTML to allow icons
            button.className = `px-3 py-1 rounded-md text-sm font-medium border border-gray-300 transition-colors ${
                isDisabled ? 'bg-gray-200 text-gray-400 cursor-not-allowed' :
                isActive ? 'bg-indigo-500 text-white border-indigo-500 z-10' :
                'bg-white text-gray-700 hover:bg-gray-50'
            }`;
            button.disabled = isDisabled;
            if (isActive) button.setAttribute('aria-current', 'page');
            button.addEventListener('click', () => {
                if (!isDisabled && !isActive) {
                    currentPage = pageNum;
                    fetchAndDisplayProducts();
                }
            });
            return button;
        };

        paginationControls.appendChild(createPageButton(`<i class="fas fa-chevron-left"></i> Prev`, currentPage - 1, currentPage === 1));

        // Simplified page numbers: show first, current +/- 1, last, and ellipses
        const pageRange = 1; // How many pages to show around current page
        let pagesShown = [];

        if (totalPages <= 5) { // Show all pages if 5 or less
            for (let i = 1; i <= totalPages; i++) pagesShown.push(i);
        } else {
            pagesShown.push(1); // Always show first page
            if (currentPage > pageRange + 2) paginationControls.appendChild(createPageButton('...', currentPage - pageRange -1, true)); // Ellipsis

            for (let i = Math.max(2, currentPage - pageRange); i <= Math.min(totalPages - 1, currentPage + pageRange); i++) {
                pagesShown.push(i);
            }
            if (currentPage < totalPages - pageRange - 1) paginationControls.appendChild(createPageButton('...', currentPage + pageRange + 1, true)); // Ellipsis
            pagesShown.push(totalPages); // Always show last page
        }
        
        // Remove duplicates that might arise from small totalPages
        pagesShown = [...new Set(pagesShown)];


        pagesShown.forEach(pageNum => {
            paginationControls.appendChild(createPageButton(pageNum.toString(), pageNum, false, pageNum === currentPage));
        });


        paginationControls.appendChild(createPageButton(`Next <i class="fas fa-chevron-right"></i>`, currentPage + 1, currentPage === totalPages));
    };

    // --- Fetch and Display Products ---
    const fetchAndDisplayProducts = async () => {
        if (!productsTableBody) {
            console.warn("productsTableBody not found, skipping product fetch.");
            return;
        }
        productsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center animate-pulse">Loading products...</td></tr>`;
        try {
            const searchTerm = productSearchInput ? productSearchInput.value.trim() : '';
            const response = await adminApi.getProducts(searchTerm, currentPage, productsPerPage);

            if (response && response.products) {
                currentProducts = response.products;
                renderProducts(currentProducts);
                setupPagination(response.total_products || currentProducts.length);
                if (currentProducts.length === 0 && searchTerm) {
                     productsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">No products found matching "${searchTerm}".</td></tr>`;
                }
            } else {
                 productsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">No products found or error fetching.</td></tr>`;
                 if (paginationControls) paginationControls.innerHTML = '';
            }
        } catch (error) {
            console.error('Failed to fetch products:', error);
            productsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 whitespace-nowrap text-sm text-red-500 text-center">Error loading products: ${error.message}. Please try again.</td></tr>`;
            if (typeof showGlobalUIMessage === 'function') {
                showGlobalUIMessage(`Error loading products: ${error.message}`, 'error');
            }
        }
    };

    // --- Handle Product Form Submission ---
    if (productForm) {
        productForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(productForm);
            saveProductBtn.disabled = true;
            saveProductBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
            clearFormMessage();

            if (productTypeSelect.value === 'variable') {
                const weightOptions = [];
                let validOptions = true;
                weightOptionsList.querySelectorAll('.flex.items-center').forEach(optDiv => {
                    const weightInput = optDiv.querySelector('.weight-grams');
                    const priceModifierInput = optDiv.querySelector('.price-modifier');
                    const stockInput = optDiv.querySelector('.weight-stock');

                    // Basic client-side validation for weight options
                    [weightInput, priceModifierInput, stockInput].forEach(input => {
                        if (!input.value) {
                            input.classList.add('border-red-500');
                            validOptions = false;
                        } else {
                            input.classList.remove('border-red-500');
                        }
                    });

                    if (validOptions) {
                         weightOptions.push({
                            weight_grams: parseInt(weightInput.value),
                            price_modifier: parseFloat(priceModifierInput.value),
                            stock_quantity: parseInt(stockInput.value)
                        });
                    }
                });
                if (!validOptions) {
                    showFormMessage('Please fill all fields for weight options.', 'error');
                    saveProductBtn.disabled = false;
                    saveProductBtn.textContent = 'Save Product';
                    return;
                }
                if (weightOptions.length === 0) {
                    showFormMessage('Please add at least one weight option for variable products.', 'error');
                    saveProductBtn.disabled = false;
                    saveProductBtn.textContent = 'Save Product';
                    return;
                }
                formData.append('weight_options_json', JSON.stringify(weightOptions));
            }

            try {
                let response;
                if (editingProductId) {
                    response = await adminApi.updateProduct(editingProductId, formData);
                } else {
                    response = await adminApi.addProduct(formData);
                }

                // Assuming backend returns { id: new_id, message: "..." } or { message: "..." } on success
                // And { error: "..." } on failure
                if (response && (response.id || response.message.toLowerCase().includes('success'))) {
                    if (typeof showGlobalUIMessage === 'function') {
                        showGlobalUIMessage(response.message || (editingProductId ? 'Product updated successfully!' : 'Product added successfully!'), 'success');
                    }
                    fetchAndDisplayProducts();
                    closeModal();
                } else {
                    throw new Error(response.error || 'Failed to save product. Unknown server error.');
                }
            } catch (error) {
                console.error('Failed to save product:', error);
                showFormMessage(`Error: ${error.message || 'Could not save product. Please check console.'}`, 'error');
            } finally {
                saveProductBtn.disabled = false;
                saveProductBtn.textContent = 'Save Product';
            }
        });
    }

    // --- Handle Edit Product ---
    const handleEditProduct = async (event) => {
        const button = event.currentTarget;
        const productId = button.dataset.id;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; // Loading state
        button.disabled = true;

        try {
            const product = await adminApi.getProductById(productId);
            if (product) {
                await loadCategories(); // Ensure categories are loaded before populating form
                openModal(true, product);
            } else {
                if (typeof showGlobalUIMessage === 'function') {
                    showGlobalUIMessage('Could not fetch product details.', 'error');
                }
            }
        } catch (error) {
            console.error('Error fetching product for edit:', error);
            if (typeof showGlobalUIMessage === 'function') {
                showGlobalUIMessage(`Error fetching product: ${error.message}`, 'error');
            }
        } finally {
            button.innerHTML = '<i class="fas fa-pencil-alt fa-fw"></i>';
            button.disabled = false;
        }
    };

    // --- Handle Delete Product ---
    const handleDeleteProduct = (event) => {
        const productId = event.currentTarget.dataset.id;
        const product = currentProducts.find(p => p.id == productId);
        const productName = product ? product.name : 'this product';

        if (typeof showConfirmModal === 'function') { // from admin_main.js
            showConfirmModal(
                `Delete Product: ${productName}?`,
                `Are you sure you want to delete "${productName}" (ID: ${productId})? This action cannot be undone.`,
                async () => { // onConfirm callback
                    try {
                        const response = await adminApi.deleteProduct(productId);
                        if (response && response.message && response.message.toLowerCase().includes('success')) {
                            if (typeof showGlobalUIMessage === 'function') {
                                showGlobalUIMessage(response.message, 'success');
                            }
                            fetchAndDisplayProducts();
                        } else {
                            throw new Error(response.error || 'Failed to delete product.');
                        }
                    } catch (error) {
                        console.error('Failed to delete product:', error);
                        if (typeof showGlobalUIMessage === 'function') {
                            showGlobalUIMessage(`Error deleting product: ${error.message}`, 'error');
                        }
                    }
                }
            );
        } else {
            // Fallback if custom confirm modal is not available
            if (confirm(`Are you sure you want to delete "${productName}"?`)) {
                // ... (duplicate deletion logic - better to ensure showConfirmModal exists)
                console.warn("showConfirmModal not found, using native confirm.");
                // Consider calling a simplified delete here or making showConfirmModal essential
            }
        }
    };

    // --- Search Functionality ---
    let searchTimeout;
    if (productSearchInput) {
        productSearchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentPage = 1;
                fetchAndDisplayProducts();
            }, 500);
        });
    }

    // --- Utility to show messages inside the modal form ---
    const showFormMessage = (message, type = 'info') => {
        if (!formMessage) return;
        formMessage.textContent = message;
        formMessage.className = 'text-sm p-3 rounded-md mt-2 '; // Base classes
        if (type === 'success') {
            formMessage.classList.add('text-green-700', 'bg-green-100');
        } else if (type === 'error') {
            formMessage.classList.add('text-red-700', 'bg-red-100');
        } else { // info
            formMessage.classList.add('text-blue-700', 'bg-blue-100');
        }
        formMessage.classList.remove('hidden');
    };
    const clearFormMessage = () => {
        if (!formMessage) return;
        formMessage.textContent = '';
        formMessage.className = 'text-sm'; // Reset classes
        formMessage.classList.add('hidden');
    }


    // --- Initial Load ---
    const initializePage = async () => {
        // ensureAdminAuthenticated should be called by admin_auth.js or admin_main.js on every admin page
        if (typeof ensureAdminAuthenticated === 'function' && !ensureAdminAuthenticated()) {
            return; // Stop execution if not authenticated and redirection is happening
        }

        // Load sidebar (if dynamically loaded, from admin_main.js)
        // if (typeof loadAdminSidebar === 'function') { loadAdminSidebar(); }
        // else if (typeof highlightActiveSidebarLink === 'function') { highlightActiveSidebarLink(); }


        await loadCategories(); // Load categories first for the modal
        await fetchAndDisplayProducts();
    };

    initializePage();
});
