// website/admin/js/admin_products.js
// Logic for managing products in the Admin Panel.

let productsForAdmin = []; // Cache for products list in admin panel
let editingProductId = null; // Tracks if a product is being edited

/**
 * Initializes product management functionalities:
 * - Sets up event listeners for form buttons.
 * - Loads the initial list of products.// website/admin/js/admin_products.js
// Logic for managing products in the Admin Panel.

let productsForAdmin = [];
let editingProductId = null;

function initializeProductManagement() {
    const showFormButton = document.getElementById('show-add-product-form-button');
    const productFormSection = document.getElementById('add-edit-product-section');
    const productForm = document.getElementById('product-form');
    const cancelFormButton = document.getElementById('cancel-product-form-button');
    const addWeightOptionButton = document.getElementById('add-weight-option-button');
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');

    if (showFormButton && productFormSection) {
        showFormButton.addEventListener('click', () => {
            editingProductId = null;
            if (productForm) productForm.reset();
            clearFormErrors(productForm);
            const formTitle = document.getElementById('product-form-title');
            if (formTitle) formTitle.textContent = "Ajouter un Nouveau Produit";
            const productIdField = document.getElementById('product-id');
            if (productIdField) productIdField.readOnly = false;
            const weightOptionsContainer = document.getElementById('weight-options-container');
            if (weightOptionsContainer) weightOptionsContainer.innerHTML = '';
            if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
            productFormSection.style.display = 'block';
            showFormButton.style.display = 'none';
        });
    }

    if (cancelFormButton && productFormSection && showFormButton) {
        cancelFormButton.addEventListener('click', () => {
            productFormSection.style.display = 'none';
            showFormButton.style.display = 'inline-flex';
            if (productForm) productForm.reset();
            clearFormErrors(productForm);
            editingProductId = null;
            if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
        });
    }

    if (productForm) {
        productForm.addEventListener('submit', handleProductFormSubmit);
    }

    if (addWeightOptionButton) {
        addWeightOptionButton.addEventListener('click', () => addWeightOptionRow());
    }

    loadAdminProductsList();
}

function addWeightOptionRow(option = { option_id: null, weight_grams: '', price: '', initial_stock: '' }) {
    const container = document.getElementById('weight-options-container');
    if (!container) return;
    const optionIndex = container.children.length;
    const optionIdInputHtml = option.option_id ? `<input type="hidden" name="weight_options[${optionIndex}][option_id]" value="${option.option_id}">` : '';
    const rowHtml = `
        <div class="weight-option-row grid grid-cols-1 md:grid-cols-4 gap-3 items-center border p-3 rounded-md mb-2">
            ${optionIdInputHtml}
            <div><label class="text-xs font-medium text-brand-near-black">Poids (g) <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][weight_grams]" class="form-input-admin text-sm p-2 mt-1" value="${option.weight_grams}" placeholder="Ex: 20" required></div>
            <div><label class="text-xs font-medium text-brand-near-black">Prix (€) <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][price]" step="0.01" class="form-input-admin text-sm p-2 mt-1" value="${option.price}" placeholder="Ex: 75.00" required></div>
            <div><label class="text-xs font-medium text-brand-near-black">Stock Initial/Actuel <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][initial_stock]" step="1" min="0" class="form-input-admin text-sm p-2 mt-1" value="${option.initial_stock}" placeholder="Ex: 10" required></div>
            <button type="button" class="btn-admin-danger text-xs py-1 px-2 self-end mt-4 md:mt-0" onclick="this.parentElement.remove()">Retirer</button>
        </div>`;
    container.insertAdjacentHTML('beforeend', rowHtml);
}

async function handleProductFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');
    const assetsLinksContainer = document.getElementById('product-assets-links');
    if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
    if(assetsLinksContainer) assetsLinksContainer.innerHTML = '';

    clearFormErrors(form);
    if (!validateProductForm(form)) return;

    const formData = new FormData(form);
    const productData = {};

     const fieldsToCollect = [
        'id', 'name_fr', 'name_en', 'category',
        'short_description_fr', 'short_description_en',
        'long_description_fr', 'long_description_en',
        'image_url_main', 'image_urls_thumb',
        'species_fr', 'species_en', 'origin_fr', 'origin_en',
        'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
        'sensory_description_fr', 'sensory_description_en',
        'pairing_suggestions_fr', 'pairing_suggestions_en',
        'base_price', 'initial_stock_quantity', // initial_stock_quantity for simple products
        'is_published',
        // Asset generation related fields
        'numero_lot_manuel', 'date_conditionnement', 'ddm',
        'specific_weight_for_label',
        'ingredients_for_label_fr', 'ingredients_for_label_en'
    ];

    for (const fieldName of fieldsToCollect) {
        if (formData.has(fieldName)) {
            if (['base_price', 'initial_stock_quantity'].includes(fieldName)) {
                productData[fieldName] = formData.get(fieldName) ? parseFloat(formData.get(fieldName)) : null;
                if (fieldName === 'initial_stock_quantity' && productData[fieldName] === null) productData[fieldName] = 0;
            } else if (fieldName === 'is_published') {
                productData[fieldName] = form.querySelector(`#product-is-published`).checked;
            } else if (fieldName === 'image_urls_thumb') {
                try {
                    const thumbString = formData.get('image_urls_thumb');
                    productData.image_urls_thumb = thumbString.trim() ? JSON.parse(thumbString) : [];
                    if (!Array.isArray(productData.image_urls_thumb)) productData.image_urls_thumb = [];
                } catch (e) {
                    productData.image_urls_thumb = [];
                    setFieldError(form.querySelector('#product-image-urls-thumb'), "Format JSON invalide pour les miniatures.");
                    return; // Stop submission if JSON is invalid
                }
            } else {
                productData[fieldName] = formData.get(fieldName);
            }
        }
    }


    const weightOptions = [];
    document.querySelectorAll('#weight-options-container .weight-option-row').forEach((row) => {
        const optionIdField = row.querySelector(`input[name*="[option_id]"]`);
        const weightGramsField = row.querySelector(`input[name*="[weight_grams]"]`);
        const priceField = row.querySelector(`input[name*="[price]"]`);
        const initialStockField = row.querySelector(`input[name*="[initial_stock]"]`);
        if (weightGramsField && priceField && initialStockField) {
            const opt = {
                weight_grams: parseInt(weightGramsField.value),
                price: parseFloat(priceField.value),
                initial_stock: parseInt(initialStockField.value)
            };
            if(optionIdField && optionIdField.value) opt.option_id = parseInt(optionIdField.value);
            weightOptions.push(opt);
        }
    });

    if (weightOptions.length > 0) {
        productData.weight_options = weightOptions;
        productData.base_price = null;
        productData.initial_stock_quantity = 0; // Stock managed by variants
    } else {
        if (productData.base_price === null) { /* Validation should catch this */ }
        if(productData.initial_stock_quantity === null) productData.initial_stock_quantity = 0;
    }

    const method = editingProductId ? 'PUT' : 'POST';
    const endpoint = editingProductId ? `/products/${editingProductId}` : '/products';

    try {
        showAdminToast("Enregistrement du produit...", "info");
        const result = await adminApiRequest(endpoint, method, productData);

        if (result.success && result.product) {
            showAdminToast(result.message || "Produit enregistré avec succès!", "success");
            if (result.product.assets && assetsPreviewSection && assetsLinksContainer) {
                let linksHtml = '';
                if (result.product.assets.passport_url) {
                    linksHtml += `<p><strong>Passeport:</strong> <a href="${result.product.assets.passport_url}" target="_blank" class="text-brand-classic-gold hover:underline">${result.product.assets.passport_url}</a></p>`;
                }
                if (result.product.assets.qr_code_file_path) {
                    const qrUrl = `/static_assets/${result.product.assets.qr_code_file_path}`;
                    linksHtml += `<p><strong>QR Code:</strong> <a href="${qrUrl}" target="_blank" class="text-brand-classic-gold hover:underline">Voir QR Code</a> <img src="${qrUrl}" alt="QR Code Preview" class="h-20 w-20 inline-block ml-2 border"></p>`;
                }
                if (result.product.assets.label_file_path) {
                    const labelUrl = `/static_assets/${result.product.assets.label_file_path}`;
                    linksHtml += `<p><strong>Étiquette:</strong> <a href="${labelUrl}" target="_blank" class="text-brand-classic-gold hover:underline">Voir Étiquette</a></p>`;
                }
                if (linksHtml) {
                    assetsLinksContainer.innerHTML = linksHtml;
                    assetsPreviewSection.style.display = 'block';
                } else {
                    assetsLinksContainer.innerHTML = '<p class="text-brand-warm-taupe">Aucun actif spécifique généré.</p>';
                    assetsPreviewSection.style.display = 'block';
                }
            }
            editingProductId = result.product.id;
            document.getElementById('product-form-title').textContent = `Modifier le Produit: ${result.product.name_fr || result.product.name_en}`;
            document.getElementById('product-id').readOnly = true;
            loadAdminProductsList();
        }
    } catch (error) {
        console.error("Erreur soumission formulaire produit:", error);
    }
}

