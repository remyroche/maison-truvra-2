// website/js/auth.js

// Ensure API_BASE_URL is defined (from config.js)
// Ensure makeApiRequest is defined (from api.js)
// Ensure translate, currentLanguage are defined (from i18n.js)
// Ensure showGlobalMessage is defined (from ui.js)

function getToken() {
    return localStorage.getItem('authToken');
}

function setToken(token) {
    localStorage.setItem('authToken', token);
}

function removeToken() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
}

function setUser(user) {
    localStorage.setItem('authUser', JSON.stringify(user));
}

function getUser() {
    const user = localStorage.getItem('authUser');
    return user ? JSON.parse(user) : null;
}

function isUserLoggedIn() {
    return !!getToken();
}

async function checkAuth() {
    const loadingDiv = document.getElementById('loading-account');
    const loginRegisterSection = document.getElementById('login-register-section');
    const b2cAccountView = document.getElementById('b2c-account-view');
    const b2bAccountView = document.getElementById('b2b-account-view');

    if (loadingDiv) loadingDiv.classList.remove('hidden');
    if (loginRegisterSection) loginRegisterSection.classList.add('hidden');
    if (b2cAccountView) b2cAccountView.classList.add('hidden');
    if (b2bAccountView) b2bAccountView.classList.add('hidden');

    const token = getToken();
    if (!token) {
        if (loadingDiv) loadingDiv.classList.add('hidden');
        if (loginRegisterSection) loginRegisterSection.classList.remove('hidden');
        updateLoginStatusInHeader(false); // Update header UI
        return null;
    }

    try {
        const response = await makeApiRequest('/api/check-auth', 'GET', null, true);
        if (response.isAuthenticated && response.user) {
            setUser(response.user);
            updateLoginStatusInHeader(true, response.user); // Update header UI
            if (loadingDiv) loadingDiv.classList.add('hidden');
            if (response.user.role === 'b2c') {
                if (b2cAccountView) {
                    b2cAccountView.classList.remove('hidden');
                    displayLoggedInB2CView(response.user);
                }
            } else if (response.user.role === 'b2b') {
                if (b2bAccountView) {
                    b2bAccountView.classList.remove('hidden');
                    displayLoggedInB2BView(response.user);
                }
            } else {
                 if (loginRegisterSection) loginRegisterSection.classList.remove('hidden'); // Fallback
            }
            return response.user;
        } else {
            throw new Error('Authentication check failed');
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        removeToken();
        if (loadingDiv) loadingDiv.classList.add('hidden');
        if (loginRegisterSection) loginRegisterSection.classList.remove('hidden');
        updateLoginStatusInHeader(false); // Update header UI
        return null;
    }
}


function displayLoggedInB2CView(user) {
    document.getElementById('b2c-user-name').textContent = user.name || user.email;
    
    // Display profile information
    document.getElementById('display-b2c-name').textContent = user.name || translate('account.notSet');
    document.getElementById('display-b2c-email').textContent = user.email || translate('account.notSet');
    document.getElementById('display-b2c-phone').textContent = user.phone || translate('account.notSet');
    document.getElementById('display-b2c-shipping-address').textContent = user.address_shipping || translate('account.notSet');
    document.getElementById('display-b2c-billing-address').textContent = user.address_billing || translate('account.notSet');

    // Populate edit form
    document.getElementById('edit-b2c-name').value = user.name || '';
    document.getElementById('edit-b2c-email').value = user.email || '';
    document.getElementById('edit-b2c-phone').value = user.phone || '';
    document.getElementById('edit-b2c-shipping-address').value = user.address_shipping || '';
    document.getElementById('edit-b2c-billing-address').value = user.address_billing || '';

    fetchB2COrders();
}

function displayLoggedInB2BView(user) {
    document.getElementById('b2b-contact-name').textContent = user.contact_name || user.email;
    document.getElementById('b2b-company-name').textContent = user.company_name || '';
    
    const statusEl = document.getElementById('b2b-account-status');
    if (user.is_approved && user.status === 'active') {
        statusEl.textContent = translate('account.b2bStatusApproved');
        statusEl.className = 'text-green-600 font-semibold';
    } else if (user.status === 'pending_approval') {
        statusEl.textContent = translate('account.b2bStatusPending');
        statusEl.className = 'text-yellow-600 font-semibold';
    } else if (user.status === 'suspended') {
        statusEl.textContent = translate('account.b2bStatusSuspended');
        statusEl.className = 'text-red-600 font-semibold';
    } else if (user.status === 'rejected') {
         statusEl.textContent = translate('account.b2bStatusRejected');
        statusEl.className = 'text-red-600 font-semibold';
    }


    // Display B2B profile information
    document.getElementById('display-b2b-company-name').textContent = user.company_name || translate('account.notSet');
    document.getElementById('display-b2b-siret').textContent = user.siret || translate('account.notSet');
    document.getElementById('display-b2b-vat').textContent = user.vat_number || translate('account.notSet');
    document.getElementById('display-b2b-contact-name').textContent = user.contact_name || translate('account.notSet');
    document.getElementById('display-b2b-email').textContent = user.email || translate('account.notSet');
    document.getElementById('display-b2b-phone').textContent = user.phone || translate('account.notSet');
    document.getElementById('display-b2b-billing-address').textContent = user.billing_address || translate('account.notSet');
    document.getElementById('display-b2b-shipping-address').textContent = user.shipping_address || translate('account.notSet');
    
    // Populate B2B edit form (only editable fields)
    document.getElementById('edit-b2b-contact-name').value = user.contact_name || '';
    document.getElementById('edit-b2b-phone').value = user.phone || '';
    document.getElementById('edit-b2b-shipping-address').value = user.shipping_address || '';


    fetchB2BInvoices();
}


async function fetchB2COrders() {
    const orderHistoryDiv = document.getElementById('b2c-order-history');
    if (!orderHistoryDiv) return;

    try {
        const orders = await makeApiRequest('/api/orders', 'GET', null, true); // Assuming this endpoint exists and returns user's orders
        if (orders && orders.length > 0) {
            orderHistoryDiv.innerHTML = orders.map(order => `
                <div class="p-3 border rounded-md bg-gray-50 hover:shadow-sm transition-shadow">
                    <div class="flex justify-between items-center">
                        <div>
                            <p class="font-semibold text-brand-primary">${translate('account.order')} #${order.id} <span class="text-xs px-2 py-0.5 rounded-full ${getOrderStatusClass(order.status)}">${translate(`orderStatus.${order.status}`)}</span></p>
                            <p class="text-sm text-gray-600">${translate('account.orderDate')}: ${new Date(order.created_at).toLocaleDateString(currentLanguage || 'fr-FR')}</p>
                            <p class="text-sm text-gray-600">${translate('account.orderTotal')}: ${formatPrice(order.total_amount, order.currency)}</p>
                        </div>
                        <button onclick="viewOrderDetail(${order.id})" class="text-sm bg-brand-accent text-brand-primary hover:opacity-90 font-semibold py-1 px-3 rounded-md transition duration-150" data-i18n="account.viewDetails">Voir détails</button>
                    </div>
                </div>
            `).join('');
        } else {
            orderHistoryDiv.innerHTML = `<p data-i18n="account.noOrders">${translate('account.noOrders')}</p>`;
        }
    } catch (error) {
        console.error('Error fetching B2C orders:', error);
        orderHistoryDiv.innerHTML = `<p class="text-red-500" data-i18n="account.errorLoadingOrders">${translate('account.errorLoadingOrders')}</p>`;
    }
}

function getOrderStatusClass(status) {
    switch (status) {
        case 'pending': return 'bg-yellow-200 text-yellow-800';
        case 'processing': return 'bg-blue-200 text-blue-800';
        case 'shipped': return 'bg-green-200 text-green-800';
        case 'delivered': return 'bg-green-300 text-green-900';
        case 'cancelled': return 'bg-red-200 text-red-800';
        case 'refunded': return 'bg-gray-200 text-gray-800';
        default: return 'bg-gray-100 text-gray-700';
    }
}


async function viewOrderDetail(orderId) {
    const modal = document.getElementById('order-detail-modal');
    const contentDiv = document.getElementById('order-detail-content');
    if (!modal || !contentDiv) return;

    contentDiv.innerHTML = `<p data-i18n="account.loadingOrderDetails">${translate('account.loadingOrderDetails')}...</p>`;
    modal.style.display = 'block';

    try {
        const order = await makeApiRequest(`/api/orders/${orderId}`, 'GET', null, true);
        if (order) {
            let itemsHtml = '<ul class="list-disc pl-5 space-y-1 mt-2">';
            order.items.forEach(item => {
                itemsHtml += `<li>${item.quantity} x ${item.name_fr || item.name_en} (${formatPrice(item.price_at_purchase, order.currency)})</li>`;
            });
            itemsHtml += '</ul>';

            contentDiv.innerHTML = `
                <p><strong>${translate('account.order')} #:</strong> ${order.id}</p>
                <p><strong>${translate('account.orderDate')}:</strong> ${new Date(order.created_at).toLocaleString(currentLanguage || 'fr-FR')}</p>
                <p><strong>${translate('account.orderStatus')}:</strong> <span class="px-2 py-0.5 rounded-full ${getOrderStatusClass(order.status)}">${translate(`orderStatus.${order.status}`)}</span></p>
                <p><strong>${translate('account.orderTotal')}:</strong> ${formatPrice(order.total_amount, order.currency)}</p>
                <div class="mt-3">
                    <h4 class="font-semibold text-md mb-1">${translate('account.shippingAddress')}:</h4>
                    <p class="whitespace-pre-line">${order.shipping_address || translate('account.notSet')}</p>
                </div>
                 <div class="mt-3">
                    <h4 class="font-semibold text-md mb-1">${translate('account.billingAddress')}:</h4>
                    <p class="whitespace-pre-line">${order.billing_address || translate('account.notSet')}</p>
                </div>
                <div class="mt-3">
                    <h4 class="font-semibold text-md mb-1">${translate('cart.items')}:</h4>
                    ${itemsHtml}
                </div>
            `;
        } else {
            contentDiv.innerHTML = `<p class="text-red-500" data-i18n="account.errorLoadingOrderDetails">${translate('account.errorLoadingOrderDetails')}</p>`;
        }
    } catch (error) {
        console.error('Error fetching order details:', error);
        contentDiv.innerHTML = `<p class="text-red-500">${translate('account.errorLoadingOrderDetails')}: ${error.message || 'Unknown error'}</p>`;
    }
}


async function fetchB2BInvoices() {
    const invoiceHistoryDiv = document.getElementById('b2b-invoice-history');
    if (!invoiceHistoryDiv) return;

    try {
        // Assuming an endpoint like /api/professional/invoices exists for B2B users
        const invoices = await makeApiRequest('/api/professional/invoices', 'GET', null, true); 
        if (invoices && invoices.length > 0) {
            invoiceHistoryDiv.innerHTML = invoices.map(invoice => `
                <div class="p-3 border rounded-md bg-gray-50 hover:shadow-sm transition-shadow">
                    <div class="flex justify-between items-center">
                        <div>
                            <p class="font-semibold text-brand-primary">${translate('account.invoice')} #${invoice.invoice_number}</p>
                            <p class="text-sm text-gray-600">${translate('account.invoiceDate')}: ${new Date(invoice.invoice_date).toLocaleDateString(currentLanguage || 'fr-FR')}</p>
                            <p class="text-sm text-gray-600">${translate('account.invoiceTotal')}: ${formatPrice(invoice.total_amount, invoice.currency)}</p>
                             <p class="text-sm text-gray-600">${translate('account.invoiceStatus')}: <span class="font-medium ${invoice.status === 'paid' ? 'text-green-600' : 'text-red-600'}">${translate(`invoiceStatus.${invoice.status}`)}</span></p>
                        </div>
                        <a href="${API_BASE_URL}/api/invoices/${invoice.id}/pdf" target="_blank" class="text-sm bg-brand-accent text-brand-primary hover:opacity-90 font-semibold py-1 px-3 rounded-md transition duration-150" data-i18n="account.downloadInvoice">Télécharger PDF</a>
                    </div>
                </div>
            `).join('');
        } else {
            invoiceHistoryDiv.innerHTML = `<p data-i18n="account.noInvoices">${translate('account.noInvoices')}</p>`;
        }
    } catch (error) {
        console.error('Error fetching B2B invoices:', error);
        invoiceHistoryDiv.innerHTML = `<p class="text-red-500" data-i18n="account.errorLoadingInvoices">${translate('account.errorLoadingInvoices')}</p>`;
    }
}


async function initAccountPage() {
    const user = await checkAuth(); // This will also display the correct view

    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const logoutButton = document.getElementById('logout-button');
    const b2bLogoutButton = document.getElementById('b2b-logout-button');
    const authMessageDiv = document.getElementById('auth-message');

    // Edit B2C Profile
    const showEditProfileFormBtn = document.getElementById('show-edit-profile-form-btn');
    const editProfileFormContainer = document.getElementById('b2c-edit-profile-form-container');
    const editProfileForm = document.getElementById('b2c-edit-profile-form');
    const cancelEditProfileBtn = document.getElementById('cancel-edit-profile-btn');
    const editProfileMessageDiv = document.getElementById('edit-profile-message');

    // Change B2C Password
    const showChangePasswordFormBtn = document.getElementById('show-change-password-form-btn');
    const changePasswordFormContainer = document.getElementById('b2c-change-password-form-container');
    const changePasswordForm = document.getElementById('b2c-change-password-form');
    const cancelChangePasswordBtn = document.getElementById('cancel-change-password-btn');
    const changePasswordMessageDiv = document.getElementById('change-password-message');

    // Edit B2B Profile
    const showEditB2BProfileFormBtn = document.getElementById('show-edit-b2b-profile-form-btn');
    const editB2BProfileFormContainer = document.getElementById('b2b-edit-profile-form-container');
    const editB2BProfileForm = document.getElementById('b2b-edit-profile-form');
    const cancelEditB2BProfileBtn = document.getElementById('cancel-edit-b2b-profile-btn');
    const editB2BProfileMessageDiv = document.getElementById('edit-b2b-profile-message');

    // Change B2B Password
    const showB2BChangePasswordFormBtn = document.getElementById('show-b2b-change-password-form-btn');
    const b2bChangePasswordFormContainer = document.getElementById('b2b-change-password-form-container');
    const b2bChangePasswordForm = document.getElementById('b2b-change-password-form');
    const cancelB2BChangePasswordBtn = document.getElementById('cancel-b2b-change-password-btn');
    const b2bChangePasswordMessageDiv = document.getElementById('b2b-change-password-message');


    // Order Detail Modal
    const closeModalBtn = document.getElementById('close-order-detail-modal');
    const orderDetailModal = document.getElementById('order-detail-modal');

    if (closeModalBtn && orderDetailModal) {
        closeModalBtn.onclick = function() {
            orderDetailModal.style.display = "none";
        }
        window.onclick = function(event) {
            if (event.target == orderDetailModal) {
                orderDetailModal.style.display = "none";
            }
        }
    }


    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            authMessageDiv.textContent = '';
            const email = loginForm.email.value;
            const password = loginForm.password.value;
            const role = loginForm.role.value; // Get role from select
            try {
                const data = await makeApiRequest('/api/login', 'POST', { email, password, role });
                setToken(data.token);
                setUser(data.user);
                authMessageDiv.textContent = translate('account.loginSuccess');
                authMessageDiv.className = 'text-green-600';
                await checkAuth(); // Re-check auth to display correct view
                // Optionally redirect or update UI further
                 window.location.reload(); // Simple reload to refresh everything
            } catch (error) {
                authMessageDiv.textContent = error.message || translate('account.loginError');
                authMessageDiv.className = 'text-red-600';
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            authMessageDiv.textContent = '';
            const name = registerForm.name.value;
            const email = registerForm.email.value;
            const password = registerForm.password.value;
            // For B2C registration, role is implicitly 'b2c'
            try {
                await makeApiRequest('/api/register', 'POST', { name, email, password, role: 'b2c' });
                authMessageDiv.textContent = translate('account.registerSuccess');
                authMessageDiv.className = 'text-green-600';
                // Optionally auto-login or prompt to login
                loginForm.email.value = email; // Pre-fill login form
            } catch (error) {
                authMessageDiv.textContent = error.message || translate('account.registerError');
                authMessageDiv.className = 'text-red-600';
            }
        });
    }

    function handleLogout() {
        removeToken();
        authMessageDiv.textContent = translate('account.logoutSuccess');
        authMessageDiv.className = 'text-green-600';
        checkAuth(); // Re-check auth to display login/register view
        window.location.reload(); // Simple reload
    }

    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }
    if (b2bLogoutButton) {
        b2bLogoutButton.addEventListener('click', handleLogout);
    }

    // B2C Profile Edit Logic
    if (showEditProfileFormBtn && editProfileFormContainer && cancelEditProfileBtn) {
        showEditProfileFormBtn.addEventListener('click', () => {
            editProfileFormContainer.classList.remove('hidden');
            showEditProfileFormBtn.classList.add('hidden');
            // Hide change password form if open
            if (changePasswordFormContainer) changePasswordFormContainer.classList.add('hidden');
            if (showChangePasswordFormBtn) showChangePasswordFormBtn.classList.remove('hidden');

            // Re-populate form with latest data in case it was fetched again
            const currentUser = getUser();
            if (currentUser && currentUser.role === 'b2c') {
                document.getElementById('edit-b2c-name').value = currentUser.name || '';
                document.getElementById('edit-b2c-email').value = currentUser.email || '';
                document.getElementById('edit-b2c-phone').value = currentUser.phone || '';
                document.getElementById('edit-b2c-shipping-address').value = currentUser.address_shipping || '';
                document.getElementById('edit-b2c-billing-address').value = currentUser.address_billing || '';
            }
        });
        cancelEditProfileBtn.addEventListener('click', () => {
            editProfileFormContainer.classList.add('hidden');
            showEditProfileFormBtn.classList.remove('hidden');
            editProfileMessageDiv.textContent = '';
        });
    }

    if (editProfileForm) {
        editProfileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            editProfileMessageDiv.textContent = '';
            const updatedData = {
                name: editProfileForm.name.value,
                email: editProfileForm.email.value,
                phone: editProfileForm.phone.value,
                address_shipping: editProfileForm.address_shipping.value,
                address_billing: editProfileForm.address_billing.value,
            };
            try {
                const response = await makeApiRequest('/api/user/profile', 'PUT', updatedData, true);
                setUser(response.user); // Update local storage with new user data
                editProfileMessageDiv.textContent = translate('account.profileUpdateSuccess');
                editProfileMessageDiv.className = 'text-green-600';
                // Update displayed info and hide form
                displayLoggedInB2CView(response.user); // Refresh displayed data
                editProfileFormContainer.classList.add('hidden');
                showEditProfileFormBtn.classList.remove('hidden');
            } catch (error) {
                editProfileMessageDiv.textContent = error.message || translate('account.profileUpdateError');
                editProfileMessageDiv.className = 'text-red-600';
            }
        });
    }

    // B2C Change Password Logic
    if (showChangePasswordFormBtn && changePasswordFormContainer && cancelChangePasswordBtn) {
        showChangePasswordFormBtn.addEventListener('click', () => {
            changePasswordFormContainer.classList.remove('hidden');
            showChangePasswordFormBtn.classList.add('hidden');
            // Hide edit profile form if open
            if (editProfileFormContainer) editProfileFormContainer.classList.add('hidden');
            if (showEditProfileFormBtn) showEditProfileFormBtn.classList.remove('hidden');
        });
        cancelChangePasswordBtn.addEventListener('click', () => {
            changePasswordFormContainer.classList.add('hidden');
            showChangePasswordFormBtn.classList.remove('hidden');
            changePasswordMessageDiv.textContent = '';
            if(changePasswordForm) changePasswordForm.reset();
        });
    }

    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            changePasswordMessageDiv.textContent = '';
            const current_password = changePasswordForm.current_password.value;
            const new_password = changePasswordForm.new_password.value;
            const confirm_new_password = changePasswordForm.confirm_new_password.value;

            if (new_password !== confirm_new_password) {
                changePasswordMessageDiv.textContent = translate('account.passwordsDoNotMatch');
                changePasswordMessageDiv.className = 'text-red-600';
                return;
            }

            try {
                await makeApiRequest('/api/user/change-password', 'POST', { current_password, new_password }, true);
                changePasswordMessageDiv.textContent = translate('account.passwordUpdateSuccess');
                changePasswordMessageDiv.className = 'text-green-600';
                changePasswordForm.reset();
                changePasswordFormContainer.classList.add('hidden');
                showChangePasswordFormBtn.classList.remove('hidden');
            } catch (error) {
                changePasswordMessageDiv.textContent = error.message || translate('account.passwordUpdateError');
                changePasswordMessageDiv.className = 'text-red-600';
            }
        });
    }


    // B2B Profile Edit Logic
    if (showEditB2BProfileFormBtn && editB2BProfileFormContainer && cancelEditB2BProfileBtn) {
        showEditB2BProfileFormBtn.addEventListener('click', () => {
            editB2BProfileFormContainer.classList.remove('hidden');
            showEditB2BProfileFormBtn.classList.add('hidden');
             // Hide change password form if open
            if (b2bChangePasswordFormContainer) b2bChangePasswordFormContainer.classList.add('hidden');
            if (showB2BChangePasswordFormBtn) showB2BChangePasswordFormBtn.classList.remove('hidden');

            const currentUser = getUser();
            if (currentUser && currentUser.role === 'b2b') {
                document.getElementById('edit-b2b-contact-name').value = currentUser.contact_name || '';
                document.getElementById('edit-b2b-phone').value = currentUser.phone || '';
                document.getElementById('edit-b2b-shipping-address').value = currentUser.shipping_address || '';
            }
        });
        cancelEditB2BProfileBtn.addEventListener('click', () => {
            editB2BProfileFormContainer.classList.add('hidden');
            showEditB2BProfileFormBtn.classList.remove('hidden');
            editB2BProfileMessageDiv.textContent = '';
        });
    }

    if (editB2BProfileForm) {
        editB2BProfileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            editB2BProfileMessageDiv.textContent = '';
            const updatedData = {
                contact_name: editB2BProfileForm.contact_name.value,
                phone: editB2BProfileForm.phone.value,
                shipping_address: editB2BProfileForm.shipping_address.value,
            };
            try {
                const response = await makeApiRequest('/api/user/profile', 'PUT', updatedData, true);
                setUser(response.user);
                editB2BProfileMessageDiv.textContent = translate('account.profileUpdateSuccess');
                editB2BProfileMessageDiv.className = 'text-green-600';
                displayLoggedInB2BView(response.user);
                editB2BProfileFormContainer.classList.add('hidden');
                showEditB2BProfileFormBtn.classList.remove('hidden');
            } catch (error) {
                editB2BProfileMessageDiv.textContent = error.message || translate('account.profileUpdateError');
                editB2BProfileMessageDiv.className = 'text-red-600';
            }
        });
    }
    
    // B2B Change Password Logic
    if (showB2BChangePasswordFormBtn && b2bChangePasswordFormContainer && cancelB2BChangePasswordBtn) {
        showB2BChangePasswordFormBtn.addEventListener('click', () => {
            b2bChangePasswordFormContainer.classList.remove('hidden');
            showB2BChangePasswordFormBtn.classList.add('hidden');
            // Hide edit profile form if open
            if (editB2BProfileFormContainer) editB2BProfileFormContainer.classList.add('hidden');
            if (showEditB2BProfileFormBtn) showEditB2BProfileFormBtn.classList.remove('hidden');
        });
        cancelB2BChangePasswordBtn.addEventListener('click', () => {
            b2bChangePasswordFormContainer.classList.add('hidden');
            showB2BChangePasswordFormBtn.classList.remove('hidden');
            b2bChangePasswordMessageDiv.textContent = '';
            if(b2bChangePasswordForm) b2bChangePasswordForm.reset();
        });
    }

    if (b2bChangePasswordForm) {
        b2bChangePasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            b2bChangePasswordMessageDiv.textContent = '';
            const current_password = b2bChangePasswordForm.current_password.value;
            const new_password = b2bChangePasswordForm.new_password.value;
            const confirm_new_password = b2bChangePasswordForm.confirm_new_password.value;

            if (new_password !== confirm_new_password) {
                b2bChangePasswordMessageDiv.textContent = translate('account.passwordsDoNotMatch');
                b2bChangePasswordMessageDiv.className = 'text-red-600';
                return;
            }

            try {
                await makeApiRequest('/api/user/change-password', 'POST', { current_password, new_password }, true);
                b2bChangePasswordMessageDiv.textContent = translate('account.passwordUpdateSuccess');
                b2bChangeMessageDiv.className = 'text-green-600';
                b2bChangePasswordForm.reset();
                b2bChangePasswordFormContainer.classList.add('hidden');
                showB2BChangePasswordFormBtn.classList.remove('hidden');
            } catch (error) {
                b2bChangePasswordMessageDiv.textContent = error.message || translate('account.passwordUpdateError');
                b2bChangePasswordMessageDiv.className = 'text-red-600';
            }
        });
    }

}

