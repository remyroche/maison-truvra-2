// website/admin/js/admin_users.js

let allUsersCache = []; // Cache for all users to allow client-side filtering/pagination
let currentUsersPage = 1;
const usersPerPage = 10; // Or make this configurable

document.addEventListener('DOMContentLoaded', () => {
    // This check ensures admin_users.js logic only runs if specifically on 'page-admin-manage-users'
    // and admin_main.js will call initializeAdminManageUsersPage()
});

async function initializeAdminManageUsersPage() {
    await loadPendingB2BUsers();
    await loadAllUsers(); // Load all users into cache

    const searchInput = document.getElementById('user-search-input');
    const typeFilter = document.getElementById('user-type-filter');
    const statusFilter = document.getElementById('user-status-filter');

    if (searchInput) searchInput.addEventListener('input', () => { currentUsersPage = 1; displayUsersFromCache(); });
    if (typeFilter) typeFilter.addEventListener('change', () => { currentUsersPage = 1; displayUsersFromCache(); });
    if (statusFilter) statusFilter.addEventListener('change', () => { currentUsersPage = 1; displayUsersFromCache(); });
    
    document.getElementById('prev-page-button')?.addEventListener('click', () => {
        if (currentUsersPage > 1) {
            currentUsersPage--;
            displayUsersFromCache();
        }
    });
    document.getElementById('next-page-button')?.addEventListener('click', () => {
        // Check against total pages before incrementing
        const totalPages = Math.ceil(getFilteredUsers().length / usersPerPage);
        if (currentUsersPage < totalPages) {
            currentUsersPage++;
            displayUsersFromCache();
        }
    });

    // Modal for B2B status update
    const b2bStatusModal = document.getElementById('update-b2b-status-modal');
    const cancelB2BStatusModalButton = document.getElementById('cancel-update-b2b-status-modal');
    const updateB2BStatusForm = document.getElementById('update-b2b-status-form');

    if (cancelB2BStatusModalButton) cancelB2BStatusModalButton.addEventListener('click', () => b2bStatusModal.style.display = 'none');
    if (updateB2BStatusForm) updateB2BStatusForm.addEventListener('submit', handleUpdateB2BUserStatus);

    // Close modal if overlay is clicked
    const userDetailModal = document.getElementById('user-detail-modal');
    if(userDetailModal) {
        userDetailModal.addEventListener('click', function(event) {
            if (event.target === userDetailModal) {
                closeUserDetailModal();
            }
        });
    }
    const closeUserDetailModalButton = document.getElementById('close-user-detail-modal-button');
    if(closeUserDetailModalButton) closeUserDetailModalButton.addEventListener('click', closeUserDetailModal);

}

