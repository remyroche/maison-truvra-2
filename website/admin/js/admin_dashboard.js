<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Maison Trüvra</title>
    <link href="https://cdn.tailwindcss.com" rel="stylesheet"><!DOCTYPE html>
<html lang="en">
<head>// website/admin/js/admin_dashboard.js
// Handles logic for the Admin Dashboard page.

async function initializeAdminDashboard() {
    console.log("Admin Dashboard script initializing...");

    // --- Ensure Global UI Functions are available (showAlert, showGlobalAdminMessage, getAdminAuthToken) ---
    if (!window.showAlert) {
        console.warn("Global showAlert function not found. Using console.log fallback.");
        window.showAlert = (message, title = "Alert") => console.log(`DASHBOARD ALERT (${title}): ${message}`);
    }
    if (!window.showGlobalAdminMessage) {
        console.warn("Global showGlobalAdminMessage function not found. Using console.log fallback.");
        window.showGlobalAdminMessage = (message, type = "info") => console.log(`DASHBOARD GLOBAL MSG (${type}): ${message}`);
    }
    if (!window.getAdminAuthToken) {
        console.warn("Global getAdminAuthToken function not found. Using placeholder token.");
        window.getAdminAuthToken = () => 'admin_token_placeholder_dashboard';
    }
    // --- End UI Function Checks ---

    // --- DOM Element References from the new HTML structure ---
    const totalSalesEl = document.getElementById('total-sales');
    const totalOrdersEl = document.getElementById('total-orders');
    const newCustomersEl = document.getElementById('new-customers');
    const pendingB2BApprovalsEl = document.getElementById('pending-b2b-approvals');
    const totalUsersStatEl = document.getElementById('total-users-stat');
    const totalProductsStatEl = document.getElementById('total-products-stat');
    const recentActivityListEl = document.getElementById('recent-activity-list');
    const dashboardErrorMsgEl = document.getElementById('dashboard-error-message');


    // Function to fetch and display statistics
    async function fetchDashboardStats() {
        try {
            if (!window.makeAdminApiRequest) {
                throw new Error("adminApi.js not loaded or makeAdminApiRequest not defined.");
            }

            // Example: Fetch combined dashboard summary statistics
            const summaryResponse = await makeAdminApiRequest('/stats/summary', 'GET');

            if (summaryResponse && summaryResponse.success && summaryResponse.data) {
                const stats = summaryResponse.data;
                if (totalSalesEl) totalSalesEl.textContent = `€${(stats.total_revenue || 0).toFixed(2)}`;
                if (totalOrdersEl) totalOrdersEl.textContent = stats.total_orders || '0';
                if (newCustomersEl) newCustomersEl.textContent = stats.new_customers_last_30d || '0'; // Assuming API provides this
                if (pendingB2BApprovalsEl) pendingB2BApprovalsEl.textContent = stats.pending_b2b_approvals || '0'; // Assuming API provides this
                if (totalUsersStatEl) totalUsersStatEl.textContent = stats.total_users || '0';
                if (totalProductsStatEl) totalProductsStatEl.textContent = stats.total_products || '0';

                if (dashboardErrorMsgEl) dashboardErrorMsgEl.classList.add('hidden');
            } else {
                console.error('Failed to fetch dashboard summary stats:', summaryResponse?.message);
                if (dashboardErrorMsgEl) {
                    dashboardErrorMsgEl.textContent = `Could not load dashboard statistics: ${summaryResponse?.message || 'Unknown error'}`;
                    dashboardErrorMsgEl.classList.remove('hidden');
                }
            }
        } catch (error) {
            console.error('Error fetching dashboard stats:', error);
            if (dashboardErrorMsgEl) {
                dashboardErrorMsgEl.textContent = `Error fetching dashboard data: ${error.message}`;
                dashboardErrorMsgEl.classList.remove('hidden');
            }
        }
    }

    // Function to fetch and display recent activity (placeholder)
    async function fetchRecentActivity() {
        if (!recentActivityListEl) return;
        recentActivityListEl.innerHTML = ''; // Clear placeholder

        try {
            // Example: Fetch recent notifications or activities
            // const activityResponse = await makeAdminApiRequest('/activity/recent?limit=5', 'GET');
            // if (activityResponse && activityResponse.success && activityResponse.data) {
            //     if (activityResponse.data.length === 0) {
            //         recentActivityListEl.innerHTML = `<li>${window.translateToken ? window.translateToken('admin.dashboard.noRecentActivity', 'No recent activity.') : 'No recent activity.'}</li>`;
            //     } else {
            //         activityResponse.data.forEach(activity => {
            //             const listItem = document.createElement('li');
            //             listItem.textContent = `${new Date(activity.timestamp).toLocaleString()}: ${activity.message}`;
            //             // Could add links or icons based on activity type
            //             recentActivityListEl.appendChild(listItem);
            //         });
            //     }
            // } else {
            //     recentActivityListEl.innerHTML = `<li>${window.translateToken ? window.translateToken('admin.dashboard.errorLoadingActivity', 'Could not load recent activity.') : 'Could not load recent activity.'}</li>`;
            // }
            recentActivityListEl.innerHTML = `<li>${window.translateToken ? window.translateToken('admin.dashboard.recentActivityPlaceholder', 'Recent activity feed placeholder.') : 'Recent activity feed placeholder.'}</li>`; // Placeholder content
        } catch (error) {
            console.error('Error fetching recent activity:', error);
            recentActivityListEl.innerHTML = `<li>${window.translateToken ? window.translateToken('admin.dashboard.errorLoadingActivity', 'Error loading recent activity.') : 'Error loading recent activity.'}</li>`;
        }
        if(window.applyI18nToElement) window.applyI18nToElement(recentActivityListEl);
    }

    // Initial data fetch
    await fetchDashboardStats();
    await fetchRecentActivity();

    // Apply i18n to the whole page after dynamic content might be loaded
    if (window.applyI18nToElement) {
        window.applyI18nToElement(document.body);
    }

    console.log("Admin Dashboard initialized.");
}

// Make the initialization function globally accessible if admin_main.js is to call it.
// Otherwise, call it directly on DOMContentLoaded.
if (typeof window.initializeAdminDashboard === 'undefined') {
    window.initializeAdminDashboard = initializeAdminDashboard;
}

// Self-initialize if not called by admin_main.js
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAdminDashboard);
} else {
    // DOMContentLoaded has already fired
    initializeAdminDashboard();
}
