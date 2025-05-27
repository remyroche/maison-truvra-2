// website/admin/js/admin_main.js

document.addEventListener('DOMContentLoaded', () => {
    // Check if user is authenticated as admin
    if (typeof checkAdminAuth === 'function') { // checkAdminAuth from admin_auth.js
        if (!checkAdminAuth() && !window.location.pathname.endsWith('admin_login.html')) {
            window.location.href = 'admin_login.html';
            return; // Stop further execution if not authenticated
        }// website/admin/js/admin_main.js

/**
 * Loads the admin sidebar component into the #admin-sidebar-placeholder div.
 * Sets the active class on the correct navigation link based on the current page.
 * Initializes the logout button functionality from the sidebar.
 */
async function loadAdminSidebar() {
    const sidebarPlaceholder = document.getElementById('admin-sidebar-placeholder');
    if (!sidebarPlaceholder) {
        console.error("Admin sidebar placeholder not found.");
        return;
    }

    try {
        const response = await fetch('admin_sidebar.html'); // Assuming admin_sidebar.html is in the same 'admin' directory
        if (!response.ok) {
            throw new Error(`Failed to load admin_sidebar.html: ${response.status}`);
        }
        const sidebarHtml = await response.text();
        sidebarPlaceholder.innerHTML = sidebarHtml;

        // Set active navigation link
        const currentPageId = document.body.id;
        const navLinks = document.querySelectorAll('#admin-nav-list .admin-nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-page-id') === currentPageId) {
                link.classList.add('active');
            }
        });

        // Initialize logout button from the loaded sidebar
        const logoutButton = document.getElementById('admin-logout-button');
        if (logoutButton && typeof handleAdminLogout === 'function') { // handleAdminLogout from admin_auth.js
            logoutButton.addEventListener('click', handleAdminLogout);
        } else if (!logoutButton) {
            console.warn("Admin logout button not found in loaded sidebar.");
        } else if (typeof handleAdminLogout !== 'function') {
            console.warn("handleAdminLogout function not found (admin_auth.js).");
        }

    } catch (error) {
        console.error("Error loading admin sidebar:", error);
        sidebarPlaceholder.innerHTML = "<p class='text-red-500 p-4'>Error loading sidebar.</p>";
    }
}


document.addEventListener('DOMContentLoaded', async () => {
    // 0. Load sidebar first as it contains elements like logout button
    await loadAdminSidebar();

    // 1. Check if user is authenticated as admin
    if (typeof checkAdminAuth === 'function') { // checkAdminAuth from admin_auth.js
        if (!checkAdminAuth() && !window.location.pathname.endsWith('admin_login.html')) {
            window.location.href = 'admin_login.html';
            return; // Stop further execution if not authenticated
        }
    } else {
        console.error("checkAdminAuth function not found. Ensure admin_auth.js is loaded.");
        if (!window.location.pathname.endsWith('admin_login.html')) {
             // Potentially redirect to login as a fallback if auth check is missing
             // window.location.href = 'admin_login.html';
        }
    }

    // 2. Initialize common admin UI elements (like header greeting, if any)
    if (typeof initializeAdminUI === 'function') { // initializeAdminUI from admin_ui.js
        initializeAdminUI();
    } else {
        console.error("initializeAdminUI function not found. Ensure admin_ui.js is loaded.");
    }

    // 3. Page-specific initializations
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
    } else if (bodyId === 'page-admin-manage-orders') { // B2C Orders
         if (typeof initializeOrderManagement === 'function') { // from admin_orders.js
            initializeOrderManagement();
        }
    } else if (bodyId === 'page-admin-manage-invoices') { // B2B Invoices
        if (typeof initializeAdminInvoiceManagement === 'function') { // from admin_invoices.js
            initializeAdminInvoiceManagement();
        } else {
            console.error("initializeAdminInvoiceManagement function not found. Ensure admin_invoices.js is loaded.");
        }
    }
    // Add more page initializations as needed
});
