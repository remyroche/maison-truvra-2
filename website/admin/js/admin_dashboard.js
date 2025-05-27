<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Maison Trüvra</title>
    <link href="https://cdn.tailwindcss.com" rel="stylesheet"><!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Maison Trüvra</title>
    <link href="https://cdn.tailwindcss.com" rel="stylesheet">
    <link rel="stylesheet" href="admin_styles.css">
    <link rel="icon" href="../assets/favicon.ico" type="image/x-icon">// Admin Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function () {
    console.log("Admin Dashboard script loaded.");

    // Function to fetch and display statistics
    async function fetchStats() {
        try {
            // --- Total Users ---
            const usersResponse = await fetch('/api/admin/stats/total_users', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${getAdminAuthToken()}`, // Implement getAdminAuthToken()
                    'Content-Type': 'application/json'
                }
            });
            if (usersResponse.ok) {
                const usersData = await usersResponse.json();
                const totalUsersElement = document.getElementById('total-users-stat');
                if (totalUsersElement) totalUsersElement.textContent = usersData.total_users || '0';
            } else {
                console.error('Failed to fetch total users:', usersResponse.status);
            }

            // --- Total Products ---
            const productsResponse = await fetch('/api/admin/stats/total_products', {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${getAdminAuthToken()}` }
            });
            if (productsResponse.ok) {
                const productsData = await productsResponse.json();
                const totalProductsElement = document.getElementById('total-products-stat');
                if (totalProductsElement) totalProductsElement.textContent = productsData.total_products || '0';
            } else {
                console.error('Failed to fetch total products:', productsResponse.status);
            }

            // --- Total Orders ---
            const ordersResponse = await fetch('/api/admin/stats/total_orders', {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${getAdminAuthToken()}` }
            });
            if (ordersResponse.ok) {
                const ordersData = await ordersResponse.json();
                const totalOrdersElement = document.getElementById('total-orders-stat');
                if (totalOrdersElement) totalOrdersElement.textContent = ordersData.total_orders || '0';
            } else {
                console.error('Failed to fetch total orders:', ordersResponse.status);
            }

            // --- Total Revenue ---
            const revenueResponse = await fetch('/api/admin/stats/total_revenue', {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${getAdminAuthToken()}` }
            });
            if (revenueResponse.ok) {
                const revenueData = await revenueResponse.json();
                const totalRevenueElement = document.getElementById('total-revenue-stat');
                if (totalRevenueElement) {
                    totalRevenueElement.textContent = `€${(revenueData.total_revenue || 0).toFixed(2)}`;
                }
            } else {
                console.error('Failed to fetch total revenue:', revenueResponse.status);
            }

            // Placeholder for Recent Orders and Recent Reviews
            fetchRecentOrders();
            fetchRecentReviews();

        } catch (error) {
            console.error('Error fetching dashboard stats:', error);
            // Display a generic error message on the dashboard if needed
            const errorElement = document.getElementById('dashboard-error-message');
            if(errorElement) errorElement.textContent = "Could not load dashboard statistics.";
        }
    }

    function getAdminAuthToken() {
        // Implement this function to retrieve the admin's authentication token
        // This might be from localStorage, a cookie, or another source
        return localStorage.getItem('adminAuthToken') || 'admin_token_placeholder'; // Fallback for testing
    }

    // Placeholder function to fetch recent orders
    async function fetchRecentOrders() {
        const recentOrdersList = document.getElementById('recent-orders-list');
        if (!recentOrdersList) return;
        
        // Example: Fetch last 5 orders
        // const response = await fetch('/api/admin/orders?limit=5&sort=desc', { headers: { 'Authorization': `Bearer ${getAdminAuthToken()}` }});
        // if (response.ok) {
        //     const orders = await response.json();
        //     recentOrdersList.innerHTML = ''; // Clear existing
        //     orders.forEach(order => {
        //         const listItem = document.createElement('li');
        //         listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
        //         listItem.innerHTML = `
        //             <span>Order #${order.id} - ${order.customer_name || 'N/A'}</span>
        //             <span class="badge bg-primary rounded-pill">${order.status}</span>
        //             <span class="text-muted">${new Date(order.order_date).toLocaleDateString()}</span>
        //             <a href="admin_manage_orders.html?order_id=${order.id}" class="btn btn-sm btn-outline-secondary">View</a>
        //         `;
        //         recentOrdersList.appendChild(listItem);
        //     });
        // } else {
        //     recentOrdersList.innerHTML = '<li class="list-group-item">Could not load recent orders.</li>';
        // }
        recentOrdersList.innerHTML = '<li class="list-group-item">Recent orders functionality placeholder.</li>'; // Placeholder
    }

    // Placeholder function to fetch recent reviews
    async function fetchRecentReviews() {
        const recentReviewsList = document.getElementById('recent-reviews-list');
        if (!recentReviewsList) return;
        // Example: Fetch last 5 pending reviews
        // const response = await fetch('/api/admin/reviews?status=pending&limit=5', { headers: { 'Authorization': `Bearer ${getAdminAuthToken()}` }});
        // if (response.ok) {
        //     const reviews = await response.json();
        //     recentReviewsList.innerHTML = ''; // Clear existing
        //     reviews.forEach(review => {
        //         const listItem = document.createElement('li');
        //         listItem.className = 'list-group-item';
        //         listItem.innerHTML = `
        //             <p><strong>${review.product_name}</strong> by ${review.user_name}</p>
        //             <p>Rating: ${review.rating}/5</p>
        //             <p class="text-muted fst-italic">"${review.comment.substring(0, 50)}..."</p>
        //             <a href="admin_manage_reviews.html?review_id=${review.id}" class="btn btn-sm btn-outline-secondary">Moderate</a>
        //         `;
        //         recentReviewsList.appendChild(listItem);
        //     });
        // } else {
        //     recentReviewsList.innerHTML = '<li class="list-group-item">Could not load recent reviews.</li>';
        // }
        recentReviewsList.innerHTML = '<li class="list-group-item">Recent reviews functionality placeholder.</li>'; // Placeholder
    }


    // Initialize dashboard
    if (document.getElementById('total-users-stat')) { // Check if we are on the dashboard page
        fetchStats();
    }

    // Add event listeners for any interactive elements on the dashboard if needed
    // e.g., refresh buttons, date range selectors for charts (if you add charts)
});

// Note: This script assumes your admin_dashboard.html has elements with these IDs:
// - total-users-stat
// - total-products-stat
// - total-orders-stat
// - total-revenue-stat
// - recent-orders-list (e.g., a <ul>)
// - recent-reviews-list (e.g., a <ul>)
// - dashboard-error-message (optional, for displaying errors)

// You will also need to implement the backend API endpoints:
// - GET /api/admin/stats/total_users
// - GET /api/admin/stats/total_products
// - GET /api/admin/stats/total_orders
// - GET /api/admin/stats/total_revenue
// - (Optional) Endpoints for recent orders and reviews
