// This file (website/admin/js/admin_users.js) will contain the JavaScript logic for managing users.
// Assuming the content was previously in 'admin/admin_manage_users.html' or this is a new/updated script.

document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Users JS Loaded");

    const usersTableBody = document.getElementById('usersTableBody');
    const userModal = document.getElementById('userModal');
    const userModalTitle = document.getElementById('userModalTitle');
    const userForm = document.getElementById('userForm');
    const closeUserModalButton = document.getElementById('closeUserModalButton');
    const cancelUserModalButton = document.getElementById('cancelUserModalButton');
    let editingUserId = null;

    // --- Alert/Confirm Modal (Ensure this is available, possibly from admin_main.js or define locally if needed) ---
    let alertModal, alertModalTitleElem, alertModalMessageElem, alertModalCloseButtonElem, alertModalActionsElem;

    function setupAlertModal() {
        // This function assumes a global modal structure. If not, it needs to be created.
        // For brevity, we'll assume it's similar to the one in admin_categories.js or admin_products.js
        // and that showAlert/showConfirm functions are available.
        // If these are defined in admin_main.js and globally accessible, this setup might not be needed here.
        // Fallback:
        if (!window.showAlert || !window.showConfirm) {
            console.warn("Global showAlert/showConfirm not found. Using local stubs for admin_users.js. Implement properly in admin_main.js");
            window.showAlert = (message, title) => console.log(`Alert (${title}): ${message}`);
            window.showConfirm = (message, title, callback) => {
                console.log(`Confirm (${title}): ${message}`);
                const confirmed = confirm(`${title}: ${message}`); // Basic confirm for fallback
                callback(confirmed);
            };
        }
    }
    setupAlertModal(); // Call it to ensure alert functions are checked/available.
    // --- End Alert/Confirm Modal ---


    // Load users and populate table
    async function loadUsers() {
        try {
            const users = await adminApi.getUsers(); // Assumes adminApi.getUsers is defined
            if (!usersTableBody) {
                console.warn("Users table body not found on this page.");
                return;
            }
            usersTableBody.innerHTML = ''; // Clear existing users
            if (users.length === 0) {
                usersTableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4">No users found.</td></tr>`;
                return;
            }
            users.forEach(user => {
                const row = usersTableBody.insertRow();
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${user.id}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${user.username || user.email.split('@')[0]}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${user.email}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${user.role || 'User'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                            ${user.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-indigo-600 hover:text-indigo-900 edit-user-btn" data-id="${user.id}">Edit</button>
                        <button class="text-red-600 hover:text-red-900 delete-user-btn ml-4" data-id="${user.id}" data-isactive="${user.is_active}">
                            ${user.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                    </td>
                `;
            });
            attachUserActionListeners();
        } catch (error) {
            console.error("Failed to load users:", error);
            if (usersTableBody) {
                usersTableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-red-500">Error loading users.</td></tr>`;
            }
            window.showAlert("Could not load users. Please try again.", "Error");
        }
    }

    // Populate form for editing a user
    async function populateUserFormForEdit(userId) {
        try {
            const user = await adminApi.getUserById(userId); // Assumes adminApi.getUserById
            if (user && userForm && userModal) {
                editingUserId = userId;
                userModalTitle.textContent = `Edit User: ${user.username || user.email}`;
                document.getElementById('userEmail').value = user.email || '';
                document.getElementById('userRole').value = user.role || 'User';
                document.getElementById('userIsActive').checked = user.is_active !== undefined ? user.is_active : true;
                
                // Fields that might not be directly editable but shown for context
                const userInfoDiv = document.getElementById('userInfo');
                if (userInfoDiv) {
                    userInfoDiv.innerHTML = `
                        <p><strong>ID:</strong> ${user.id}</p>
                        <p><strong>Username:</strong> ${user.username || 'N/A'}</p>
                        <p><strong>Registered:</strong> ${user.date_registered ? new Date(user.date_registered).toLocaleDateString() : 'N/A'}</p>
                    `;
                }

                userModal.classList.remove('hidden');
            } else {
                window.showAlert("Could not find user details to edit.", "Error");
            }
        } catch (error) {
            console.error("Failed to fetch user for editing:", error);
            window.showAlert(`Error fetching user details: ${error.message || 'Unknown error.'}`, "Error");
        }
    }

    // Handle user form submission (Edit)
    if (userForm) {
        userForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (!editingUserId) return;

            const role = document.getElementById('userRole').value;
            const isActive = document.getElementById('userIsActive').checked;

            const userData = {
                role: role,
                is_active: isActive
                // Add other fields as necessary, e.g., if username or password can be changed by admin
            };

            try {
                await adminApi.updateUser(editingUserId, userData); // Assumes adminApi.updateUser
                window.showAlert("User updated successfully!", "Success");
                userModal.classList.add('hidden');
                userForm.reset();
                editingUserId = null;
                loadUsers(); // Refresh user list
            } catch (error) {
                console.error("Failed to update user:", error);
                window.showAlert(`Error updating user: ${error.message || 'Unknown error.'}`, "Error");
            }
        });
    }

    // Close modal listeners
    if (userModal && closeUserModalButton) {
        closeUserModalButton.addEventListener('click', () => userModal.classList.add('hidden'));
    }
    if (userModal && cancelUserModalButton) {
        cancelUserModalButton.addEventListener('click', () => userModal.classList.add('hidden'));
    }
    if (userModal) {
        userModal.addEventListener('click', (event) => {
            if (event.target === userModal) { // Clicked on backdrop
                userModal.classList.add('hidden');
            }
        });
    }


    // Attach event listeners for edit and delete/deactivate buttons
    function attachUserActionListeners() {
        document.querySelectorAll('.edit-user-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const userId = event.target.dataset.id;
                populateUserFormForEdit(userId);
            });
        });

        document.querySelectorAll('.delete-user-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const userId = event.target.dataset.id;
                const isActive = event.target.dataset.isactive === 'true';
                const actionText = isActive ? 'Deactivate' : 'Activate';
                
                window.showConfirm(`Are you sure you want to ${actionText.toLowerCase()} this user?`, `${actionText} User`, async (confirmed) => {
                    if (confirmed) {
                        try {
                            // For deactivation/activation, we typically update the user's status
                            // This might be the same updateUser endpoint or a dedicated one.
                            // Here, we assume updateUser can handle 'is_active' field.
                            await adminApi.updateUser(userId, { is_active: !isActive });
                            window.showAlert(`User ${actionText.toLowerCase()}d successfully!`, "Success");
                            loadUsers(); // Refresh user list
                        } catch (error) {
                            console.error(`Failed to ${actionText.toLowerCase()} user:`, error);
                            window.showAlert(`Error ${actionText.toLowerCase()}ing user: ${error.message || 'Unknown error.'}`, "Error");
                        }
                    }
                });
            });
        });
    }

    // Initial load
    if (usersTableBody) {
        loadUsers();
    }
});