async function loadPendingB2BUsers() {
    const tableBody = document.getElementById('pending-b2b-users-table-body');
    tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Chargement...</td></tr>';
    try {
        const response = await makeAdminApiRequest('/users/b2b/pending', 'GET');
        if (response.success && response.users) {
            if (response.users.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Aucune demande B2B en attente.</td></tr>';
                return;
            }
            let rowsHtml = '';
            response.users.forEach(user => {
                const createdAt = user.created_at ? new Date(user.created_at).toLocaleDateString('fr-FR') : 'N/A';
                rowsHtml += `
                    <tr class="border-b border-brand-cream hover:bg-brand-cream/30">
                        <td class="px-4 py-3">${user.id}</td>
                        <td class="px-4 py-3">${user.email}</td>
                        <td class="px-4 py-3">${user.company_name || 'N/A'}</td>
                        <td class="px-4 py-3">${user.prenom || ''} ${user.nom || ''}</td>
                        <td class="px-4 py-3">${user.phone_number || 'N/A'}</td>
                        <td class="px-4 py-3">${createdAt}</td>
                        <td class="px-4 py-3">
                            <button class="btn-admin-success text-xs approve-b2b-button" data-user-id="${user.id}" data-user-name="${user.company_name || user.email}">
                                Approuver
                            </button>
                            </td>
                    </tr>
                `;
            });
            tableBody.innerHTML = rowsHtml;
            attachB2BApprovalListeners();
        } else {
            tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4">${response.message || 'Erreur de chargement.'}</td></tr>`;
        }
    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Erreur serveur: ${error.message}</td></tr>`;
    }
}

function attachB2BApprovalListeners() {
    document.querySelectorAll('.approve-b2b-button').forEach(button => {
        button.addEventListener('click', async function() {
            const userId = this.dataset.userId;
            const userName = this.dataset.userName;
            if (confirm(`Voulez-vous vraiment approuver le compte B2B pour ${userName} ?`)) {
                showAdminGlobalMessage("Approbation en cours...", "info");
                try {
                    const response = await makeAdminApiRequest(`/users/b2b/${userId}/approve`, 'POST');
                    if (response.success) {
                        showAdminGlobalMessage(response.message || `Compte pour ${userName} approuvé.`, "success");
                        await loadPendingB2BUsers(); // Refresh pending list
                        await loadAllUsers(); // Refresh all users list as status changed
                    } else {
                        showAdminGlobalMessage(response.message || "Échec de l'approbation.", "error");
                    }
                } catch (error) {
                    showAdminGlobalMessage(`Erreur serveur: ${error.message}`, "error");
                }
            }
        });
    });
}

async function loadAllUsers() {
    // This function now populates the cache, display is handled by displayUsersFromCache
    try {
        const response = await makeAdminApiRequest('/users?page_size=1000', 'GET'); // Fetch a large number, or implement proper pagination API
        if (response.success && response.users) {
            allUsersCache = response.users;
            currentUsersPage = 1; // Reset to first page
            displayUsersFromCache();
        } else {
            document.getElementById('users-table-body').innerHTML = `<tr><td colspan="9" class="text-center py-4">${response.message || 'Erreur de chargement.'}</td></tr>`;
        }
    } catch (error) {
        document.getElementById('users-table-body').innerHTML = `<tr><td colspan="9" class="text-center py-4">Erreur serveur: ${error.message}</td></tr>`;
    }
}

function getFilteredUsers() {
    const searchTerm = document.getElementById('user-search-input')?.value.toLowerCase() || '';
    const typeFilter = document.getElementById('user-type-filter')?.value || '';
    const statusFilter = document.getElementById('user-status-filter')?.value || '';

    return allUsersCache.filter(user => {
        const matchesSearch = searchTerm === '' ||
            user.email.toLowerCase().includes(searchTerm) ||
            (user.nom && user.nom.toLowerCase().includes(searchTerm)) ||
            (user.prenom && user.prenom.toLowerCase().includes(searchTerm)) ||
            (user.company_name && user.company_name.toLowerCase().includes(searchTerm));
        
        const matchesType = typeFilter === '' || user.user_type === typeFilter;
        const matchesStatus = statusFilter === '' || user.status === statusFilter;

        return matchesSearch && matchesType && matchesStatus;
    });
}


function displayUsersFromCache() {
    const tableBody = document.getElementById('users-table-body');
    const filteredUsers = getFilteredUsers();

    const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
    const startIndex = (currentUsersPage - 1) * usersPerPage;
    const endIndex = startIndex + usersPerPage;
    const paginatedUsers = filteredUsers.slice(startIndex, endIndex);

    if (paginatedUsers.length === 0 && allUsersCache.length > 0) { // Check if cache has users but filter yields none
        tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4">Aucun utilisateur ne correspond à vos filtres.</td></tr>';
    } else if (allUsersCache.length === 0) { // Cache is empty
         tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4">Aucun utilisateur trouvé.</td></tr>';
    }
    else {
        let rowsHtml = '';
        paginatedUsers.forEach(user => {
            const createdAt = user.created_at ? new Date(user.created_at).toLocaleDateString('fr-FR') : 'N/A';
            const userStatus = user.status || 'N/A';
            rowsHtml += `
                <tr class="border-b border-brand-cream hover:bg-brand-cream/30">
                    <td class="px-4 py-3">${user.id}</td>
                    <td class="px-4 py-3">${user.email}</td>
                    <td class="px-4 py-3">${user.prenom || ''} ${user.nom || ''}</td>
                    <td class="px-4 py-3">${user.company_name || 'N/A'}</td>
                    <td class="px-4 py-3">${user.user_type}</td>
                    <td class="px-4 py-3"><span class="status-badge status-${userStatus.replace(/\s+/g, '_').toLowerCase()}">${userStatus}</span></td>
                    <td class="px-4 py-3">${user.is_admin ? 'Oui' : 'Non'}</td>
                    <td class="px-4 py-3">${createdAt}</td>
                    <td class="px-4 py-3">
                        <button class="btn-admin-icon view-user-detail-button" data-user-id="${user.id}" title="Voir Détails">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                        </button>
                        ${user.user_type === 'b2b' ? `
                        <button class="btn-admin-icon edit-b2b-status-button" data-user-id="${user.id}" data-user-name="${user.company_name || user.email}" data-current-status="${user.status}" title="Modifier Statut B2B">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" /></svg>
                        </button>
                        ` : ''}
                        </td>
                </tr>
            `;
        });
        tableBody.innerHTML = rowsHtml;
        attachViewDetailListeners();
        attachB2BStatusEditListeners();
    }
    updatePaginationControls(filteredUsers.length, totalPages);
}

function updatePaginationControls(totalFilteredItems, totalPages) {
    const pageInfo = document.getElementById('page-info');
    const prevButton = document.getElementById('prev-page-button');
    const nextButton = document.getElementById('next-page-button');

    if (pageInfo) pageInfo.textContent = `Page ${currentUsersPage} sur ${totalPages > 0 ? totalPages : 1}`;
    if (prevButton) prevButton.disabled = currentUsersPage === 1;
    if (nextButton) nextButton.disabled = currentUsersPage === totalPages || totalPages === 0;
}


function attachViewDetailListeners() {
    document.querySelectorAll('.view-user-detail-button').forEach(button => {
        button.addEventListener('click', async function() {
            const userId = this.dataset.userId;
            await openUserDetailModal(userId);
        });
    });
}

function attachB2BStatusEditListeners() {
    document.querySelectorAll('.edit-b2b-status-button').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const userName = this.dataset.userName;
            const currentStatus = this.dataset.currentStatus;

            document.getElementById('modal-b2b-user-id-status').value = userId;
            document.getElementById('modal-b2b-user-name-status').textContent = userName;
            document.getElementById('modal-select-b2b-status').value = currentStatus;
            document.getElementById('update-b2b-status-modal').style.display = 'flex';
        });
    });
}

async function handleUpdateB2BUserStatus(event) {
    event.preventDefault();
    const form = event.target;
    const userId = form.querySelector('#modal-b2b-user-id-status').value;
    const newStatus = form.querySelector('#modal-select-b2b-status').value;

    try {
        const response = await makeAdminApiRequest(`/users/b2b/${userId}/status`, 'PUT', { status: newStatus });
        if (response.success) {
            showAdminGlobalMessage(response.message || "Statut de l'utilisateur B2B mis à jour.", "success");
            document.getElementById('update-b2b-status-modal').style.display = 'none';
            await loadAllUsers(); // Refresh user list
            if (newStatus !== 'pending_approval') { // If status changed from pending, refresh pending list too
                await loadPendingB2BUsers();
            }
        } else {
            showAdminGlobalMessage(response.message || "Erreur lors de la mise à jour du statut.", "error");
        }
    } catch (error) {
        showAdminGlobalMessage(`Erreur serveur: ${error.message}`, "error");
    }
}


async function openUserDetailModal(userId) {
    const modal = document.getElementById('user-detail-modal');
    const modalBody = document.getElementById('user-detail-modal-body');
    modalBody.querySelectorAll('.data-field').forEach(el => el.textContent = 'Chargement...'); // Clear previous data

    try {
        const response = await makeAdminApiRequest(`/users/${userId}`, 'GET'); // Assuming a /users/:id endpoint exists
        if (response.success && response.user) {
            const user = response.user;
            document.getElementById('user-detail-modal-title').textContent = `Détails de: ${user.prenom || ''} ${user.nom || user.email}`;
            document.getElementById('detail-user-id').textContent = user.id;
            document.getElementById('detail-user-email').textContent = user.email;
            document.getElementById('detail-user-nom').textContent = user.nom || 'N/A';
            document.getElementById('detail-user-prenom').textContent = user.prenom || 'N/A';
            document.getElementById('detail-user-type').textContent = user.user_type;
            document.getElementById('detail-user-company').textContent = user.company_name || 'N/A';
            document.getElementById('detail-user-phone').textContent = user.phone_number || 'N/A';
            document.getElementById('detail-user-status').innerHTML = `<span class="status-badge status-${(user.status || 'N/A').replace(/\s+/g, '_').toLowerCase()}">${user.status || 'N/A'}</span>`;
            document.getElementById('detail-user-isadmin').textContent = user.is_admin ? 'Oui' : 'Non';
            document.getElementById('detail-user-createdat').textContent = user.created_at ? new Date(user.created_at).toLocaleString('fr-FR') : 'N/A';
            document.getElementById('detail-user-passwordlastchanged').textContent = user.password_last_changed ? new Date(user.password_last_changed).toLocaleString('fr-FR') : 'Jamais';

            // Fetch and display orders (B2C)
            const ordersList = document.getElementById('detail-user-orders');
            ordersList.innerHTML = '<li>Chargement des commandes...</li>';
            // const ordersResponse = await makeAdminApiRequest(`/orders?user_id=${userId}`, 'GET');
            // if (ordersResponse.success && ordersResponse.orders && ordersResponse.orders.length > 0) {
            //     ordersList.innerHTML = ordersResponse.orders.map(o => `<li>${o.order_number} - ${o.total_amount} € (${new Date(o.order_date).toLocaleDateString()})</li>`).join('');
            // } else {
                 ordersList.innerHTML = '<li class="text-brand-warm-taupe italic">Aucune commande B2C trouvée.</li>';
            // }

            // Fetch and display invoices (B2B)
            const invoicesList = document.getElementById('detail-user-invoices');
            if (user.user_type === 'b2b') {
                invoicesList.innerHTML = '<li>Chargement des factures...</li>';
                const invoicesResponse = await makeAdminApiRequest(`/invoices/b2b/for-user/${userId}`, 'GET');
                if (invoicesResponse.success && invoicesResponse.invoices && invoicesResponse.invoices.length > 0) {
                    invoicesList.innerHTML = invoicesResponse.invoices.map(inv => `<li>${inv.invoice_number} - ${inv.total_amount_ttc} € (${inv.status})</li>`).join('');
                } else {
                    invoicesList.innerHTML = '<li class="text-brand-warm-taupe italic">Aucune facture B2B trouvée.</li>';
                }
            } else {
                invoicesList.innerHTML = '<li class="text-brand-warm-taupe italic">N/A (Utilisateur non B2B).</li>';
            }


            modal.style.display = 'flex';
        } else {
            showAdminGlobalMessage(response.message || "Impossible de charger les détails de l'utilisateur.", "error");
        }
    } catch (error) {
        showAdminGlobalMessage(`Erreur serveur: ${error.message}`, "error");
    }
}

function closeUserDetailModal() {
    const modal = document.getElementById('user-detail-modal');
    if(modal) modal.style.display = 'none';
}

window.initializeAdminManageUsersPage = initializeAdminManageUsersPage;

