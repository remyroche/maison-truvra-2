// website/js/auth.js

// Ensure API_BASE_URL is defined (from config.js)
// Ensure makeApiRequest, ApiError are defined (from api.js)
// Ensure t, getCurrentLang are defined (from i18n.js)
// Ensure showGlobalMessage, showButtonLoading, hideButtonLoading are defined (from ui.js)

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
    try {
        return user ? JSON.parse(user) : null;
    } catch (e) {
        console.error("Error parsing user from localStorage", e);
        removeToken(); // Clear corrupted data
        return null;
    }
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
        updateLoginStatusInHeader(false);
        return null;
    }

    try {
        // Endpoint should be /auth/check-auth or similar, ensure it's correct
        const response = await makeApiRequest('/auth/check-auth', 'GET', null, true); 
        if (response.isAuthenticated && response.user) {
            setUser(response.user);
            updateLoginStatusInHeader(true, response.user);
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
            // This case should ideally be caught by makeApiRequest if response.ok is false
            throw new Error(t('auth_check_failed_unexpected_response'));
        }
    } catch (error) {
        console.error('Auth check failed:', error.message);
        removeToken(); // Crucial to remove invalid token
        if (loadingDiv) loadingDiv.classList.add('hidden');
        if (loginRegisterSection) loginRegisterSection.classList.remove('hidden');
        updateLoginStatusInHeader(false);
        // No global message here, as UI is already updated to show login form.
        return null;
    }
}


function displayLoggedInB2CView(user) {
    const userNameEl = document.getElementById('b2c-user-name');
    if(userNameEl) userNameEl.textContent = user.name || user.email;
    
    const fields = {
        'display-b2c-name': user.name,
        'display-b2c-email': user.email,
        'display-b2c-phone': user.phone,
        'display-b2c-shipping-address': user.address_shipping,
        'display-b2c-billing-address': user.address_billing,
        'edit-b2c-name': user.name,
        'edit-b2c-email': user.email, // Usually not editable or requires verification
        'edit-b2c-phone': user.phone,
        'edit-b2c-shipping-address': user.address_shipping,
        'edit-b2c-billing-address': user.address_billing,
    };

    for (const id in fields) {
        const element = document.getElementById(id);
        if (element) {
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.value = fields[id] || '';
                 if (id === 'edit-b2c-email') element.readOnly = true; // Make email readonly
            } else {
                element.textContent = fields[id] || t('account.notSet');
            }
        }
    }
    fetchB2COrders();
}

function displayLoggedInB2BView(user) {
    const contactNameEl = document.getElementById('b2b-contact-name');
    const companyNameEl = document.getElementById('b2b-company-name');
    if(contactNameEl) contactNameEl.textContent = user.contact_name || user.email;
    if(companyNameEl) companyNameEl.textContent = user.company_name || '';
    
    const statusEl = document.getElementById('b2b-account-status');
    if (statusEl) {
        if (user.is_approved && user.status === 'active') {
            statusEl.textContent = t('account.b2bStatusApproved');
            statusEl.className = 'text-green-600 font-semibold';
        } else if (user.status === 'pending_approval') {
            statusEl.textContent = t('account.b2bStatusPending');
            statusEl.className = 'text-yellow-600 font-semibold';
        } else if (user.status === 'suspended') {
            statusEl.textContent = t('account.b2bStatusSuspended');
            statusEl.className = 'text-red-600 font-semibold';
        } else if (user.status === 'rejected') {
            statusEl.textContent = t('account.b2bStatusRejected');
            statusEl.className = 'text-red-600 font-semibold';
        } else {
            statusEl.textContent = user.status || t('account.statusUnknown');
            statusEl.className = 'text-gray-600 font-semibold';
        }
    }

    const fields = {
        'display-b2b-company-name': user.company_name,
        'display-b2b-siret': user.siret,
        'display-b2b-vat': user.vat_number,
        'display-b2b-contact-name': user.contact_name,
        'display-b2b-email': user.email,
        'display-b2b-phone': user.phone,
        'display-b2b-billing-address': user.billing_address,
        'display-b2b-shipping-address': user.shipping_address,
        'edit-b2b-contact-name': user.contact_name,
        // 'edit-b2b-email': user.email, // B2B email likely not editable by user directly
        'edit-b2b-phone': user.phone,
        'edit-b2b-shipping-address': user.shipping_address,
    };
    for (const id in fields) {
        const element = document.getElementById(id);
        if (element) {
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.value = fields[id] || '';
            } else {
                element.textContent = fields[id] || t('account.notSet');
            }
        }
    }
    fetchB2BInvoices();
}


