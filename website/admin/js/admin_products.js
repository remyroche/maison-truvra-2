// Content from admin/admin_manage_products.html
// This file (website/admin/js/admin_products.js) will now contain the JavaScript logic for managing products.

document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Products JS Loaded");

    // Get references to DOM elements
    const productForm = document.getElementById('productForm');
    const productsTableBody = document.getElementById('productsTableBody');
    const categorySelect = document.getElementById('productCategory');
    const imagePreview = document.getElementById('imagePreview');
    const productImageInput = document.getElementById('productImage');
    let editingProductId = null; // Variable to store the ID of the product being edited

    // --- Modal for Confirmations/Alerts ---
    const alertModal = document.createElement('div');
    alertModal.id = 'alertModal';
    alertModal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex items-center justify-center hidden z-50';
    alertModal.innerHTML = `
        <div class="relative p-5 border w-full max-w-md m-auto flex-col flex rounded-lg shadow-lg bg-white">
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-medium text-gray-900" id="alertModalTitle">Alert</h3>
                <button type="button" class="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm p-1.5 ml-auto inline-flex items-center" id="alertModalCloseButton">
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
                </button>
            </div>
            <div class="p-2 mt-2 text-center">
                <p class="text-sm text-gray-500" id="alertModalMessage">Modal message goes here.</p>
            </div>
            <div class="mt-3 flex justify-end space-x-2" id="alertModalActions">
                <button id="alertModalOkButton" class="px-4 py-2 bg-indigo-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">OK</button>
            </div>
        </div>
    `;
    document.body.appendChild(alertModal);

    const alertModalTitle = document.getElementById('alertModalTitle');
    const alertModalMessage = document.getElementById('alertModalMessage');
    const alertModalCloseButton = document.getElementById('alertModalCloseButton');
    const alertModalOkButton = document.getElementById('alertModalOkButton');
    const alertModalActions = document.getElementById('alertModalActions');

    // Function to show a custom alert
    function showAlert(message, title = "Alert") {
        alertModalTitle.textContent = title;
        alertModalMessage.textContent = message;
        alertModalActions.innerHTML = `<button id="alertModalOkButton" class="px-4 py-2 bg-indigo-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">OK</button>`;
        alertModal.classList.remove('hidden');
        document.getElementById('alertModalOkButton').onclick = () => alertModal.classList.add('hidden');
        alertModalCloseButton.onclick = () => alertModal.classList.add('hidden');
    }

    // Function to show a custom confirmation dialog
    function showConfirm(message, title = "Confirm", callback) {
        alertModalTitle.textContent = title;
        alertModalMessage.textContent = message;
        alertModalActions.innerHTML = `
            <button id="confirmModalCancelButton" class="px-4 py-2 bg-gray-200 text-gray-800 text-base font-medium rounded-md shadow-sm hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500">Cancel</button>
            <button id="confirmModalConfirmButton" class="px-4 py-2 bg-red-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500">Confirm</button>
        `;
        alertModal.classList.remove('hidden');

        const confirmBtn = document.getElementById('confirmModalConfirmButton');
        const cancelBtn = document.getElementById('confirmModalCancelButton');

        confirmBtn.onclick = () => {
            alertModal.classList.add('hidden');
            callback(true);
        };
        cancelBtn.onclick = () => {
            alertModal.classList.add('hidden');
            callback(false);
        };
        alertModalCloseButton.onclick = () => {
            alertModal.classList.add('hidden');
            callback(false);
        };
    }
    // --- End Modal ---


    // Fetch categories and populate select dropdown
    async function loadCategories() {
        try {
            const categories = await adminApi.getCategories(); // Assumes adminApi.getCategories() is defined in admin_api.js
            if (!categorySelect) {
                console.warn("Category select dropdown not found on this page.");
                return;
            }
            categorySelect.innerHTML = '<option value="">Select Category</option>'; // Clear existing options
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                categorySelect.appendChild(option);
            });
        } catch (error) {
            console.error("Failed to load categories:", error);
            showAlert("Could not load categories. Please try again later.", "Error");
        }
    }

    // Load products and populate table
    async function loadProducts() {
        try {
            const products = await adminApi.getProducts(); // Assumes adminApi.getProducts() is defined
            if (!productsTableBody) {
                console.warn("Products table body not found on this page.");
                return;
            }
            productsTableBody.innerHTML = ''; // Clear existing products
            if (products.length === 0) {
                productsTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4">No products found.</td></tr>`;
                return;
            }
            products.forEach(product => {
                const row = productsTableBody.insertRow();
                // Ensure all product properties are accessed safely, providing defaults if necessary
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product.id || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <img src="${product.image_url || 'https://placehold.co/60x60/eee/ccc?text=No+Image'}" alt="${product.name || 'Product Image'}" class="w-10 h-10 rounded object-cover" onerror="this.onerror=null;this.src='https://placehold.co/60x60/eee/ccc?text=Error';">
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product.name || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product.category_name || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product.price !== undefined ? product.price.toFixed(2) : 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product.stock_quantity !== undefined ? product.stock_quantity : 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-indigo-600 hover:text-indigo-900 edit-btn" data-id="${product.id}">Edit</button>
                        <button class="text-red-600 hover:text-red-900 delete-btn ml-4" data-id="${product.id}">Delete</button>
                    </td>
                `;
            });
            attachActionListeners(); // Re-attach listeners after table is populated
        } catch (error) {
            console.error("Failed to load products:", error);
            if (productsTableBody) {
                productsTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-red-500">Error loading products.</td></tr>`;
            }
            showAlert("Could not load products. Please try again later.", "Error");
        }
    }

    // Handle product form submission (Add/Edit)
    if (productForm) {
        productForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(productForm);
            const name = formData.get('productName');
            const description = formData.get('productDescription');
            const price = parseFloat(formData.get('productPrice'));
            const categoryId = formData.get('productCategory');
            const stockQuantity = parseInt(formData.get('productStock'), 10);
            const imageFile = productImageInput.files[0]; // Get file from input

            // Basic validation
            if (!name || !price || !categoryId || isNaN(stockQuantity)) {
                showAlert("Please fill in all required fields (Name, Price, Category, Stock).", "Validation Error");
                return;
            }

            const productData = {
                name,
                description,
                price,
                category_id: categoryId,
                stock_quantity: stockQuantity
            };

            try {
                let response;
                if (editingProductId) {
                    // Update existing product
                    response = await adminApi.updateProduct(editingProductId, productData); // Assumes adminApi.updateProduct is defined
                    if (imageFile && imageFile.size > 0) {
                        await adminApi.uploadProductImage(editingProductId, imageFile); // Assumes adminApi.uploadProductImage is defined
                    }
                     showAlert("Product updated successfully!", "Success");
                } else {
                    // Add new product
                    response = await adminApi.addProduct(productData); // Assumes adminApi.addProduct is defined
                    if (imageFile && imageFile.size > 0 && response && response.id) {
                         await adminApi.uploadProductImage(response.id, imageFile);
                    }
                    showAlert("Product added successfully!", "Success");
                }
                console.log("Product saved:", response);
                productForm.reset(); // Reset form fields
                if(imagePreview) {
                    imagePreview.style.backgroundImage = 'none'; // Clear image preview
                    imagePreview.textContent = 'Image Preview';
                }
                if(productImageInput) productImageInput.value = null; // Reset file input

                editingProductId = null; // Reset editing state
                document.getElementById('formTitle').textContent = 'Add New Product';
                document.getElementById('submitButton').textContent = 'Add Product';
                loadProducts(); // Refresh product list
            } catch (error) {
                console.error("Failed to save product:", error);
                showAlert(`Error saving product: ${error.message || 'Unknown error. Check console for details.'}`, "Error");
            }
        });
    }

    // Preview image before upload
    if (productImageInput && imagePreview) {
        productImageInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.style.backgroundImage = `url(${e.target.result})`;
                    imagePreview.textContent = ''; // Clear placeholder text
                }
                reader.readAsDataURL(file);
            } else {
                imagePreview.style.backgroundImage = 'none';
                imagePreview.textContent = 'Image Preview';
            }
        });
    }
    
    // Attach event listeners for edit and delete buttons
    function attachActionListeners() {
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const productId = event.target.dataset.id;
                await populateFormForEdit(productId);
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const productId = event.target.dataset.id;
                showConfirm('Are you sure you want to delete this product?', 'Delete Product', async (confirmed) => {
                    if (confirmed) {
                        try {
                            await adminApi.deleteProduct(productId); // Assumes adminApi.deleteProduct is defined
                            showAlert("Product deleted successfully!", "Success");
                            loadProducts(); // Refresh product list
                        } catch (error) {
                            console.error("Failed to delete product:", error);
                            showAlert(`Error deleting product: ${error.message || 'Unknown error. Check console for details.'}`, "Error");
                        }
                    }
                });
            });
        });
    }

    // Populate form for editing a product
    async function populateFormForEdit(productId) {
        try {
            const product = await adminApi.getProductById(productId); // Assuming adminApi has getProductById
            if (product && productForm) {
                document.getElementById('productName').value = product.name || '';
                document.getElementById('productDescription').value = product.description || '';
                document.getElementById('productPrice').value = product.price !== undefined ? product.price : '';
                document.getElementById('productCategory').value = product.category_id || '';
                document.getElementById('productStock').value = product.stock_quantity !== undefined ? product.stock_quantity : '';
                
                if (productImageInput) productImageInput.value = null; // Reset file input as we can't pre-populate it for security reasons

                if (imagePreview) {
                    if (product.image_url) {
                        imagePreview.style.backgroundImage = `url(${product.image_url})`;
                        imagePreview.textContent = '';
                    } else {
                        imagePreview.style.backgroundImage = 'none';
                        imagePreview.textContent = 'Image Preview';
                    }
                }
                
                editingProductId = productId;
                document.getElementById('formTitle').textContent = 'Edit Product';
                document.getElementById('submitButton').textContent = 'Update Product';
                productForm.scrollIntoView({ behavior: 'smooth' }); // Scroll to form for better UX
            } else {
                showAlert("Could not find product details to edit.", "Error");
            }
        } catch (error) {
            console.error("Failed to fetch product for editing:", error);
            showAlert(`Error fetching product details: ${error.message || 'Unknown error. Check console.'}`, "Error");
        }
    }


    // Initial loads - check if elements exist before trying to load data for them
    // This makes the script more robust if used on pages where not all elements are present.
    if (categorySelect) { 
        loadCategories();
    }
    if (productsTableBody) { 
        loadProducts();
    } else {
        // If there's no product table, but there's a form, still load categories for the form.
        // This case is already handled by the `if (categorySelect)` above.
        // console.log("Product table not found, skipping product load.");
    }
});
