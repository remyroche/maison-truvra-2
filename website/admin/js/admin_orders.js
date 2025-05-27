// This file (website/admin/js/admin_orders.js) will contain the JavaScript logic for managing orders.
// Assuming the content was previously in 'admin/admin_manage_orders.html' or this is a new/updated script.

document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Orders JS Loaded");

    const ordersTableBody = document.getElementById('ordersTableBody');
    const orderModal = document.getElementById('orderModal');
    const orderModalTitle = document.getElementById('orderModalTitle');
    const orderDetailsDiv = document.getElementById('orderDetails');
    const orderItemsTableBody = document.getElementById('orderItemsTableBody');
    const orderStatusSelect = document.getElementById('orderStatus');
    const updateOrderStatusButton = document.getElementById('updateOrderStatusButton');
    const closeOrderModalButton = document.getElementById('closeOrderModalButton');
    let currentOrderId = null;

    // --- Alert/Confirm Modal (Ensure this is available, possibly from admin_main.js) ---
    // Basic fallback if not globally available.
    if (!window.showAlert || !window.showConfirm) {
        console.warn("Global showAlert/showConfirm not found. Using basic stubs for admin_orders.js.");
        window.showAlert = (message, title) => console.log(`Alert (${title}): ${message}`); // Basic alert for fallback
        window.showConfirm = (message, title, callback) => {
            const confirmed = confirm(`${title}: ${message}`); // Basic confirm for fallback
            callback(confirmed);
        };
    }
    // --- End Alert/Confirm Modal ---

    // Format currency (simple version)
    function formatCurrency(amount) {
        return `€${Number(amount).toFixed(2)}`;
    }

    // Format date (simple version)
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            return new Date(dateString).toLocaleDateString('fr-FR', { // Example: French locale
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return dateString; // Return original if parsing fails
        }
    }

    // Load orders and populate table
    async function loadOrders() {
        try {
            const orders = await adminApi.getOrders(); // Assumes adminApi.getOrders is defined
            if (!ordersTableBody) {
                console.warn("Orders table body not found on this page.");
                return;
            }
            ordersTableBody.innerHTML = ''; // Clear existing orders
            if (!orders || orders.length === 0) {
                ordersTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4">No orders found.</td></tr>`;
                return;
            }
            orders.forEach(order => {
                const row = ordersTableBody.insertRow();
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${order.id}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${order.user_email || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatDate(order.order_date)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatCurrency(order.total_amount)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                            ${order.status === 'Completed' ? 'bg-green-100 text-green-800' :
                            order.status === 'Shipped' ? 'bg-blue-100 text-blue-800' :
                            order.status === 'Processing' ? 'bg-yellow-100 text-yellow-800' :
                            order.status === 'Pending' ? 'bg-orange-100 text-orange-800' :
                            order.status === 'Cancelled' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'}">
                            ${order.status || 'N/A'}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${order.payment_status || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-indigo-600 hover:text-indigo-900 view-order-btn" data-id="${order.id}">View/Edit</button>
                    </td>
                `;
            });
            attachOrderActionListeners();
        } catch (error) {
            console.error("Failed to load orders:", error);
            if (ordersTableBody) {
                ordersTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-red-500">Error loading orders.</td></tr>`;
            }
            window.showAlert("Could not load orders. Please try again.", "Error");
        }
    }

    // Populate modal with order details
    async function populateOrderModal(orderId) {
        try {
            const order = await adminApi.getOrderById(orderId); // Assumes adminApi.getOrderById
            if (order && orderModal && orderDetailsDiv && orderItemsTableBody && orderStatusSelect) {
                currentOrderId = orderId;
                orderModalTitle.textContent = `Order Details - ID: ${order.id}`;
                
                orderDetailsDiv.innerHTML = `
                    <p><strong>Customer:</strong> ${order.user_name || order.user_email || 'N/A'}</p>
                    <p><strong>Order Date:</strong> ${formatDate(order.order_date)}</p>
                    <p><strong>Total Amount:</strong> ${formatCurrency(order.total_amount)}</p>
                    <p><strong>Payment Status:</strong> ${order.payment_status || 'N/A'}</p>
                    <h4 class="text-md font-semibold mt-3 mb-1 text-gray-700">Shipping Address:</h4>
                    <p>${order.shipping_address?.street || ''}<br>
                       ${order.shipping_address?.city || ''}, ${order.shipping_address?.postal_code || ''}<br>
                       ${order.shipping_address?.country || ''}</p>
                     <h4 class="text-md font-semibold mt-3 mb-1 text-gray-700">Billing Address:</h4>
                    <p>${order.billing_address?.street || ''}<br>
                       ${order.billing_address?.city || ''}, ${order.billing_address?.postal_code || ''}<br>
                       ${order.billing_address?.country || ''}</p>
                `;

                orderItemsTableBody.innerHTML = '';
                if (order.items && order.items.length > 0) {
                    order.items.forEach(item => {
                        const row = orderItemsTableBody.insertRow();
                        row.innerHTML = `
                            <td class="px-4 py-2 text-sm text-gray-800">${item.product_name} (ID: ${item.product_id})</td>
                            <td class="px-4 py-2 text-sm text-gray-800">${item.quantity}</td>
                            <td class="px-4 py-2 text-sm text-gray-800">${formatCurrency(item.unit_price)}</td>
                            <td class="px-4 py-2 text-sm text-gray-800">${formatCurrency(item.quantity * item.unit_price)}</td>
                        `;
                    });
                } else {
                    orderItemsTableBody.innerHTML = `<tr><td colspan="4" class="text-center py-3">No items in this order.</td></tr>`;
                }
                
                orderStatusSelect.value = order.status || 'Pending';
                orderModal.classList.remove('hidden');
            } else {
                window.showAlert("Could not find order details.", "Error");
            }
        } catch (error) {
            console.error("Failed to fetch order details:", error);
            window.showAlert(`Error fetching order details: ${error.message || 'Unknown error.'}`, "Error");
        }
    }

    // Handle order status update
    if (updateOrderStatusButton && orderStatusSelect) {
        updateOrderStatusButton.addEventListener('click', async () => {
            if (!currentOrderId) return;

            const newStatus = orderStatusSelect.value;
            try {
                await adminApi.updateOrderStatus(currentOrderId, newStatus); // Assumes adminApi.updateOrderStatus
                window.showAlert("Order status updated successfully!", "Success");
                if(orderModal) orderModal.classList.add('hidden');
                loadOrders(); // Refresh order list
                currentOrderId = null;
            } catch (error) {
                console.error("Failed to update order status:", error);
                window.showAlert(`Error updating order status: ${error.message || 'Unknown error.'}`, "Error");
            }
        });
    }
    
    // Close modal listener
    if (orderModal && closeOrderModalButton) {
        closeOrderModalButton.addEventListener('click', () => {
            orderModal.classList.add('hidden');
            currentOrderId = null;
        });
    }
     if (orderModal) { // Close on backdrop click
        orderModal.addEventListener('click', (event) => {
            if (event.target === orderModal) {
                orderModal.classList.add('hidden');
                currentOrderId = null;
            }
        });
    }


    // Attach event listeners for view/edit buttons
    function attachOrderActionListeners() {
        document.querySelectorAll('.view-order-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const orderId = event.target.dataset.id;
                populateOrderModal(orderId);
            });
        });
    }

    // Initial load
    if (ordersTableBody) {
        loadOrders();
    }
});