async function fetchB2COrders() {
    const orderHistoryDiv = document.getElementById('b2c-order-history');
    if (!orderHistoryDiv) return;
    orderHistoryDiv.innerHTML = `<p>${t('account.loadingOrders')}...</p>`; // Loading state

    try {
        const response = await makeApiRequest('/orders', 'GET', null, true); // API endpoint for user's orders
        const orders = response.orders || response; // Adjust based on actual API response structure

        if (orders && Array.isArray(orders) && orders.length > 0) {
            orderHistoryDiv.innerHTML = orders.map(order => `
                <div class="p-3 border rounded-md bg-gray-50 hover:shadow-sm transition-shadow mb-2">
                    <div class="flex justify-between items-center">
                        <div>
                            <p class="font-semibold text-brand-primary">${t('account.order')} #${order.id} <span class="text-xs px-2 py-0.5 rounded-full ${getOrderStatusClass(order.status)}">${t(`orderStatus.${order.status}`)}</span></p>
                            <p class="text-sm text-gray-600">${t('account.orderDate')}: ${new Date(order.created_at).toLocaleDateString(getCurrentLang() || 'fr-FR')}</p>
                            <p class="text-sm text-gray-600">${t('account.orderTotal')}: ${formatPrice(order.total_amount, order.currency)}</p>
                        </div>
                        <button onclick="viewOrderDetail(${order.id})" class="text-sm bg-brand-accent text-brand-primary hover:opacity-90 font-semibold py-1 px-3 rounded-md transition duration-150" data-i18n="account.viewDetails">${t('account.viewDetails')}</button>
                    </div>
                </div>
            `).join('');
        } else {
            orderHistoryDiv.innerHTML = `<p data-i18n="account.noOrders">${t('account.noOrders')}</p>`;
        }
    } catch (error) {
        console.error('Error fetching B2C orders:', error.message);
        orderHistoryDiv.innerHTML = `<p class="text-red-500" data-i18n="account.errorLoadingOrders">${t('account.errorLoadingOrders')}: ${error.message}</p>`;
    }
}


async function viewOrderDetail(orderId) {
    const modal = document.getElementById('order-detail-modal');
    const contentDiv = document.getElementById('order-detail-content');
    if (!modal || !contentDiv) return;

    contentDiv.innerHTML = `<p data-i18n="account.loadingOrderDetails">${t('account.loadingOrderDetails')}...</p>`;
    openModal('order-detail-modal'); // Use openModal from ui.js

    try {
        const order = await makeApiRequest(`/orders/${orderId}`, 'GET', null, true);
        if (order) {
            let itemsHtml = '<ul class="list-disc pl-5 space-y-1 mt-2">';
            (order.items || []).forEach(item => { // Ensure order.items is an array
                itemsHtml += `<li>${item.quantity} x ${item.name_fr || item.name_en || item.name} (${formatPrice(item.price_at_purchase, order.currency)})</li>`;
            });
            itemsHtml += '</ul>';

            contentDiv.innerHTML = `
                <p><strong>${t('account.order')} #:</strong> ${order.id}</p>
                <p><strong>${t('account.orderDate')}:</strong> ${new Date(order.created_at).toLocaleString(getCurrentLang() || 'fr-FR')}</p>
                <p><strong>${t('account.orderStatus')}:</strong> <span class="px-2 py-0.5 rounded-full ${getOrderStatusClass(order.status)}">${t(`orderStatus.${order.status}`)}</span></p>
                <p><strong>${t('account.orderTotal')}:</strong> ${formatPrice(order.total_amount, order.currency)}</p>
                <div class="mt-3">
                    <h4 class="font-semibold text-md mb-1">${t('account.shippingAddress')}:</h4>
                    <p class="whitespace-pre-line">${order.shipping_address || t('account.notSet')}</p>
                </div>
                 <div class="mt-3">
                    <h4 class="font-semibold text-md mb-1">${t('account.billingAddress')}:</h4>
                    <p class="whitespace-pre-line">${order.billing_address || t('account.notSet')}</p>
                </div>
                <div class="mt-3">
                    <h4 class="font-semibold text-md mb-1">${t('cart.items')}:</h4>
                    ${itemsHtml}
                </div>
            `;
        } else {
            contentDiv.innerHTML = `<p class="text-red-500" data-i18n="account.errorLoadingOrderDetails">${t('account.errorLoadingOrderDetails')}</p>`;
        }
    } catch (error) {
        console.error('Error fetching order details:', error.message);
        contentDiv.innerHTML = `<p class="text-red-500">${t('account.errorLoadingOrderDetails')}: ${error.message || t('error_unknown')}</p>`;
    }
}


