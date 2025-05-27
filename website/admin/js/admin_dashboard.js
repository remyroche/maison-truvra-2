<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Maison Trüvra</title>
    <link href="https://cdn.tailwindcss.com" rel="stylesheet">
    <link rel="stylesheet" href="admin_styles.css">
    <link rel="icon" href="../assets/favicon.ico" type="image/x-icon">
    <link rel="shortcut icon" href="../assets/favicon.png" type="image/png">
    <link rel="apple-touch-icon" sizes="180x180" href="../assets/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="../assets/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="../assets/favicon-16x16.png">
</head>
<body class="bg-gray-100 font-sans">
    <div class="flex h-screen">
        <div id="adminSidebarContainer" class="w-64 bg-gray-800 text-white p-5 space-y-6">
            <div class="text-center py-4">
                <a href="admin_dashboard.html" class="text-2xl font-semibold hover:text-gold-500 transition-colors">Maison Trüvra</a>
                <p class="text-sm text-gray-400">Admin Panel</p>
            </div>
            <nav class="space-y-2">
                <a href="admin_dashboard.html" class="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 hover:text-gold-400">Dashboard</a>
                <a href="admin_manage_products.html" class="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 hover:text-gold-400">Manage Products</a>
                <a href="admin_manage_orders.html" class="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 hover:text-gold-400">Manage Orders</a>
                <a href="admin_manage_users.html" class="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 hover:text-gold-400">Manage Users</a>
                <a href="admin_manage_inventory.html" class="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 hover:text-gold-400">Manage Inventory</a>
                <a href="admin_manage_invoices.html" class="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 hover:text-gold-400">Manage Invoices (B2B)</a>
                <a href="#" id="adminLogoutLink" class="block py-2.5 px-4 rounded transition duration-200 hover:bg-red-600 hover:text-white">Logout</a>
            </nav>
        </div>

        <div class="flex-1 flex flex-col overflow-hidden">
            <header class="bg-white shadow-md p-4">
                <div class="flex justify-between items-center">
                    <h1 class="text-2xl font-semibold text-gray-800">Dashboard Overview</h1>
                    <div id="adminUserDisplay" class="text-sm text-gray-600">
                        </div>
                </div>
            </header>
            
            <main class="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100 p-6">
                <div class="container mx-auto">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                        <div class="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl transition-shadow">
                            <h3 class="text-lg font-semibold text-gray-600 mb-1">Total Sales</h3>
                            <p id="stats-total-sales" class="text-3xl font-bold text-green-600">Loading...</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl transition-shadow">
                            <h3 class="text-lg font-semibold text-gray-600 mb-1">Recent Orders</h3>
                            <p id="stats-recent-orders-count" class="text-3xl font-bold text-blue-600">Loading...</p>
                            <p class="text-xs text-gray-500">(Last 7 days)</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl transition-shadow">
                            <h3 class="text-lg font-semibold text-gray-600 mb-1">New Users</h3>
                            <p id="stats-new-users-count" class="text-3xl font-bold text-purple-600">Loading...</p>
                             <p class="text-xs text-gray-500">(Last 7 days)</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl transition-shadow">
                            <h3 class="text-lg font-semibold text-gray-600 mb-1">Total Products</h3>
                            <p id="stats-total-products" class="text-3xl font-bold text-yellow-600">Loading...</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl transition-shadow">
                            <h3 class="text-lg font-semibold text-gray-600 mb-1">Pending B2B Approvals</h3>
                            <p id="stats-pending-b2b-approvals" class="text-3xl font-bold text-red-600">Loading...</p>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="text-xl font-semibold text-gray-700 mb-4">Recent Activity</h3>
                            <ul id="recentActivityList" class="space-y-3 text-sm text-gray-600">
                                <li>New order #1234 placed by user@example.com</li>
                                <li>Product "Black Truffle" stock updated.</li>
                                <li>New professional user "Pro User Inc." registered.</li>
                                <li>Invoice INV-2024-001 generated.</li>
                            </ul>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="text-xl font-semibold text-gray-700 mb-4">Quick Links</h3>
                            <div class="space-y-2">
                                <a href="admin_manage_products.html#addProductForm" class="block text-blue-600 hover:underline">Add New Product</a>
                                <a href="admin_manage_users.html?filter=pending_approval" class="block text-blue-600 hover:underline">View Pending Approvals</a>
                                <a href="admin_manage_orders.html" class="block text-blue-600 hover:underline">View All Orders</a>
                            </div>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    </div>

    <div id="adminToast" class="fixed bottom-5 right-5 bg-gray-800 text-white py-3 px-5 rounded-lg shadow-xl text-sm z-50 transition-opacity duration-300 opacity-0">
        <span id="adminToastMessage">Default Toast Message</span>
    </div>

    <script type="module" src="js/admin_main.js"></script>
    <script type="module" src="js/admin_dashboard.js"></script> 
</body>
</html>
