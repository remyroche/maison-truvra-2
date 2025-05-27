// website/admin/js/admin_dashboard.js
import { callAdminApi, showAdminToast } from './admin_api.js';

document.addEventListener('DOMContentLoaded', () => {
    const page = getCurrentPageName();

    if (page === 'admin_dashboard.html') {
        loadDashboardStats();
        // Potentially load recent orders or other dynamic content here
    }
});

function getCurrentPageName() {
    const path = window.location.pathname;
    return path.substring(path.lastIndexOf('/') + 1);
}

// Helper to format currency (simple example)
function formatCurrency(amount, currency = 'EUR') {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: currency }).format(amount);
}


async function loadDashboardStats() {
    try {
        const data = await callAdminApi('/dashboard-stats', 'GET');
        if (data.success && data.stats) {
            const stats = data.stats;
            
            const totalProductsEl = document.getElementById('stats-total-products');
            if (totalProductsEl) totalProductsEl.textContent = stats.total_products !== undefined ? stats.total_products : 'N/A';
            
            const recentOrdersEl = document.getElementById('stats-recent-orders-count'); // ID updated for clarity
            if (recentOrdersEl) recentOrdersEl.textContent = stats.recent_orders_count !== undefined ? stats.recent_orders_count : 'N/A';
            
            const newUsersEl = document.getElementById('stats-new-users-count'); // ID updated for clarity
            if (newUsersEl) newUsersEl.textContent = stats.new_users_count !== undefined ? stats.new_users_count : 'N/A';
            
            const totalSalesEl = document.getElementById('stats-total-sales');
            if (totalSalesEl) totalSalesEl.textContent = stats.total_sales !== undefined ? formatCurrency(stats.total_sales) : 'N/A';
            
            const pendingB2BEl = document.getElementById('stats-pending-b2b-approvals');
            if (pendingB2BEl) pendingB2BEl.textContent = stats.pending_b2b_approvals !== undefined ? stats.pending_b2b_approvals : 'N/A';

        } else {
            showAdminToast(data.message || 'Failed to load dashboard stats.', 'error');
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showAdminToast('An error occurred while fetching dashboard statistics.', 'error');
        // Optionally, set text of stat elements to 'Error'
        const statIds = ['stats-total-products', 'stats-recent-orders-count', 'stats-new-users-count', 'stats-total-sales', 'stats-pending-b2b-approvals'];
        statIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = 'Error';
        });
    }
}