// Expose functions to global scope if they are called from HTML attributes like onclick
window.viewOrderDetail = viewOrderDetail;
window.initAccountPage = initAccountPage; // Make sure it's callable after DOMContentLoaded

// Update header based on login status (called from checkAuth and logout)
function updateLoginStatusInHeader(isLoggedIn, user = null) {
    const accountLink = document.querySelector('#header-placeholder a[href="compte.html"]');
    const logoutLink = document.getElementById('header-logout-link'); // Assuming an ID for a dedicated logout link/button in header
    const loginLink = document.getElementById('header-login-link'); // Assuming an ID for a dedicated login link in header
    const userNameDisplay = document.getElementById('header-user-name'); // Assuming an element to display user name

    if (accountLink) {
        // The "Mon Compte" link is always visible, its behavior changes based on login status on compte.html itself.
    }

    // This is a conceptual update; actual header structure might vary.
    // You might need to adjust selectors based on your header.html
    if (isLoggedIn && user) {
        if (userNameDisplay) {
            userNameDisplay.textContent = user.name || user.contact_name || user.email;
            userNameDisplay.classList.remove('hidden');
        }
        if (loginLink) loginLink.classList.add('hidden');
        if (logoutLink) {
             logoutLink.classList.remove('hidden');
             logoutLink.onclick = (e) => { // Add click listener if it's a dynamic element
                 e.preventDefault();
                 removeToken();
                 window.location.href = 'compte.html'; // or reload
             };
        }
    } else {
        if (userNameDisplay) {
            userNameDisplay.textContent = '';
            userNameDisplay.classList.add('hidden');
        }
        if (loginLink) loginLink.classList.remove('hidden');
        if (logoutLink) logoutLink.classList.add('hidden');
    }
}