function validateProductForm(form) {
    let isValid = true;
    const requiredFields = [
        { id: 'product-name-fr', message: "Le nom du produit (FR) est requis." },
        { id: 'product-name-en', message: "Product Name (EN) is required." },
        { id: 'product-category', message: "La catégorie est requise." },
        // { id: 'product-short-description-fr', message: "Description courte (FR) requise."}, // Optional now
        // { id: 'product-short-description-en', message: "Short description (EN) required."},
        { id: 'product-image-url-main', message: "L'URL de l'image principale est requise." }
    ];
    if (!editingProductId) {
        requiredFields.unshift({ id: 'product-id', message: "L'ID du produit est requis." });
    }
    requiredFields.forEach(fieldInfo => {
        const field = form.querySelector(`#${fieldInfo.id}`);
        if (field && !field.value.trim()) {
            setFieldError(field, fieldInfo.message);
            isValid = false;
        }
    });

    const basePriceField = form.querySelector('#product-base-price');
    const weightOptionsRows = form.querySelectorAll('#weight-options-container .weight-option-row');
    if (!basePriceField.value.trim() && weightOptionsRows.length === 0) {
        setFieldError(basePriceField, "Un prix de base ou au moins une option de poids est requis.");
        isValid = false;
    }
    if (basePriceField.value.trim() && weightOptionsRows.length > 0) {
        setFieldError(basePriceField, "Ne pas spécifier de prix de base si des options de poids sont définies.");
        isValid = false;
    }
    // ... (rest of validation)
    return isValid;
}

