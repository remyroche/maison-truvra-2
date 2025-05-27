// Create this file: remyroche/maison-truvra-2/maison-truvra-2-main/website/admin/js/admin_dashboard.js
async function initializeAdminDashboard() {
    if (document.body.id !== 'page-admin-dashboard') return;
    console.log("Initializing Admin Dashboard...");
    try {
        const response = await adminApiRequest('/dashboard-stats'); // Assumes adminApiRequest is globally available
        if (response.success) {
            document.getElementById('stats-total-products').textContent = response.stats.total_products || '0';
            document.getElementById('stats-recent-orders').textContent = response.stats.recent_orders || '0';
            document.getElementById('stats-new-users').textContent = response.stats.new_users || '0';

            const notificationsList = document.getElementById('recent-notifications');
            if (response.notifications && response.notifications.length > 0) {
                notificationsList.innerHTML = response.notifications.map(n =>
                    `<li class="<span class="math-inline">\{n\.read ? 'text\-brand\-warm\-taupe' \: 'text\-brand\-near\-black font\-semibold'\}"\>
