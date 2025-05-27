// website/admin/js/admin_invoices.js

document.addEventListener('DOMContentLoaded', () => {
    // This function will be called by admin_main.js if on the correct page
});

async function initializeAdminInvoiceManagement() {
    const userSelectDropdown = document.getElementById('select-b2b-user-for-invoice');
    const uploadFormSection = document.getElementById('upload-invoice-form-section');
    const invoiceListSection = document.getElementById('user-invoices-list-section');
    const uploadInvoiceForm = document.getElementById('admin-upload-invoice-form');
    const selectedUserNameSpanInvoice = document.getElementById('selected-b2b-user-name-invoice');
    const selectedUserNameSpanList = document.getElementById('selected-b2b-user-name-list');
    const hiddenUserIdField = document.getElementById('invoice-user-id-hidden');

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
            document.getElementById('admin-invoices-table-body').innerHTML = '<tr><td colspan="6" class="text-center py-3">Sélectionnez un utilisateur pour voir ses factures.</td></tr>';
        }
    });

    if (uploadInvoiceForm) {
        uploadInvoiceForm.addEventListener('submit', handleInvoiceUpload);
    }
}

async function populateB2BUserDropdown(selectElement) {
    if (!selectElement) return;
    try {
        const users = await adminApiRequest('/users'); // Assuming this endpoint lists all users
        selectElement.innerHTML = '<option value="">-- Sélectionner un Professionnel --</option>'; // Default empty option
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
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString('fr-CA'); // YYYY-MM-DD for consistency
                const uploadedDate = new Date(invoice.uploaded_at).toLocaleString('fr-FR');
                // Construct download URL. Assuming INVOICES_UPLOAD_DIR is served under /static/invoices_uploads/
                // The backend download route for professionals is different, admin might just link to static file or have its own download route.
                // For simplicity here, linking to where the professional would download it (if that route is accessible by admin or if it's just a static link)
                // A dedicated admin download link might be better for tracking/permissions.
                // The file_path from DB is just the filename.pdf
                const downloadUrl = `/static_assets/invoices_uploads/${invoice.file_path}`;


                rowsHtml += `
                    <tr>
                        <td class="px-4 py-2 text-xs">${invoice.invoice_number}</td>
                        <td class="px-4 py-2 text-xs">${invoiceDate}</td>
                        <td class="px-4 py-2 text-xs text-right">${parseFloat(invoice.total_amount_ttc).toFixed(2)} €</td>
                        <td class="px-4 py-2 text-xs"><a href="${downloadUrl}" target="_blank" class="text-brand-classic-gold hover:underline">${invoice.file_path}</a></td>
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
    const userId = form.querySelector('#invoice-user-id-hidden').value;
    if (!userId) {
        showAdminToast("Veuillez d'abord sélectionner un client professionnel.", "error");
        return;
    }

    const formData = new FormData(form);
    // user_id is already in hidden field, FormData will pick it up.

    showAdminToast("Téléversement de la facture en cours...", "info");
    try {
        // adminApiRequest needs to be able to handle FormData
        const result = await adminApiRequest('/invoices/upload', 'POST', formData); // Pass FormData directly

        if (result.success) {
            showAdminToast(result.message || "Facture téléversée avec succès!", "success");
            form.reset(); // Reset form fields
            //form.querySelector('#invoice-file').value = null; // Clear file input specifically
            await loadInvoicesForUser(userId); // Refresh the list
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