async function fetchB2BInvoices() {
    const invoiceHistoryDiv = document.getElementById('b2b-invoice-history');
    if (!invoiceHistoryDiv) return;
    invoiceHistoryDiv.innerHTML = `<p>${t('account.loadingInvoices')}...</p>`; // Loading state

    try {
        const response = await makeApiRequest('/professional/invoices', 'GET', null, true); 
        const invoices = response.invoices || response; // Adjust based on actual API response structure

        if (invoices && Array.isArray(invoices) && invoices.length > 0) {
            invoiceHistoryDiv.innerHTML = invoices.map(invoice => `
                <div class="p-3 border rounded-md bg-gray-50 hover:shadow-sm transition-shadow mb-2">
                    <div class="flex justify-between items-center">
                        <div>
                            <p class="font-semibold text-brand-primary">${t('account.invoice')} #${invoice.invoice_number}</p>
                            <p class="text-sm text-gray-600">${t('account.invoiceDate')}: ${new Date(invoice.invoice_date).toLocaleDateString(getCurrentLang() || 'fr-FR')}</p>
                            <p class="text-sm text-gray-600">${t('account.invoiceTotal')}: ${formatPrice(invoice.total_amount, invoice.currency)}</p>
                             <p class="text-sm text-gray-600">${t('account.invoiceStatus')}: <span class="font-medium ${invoice.status === 'paid' ? 'text-green-600' : 'text-red-600'}">${t(`invoiceStatus.${invoice.status}`)}</span></p>
                        </div>
                        <a href="${API_BASE_URL}/invoices/${invoice.id}/pdf" target="_blank" class="text-sm bg-brand-accent text-brand-primary hover:opacity-90 font-semibold py-1 px-3 rounded-md transition duration-150" data-i18n="account.downloadInvoice">${t('account.downloadInvoice')}</a>
                    </div>
                </div>
            `).join('');
        } else {
            invoiceHistoryDiv.innerHTML = `<p data-i18n="account.noInvoices">${t('account.noInvoices')}</p>`;
        }
    } catch (error) {
        console.error('Error fetching B2B invoices:', error.message);
        invoiceHistoryDiv.innerHTML = `<p class="text-red-500" data-i18n="account.errorLoadingInvoices">${t('account.errorLoadingInvoices')}: ${error.message}</p>`;
    }
}


