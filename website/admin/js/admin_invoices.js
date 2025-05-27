// website/admin/js/admin_invoices.js

document.addEventListener('DOMContentLoaded', () => {
    // Called by admin_main.js
});

let b2bUsersCache = []; // Cache for B2B users

async function initializeAdminInvoiceManagement() {
    const userSelectDropdown = document.getElementById('select-b2b-user-for-invoice');
    const createInvoiceFormSection = document.getElementById('create-invoice-form-section');
    const invoiceListSection = document.getElementById('user-invoices-list-section');
    const createInvoiceForm = document.getElementById('admin-create-invoice-form');
    const selectedUserNameSpanInvoice = document.getElementById('selected-b2b-user-name-invoice');
    const selectedUserNameSpanList = document.getElementById('selected-b2b-user-name-list');
    const hiddenUserIdField = document.getElementById('invoice-user-id-hidden');
    const addInvoiceItemButton = document.getElementById('add-invoice-item-button');
    const lineItemsContainer = document.getElementById('invoice-line-items-container');

    if (!userSelectDropdown || !createInvoiceForm || !invoiceListSection || !addInvoiceItemButton || !lineItemsContainer) {
        console.error("One or more critical elements for invoice management are missing from the DOM.");
        return;
    }

    await populateB2BUserDropdown(userSelectDropdown);

    userSelectDropdown.addEventListener('change', async (event) => {
        const selectedUserId = event.target.value;
        const selectedUser = b2bUsersCache.find(u => u.id.toString() === selectedUserId);

        if (selectedUser) {
            if (selectedUserNameSpanInvoice) selectedUserNameSpanInvoice.textContent = selectedUser.company_name || `${selectedUser.prenom} ${selectedUser.nom}`;
            if (selectedUserNameSpanList) selectedUserNameSpanList.textContent = selectedUser.company_name || `${selectedUser.prenom} ${selectedUser.nom}`;
            if (hiddenUserIdField) hiddenUserIdField.value = selectedUserId;

            // Populate client details in the create form
            document.getElementById('create-client-company-name').value = selectedUser.company_name || '';
            document.getElementById('create-client-contact-person').value = `${selectedUser.prenom || ''} ${selectedUser.nom || ''}`.trim();
            // TODO: Add address and VAT fields to user table or fetch from a dedicated client profile if needed. For now, these might be manual.
            // document.getElementById('create-client-address-lines').value = selectedUser.address || '';
            // document.getElementById('create-client-vat-number').value = selectedUser.vat_number || '';


            if (createInvoiceFormSection) createInvoiceFormSection.style.display = 'block';
            if (invoiceListSection) invoiceListSection.style.display = 'block';
            await loadInvoicesForUser(selectedUserId);
            resetCreateInvoiceForm(); // Reset form when user changes
        } else {
            if (createInvoiceFormSection) createInvoiceFormSection.style.display = 'none';
            if (invoiceListSection) invoiceListSection.style.display = 'none';
            if (selectedUserNameSpanInvoice) selectedUserNameSpanInvoice.textContent = '';
            if (selectedUserNameSpanList) selectedUserNameSpanList.textContent = '';
            const tableBody = document.getElementById('admin-invoices-table-body');
            if(tableBody) tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3">Sélectionnez un utilisateur pour voir ses factures.</td></tr>';
        }
    });

    createInvoiceForm.addEventListener('submit', handleCreateAndSaveInvoice);
    addInvoiceItemButton.addEventListener('click', addInvoiceItemRow);

    // Initial call to add one line item row
    addInvoiceItemRow();
    // Add event listener for dynamic total calculation
    lineItemsContainer.addEventListener('input', updateInvoiceTotalsPreview);
    document.getElementById('create-invoice-discount').addEventListener('input', updateInvoiceTotalsPreview);
    document.getElementById('create-invoice-vat-rate').addEventListener('input', updateInvoiceTotalsPreview);

}

function resetCreateInvoiceForm() {
    const form = document.getElementById('admin-create-invoice-form');
    if (form) {
        form.reset();
        document.getElementById('invoice-line-items-container').innerHTML = '';
        addInvoiceItemRow(); // Add one blank row
        updateInvoiceTotalsPreview();
        document.getElementById('invoice-preview-area').style.display = 'none';
        const downloadLink = document.getElementById('generated-pdf-download-link');
        if(downloadLink) {
            downloadLink.href = "#";
            downloadLink.style.display = "none";
            downloadLink.textContent = "";
        }
    }
}


async function populateB2BUserDropdown(selectElement) {
    if (!selectElement) return;
    try {
        const users = await adminApiRequest('/users');
        b2bUsersCache = users.filter(user => user.user_type === 'b2b');
        selectElement.innerHTML = '<option value="">-- Sélectionner un Professionnel --</option>';
        b2bUsersCache.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = `<span class="math-inline">\{user\.company\_name \|\| 'N/A'\} \(</span>{user.prenom || ''} ${user.nom || ''} - ${user.email})`;
            selectElement.appendChild(option);
        });
    } catch (error) {
        console.error("Erreur chargement utilisateurs B2B:", error);
        selectElement.innerHTML = '<option value="">Erreur chargement utilisateurs</option>';
    }
}

