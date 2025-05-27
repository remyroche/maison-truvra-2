// website/admin/js/admin_invoices.js
import { callAdminApi, showAdminToast } from './admin_api.js';

document.addEventListener('DOMContentLoaded', () => {
    const page = getCurrentPageName();

    if (page === 'admin_manage_invoices.html') {
        initManageInvoicesPage();
    }
});

function getCurrentPageName() {
    const path = window.location.pathname;
    return path.substring(path.lastIndexOf('/') + 1);
}

async function initManageInvoicesPage() {
    const createInvoiceForm = document.getElementById('createInvoiceForm');
    const uploadInvoiceForm = document.getElementById('uploadInvoiceForm');
    const invoicesTableBody = document.getElementById('invoicesTableBody');
    const b2bUserSelect = document.getElementById('b2bUserSelect'); // For create form
    const b2bUserUploadSelect = document.getElementById('b2bUserUploadSelect'); // For upload form
    const filterUserIdInput = document.getElementById('filterUserId');
    const applyFilterButton = document.getElementById('applyInvoiceFilter');


    if (!invoicesTableBody) {
        console.error('Invoices table body not found.');
        return;
    }
    if (b2bUserSelect) await populateB2BUserDropdown(b2bUserSelect);
    if (b2bUserUploadSelect) await populateB2BUserDropdown(b2bUserUploadSelect);


    if (createInvoiceForm) {
        const addItemButton = document.getElementById('addInvoiceItem');
        if (addItemButton) {
            addItemButton.addEventListener('click', addInvoiceItemRow);
        } else {
            console.warn('Add invoice item button not found');
        }
        createInvoiceForm.addEventListener('submit', handleCreateInvoice);
    } else {
        console.warn('Create invoice form not found');
    }
    
    if (uploadInvoiceForm) {
        uploadInvoiceForm.addEventListener('submit', handleUploadInvoice);
    } else {
        console.warn('Upload invoice form not found');
    }

    if (applyFilterButton && filterUserIdInput) {
        applyFilterButton.addEventListener('click', () => {
            const userId = filterUserIdInput.value.trim();
            loadInvoices(1, userId ? parseInt(userId) : null);
        });
    }


    loadInvoices(); // Initial load
}

async function populateB2BUserDropdown(selectElement) {
    if (!selectElement) return;
    try {
        // Fetch only B2B (professional) users
        const response = await callAdminApi('/users?user_type=b2b&per_page=1000', 'GET'); // Fetch more users if needed
        if (response && response.users) {
            selectElement.innerHTML = '<option value="">Select B2B User</option>'; // Default option
            response.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `${user.company_name || user.email} (ID: ${user.id})`;
                selectElement.appendChild(option);
            });
        } else {
             selectElement.innerHTML = '<option value="">Could not load users</option>';
        }
    } catch (error) {
        console.error('Failed to populate B2B user dropdown:', error);
        showAdminToast('Error fetching B2B users.', 'error');
        if(selectElement) selectElement.innerHTML = '<option value="">Error loading users</option>';
    }
}

function addInvoiceItemRow() {
    const itemsContainer = document.getElementById('invoiceItemsContainer');
    if (!itemsContainer) {
        console.error('Invoice items container not found');
        return;
    }
    const itemIndex = itemsContainer.children.length;
    const itemRow = document.createElement('div');
    itemRow.classList.add('flex', 'space-x-2', 'mb-2', 'invoice-item-row');
    itemRow.innerHTML = `
        <input type="text" name="items[${itemIndex}][description]" placeholder="Description" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50 p-2 text-sm" required>
        <input type="number" name="items[${itemIndex}][quantity]" placeholder="Qty" class="mt-1 block w-1/4 rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50 p-2 text-sm" required step="any">
        <input type="number" name="items[${itemIndex}][unit_price]" placeholder="Unit Price" class="mt-1 block w-1/4 rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50 p-2 text-sm" required step="0.01">
        <button type="button" class="remove-item-btn bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-xs">Remove</button>
    `;
    itemsContainer.appendChild(itemRow);
    itemRow.querySelector('.remove-item-btn').addEventListener('click', () => itemRow.remove());
}