async function initAccountPage() {
    await checkAuth(); // This will also display the correct view

    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const logoutButton = document.getElementById('logout-button');
    const b2bLogoutButton = document.getElementById('b2b-logout-button');
    
    // Message divs for specific forms (can be targeted by showGlobalMessage with targetElementId)
    // const authMessageDiv = document.getElementById('auth-message'); // Used as target for login/register

    // Edit B2C Profile
    const showEditProfileFormBtn = document.getElementById('show-edit-profile-form-btn');
    const editProfileFormContainer = document.getElementById('b2c-edit-profile-form-container');
    const editProfileForm = document.getElementById('b2c-edit-profile-form');
    const cancelEditProfileBtn = document.getElementById('cancel-edit-profile-btn');
    // const editProfileMessageDiv = document.getElementById('edit-profile-message'); // Used as target

    // Change B2C Password
    const showChangePasswordFormBtn = document.getElementById('show-change-password-form-btn');
    const changePasswordFormContainer = document.getElementById('b2c-change-password-form-container');
    const changePasswordForm = document.getElementById('b2c-change-password-form');
    const cancelChangePasswordBtn = document.getElementById('cancel-change-password-btn');
    // const changePasswordMessageDiv = document.getElementById('change-password-message'); // Used as target

    // Edit B2B Profile
    const showEditB2BProfileFormBtn = document.getElementById('show-edit-b2b-profile-form-btn');
    const editB2BProfileFormContainer = document.getElementById('b2b-edit-profile-form-container');
    const editB2BProfileForm = document.getElementById('b2b-edit-profile-form');
    const cancelEditB2BProfileBtn = document.getElementById('cancel-edit-b2b-profile-btn');
    // const editB2BProfileMessageDiv = document.getElementById('edit-b2b-profile-message'); // Used as target

    // Change B2B Password
    const showB2BChangePasswordFormBtn = document.getElementById('show-b2b-change-password-form-btn');
    const b2bChangePasswordFormContainer = document.getElementById('b2b-change-password-form-container');
    const b2bChangePasswordForm = document.getElementById('b2b-change-password-form');
    const cancelB2BChangePasswordBtn = document.getElementById('cancel-b2b-change-password-btn');
    // const b2bChangePasswordMessageDiv = document.getElementById('b2b-change-password-message'); // Used as target

    // Order Detail Modal
    const closeModalBtn = document.getElementById('close-order-detail-modal');
    if (closeModalBtn) {
        closeModalBtn.onclick = function() {
            closeModal('order-detail-modal');
        }
        // Close modal on outside click
        window.onclick = function(event) {
            const orderDetailModal = document.getElementById('order-detail-modal');
            if (event.target == orderDetailModal) {
                closeModal('order-detail-modal');
            }
        }
    }


    if (loginForm) {
        const submitButton = loginForm.querySelector('button[type="submit"]');
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (submitButton) showButtonLoading(submitButton, t('logging_in'));
            
            const email = loginForm.email.value;
            const password = loginForm.password.value;
            const role = loginForm.role.value; 
            try {
                // API endpoint for login should be /auth/login or similar
                const data = await makeApiRequest('/auth/login', 'POST', { email, password, role });
                setToken(data.token);
                setUser(data.user);
                showGlobalMessage({ message: t('account.loginSuccess'), type: 'success', targetElementId: 'auth-message' });
                await checkAuth(); 
                window.location.reload(); 
            } catch (error) {
                showGlobalMessage({ message: error.message || t('account.loginError'), type: 'error', targetElementId: 'auth-message' });
            } finally {
                if (submitButton) hideButtonLoading(submitButton);
            }
        });
    }

    if (registerForm) {
        const submitButton = registerForm.querySelector('button[type="submit"]');
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (submitButton) showButtonLoading(submitButton, t('registering'));
            
            const name = registerForm.name.value;
            const email = registerForm.email.value;
            const password = registerForm.password.value;
            try {
                 // API endpoint for register should be /auth/register or similar
                await makeApiRequest('/auth/register', 'POST', { name, email, password, role: 'b2c' });
                showGlobalMessage({ message: t('account.registerSuccess'), type: 'success', targetElementId: 'auth-message' });
                if(loginForm) loginForm.email.value = email; // Pre-fill login form
                registerForm.reset();
            } catch (error) {
                 showGlobalMessage({ message: error.message || t('account.registerError'), type: 'error', targetElementId: 'auth-message' });
            } finally {
                if (submitButton) hideButtonLoading(submitButton);
            }
        });
    }

    function handleLogout() {
        removeToken();
        // No need for authMessageDiv here, checkAuth will refresh the UI.
        // showGlobalMessage({ message: t('account.logoutSuccess'), type: 'success' }); // Optional global toast
        checkAuth(); 
        window.location.reload(); 
    }

    if (logoutButton) logoutButton.addEventListener('click', handleLogout);
    if (b2bLogoutButton) b2bLogoutButton.addEventListener('click', handleLogout);

    // B2C Profile Edit Logic
    if (showEditProfileFormBtn && editProfileFormContainer && cancelEditProfileBtn) {
        showEditProfileFormBtn.addEventListener('click', () => {
            editProfileFormContainer.classList.remove('hidden');
            showEditProfileFormBtn.classList.add('hidden');
            if (changePasswordFormContainer) changePasswordFormContainer.classList.add('hidden');
            if (showChangePasswordFormBtn) showChangePasswordFormBtn.classList.remove('hidden');
            const currentUser = getUser();
            if (currentUser && currentUser.role === 'b2c') displayLoggedInB2CView(currentUser); // Re-populate
        });
        cancelEditProfileBtn.addEventListener('click', () => {
            editProfileFormContainer.classList.add('hidden');
            showEditProfileFormBtn.classList.remove('hidden');
            const msgDiv = document.getElementById('edit-profile-message');
            if(msgDiv) msgDiv.textContent = '';
        });
    }

    if (editProfileForm) {
        const submitButton = editProfileForm.querySelector('button[type="submit"]');
        editProfileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (submitButton) showButtonLoading(submitButton, t('saving_changes'));
            const updatedData = {
                name: editProfileForm.name.value,
                // email: editProfileForm.email.value, // Email usually not directly updatable this way
                phone: editProfileForm.phone.value,
                address_shipping: editProfileForm.address_shipping.value,
                address_billing: editProfileForm.address_billing.value,
            };
            try {
                // Endpoint should be /user/profile or similar
                const response = await makeApiRequest('/user/profile', 'PUT', updatedData, true);
                setUser(response.user); 
                showGlobalMessage({ message: t('account.profileUpdateSuccess'), type: 'success', targetElementId: 'edit-profile-message' });
                displayLoggedInB2CView(response.user); 
                if(editProfileFormContainer) editProfileFormContainer.classList.add('hidden');
                if(showEditProfileFormBtn) showEditProfileFormBtn.classList.remove('hidden');
            } catch (error) {
                showGlobalMessage({ message: error.message || t('account.profileUpdateError'), type: 'error', targetElementId: 'edit-profile-message' });
            } finally {
                if (submitButton) hideButtonLoading(submitButton);
            }
        });
    }

    // B2C Change Password Logic
    if (showChangePasswordFormBtn && changePasswordFormContainer && cancelChangePasswordBtn) {
        showChangePasswordFormBtn.addEventListener('click', () => {
            changePasswordFormContainer.classList.remove('hidden');
            showChangePasswordFormBtn.classList.add('hidden');
            if (editProfileFormContainer) editProfileFormContainer.classList.add('hidden');
            if (showEditProfileFormBtn) showEditProfileFormBtn.classList.remove('hidden');
        });
        cancelChangePasswordBtn.addEventListener('click', () => {
            changePasswordFormContainer.classList.add('hidden');
            showChangePasswordFormBtn.classList.remove('hidden');
            const msgDiv = document.getElementById('change-password-message');
            if(msgDiv) msgDiv.textContent = '';
            if(changePasswordForm) changePasswordForm.reset();
        });
    }

    if (changePasswordForm) {
        const submitButton = changePasswordForm.querySelector('button[type="submit"]');
        changePasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const current_password = changePasswordForm.current_password.value;
            const new_password = changePasswordForm.new_password.value;
            const confirm_new_password = changePasswordForm.confirm_new_password.value;

            if (new_password !== confirm_new_password) {
                showGlobalMessage({ message: t('account.passwordsDoNotMatch'), type: 'error', targetElementId: 'change-password-message' });
                return;
            }
            if (submitButton) showButtonLoading(submitButton, t('updating_password'));
            try {
                 // Endpoint should be /user/change-password or similar
                await makeApiRequest('/user/change-password', 'POST', { current_password, new_password }, true);
                showGlobalMessage({ message: t('account.passwordUpdateSuccess'), type: 'success', targetElementId: 'change-password-message' });
                changePasswordForm.reset();
                if(changePasswordFormContainer) changePasswordFormContainer.classList.add('hidden');
                if(showChangePasswordFormBtn) showChangePasswordFormBtn.classList.remove('hidden');
            } catch (error) {
                showGlobalMessage({ message: error.message || t('account.passwordUpdateError'), type: 'error', targetElementId: 'change-password-message' });
            } finally {
                if (submitButton) hideButtonLoading(submitButton);
            }
        });
    }


    // B2B Profile Edit Logic
    if (showEditB2BProfileFormBtn && editB2BProfileFormContainer && cancelEditB2BProfileBtn) {
        showEditB2BProfileFormBtn.addEventListener('click', () => {
            editB2BProfileFormContainer.classList.remove('hidden');
            showEditB2BProfileFormBtn.classList.add('hidden');
            if (b2bChangePasswordFormContainer) b2bChangePasswordFormContainer.classList.add('hidden');
            if (showB2BChangePasswordFormBtn) showB2BChangePasswordFormBtn.classList.remove('hidden');
            const currentUser = getUser();
            if (currentUser && currentUser.role === 'b2b') displayLoggedInB2BView(currentUser); // Re-populate
        });
        cancelEditB2BProfileBtn.addEventListener('click', () => {
            editB2BProfileFormContainer.classList.add('hidden');
            showEditB2BProfileFormBtn.classList.remove('hidden');
            const msgDiv = document.getElementById('edit-b2b-profile-message');
            if(msgDiv) msgDiv.textContent = '';
        });
    }

    if (editB2BProfileForm) {
        const submitButton = editB2BProfileForm.querySelector('button[type="submit"]');
        editB2BProfileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (submitButton) showButtonLoading(submitButton, t('saving_changes'));
            const updatedData = {
                contact_name: editB2BProfileForm.contact_name.value,
                phone: editB2BProfileForm.phone.value,
                shipping_address: editB2BProfileForm.shipping_address.value,
            };
            try {
                const response = await makeApiRequest('/user/profile', 'PUT', updatedData, true); // Same endpoint for B2B profile
                setUser(response.user);
                showGlobalMessage({ message: t('account.profileUpdateSuccess'), type: 'success', targetElementId: 'edit-b2b-profile-message' });
                displayLoggedInB2BView(response.user);
                if(editB2BProfileFormContainer) editB2BProfileFormContainer.classList.add('hidden');
                if(showEditB2BProfileFormBtn) showEditB2BProfileFormBtn.classList.remove('hidden');
            } catch (error) {
                showGlobalMessage({ message: error.message || t('account.profileUpdateError'), type: 'error', targetElementId: 'edit-b2b-profile-message' });
            } finally {
                if (submitButton) hideButtonLoading(submitButton);
            }
        });
    }
    
    // B2B Change Password Logic
    if (showB2BChangePasswordFormBtn && b2bChangePasswordFormContainer && cancelB2BChangePasswordBtn) {
        showB2BChangePasswordFormBtn.addEventListener('click', () => {
            b2bChangePasswordFormContainer.classList.remove('hidden');
            showB2BChangePasswordFormBtn.classList.add('hidden');
            if (editB2BProfileFormContainer) editB2BProfileFormContainer.classList.add('hidden');
            if (showEditB2BProfileFormBtn) showEditB2BProfileFormBtn.classList.remove('hidden');
        });
        cancelB2BChangePasswordBtn.addEventListener('click', () => {
            b2bChangePasswordFormContainer.classList.add('hidden');
            showB2BChangePasswordFormBtn.classList.remove('hidden');
            const msgDiv = document.getElementById('b2b-change-password-message');
            if(msgDiv) msgDiv.textContent = '';
            if(b2bChangePasswordForm) b2bChangePasswordForm.reset();
        });
    }

    if (b2bChangePasswordForm) {
        const submitButton = b2bChangePasswordForm.querySelector('button[type="submit"]');
        b2bChangePasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const current_password = b2bChangePasswordForm.current_password.value;
            const new_password = b2bChangePasswordForm.new_password.value;
            const confirm_new_password = b2bChangePasswordForm.confirm_new_password.value;

            if (new_password !== confirm_new_password) {
                showGlobalMessage({ message: t('account.passwordsDoNotMatch'), type: 'error', targetElementId: 'b2b-change-password-message' });
                return;
            }
            if (submitButton) showButtonLoading(submitButton, t('updating_password'));
            try {
                await makeApiRequest('/user/change-password', 'POST', { current_password, new_password }, true); // Same endpoint
                showGlobalMessage({ message: t('account.passwordUpdateSuccess'), type: 'success', targetElementId: 'b2b-change-password-message' });
                b2bChangePasswordForm.reset();
                if(b2bChangePasswordFormContainer) b2bChangePasswordFormContainer.classList.add('hidden');
                if(showB2BChangePasswordFormBtn) showB2BChangePasswordFormBtn.classList.remove('hidden');
            } catch (error) {
                showGlobalMessage({ message: error.message || t('account.passwordUpdateError'), type: 'error', targetElementId: 'b2b-change-password-message' });
            } finally {
                if (submitButton) hideButtonLoading(submitButton);
            }
        });
    }
}

