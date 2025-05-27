// website/admin/js/admin_main.js

document.addEventListener('DOMContentLoaded', () => {
    // Check if user is authenticated as admin
    if (typeof checkAdminAuth === 'function') { // checkAdminAuth from admin_auth.js
        if (!checkAdminAuth() && !window.location.pathname.endsWith('admin_login.html')) {
            window.location.href = 'admin_login.html';
            return; // Stop further execution if not authenticated
        }
    } else {
        console.error("checkAdminAuth function not found. Ensure admin_auth.js is loaded.");
        // Potentially redirect to login as a fallback if auth check is missing
        if (!window.location.pathname.endsWith('admin_login.html')) {
             // window.location.href = 'admin_login.html';
        }
    }


    // Initialize common admin UI elements
    if (typeof initializeAdminUI === 'function') { // initializeAdminUI from admin_ui.js
        initializeAdminUI();
    } else {
        console.error("initializeAdminUI function not found. Ensure admin_ui.js is loaded.");
    }


    // Page-specific initializations
    const bodyId = document.body.id;

    if (bodyId === 'page-admin-dashboard') {
        if (typeof initializeAdminDashboard === 'function') { // from admin_dashboard.js
            initializeAdminDashboard();
        }
    } else if (bodyId === 'page-admin-manage-products') {
        if (typeof initializeProductManagement === 'function') { // from admin_products.js
            initializeProductManagement();
        }
    } else if (bodyId === 'page-admin-manage-inventory') {
         if (typeof initializeInventoryManagement === 'function') { // from admin_inventory.js
            initializeInventoryManagement();
        }
    } else if (bodyId === 'page-admin-manage-users') {
        if (typeof initializeUserManagement === 'function') { // from admin_users.js
            initializeUserManagement();
        }
    } else if (bodyId === 'page-admin-manage-orders') {
         if (typeof initializeOrderManagement === 'function') { // from admin_orders.js
            initializeOrderManagement();
        }
    } else if (bodyId === 'page-admin-manage-invoices') { // NEW
        if (typeof initializeAdminInvoiceManagement === 'function') { // from admin_invoices.js
            initializeAdminInvoiceManagement();
        } else {
            console.error("initializeAdminInvoiceManagement function not found. Ensure admin_invoices.js is loaded.");
        }
    }
    // Add more page initializations as needed
});