function addInvoiceItemRow(item = { description: '', quantity: 1, unit_price_ht: '' }) {
    const container = document.getElementById('invoice-line-items-container');
    const itemIndex = container.children.length;
    const rowHtml = `
        <div class="invoice-item-row grid grid-cols-12 gap-2 items-center mb-2 p-2 border rounded-md">
            <div class="col-span-5">
                <label class="text-xs">Description</label>
                <input type="text" name="items[<span class="math-inline">\{itemIndex\}\]\[description\]" class\="form\-input\-admin item\-description text\-sm p\-1" value\="</span>{item.description}" required placeholder="Description article">
            </div>
            <div class="col-span-2">
                <label class="text-xs">Qté</label>
                <input type="number" name="items[<span class="math-inline">\{itemIndex\}\]\[quantity\]" class\="form\-input\-admin item\-quantity text\-sm p\-1" value\="</span>{item.quantity}" min="1" step="1" required placeholder="Qté">
            </div>
            <div class="col-span-3">
                <label class="text-xs">Prix Unit. HT (€)</label>
                <input type="number" name="items[<span class="math-inline">\{itemIndex\}\]\[unit\_price\_ht\]" class\="form\-input\-admin item\-price\-ht text\-sm p\-1" value\="</span>{item.unit_price_ht}" step="0.01" min="0" required placeholder="Prix HT">
            </div>
            <div class="col-span-1">
                 <label class="text-xs block">&nbsp;</label> <button type="button" class="btn-admin-danger text-xs p-1 remove-item-btn self-end">✕</button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', rowHtml);
    const newRow = container.lastElementChild;
    newRow.querySelector('.remove-item-btn').addEventListener('click', function() {
        this.closest('.invoice-item-row').remove();
        updateInvoiceTotalsPreview(); // Recalculate totals when an item is removed
    });
    updateInvoiceTotalsPreview(); // Recalculate after adding
}

function updateInvoiceTotalsPreview() {
    const itemsContainer = document.getElementById('invoice-line-items-container');
    let totalHtBeforeDiscount = 0;
    itemsContainer.querySelectorAll('.invoice-item-row').forEach(row => {
        const qty = parseFloat(row.querySelector('.item-quantity').value) || 0;
        const priceHt = parseFloat(row.querySelector('.item-price-ht').value) || 0;
        totalHtBeforeDiscount += qty * priceHt;
    });

    const discountPercent = parseFloat(document.getElementById('create-invoice-discount').value) || 0;
    const vatRatePercent = parseFloat(document.getElementById('create-invoice-vat-rate').value) || 0;

    const discountAmount = (totalHtBeforeDiscount * discountPercent) / 100;
    const totalHtAfterDiscount = totalHtBeforeDiscount - discountAmount;
    const vatAmount = (totalHtAfterDiscount * vatRatePercent) / 100;
    const totalTtc = totalHtAfterDiscount + vatAmount;

    document.getElementById('preview-total-ht-before-discount').textContent = totalHtBeforeDiscount.toFixed(2);
    document.getElementById('preview-discount-amount').textContent = discountAmount.toFixed(2);
    document.getElementById('preview-total-ht-after-discount').textContent = totalHtAfterDiscount.toFixed(2);
    document.getElementById('preview-vat-amount').textContent = vatAmount.toFixed(2);
    document.getElementById('preview-total-ttc').textContent = totalTtc.toFixed(2);
}


async function handleCreateAndSaveInvoice(event) {
    event.preventDefault();
    const form = event.target;
    const b2bUserId = document.getElementById('invoice-user-id-hidden').value;

    if (!b2bUserId) {
        showAdminToast("Veuillez sélectionner un client professionnel.", "error");
        return;
    }

    const itemsData = [];
    document.querySelectorAll('#invoice-line-items-container .invoice-item-row').forEach(row => {
        const description = row.querySelector('input[name*="[description]"]').value.trim();
        const quantity = row.querySelector('input[name*="[quantity]"]').value;
        const unit_price_ht = row.querySelector('input[name*="[unit_price_ht]"]').value;

        if (description && quantity && unit_price_ht) { // Basic validation
            itemsData.push({
                description: description,
                quantity: parseInt(quantity),
                unit_price_ht: parseFloat(unit_price_ht)
            });
        }
    });

    if (itemsData.length === 0) {
        showAdminToast("Veuillez ajouter au moins un article à la facture.", "error");
        return;
    }

    const invoicePayload = {
        user_id: b2bUserId,
        client_data: { // These would ideally be pre-filled when selecting a user, or fetched from user's profile
            company_name: document.getElementById('create-client-company-name').value,
            contact_person: document.getElementById('create-client-contact-person').value,
            address_lines: document.getElementById('create-client-address-lines').value.split('\n').map(s => s.trim()).filter(s => s),
            vat_number: document.getElementById('create-client-vat-number').value
        },
        invoice_meta: {
            number: document.getElementById('create-invoice-number').value,
            date: document.getElementById('create-invoice-date').value,
            due_date: document.getElementById('create-invoice-due-date').value,
            discount_percentage_str: document.getElementById('create-invoice-discount').value || "0",
            vat_rate_percent_str: document.getElementById('create-invoice-vat-rate').value || "20"
        },
        items_data: itemsData
    };

    showAdminToast("Génération et enregistrement de la facture en cours...", "info");
    try {
        const result = await adminApiRequest('/invoices/generate-and-save', 'POST', invoicePayload);
        if (result.success) {
            showAdminToast(result.message || "Facture générée et enregistrée avec succès!", "success");

            const previewArea = document.getElementById('invoice-preview-area');
            const downloadLink = document.getElementById('generated-pdf-download-link');

            if (result.download_url && downloadLink && previewArea) {
                downloadLink.href = result.download_url;
                downloadLink.textContent = `Télécharger/Voir Facture: ${result.file_path}`;
                downloadLink.style.display = 'inline-block';
                // For iframe preview:
                // const iframe = document.getElementById('pdf-preview-iframe');
                // iframe.src = result.download_url; // Or a specific preview URL if different
                // previewArea.style.display = 'block';
            } else if (result.file_path && downloadLink && previewArea) { // Fallback if only relative path given
                const staticBase = "/static_assets/invoices_uploads/"; // Assuming this base
                downloadLink.href = staticBase + result.file_path;
                downloadLink.textContent = `Télécharger/Voir Facture: ${result.file_path}`;
                downloadLink.style.display = 'inline-block';
            }


            form.reset();
            document.getElementById('invoice-line-items-container').innerHTML = ''; // Clear items
            addInvoiceItemRow(); // Add a blank row back
            updateInvoiceTotalsPreview(); // Reset totals preview
            await loadInvoicesForUser(b2bUserId); // Refresh the list of invoices for the user
        } else {
            showAdminToast(result.message || "Échec de la création de la facture.", "error");
        }
    } catch (error) {
        showAdminToast(error.message || "Erreur lors de la création de la facture.", "error");
        console.error("Erreur création facture:", error);
    }
}

async function loadInvoicesForUser(userId) {
    // ... (same as previous version, ensures list is refreshed)
    const tableBody = document.getElementById('admin-invoices-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3">Chargement des factures...</td></tr>';

    try {
        const data = await adminApiRequest(`/users/${userId}/invoices`); // Endpoint for fetching invoices for a specific user
        if (data.success && data.invoices) {
            if (data.invoices.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3">Aucune facture trouvée pour cet utilisateur.</td></tr>';
                return;
            }
            let rowsHtml = '';
            data.invoices.forEach(invoice => {
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString('fr-CA');
                const uploadedDate = new Date(invoice.uploaded_at).toLocaleString('fr-FR');
                // Construct a direct link to the static asset if INVOICES_UPLOAD_DIR is served
                // This path needs to match how your Flask app serves static files from INVOICES_UPLOAD_DIR
                const downloadUrl = `/static_assets/invoices_uploads/${invoice.file_path}`; // Adjust if your static path is different

                rowsHtml += `
                    <tr>
                        <td class="px-4 py-2 text-xs"><span class="math-inline">\{invoice\.invoice\_number\}</td\>
            data.invoices.forEach(invoice => {
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString('fr-CA');
                const uploadedDate = new Date(invoice.uploaded_at).toLocaleString('fr-FR');
                // Construct a direct link to the static asset if INVOICES_UPLOAD_DIR is served
                // This path needs to match how your Flask app serves static files from INVOICES_UPLOAD_DIR
                const downloadUrl = `/static_assets/invoices_uploads/${invoice.file_path}`; // Adjust if your static path is different

                rowsHtml += `
                    <tr>
                        <td class="px-4 py-2 text-xs"><span class="math-inline">\{invoice\.invoice\_number\}</td\>
                        <td class="px-4 py-2 text-xs">{invoiceDate}</td>
                        <td class="px-4 py-2 text-xs text-right">parseFloat(invoice.totala​mountt​tc).toFixed(2)€</td><tdclass="px−4py−2text−xs"><ahref="{downloadUrl}" target="_blank" class="text-brand-classic-gold hover:underline">invoice.filep​ath</a></td><tdclass="px−4py−2text−xs">{uploadedDate}</td>
                        <td class="px-4 py-2 text-xs space-x-2">
                        <button onclick="confirmDeleteInvoice(invoice.invoicei​d,′{invoice.invoice_number}')" class="btn-admin-danger p-1 text-xs">Supprimer</button>
                        </td>
                        </tr>
                        ; }); tableBody.innerHTML = rowsHtml; } else { tableBody.innerHTML =<tr><td colspan="6" class="text-center py-3 text-red-500">${data.message || "Erreur chargement factures."}</td></tr>; } } catch (error) { console.error(Erreur chargement factures pour user ${userId}:`, error);
                        tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3 text-red-500">Erreur de communication.</td></tr>';
                        }
                        }
                        
                        function confirmDelete
