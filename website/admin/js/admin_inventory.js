// This file (website/admin/js/admin_inventory.js) will contain the JavaScript logic for managing inventory.
// Assuming the content was previously in 'admin/admin_manage_inventory.html' or this is a new/updated script.

document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Inventory JS Loaded");

    const inventoryTableBody = document.getElementById('inventoryTableBody');
    const productSelectForInventory = document.getElementById('productSelectForInventory');
    const addStockForm = document.getElementById('addStockForm');
    const itemDetailModal = document.getElementById('itemDetailModal');
    const itemDetailContent = document.getElementById('itemDetailContent');
    const closeItemDetailModalButton = document.getElementById('closeItemDetailModalButton');

    // --- Alert/Confirm Modal (Ensure this is available) ---
    if (!window.showAlert) {
        console.warn("Global showAlert not found. Using basic stubs for admin_inventory.js.");
        window.showAlert = (message, title) => console.log(`Alert (${title}): ${message}`);
    }
    // --- End Alert/Confirm Modal ---

    // Format date
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            return new Date(dateString).toLocaleDateString('fr-FR', {
                day: '2-digit', month: '2-digit', year: 'numeric'
            });
        } catch (e) { return dateString; }
    }
    
    // Load products into select dropdown for adding stock
    async function loadProductsForSelect() {
        if (!productSelectForInventory) return;
        try {
            const products = await adminApi.getProducts(); // Assumes adminApi.getProducts
            productSelectForInventory.innerHTML = '<option value="">Select Product</option>';
            products.forEach(product => {
                const option = document.createElement('option');
                option.value = product.id;
                option.textContent = `${product.name} (ID: ${product.id})`;
                productSelectForInventory.appendChild(option);
            });
        } catch (error) {
            console.error("Failed to load products for select:", error);
            window.showAlert("Could not load products for stock addition.", "Error");
        }
    }


    // Load inventory items and populate table
    async function loadInventory() {
        try {
            const inventoryItems = await adminApi.getInventoryItems(); // Assumes adminApi.getInventoryItems
            if (!inventoryTableBody) {
                console.warn("Inventory table body not found on this page.");
                return;
            }
            inventoryTableBody.innerHTML = ''; // Clear existing items
            if (!inventoryItems || inventoryItems.length === 0) {
                inventoryTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4">No inventory items found.</td></tr>`;
                return;
            }
            inventoryItems.forEach(item => {
                const row = inventoryTableBody.insertRow();
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.id}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.uid || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.product_name} (ID: ${item.product_id})</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.batch_number || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatDate(item.production_date)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${item.is_sold ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
                            ${item.is_sold ? 'Sold' : 'Available'}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-indigo-600 hover:text-indigo-900 view-item-details-btn" data-uid="${item.uid}">View Passport</button>
                        </td>
                `;
            });
            attachInventoryActionListeners();
        } catch (error) {
            console.error("Failed to load inventory:", error);
            if (inventoryTableBody) {
                inventoryTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-red-500">Error loading inventory.</td></tr>`;
            }
            window.showAlert("Could not load inventory. Please try again.", "Error");
        }
    }

    // Handle "Add Stock" form submission
    if (addStockForm) {
        addStockForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const productId = document.getElementById('productSelectForInventory').value;
            const quantity = parseInt(document.getElementById('quantityToAdd').value, 10);
            const batchNumber = document.getElementById('batchNumber').value;
            const productionDate = document.getElementById('productionDate').value;

            if (!productId || isNaN(quantity) || quantity <= 0) {
                window.showAlert("Please select a product and enter a valid quantity.", "Validation Error");
                return;
            }

            try {
                // This API might create multiple serialized items based on quantity
                await adminApi.addStockToInventory({ 
                    product_id: productId, 
                    quantity: quantity,
                    batch_number: batchNumber,
                    production_date: productionDate 
                }); 
                window.showAlert(`${quantity} item(s) added to stock successfully!`, "Success");
                addStockForm.reset();
                loadInventory(); // Refresh inventory list
                // Also update product stock count on product management page if that's separate
            } catch (error) {
                console.error("Failed to add stock:", error);
                window.showAlert(`Error adding stock: ${error.message || 'Unknown error.'}`, "Error");
            }
        });
    }
    
    // Show item details (passport) in modal
    async function showItemDetails(itemUID) {
        if (!itemDetailModal || !itemDetailContent) return;
        try {
            // Assuming an API endpoint to get passport details by UID
            // This might be the same as the public passport page, or a specific admin version
            const passportData = await adminApi.getItemPassport(itemUID); // Needs adminApi.getItemPassport(uid)

            if (passportData) {
                 // Basic display, enhance as needed. Could be an iframe to the actual passport HTML page.
                itemDetailContent.innerHTML = `
                    <h4 class="text-lg font-semibold mb-2">Digital Passport - UID: ${passportData.uid}</h4>
                    <p><strong>Product:</strong> ${passportData.product_name} (ID: ${passportData.product_id})</p>
                    <p><strong>Batch Number:</strong> ${passportData.batch_number || 'N/A'}</p>
                    <p><strong>Production Date:</strong> ${formatDate(passportData.production_date)}</p>
                    <p><strong>Added to Stock:</strong> ${formatDate(passportData.creation_date)}</p>
                    <p><strong>Status:</strong> ${passportData.is_sold ? 'Sold' : 'Available'}</p>
                    ${passportData.is_sold && passportData.order_id ? `<p><strong>Order ID:</strong> ${passportData.order_id}</p>` : ''}
                    <div class="mt-4">
                        <img src="${passportData.qr_code_url}" alt="QR Code for UID ${passportData.uid}" class="mx-auto w-32 h-32 border p-1">
                        <p class="text-center text-xs mt-1">Scan for details</p>
                    </div>
                    `;
            } else {
                itemDetailContent.innerHTML = `<p class="text-red-500">Could not load details for UID: ${itemUID}.</p>`;
            }
            itemDetailModal.classList.remove('hidden');
        } catch (error) {
            console.error("Failed to load item passport:", error);
            itemDetailContent.innerHTML = `<p class="text-red-500">Error loading details: ${error.message}</p>`;
            itemDetailModal.classList.remove('hidden');
        }
    }

    // Close item detail modal
    if (itemDetailModal && closeItemDetailModalButton) {
        closeItemDetailModalButton.addEventListener('click', () => itemDetailModal.classList.add('hidden'));
    }
    if (itemDetailModal) { // Close on backdrop click
        itemDetailModal.addEventListener('click', (event) => {
            if (event.target === itemDetailModal) {
                itemDetailModal.classList.add('hidden');
            }
        });
    }

    // Attach event listeners
    function attachInventoryActionListeners() {
        document.querySelectorAll('.view-item-details-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const itemUID = event.target.dataset.uid;
                if (itemUID) {
                    showItemDetails(itemUID);
                } else {
                    window.showAlert("Item UID not found.", "Error");
                }
            });
        });
    }

    // Initial loads
    if (productSelectForInventory) {
        loadProductsForSelect();
    }
    if (inventoryTableBody) {
        loadInventory();
    }
});
