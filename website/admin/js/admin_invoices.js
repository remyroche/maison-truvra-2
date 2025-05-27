// website/admin/js/admin_invoices.js

document.addEventListener('DOMContentLoaded', () => {
    // This function will be called by admin_main.js if on the correct page
});

async function initializeAdminInvoiceManagement() {
    const userSelectDropdown = document.getElementById('select-b2b-user-for-invoice');
    const uploadFormSection = document.getElementById('upload-invoice-form-section');
    const invoiceListSection = document.getElementById('user-invoices-list-section');
    const uploadInvoiceForm = document.getElementById('admin-upload-invoice-form');
    const selectedUserNameSpanInvoice = document.getElementById('selected-b2b-user-name-invoice');// website/admin/js/admin_invoices.js

document.addEventListener('DOMContentLoaded', () => {
    // This function will be called by admin_main.js if on the correct page
    // (Assuming initializeAdminInvoiceManagement is called from admin_main.js)
});

async function initializeAdminInvoiceManagement() {
    const userSelectDropdown = document.getElementById('select-b2b-user-for-invoice');
    const uploadFormSection = document.getElementById('upload-invoice-form-section');
    const invoiceListSection = document.getElementById('user-invoices-list-section');
    const uploadInvoiceForm = document.getElementById('admin-upload-invoice-form');
    const selectedUserNameSpanInvoice = document.getElementById('selected-b2b-user-name-invoice');
    const selectedUserNameSpanList = document.getElementById('selected-b2b-user-name-list');
    const hiddenUserIdField = document.getElementById('invoice-user-id-hidden'); // Corrected ID

    if (!userSelectDropdown || !uploadInvoiceForm || !invoiceListSection) {
        console.error("One or more critical elements for invoice management are missing.");
        return;
    }

    await populateB2BUserDropdown(userSelectDropdown);

    userSelectDropdown.addEventListener('change', async (event) => {
        const selectedUserId = event.target.value;
        const selectedUserName = event.target.options[event.target.selectedIndex].text;

        if (selectedUserId) {
            if (selectedUserNameSpanInvoice) selectedUserNameSpanInvoice.textContent = selectedUserName;
            if (selectedUserNameSpanList) selectedUserNameSpanList.textContent = selectedUserName;
            if (hiddenUserIdField) hiddenUserIdField.value = selectedUserId;

            if (uploadFormSection) uploadFormSection.style.display = 'block';
            if (invoiceListSection) invoiceListSection.style.display = 'block';
            await loadInvoicesForUser(selectedUserId);
        } else {
            if (uploadFormSection) uploadFormSection.style.display = 'none';
            if (invoiceListSection) invoiceListSection.style.display = 'none';
            if (selectedUserNameSpanInvoice) selectedUserNameSpanInvoice.textContent = '';
            if (selectedUserNameSpanList) selectedUserNameSpanList.textContent = '';
            const tableBody = document.getElementById('admin-invoices-table-body');
            if(tableBody) tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3">Sélectionnez un utilisateur pour voir ses factures.</td></tr>';
        }
    });

    uploadInvoiceForm.addEventListener('submit', handleInvoiceUpload);
}

async function populateB2BUserDropdown(selectElement) {
    if (!selectElement) return;
    try {
        const users = await adminApiRequest('/users'); // Assuming this endpoint lists all users
        selectElement.innerHTML = '<option value="">-- Sélectionner un Professionnel --</option>';
        users.filter(user => user.user_type === 'b2b').forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = `${user.company_name || 'N/A'} (${user.prenom || ''} ${user.nom || ''} - ${user.email})`;
            selectElement.appendChild(option);
        });
    } catch (error) {
        console.error("Erreur chargement utilisateurs B2B:", error);
        selectElement.innerHTML = '<option value="">Erreur chargement utilisateurs</option>';
    }
}