async function handleCreateInvoice(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const invoiceData = {
        user_id: formData.get('user_id'),
        order_id: formData.get('order_id') || null, // Optional
        client_details: { // Assuming you might add specific client detail fields later
            name: formData.get('client_name_override') || null, // Example: allow override
            address: formData.get('client_address_override') || null,
            vat_number: formData.get('client_vat_override') || null,
        },
        items: [],
        invoice_number: formData.get('invoice_number') || null, // Optional, can be auto-generated
        issue_date: formData.get('issue_date'),
        due_date: formData.get('due_date') || null,
        payment_terms: formData.get('payment_terms') || null,
        notes: formData.get('notes') || null,
    };

    const itemRows = document.querySelectorAll('#invoiceItemsContainer .invoice-item-row');
    itemRows.forEach(row => {
        const descriptionInput = row.querySelector('input[name*="[description]"]');
        const quantityInput = row.querySelector('input[name*="[quantity]"]');
        const unitPriceInput = row.querySelector('input[name*="[unit_price]"]');
        
        if (descriptionInput && quantityInput && unitPriceInput) {
            invoiceData.items.push({
                description: descriptionInput.value,
                quantity: parseFloat(quantityInput.value),
                unit_price: parseFloat(unitPriceInput.value)
            });
        }
    });
    
    if (!invoiceData.user_id) {
        showAdminToast('Please select a B2B User.', 'error');
        return;
    }
    if (invoiceData.items.length === 0) {
        showAdminToast('Please add at least one item to the invoice.', 'error');
        return;
    }


    try {
        const result = await callAdminApi('/invoices/generate', 'POST', invoiceData);
        if (result.success) {
            showAdminToast('Invoice generated successfully!', 'success');
            event.target.reset(); // Reset form
            document.getElementById('invoiceItemsContainer').innerHTML = ''; // Clear items
            loadInvoices(); // Refresh table
        } else {
            showAdminToast(`Failed to generate invoice: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('Error generating invoice:', error);
        showAdminToast('An error occurred while generating the invoice.', 'error');
    }
}

async function handleUploadInvoice(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    // FormData will correctly handle the file input named "invoice_file"

    if (!formData.get('user_id')) {
        showAdminToast('Please select a B2B User for the upload.', 'error');
        return;
    }
     if (!formData.get('invoice_file') || formData.get('invoice_file').size === 0) {
        showAdminToast('Please select an invoice file to upload.', 'error');
        return;
    }


    try {
        // The 'callAdminApi' needs to be able to handle FormData for file uploads
        // If it stringifies the body by default, it won't work for files.
        // Let's assume callAdminApi can handle FormData if body is FormData instance.
        const result = await callAdminApi('/invoices/upload', 'POST', formData, true); // true to indicate FormData

        if (result.success) {
            showAdminToast('Invoice uploaded successfully!', 'success');
            event.target.reset();
            loadInvoices(); // Refresh table
        } else {
            showAdminToast(`Failed to upload invoice: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('Error uploading invoice:', error);
        showAdminToast('An error occurred while uploading the invoice.', 'error');
    }
}


async function loadInvoices(page = 1, userId = null) {
    const invoicesTableBody = document.getElementById('invoicesTableBody');
    if (!invoicesTableBody) return;

    let url = `/invoices?page=${page}&per_page=10`;
    if (userId) {
        url += `&user_id=${userId}`;
    }

    try {
        const data = await callAdminApi(url, 'GET');
        if (data.success && data.invoices) {
            invoicesTableBody.innerHTML = ''; // Clear existing rows
            if (data.invoices.length === 0) {
                invoicesTableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4">No invoices found.</td></tr>';
            } else {
                data.invoices.forEach(invoice => {
                    const row = invoicesTableBody.insertRow();
                    row.innerHTML = `
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${invoice.id}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${invoice.invoice_number}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${invoice.user ? (invoice.user.company_name || invoice.user.email) : 'N/A'} (ID: ${invoice.user_id})</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${new Date(invoice.issue_date).toLocaleDateString()}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${invoice.total_amount.toFixed(2)} ${invoice.currency || 'EUR'}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${invoice.status === 'paid' ? 'bg-green-100 text-green-800' : invoice.status === 'unpaid' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}">
                                ${invoice.status}
                            </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            ${invoice.download_url ? `<a href="${invoice.download_url}" target="_blank" class="text-indigo-600 hover:text-indigo-900 mr-2">View</a>` : ''}
                            <button class="text-blue-600 hover:text-blue-900" onclick="alert('Edit invoice ${invoice.id} - TBD')">Edit</button>
                            <button class="text-red-600 hover:text-red-900 ml-2" onclick="confirmDeleteInvoice(${invoice.id})">Delete</button>
                        </td>
                    `;
                });
            }
            setupInvoicePagination(data.current_page, data.pages, userId);
        } else {
            invoicesTableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Failed to load invoices.</td></tr>';
            showAdminToast(data.message || 'Failed to load invoices.', 'error');
        }
    } catch (error) {
        console.error('Error loading invoices:', error);
        invoicesTableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Error loading invoices.</td></tr>';
        showAdminToast('Error loading invoices.', 'error');
    }
}

function setupInvoicePagination(currentPage, totalPages, currentFilterUserId) {
    const paginationControls = document.getElementById('invoicePaginationControls');
    if (!paginationControls) return;

    paginationControls.innerHTML = ''; // Clear existing controls

    if (totalPages <= 1) return;

    // Previous Button
    if (currentPage > 1) {
        const prevButton = document.createElement('button');
        prevButton.textContent = 'Previous';
        prevButton.classList.add('px-4', 'py-2', 'text-sm', 'font-medium', 'text-gray-700', 'bg-white', 'border', 'border-gray-300', 'rounded-md', 'hover:bg-gray-50');
        prevButton.addEventListener('click', () => loadInvoices(currentPage - 1, currentFilterUserId));
        paginationControls.appendChild(prevButton);
    }

    // Page Numbers (simplified: just show current page and total)
    const pageInfo = document.createElement('span');
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    pageInfo.classList.add('px-4', 'py-2', 'text-sm');
    paginationControls.appendChild(pageInfo);


    // Next Button
    if (currentPage < totalPages) {
        const nextButton = document.createElement('button');
        nextButton.textContent = 'Next';
        nextButton.classList.add('ml-2', 'px-4', 'py-2', 'text-sm', 'font-medium', 'text-gray-700', 'bg-white', 'border', 'border-gray-300', 'rounded-md', 'hover:bg-gray-50');
        nextButton.addEventListener('click', () => loadInvoices(currentPage + 1, currentFilterUserId));
        paginationControls.appendChild(nextButton);
    }
}

// Make functions globally available if called by inline event handlers
window.confirmDeleteInvoice = async (invoiceId) => {
    if (confirm(`Are you sure you want to delete invoice ID ${invoiceId}? This action cannot be undone.`)) {
        try {
            const result = await callAdminApi(`/invoices/${invoiceId}`, 'DELETE');
            if (result.success) {
                showAdminToast('Invoice deleted successfully!', 'success');
                loadInvoices(); // Refresh the list
            } else {
                showAdminToast(`Failed to delete invoice: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('Error deleting invoice:', error);
            showAdminToast('An error occurred while deleting the invoice.', 'error');
        }
    }
};