async function loadAdminProductsList() {
    const tableBody = document.getElementById('products-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">Chargement des produits...</td></tr>';
    try {
        productsForAdmin = await adminApiRequest('/products');
        if (productsForAdmin.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">Aucun produit trouvé.</td></tr>';
            return;
        }
        let rowsHtml = '';
        productsForAdmin.forEach(product => {
            let priceDisplay = product.base_price !== null ? `${parseFloat(product.base_price).toFixed(2)} €` : 'Variantes';
            let stockDisplay = product.stock_quantity !== undefined ? product.stock_quantity : 'N/A';
            rowsHtml += `
                <tr>
                    <td class="px-6 py-3 text-xs">${product.id}</td>
                    <td class="px-6 py-3 font-medium text-brand-near-black">${product.name_fr || product.name_en}</td>
                    <td class="px-6 py-3 font-medium text-brand-near-black">${product.name_en || product.name_fr}</td>
                    <td class="px-6 py-3">${product.category}</td>
                    <td class="px-6 py-3">${priceDisplay}</td>
                    <td class="px-6 py-3">${stockDisplay}</td>
                    <td class="px-6 py-3">${product.is_published ? '<span class="text-green-600 font-semibold">Oui</span>' : '<span class="text-red-600">Non</span>'}</td>
                    <td class="px-6 py-3 space-x-2 whitespace-nowrap">
                        <button onclick="editProduct('${product.id}')" class="btn-admin-secondary text-xs p-1.5">Éditer</button>
                    </td>
                </tr>`;
        });
        tableBody.innerHTML = rowsHtml;
    } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-red-600">Erreur de chargement des produits.</td></tr>';
    }
}