async function loadInvoicesForUser(userId) {
    const tableBody = document.getElementById('admin-invoices-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3">Chargement des factures...</td></tr>';

    try {
        const data = await adminApiRequest(`/users/${userId}/invoices`);
        if (data.success && data.invoices) {
            if (data.invoices.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3">Aucune facture trouvée pour cet utilisateur.</td></tr>';
                return;
            }
            let rowsHtml = '';
            data.invoices.forEach(invoice => {
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString('fr-CA');
                const uploadedDate = new Date(invoice.uploaded_at).toLocaleString('fr-FR');
                // Construct download URL using the professional-facing download route for consistency,
                // or use a direct static link if INVOICES_UPLOAD_DIR is served publicly (less secure).
                // The backend /api/professional/invoices/:id/download handles auth for the professional.
                // For admin, direct link to static could be an option if permissions are handled by static server config.
                // For now, let's assume the file_path is just the filename.
                const staticDownloadUrl = `${window.location.origin}/static_assets/invoices_uploads/${invoice.file_path}`;


                rowsHtml += `
                    <tr>
                        <td class="px-4 py-2 text-xs">${invoice.invoice_number}</td>
                        <td class="px-4 py-2 text-xs">${invoiceDate}</td>
                        <td class="px-4 py-2 text-xs text-right">${parseFloat(invoice.total_amount_ttc).toFixed(2)} €</td>
                        <td class="px-4 py-2 text-xs"><a href="${staticDownloadUrl}" target="_blank" class="text-brand-classic-gold hover:underline">${invoice.file_path}</a></td>
                        <td class="px-4 py-2 text-xs">${uploadedDate}</td>
                        <td class="px-4 py-2 text-xs space-x-2">
                            <button onclick="confirmDeleteInvoice(${invoice.invoice_id}, '${invoice.invoice_number}')" class="btn-admin-danger p-1 text-xs">Supprimer</button>
                        </td>
                    </tr>
                `;
            });
            tableBody.innerHTML = rowsHtml;
        } else {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-3 text-red-500">${data.message || "Erreur chargement factures."}</td></tr>`;
        }
    } catch (error) {
        console.error(`Erreur chargement factures pour user ${userId}:`, error);
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3 text-red-500">Erreur de communication.</td></tr>';
    }
}

async function handleInvoiceUpload(event) {
    event.preventDefault();
    const form = event.target;
    const userId = form.querySelector('#invoice-user-id-hidden').value; // Corrected ID used
    if (!userId) {
        showAdminToast("Veuillez d'abord sélectionner un client professionnel.", "error");
        return;
    }

    const formData = new FormData(form);
    // The 'user_id' is already part of 'formData' because of the hidden input field.

    // Optional: Add line items if your form includes them.
    // For now, this assumes the PDF is complete and only metadata is entered in the form.
    // If you were to add line items to the form:
    // const items = [];
    // document.querySelectorAll('.invoice-item-row').forEach(row => {
    //     items.push({
    //         name: row.querySelector('.item-name').value,
    //         quantity: row.querySelector('.item-quantity').value,
    //         unit_price_ht: row.querySelector('.item-price').value,
    //     });
    // });
    // formData.append('items_data', JSON.stringify(items)); // Send items as JSON string

    showAdminToast("Téléversement de la facture en cours...", "info");
    try {
        // adminApiRequest is already set up to handle FormData
        const result = await adminApiRequest('/invoices/upload', 'POST', formData);

        if (result.success) {
            showAdminToast(result.message || "Facture téléversée avec succès!", "success");
            form.reset(); // Reset form fields, including the file input
            // Re-select the current user in the dropdown to refresh their invoice list
            const userSelectDropdown = document.getElementById('select-b2b-user-for-invoice');
            if (userSelectDropdown.value === userId) { // If the same user is still selected
                await loadInvoicesForUser(userId);
            } else { // If user changed, or to be safe, reset selection
                userSelectDropdown.value = userId; // This should trigger the change event again if not already selected
                // If change event not triggered, manually call: await loadInvoicesForUser(userId);
            }
        } else {
            showAdminToast(result.message || "Échec du téléversement de la facture.", "error");
        }
    } catch (error) {
        showAdminToast(error.message || "Erreur lors du téléversement.", "error");
        console.error("Erreur téléversement facture:", error);
    }
}

function confirmDeleteInvoice(invoiceId, invoiceNumber) {
    if (confirm(`Êtes-vous sûr de vouloir supprimer la facture N° ${invoiceNumber} (ID: ${invoiceId}) ? Cette action est irréversible.`)) {
        deleteInvoice(invoiceId);
    }
}

async function deleteInvoice(invoiceId) {
    showAdminToast("Suppression de la facture en cours...", "info");
    try {
        const result = await adminApiRequest(`/invoices/${invoiceId}`, 'DELETE');
        if (result.success) {
            showAdminToast(result.message || "Facture supprimée avec succès!", "success");
            const selectedUserId = document.getElementById('select-b2b-user-for-invoice').value;
            if (selectedUserId) {
                await loadInvoicesForUser(selectedUserId); // Refresh list
            }
        } else {
            showAdminToast(result.message || "Échec de la suppression.", "error");
        }
    } catch (error) {
        showAdminToast(error.message || "Erreur lors de la suppression.", "error");
        console.error("Erreur suppression facture:", error);
    }
}