// Update header based on login status
function updateLoginStatusInHeader(isLoggedIn, user = null) {
    const accountLink = document.querySelector('#header-placeholder a[href="compte.html"]'); // This selector might need adjustment
    const logoutLinkContainer = document.getElementById('header-logout-link-container'); // Assuming a container for logout
    const loginRegisterLinkContainer = document.getElementById('header-login-register-link-container'); // Assuming a container for login/register
    const userNameDisplay = document.getElementById('header-user-name');

    // Fallback selectors if the above are not found (more generic)
    const genericAccountLink = Array.from(document.querySelectorAll('header a')).find(a => a.href && a.href.includes('compte.html'));
    const genericLogoutLink = document.getElementById('header-logout-link'); // More specific ID needed if dynamic
    
    if (isLoggedIn && user) {
        if (userNameDisplay) {
            userNameDisplay.textContent = user.name || user.contact_name || user.email;
            userNameDisplay.classList.remove('hidden');
        }
        if (accountLink) { // Or genericAccountLink
            // Account link might change text or behavior, or stay as "Mon Compte"
        }
        if (loginRegisterLinkContainer) loginRegisterLinkContainer.classList.add('hidden');
        if (logoutLinkContainer) {
            logoutLinkContainer.classList.remove('hidden');
            const logoutBtn = logoutLinkContainer.querySelector('button') || logoutLinkContainer.querySelector('a');
            if (logoutBtn && !logoutBtn.dataset.logoutHandlerAttached) { // Prevent multiple listeners
                 logoutBtn.addEventListener('click', (e) => {
                     e.preventDefault();
                     removeToken();
                     window.location.href = 'index.html'; // Or compte.html then reload
                 });
                 logoutBtn.dataset.logoutHandlerAttached = 'true';
            }
        } else if (genericLogoutLink) { // Fallback for a single logout link
            genericLogoutLink.classList.remove('hidden');
             if (!genericLogoutLink.dataset.logoutHandlerAttached) {
                 genericLogoutLink.addEventListener('click', (e) => {
                     e.preventDefault(); removeToken(); window.location.href = 'index.html';
                 });
                 genericLogoutLink.dataset.logoutHandlerAttached = 'true';
            }
        }

    } else { // Logged out
        if (userNameDisplay) {
            userNameDisplay.textContent = '';
            userNameDisplay.classList.add('hidden');
        }
        if (loginRegisterLinkContainer) loginRegisterLinkContainer.classList.remove('hidden');
        if (logoutLinkContainer) logoutLinkContainer.classList.add('hidden');
        else if (genericLogoutLink) genericLogoutLink.classList.add('hidden');
    }
}


// Expose functions to global scope if they are called from HTML attributes like onclick
window.viewOrderDetail = viewOrderDetail;
// initAccountPage should be called on DOMContentLoaded for 'compte.html'
// e.g. in main.js or directly in compte.html script tag.
// If it's specific to compte.html, it can be:
// if (window.location.pathname.endsWith('compte.html')) {
// document.addEventListener('DOMContentLoaded', initAccountPage);
// }