async function editProduct(productId) {
    editingProductId = productId;
    let productToEdit;
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');
    const assetsLinksContainer = document.getElementById('product-assets-links');
    if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
    if(assetsLinksContainer) assetsLinksContainer.innerHTML = '';

    try {
        productToEdit = await adminApiRequest(`/products/${productId}`);
        if (!productToEdit) throw new Error("Produit non trouvé pour l'édition.");
    } catch (e) {
        showAdminToast("Impossible de charger les détails du produit pour l'édition.", "error");
        return;
    }

    const form = document.getElementById('product-form');
    if (!form) return;
    form.reset();
    clearFormErrors(form);

    document.getElementById('product-form-title').textContent = `Modifier le Produit: ${productToEdit.name_fr || productToEdit.name_en}`;
    document.getElementById('product-id').value = productToEdit.id;
    document.getElementById('product-id').readOnly = true;

    const fieldsToPopulate = [
        'name_fr', 'name_en', 'category',
        'short_description_fr', 'short_description_en',
        'long_description_fr', 'long_description_en',
        'image_url_main', 'image_urls_thumb',
        'species_fr', 'species_en', 'origin_fr', 'origin_en',
        'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
        'sensory_description_fr', 'sensory_description_en',
        'pairing_suggestions_fr', 'pairing_suggestions_en',
        'base_price', // stock_quantity is handled by context
        'is_published',
        'numero_lot_manuel', 'date_conditionnement', 'ddm',
        'specific_weight_for_label',
        'ingredients_for_label_fr', 'ingredients_for_label_en'
    ];

    fieldsToPopulate.forEach(fieldName => {
        const elementId = `product-${fieldName.replace(/_/g, '-')}`; // Convert snake_case to kebab-case for IDs
        const element = document.getElementById(elementId);
        if (element) {
            if (fieldName === 'image_urls_thumb') {
                element.value = productToEdit.image_urls_thumb ? JSON.stringify(productToEdit.image_urls_thumb) : '[]';
            } else if (element.type === 'checkbox') {
                 element.checked = productToEdit[fieldName];
            }
            else {
                element.value = productToEdit[fieldName] || '';
            }
        } else {
            console.warn(`Element with ID ${elementId} not found for field ${fieldName}`);
        }
    });


    const weightOptionsContainer = document.getElementById('weight-options-container');
    weightOptionsContainer.innerHTML = '';
    if (productToEdit.weight_options && productToEdit.weight_options.length > 0) {
        productToEdit.weight_options.forEach(opt => addWeightOptionRow({
            option_id: opt.option_id,
            weight_grams: opt.weight_grams,
            price: opt.price,
            initial_stock: opt.stock_quantity
        }));
        document.getElementById('product-base-price').value = '';
        document.getElementById('product-initial-stock-quantity').value = '';
        document.getElementById('simple-product-stock-section').style.display = 'none';
    } else {
        document.getElementById('product-base-price').value = productToEdit.base_price !== null ? productToEdit.base_price : '';
        document.getElementById('product-initial-stock-quantity').value = productToEdit.stock_quantity || 0;
        document.getElementById('simple-product-stock-section').style.display = 'block';
    }

    if (productToEdit.assets && assetsPreviewSection && assetsLinksContainer) {
        let linksHtml = '';
        if (productToEdit.assets.passport_url) { linksHtml += `<p><strong>Passeport:</strong> <a href="${productToEdit.assets.passport_url}" target="_blank" class="text-brand-classic-gold hover:underline">${productToEdit.assets.passport_url}</a></p>`; }
        if (productToEdit.assets.qr_code_file_path) { linksHtml += `<p><strong>QR Code:</strong> <a href="/static_assets/${productToEdit.assets.qr_code_file_path}" target="_blank" class="text-brand-classic-gold hover:underline">Voir QR</a></p>`; }
        if (productToEdit.assets.label_file_path) { linksHtml += `<p><strong>Étiquette:</strong> <a href="/static_assets/${productToEdit.assets.label_file_path}" target="_blank" class="text-brand-classic-gold hover:underline">Voir Étiquette</a></p>`; }
        if (linksHtml) {
            assetsLinksContainer.innerHTML = linksHtml;
            assetsPreviewSection.style.display = 'block';
        }
    }

    document.getElementById('add-edit-product-section').style.display = 'block';
    document.getElementById('show-add-product-form-button').style.display = 'none';
    window.scrollTo(0, 0);
}

// Helper to check if a string is a valid URL (basic check)
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}
