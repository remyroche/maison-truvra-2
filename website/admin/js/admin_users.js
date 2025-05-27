// website/admin/js/admin_users.js

/**
 * Initializes user management functionalities:
 * - Loads the list of all users.
 * - Loads the list of pending B2B users.
 * - Sets up event listeners for viewing user details.
 */
async function initializeUserManagement() {
    if (document.body.id !== 'page-admin-manage-users') return;
    console.log("Initializing User Management...");

    await loadAllUsers();
    await loadPendingB2BUsers();

    const closeDetailModalButton = document.getElementById('close-user-detail-modal-button');
    if (closeDetailModalButton) {
        closeDetailModalButton.addEventListener('click', () => closeAdminModal('user-detail-modal'));
    }
    // Add event listener for modal overlay click to close (if not already generic)
    const userDetailModal = document.getElementById('user-detail-modal');
    if (userDetailModal) {
        userDetailModal.addEventListener('click', function(event) {
            if (event.target === userDetailModal) {
                closeAdminModal('user-detail-modal');
            }
        });
    }
}

/**
 * Loads and displays all registered users.
 */
async function loadAllUsers() {
    const tableBody = document.getElementById('users-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4">Chargement des utilisateurs...</td></tr>';
    try {
        const users = await adminApiRequest('/users'); // Assumes adminApiRequest is globally available
        if (users && users.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4">Aucun utilisateur trouvé.</td></tr>';
            return;
        }
        let rowsHtml = '';
        users.forEach(user => {
            const createdAt = new Date(user.created_at).toLocaleDateString('fr-FR');
            rowsHtml += `
                <tr>
                    <td class="px-6 py-3 text-xs">${user.id}</td>
                    <td class="px-6 py-3 text-xs">${user.email}</td>
                    <td class="px-6 py-3 text-xs">${user.nom || 'N/A'}</td>
                    <td class="px-6 py-3 text-xs">${user.prenom || 'N/A'}</td>
                    <td class="px-6 py-3 text-xs">${user.user_type === 'b2b' ? 'Professionnel' : 'Particulier'}</td>
                    <td class="px-6 py-3 text-xs">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${user.status === 'active' ? 'bg-green-100 text-green-800' : (user.status === 'pending_approval' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800')}">
                            ${user.status === 'active' ? 'Actif' : (user.status === 'pending_approval' ? 'En attente' : (user.status || 'N/A'))}
                        </span>
                    </td>
                    <td class="px-6 py-3 text-xs">${user.is_admin ? 'Oui' : 'Non'}</td>
                    <td class="px-6 py-3 text-xs">${createdAt}</td>
                    <td class="px-6 py-3 space-x-2 whitespace-nowrap">
                        <button onclick="viewUserDetails(${user.id})" class="btn-admin-secondary text-xs p-1.5">Détails</button>
                        </td>
                </tr>`;
        });
        tableBody.innerHTML = rowsHtml;
    } catch (error) {
        console.error("Failed to load users:", error);
        tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-red-600">Erreur de chargement des utilisateurs.</td></tr>';
    }
}

/**
 * Loads and displays B2B users pending approval.
 */
async function loadPendingB2BUsers() {
    const tableBody = document.getElementById('pending-b2b-users-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Chargement des demandes...</td></tr>';
    try {
        const response = await adminApiRequest('/users/pending-b2b');
        if (response.success && response.users) {
            if (response.users.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Aucun compte professionnel en attente d\'approbation.</td></tr>';
                return;
            }
            let rowsHtml = '';
            response.users.forEach(user => {
                const createdAt = new Date(user.created_at).toLocaleDateString('fr-FR');
                rowsHtml += `
                    <tr>
                        <td class="px-6 py-3 text-xs">${user.id}</td>
                        <td class="px-6 py-3 text-xs">${user.email}</td>
                        <td class="px-6 py-3 text-xs">${user.company_name || 'N/A'}</td>
                        <td class="px-6 py-3 text-xs">${user.prenom || ''} ${user.nom || ''}</td>
                        <td class="px-6 py-3 text-xs">${createdAt}</td>
                        <td class="px-6 py-3 space-x-2 whitespace-nowrap">
                            <button onclick="approveB2BUser(${user.id})" class="btn-admin-primary text-xs p-1.5">Approuver</button>
                            <button onclick="viewUserDetails(${user.id})" class="btn-admin-secondary text-xs p-1.5">Détails</button>
                            </td>
                    </tr>`;
            });
            tableBody.innerHTML = rowsHtml;
        } else {
            throw new Error(response.message || "Failed to load pending B2B users.");
        }
    } catch (error) {
        console.error("Failed to load pending B2B users:", error);
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-red-600">Erreur de chargement des demandes.</td></tr>';
    }
}

/**
 * Approves a B2B user.
 * @param {number} userId - The ID of the user to approve.
 */
async function approveB2BUser(userId) {
    if (!confirm(`Voulez-vous vraiment approuver l'utilisateur ID ${userId} ?`)) return;

    try {
        const result = await adminApiRequest(`/users/${userId}/approve-b2b`, 'POST');
        if (result.success) {
            showAdminToast(result.message || "Utilisateur B2B approuvé avec succès.", "success");
            loadPendingB2BUsers(); // Refresh pending list
            loadAllUsers();       // Refresh all users list as status changes
        } else {
            showAdminToast(result.message || "Échec de l'approbation de l'utilisateur.", "error");
        }
    } catch (error) {
        showAdminToast("Erreur lors de l'approbation: " + error.message, "error");
        console.error("Error approving B2B user:", error);
    }
}


/**
 * Fetches and displays details for a specific user in a modal.
 * @param {number} userId - The ID of the user.
 */
async function viewUserDetails(userId) {
    try {
        const user = await adminApiRequest(`/users/${userId}`); // This endpoint should fetch full user details
        if (user) {
            document.getElementById('detail-user-id').textContent = user.id;
            document.getElementById('detail-user-email').textContent = user.email;
            document.getElementById('detail-user-nom').textContent = user.nom || 'N/A';
            document.getElementById('detail-user-prenom').textContent = user.prenom || 'N/A';
            document.getElementById('detail-user-type').textContent = user.user_type === 'b2b' ? 'Professionnel' : (user.user_type === 'b2c' ? 'Particulier' : 'N/A');
            document.getElementById('detail-user-company').textContent = user.company_name || 'N/A';
            document.getElementById('detail-user-phone').textContent = user.phone_number || 'N/A';
            document.getElementById('detail-user-status').textContent = user.status || 'N/A';
            document.getElementById('detail-user-isadmin').textContent = user.is_admin ? 'Oui' : 'Non';
            document.getElementById('detail-user-createdat').textContent = new Date(user.created_at).toLocaleString('fr-FR');

            const ordersList = document.getElementById('detail-user-orders');
            if (user.orders && user.orders.length > 0) {
                ordersList.innerHTML = user.orders.map(order =>
                    `<li>Commande #${order.order_id} - ${order.total_amount}€ (${new Date(order.order_date).toLocaleDateString('fr-FR')}) - Statut: ${order.status}</li>`
                ).join('');
            } else {
                ordersList.innerHTML = '<li class="text-brand-warm-taupe italic">Aucune commande pour cet utilisateur.</li>';
            }
            openAdminModal('user-detail-modal');
        } else {
            showAdminToast("Détails de l'utilisateur non trouvés.", "error");
        }
    } catch (error) {
        console.error("Error fetching user details:", error);
        showAdminToast("Erreur de chargement des détails de l'utilisateur.", "error");
    }
}

// Make sure admin_ui.js defines openAdminModal and closeAdminModal
// If not, here are basic implementations:
// function openAdminModal(modalId) {
//     const modal = document.getElementById(modalId);
//     if (modal) modal.classList.add('active');
// }
// function closeAdminModal(modalId) {
//     const modal = document.getElementById(modalId);
//     if (modal) modal.classList.remove('active');
// }
