// website/admin/js/admin_invoices.js
document.addEventListener('DOMContentLoaded', () => {
    // This check ensures admin_invoices.js logic only runs if specifically on 'page-admin-manage-invoices'
    // and admin_main.js will call initializeAdminManageInvoicesPage()
});

let currentSelectedB2BUserId = null;
let currentSelectedB2BUserName = '';
let invoiceTemplateDefaults = {}; // To store company defaults for invoice template

async function initializeAdminManageInvoicesPage() {
    const b2bUserSelect = document.getElementById('select-b2b-user-for-invoice');
    const createInvoiceFormSection = document.getElementById('create-invoice-form-section');
    const userInvoicesListSection = document.getElementById('user-invoices-list-section');
    const adminCreateInvoiceForm = document.getElementById('admin-create-invoice-form');
    const addInvoiceItemButton = document.getElementById('add-invoice-item-button');
    const invoiceLineItemsContainer = document.getElementById('invoice-line-items-container');

    // Invoice template config button
    const loadInvoiceTemplateDefaultsButton = document.getElementById('load-invoice-template-defaults-button');
    if (loadInvoiceTemplateDefaultsButton) {
        loadInvoiceTemplateDefaultsButton.addEventListener('click', populateInvoiceTemplateFormWithDefaults);
        fetchInvoiceTemplateDefaults(); // Fetch on page load
    }


    // Modal elements for status update
    const updateStatusModal = document.getElementById('update-invoice-status-modal');
    const updateStatusForm = document.getElementById('update-invoice-status-form');
    const cancelUpdateStatusModalButton = document.getElementById('cancel-update-status-modal');
    const paidDateContainer = document.getElementById('modal-paid-date-container');
    const statusSelectModal = document.getElementById('modal-select-invoice-status');

    if (statusSelectModal) {
        statusSelectModal.addEventListener('change', function() {
            paidDateContainer.style.display = this.value === 'paid' ? 'block' : 'none';
            if (this.value === 'paid' && !document.getElementById('modal-invoice-paid-date').value) {
                 document.getElementById('modal-invoice-paid-date').value = new Date().toISOString().split('T')[0]; // Default to today
            }
        });
    }
    if (cancelUpdateStatusModalButton) {
        cancelUpdateStatusModalButton.addEventListener('click', () => updateStatusModal.style.display = 'none');
    }
    if (updateStatusForm) {
        updateStatusForm.addEventListener('submit', handleUpdateInvoiceStatus);
    }


    await loadB2BUsersForInvoiceSelect();

    if (b2bUserSelect) {
        b2bUserSelect.addEventListener('change', async (event) => {
            currentSelectedB2BUserId = event.target.value;
            if (currentSelectedB2BUserId) {
                const selectedOption = event.target.options[event.target.selectedIndex];
                currentSelectedB2BUserName = selectedOption.dataset.userName || selectedOption.text;

                document.getElementById('selected-b2b-user-name-invoice').textContent = currentSelectedB2BUserName;
                document.getElementById('selected-b2b-user-name-list').textContent = currentSelectedB2BUserName;
                document.getElementById('invoice-user-id-hidden').value = currentSelectedB2BUserId;
                
                // Auto-fill client info in create form
                populateClientInfoForInvoice(selectedOption.dataset);


                createInvoiceFormSection.style.display = 'block';
                userInvoicesListSection.style.display = 'block';
                await loadAdminInvoicesForUser(currentSelectedB2BUserId);
                resetCreateInvoiceForm(); // Reset form when user changes
            } else {
                createInvoiceFormSection.style.display = 'none';
                userInvoicesListSection.style.display = 'none';
                currentSelectedB2BUserName = '';
            }
        });
    }

    if (addInvoiceItemButton) {
        addInvoiceItemButton.addEventListener('click', addInvoiceLineItem);
        addInvoiceLineItem(); // Add one item row by default
    }

    if (adminCreateInvoiceForm) {
        adminCreateInvoiceForm.addEventListener('submit', handleAdminCreateInvoice);
        // Add event listeners to inputs that affect totals for live preview
        ['create-invoice-discount', 'create-invoice-vat-rate'].forEach(id => {
            const input = document.getElementById(id);
            if (input) input.addEventListener('input', updateInvoiceTotalsPreview);
        });
    }
     // Initial call to update preview if there are default values
    updateInvoiceTotalsPreview();
}

async function fetchInvoiceTemplateDefaults() {
    try {
        const response = await makeAdminApiRequest('/settings/invoice-template', 'GET');
        if (response.success && response.settings) {
            invoiceTemplateDefaults = response.settings;
            // Optionally populate the form immediately if it's always visible
            // populateInvoiceTemplateFormWithDefaults();
        } else {
            showAdminGlobalMessage("Erreur lors du chargement des paramètres du modèle de facture.", "error");
        }
    } catch (error) {
        showAdminGlobalMessage(`Erreur serveur (paramètres modèle): ${error.message}`, "error");
    }
}

function populateInvoiceTemplateFormWithDefaults() {
    if (!invoiceTemplateDefaults) return;
    document.getElementById('template-company-name').value = invoiceTemplateDefaults.company_name || '';
    document.getElementById('template-company-contact').value = invoiceTemplateDefaults.company_contact_info || '';
    document.getElementById('template-company-address').value = (invoiceTemplateDefaults.company_address_lines || []).join('\n');
    document.getElementById('template-company-siret').value = invoiceTemplateDefaults.company_siret || '';
    document.getElementById('template-company-vat').value = invoiceTemplateDefaults.company_vat_number || '';
    document.getElementById('template-footer-text').value = invoiceTemplateDefaults.invoice_footer_text || '';
    document.getElementById('template-bank-details').value = invoiceTemplateDefaults.bank_details || '';
    // document.getElementById('template-logo-path').value = invoiceTemplateDefaults.company_logo_path || '';
    showAdminGlobalMessage("Infos de l'entreprise par défaut chargées dans le formulaire.", "info");
}


function populateClientInfoForInvoice(userData) {
    // userData comes from dataset of the selected option
    document.getElementById('create-client-company-name').value = userData.companyName || '';
    document.getElementById('create-client-contact-person').value = `${userData.prenom || ''} ${userData.nom || ''}`.trim();
    // Potentially fetch full address if not in dataset
    // document.getElementById('create-client-address-lines').value = userData.address || '';
    // document.getElementById('create-client-vat-number').value = userData.vatNumber || '';
}


async function loadB2BUsersForInvoiceSelect() {
    const selectElement = document.getElementById('select-b2b-user-for-invoice');
    if (!selectElement) return;
    selectElement.innerHTML = '<option value="">Chargement...</option>';
    try {
        const response = await makeAdminApiRequest('/users?user_type=b2b&status=active', 'GET'); // Fetch only active B2B
        if (response.success && response.users) {
            selectElement.innerHTML = '<option value="">-- Sélectionner un client B2B --</option>';
            response.users.forEach(user => {
                if (user.user_type === 'b2b' && user.status === 'active') { // Double check, though API should filter
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = `${user.company_name} (${user.email})`;
                    option.dataset.userName = user.company_name; // For display
                    option.dataset.companyName = user.company_name;
                    option.dataset.nom = user.nom;
                    option.dataset.prenom = user.prenom;
                    // Add more data attributes if needed for auto-fill
                    selectElement.appendChild(option);
                }
            });
        } else {
            selectElement.innerHTML = '<option value="">Erreur de chargement</option>';
        }
    } catch (error) {
        selectElement.innerHTML = '<option value="">Erreur serveur</option>';
        showAdminGlobalMessage(`Erreur chargement utilisateurs B2B: ${error.message}`, 'error');
    }
}

function addInvoiceLineItem() {
    const container = document.getElementById('invoice-line-items-container');
    const itemIndex = container.children.length;
    const itemHtml = `
        <div class="grid grid-cols-12 gap-2 items-center invoice-line-item py-1">
            <div class="col-span-5">
                <input type="text" name="items[${itemIndex}][description]" class="form-input-admin text-sm" placeholder="Description article" required>
            </div>
            <div class="col-span-2">
                <input type="number" name="items[${itemIndex}][quantity]" class="form-input-admin text-sm" placeholder="Qté" required min="1" value="1">
            </div>
            <div class="col-span-2">
                <input type="number" name="items[${itemIndex}][unit_price_ht]" step="0.01" class="form-input-admin text-sm" placeholder="Prix U. HT" required min="0">
            </div>
            <div class="col-span-2">
                <input type="text" name="items[${itemIndex}][total_ht]" class="form-input-admin text-sm bg-gray-100" placeholder="Total HT" readonly>
            </div>
            <div class="col-span-1">
                <button type="button" class="btn-admin-danger text-xs py-1 px-2 remove-invoice-item-button">&times;</button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', itemHtml);
    // Add event listeners for dynamic calculation and removal
    const newItemRow = container.lastElementChild;
    newItemRow.querySelector('input[name$="[quantity]"]').addEventListener('input', updateInvoiceTotalsPreview);
    newItemRow.querySelector('input[name$="[unit_price_ht]"]').addEventListener('input', updateInvoiceTotalsPreview);
    newItemRow.querySelector('.remove-invoice-item-button').addEventListener('click', function() {
        this.closest('.invoice-line-item').remove();
        updateInvoiceTotalsPreview(); // Recalculate after removal
        // Re-index items (optional, but good for backend if it expects contiguous indices)
        reindexLineItems();
    });
    updateInvoiceTotalsPreview(); // Update totals when a new line is added
}

function reindexLineItems() {
    const container = document.getElementById('invoice-line-items-container');
    const items = container.querySelectorAll('.invoice-line-item');
    items.forEach((item, index) => {
        item.querySelectorAll('input, select, textarea').forEach(input => {
            if (input.name) {
                input.name = input.name.replace(/items\[\d+\]/, `items[${index}]`);
            }
        });
    });
}


function updateInvoiceTotalsPreview() {
    let totalHtBeforeDiscount = 0;
    const lineItems = document.querySelectorAll('#invoice-line-items-container .invoice-line-item');
    
    lineItems.forEach(item => {
        const qtyInput = item.querySelector('input[name$="[quantity]"]');
        const priceInput = item.querySelector('input[name$="[unit_price_ht]"]');
        const totalHtInput = item.querySelector('input[name$="[total_ht]"]');
        
        const qty = parseFloat(qtyInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;
        const lineTotal = qty * price;
        
        if (totalHtInput) totalHtInput.value = lineTotal.toFixed(2);
        totalHtBeforeDiscount += lineTotal;
    });

    document.getElementById('preview-total-ht-before-discount').textContent = totalHtBeforeDiscount.toFixed(2);

    const discountPercent = parseFloat(document.getElementById('create-invoice-discount').value) || 0;
    const vatRatePercent = parseFloat(document.getElementById('create-invoice-vat-rate').value) || 0;

    const discountAmount = (totalHtBeforeDiscount * discountPercent) / 100;
    document.getElementById('preview-discount-amount').textContent = discountAmount.toFixed(2);

    const totalHtAfterDiscount = totalHtBeforeDiscount - discountAmount;
    document.getElementById('preview-total-ht-after-discount').textContent = totalHtAfterDiscount.toFixed(2);

    const vatAmount = (totalHtAfterDiscount * vatRatePercent) / 100;
    document.getElementById('preview-vat-amount').textContent = vatAmount.toFixed(2);

    const totalTtc = totalHtAfterDiscount + vatAmount;
    document.getElementById('preview-total-ttc').textContent = totalTtc.toFixed(2);
}


async function handleAdminCreateInvoice(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form); // Use FormData for multipart/form-data
    
    // Append invoice template overrides from the form if they exist
    // This part assumes your backend /admin_api/invoices/b2b endpoint
    // is set up to receive these `template_` prefixed fields and pass them
    // to the `company_info_override` parameter of `generate_invoice_pdf`.
    // If not, this data would need to be handled differently (e.g., saved as global settings first).
    const templateFields = [
        'template_company_name', 'template_company_contact_info', 'template_company_address_lines',
        'template_company_siret', 'template_company_vat_number', 'template_invoice_footer_text', 'template_bank_details'
    ];
    templateFields.forEach(id => {
        const element = document.getElementById(id);
        if (element && element.value.trim() !== '') {
            formData.append(element.name, element.value.trim());
        }
    });


    showAdminGlobalMessage("Génération de la facture en cours...", "info");
    document.getElementById('invoice-preview-area').style.display = 'none'; // Hide previous preview
    document.getElementById('generated-pdf-download-link').style.display = 'none';


    try {
        // The makeAdminApiRequest needs to be adapted if it doesn't handle FormData well for POST
        // For FormData, typically you don't set Content-Type header, browser does it.
        // If makeAdminApiRequest stringifies body, it won't work for FormData.
        // Let's assume makeAdminApiRequest can handle FormData or we use fetch directly.

        const token = getAdminAuthToken(); // Assuming you have this function
        const response = await fetch(`${ADMIN_API_BASE_URL}/invoices/b2b`, {
            method: 'POST',
            headers: {
                'x-access-token': token
                // 'Content-Type' is NOT set for FormData, browser handles it with boundary
            },
            body: formData
        });
        
        const result = await response.json();

        if (result.success) {
            showAdminGlobalMessage(result.message || "Facture créée avec succès!", "success");
            form.reset(); // Reset form fields
            document.getElementById('invoice-line-items-container').innerHTML = ''; // Clear line items
            addInvoiceLineItem(); // Add one default line item back
            updateInvoiceTotalsPreview(); // Reset totals preview
            await loadAdminInvoicesForUser(currentSelectedB2BUserId); // Refresh list

            if (result.pdf_download_url) { // If backend returns a direct download URL for the generated PDF
                const previewArea = document.getElementById('invoice-preview-area');
                const pdfLink = document.getElementById('generated-pdf-download-link');
                const pdfIframe = document.getElementById('pdf-preview-iframe');
                
                // Construct full URL for iframe and link if relative
                const fullPdfUrl = result.pdf_download_url.startsWith('http') ? result.pdf_download_url : `${API_BASE_URL}${result.pdf_download_url}`;

                pdfLink.href = fullPdfUrl;
                pdfLink.textContent = `Télécharger ${result.pdf_filename || 'Facture PDF'}`;
                pdfLink.style.display = 'inline-block';
                
                // For iframe preview, ensure the URL is safe and CORS allows it.
                // Direct PDF rendering in iframe can be tricky due to browser plugins/settings.
                // pdfIframe.src = fullPdfUrl; // This might not work if Content-Disposition is attachment
                // A better approach for preview might be to have a separate endpoint that serves PDF inline
                // or use a PDF viewer library. For now, just provide the download link.
                pdfIframe.src = `https://docs.google.com/gview?url=${encodeURIComponent(fullPdfUrl)}&embedded=true`; // Google Docs viewer as a fallback
                
                previewArea.style.display = 'block';
            }

        } else {
            showAdminGlobalMessage(result.message || "Erreur lors de la création de la facture.", "error");
        }
    } catch (error) {
        showAdminGlobalMessage(`Erreur serveur: ${error.message}`, "error");
    }
}


function resetCreateInvoiceForm() {
    const form = document.getElementById('admin-create-invoice-form');
    if (form) form.reset();
    document.getElementById('invoice-line-items-container').innerHTML = '';
    addInvoiceLineItem();
    updateInvoiceTotalsPreview();
    document.getElementById('invoice-preview-area').style.display = 'none';
    document.getElementById('generated-pdf-download-link').style.display = 'none';
    // Also reset template override fields
    const templateFieldsToReset = [
        'template-company-name', 'template-company-contact', 'template-company-address',
        'template-company-siret', 'template-company-vat', 'template-footer-text', 'template-bank-details'
    ];
    templateFieldsToReset.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.value = '';
    });

}


async function loadAdminInvoicesForUser(userId) {
    const tableBody = document.getElementById('admin-invoices-table-body');
    tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">Chargement des factures...</td></tr>';
    try {
        const response = await makeAdminApiRequest(`/invoices/b2b/for-user/${userId}`, 'GET');
        if (response.success && response.invoices) {
            if (response.invoices.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">Aucune facture trouvée pour ce client.</td></tr>';
                return;
            }
            let rowsHtml = '';
            response.invoices.forEach(invoice => {
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString('fr-FR');
                const paidDate = invoice.paid_date ? new Date(invoice.paid_date).toLocaleDateString('fr-FR') : 'N/A';
                const createdAt = invoice.created_at ? new Date(invoice.created_at).toLocaleDateString('fr-FR') : 'N/A'; // Assuming created_at exists
                
                // Construct download URL for the PDF
                // The backend professional/invoices/<id>/download is for B2B users.
                // Admin might need a different endpoint or use the professional one if permissions allow.
                // For now, assume file_path is just the filename and we prepend API_BASE_URL + /invoices_b2b_files/ (hypothetical static serve path)
                // Or better, use the download URL from professional_bp if it's accessible by admin token
                let downloadLink = '#';
                if (invoice.file_path) {
                     // Assuming the professional download route works with admin token or a similar admin route exists
                    downloadLink = `${API_BASE_URL}/professional/invoices/${invoice.invoice_id}/download`;
                }

                rowsHtml += `
                    <tr class="border-b border-brand-cream hover:bg-brand-cream/30">
                        <td class="px-4 py-3">${invoice.invoice_number}</td>
                        <td class="px-4 py-3">${invoiceDate}</td>
                        <td class="px-4 py-3">${parseFloat(invoice.total_amount_ttc).toFixed(2)} €</td>
                        <td class="px-4 py-3">
                            <span class="status-badge status-${invoice.status || 'pending'}">${invoice.status || 'pending'}</span>
                        </td>
                        <td class="px-4 py-3">${paidDate}</td>
                        <td class="px-4 py-3">
                            ${invoice.file_path ? `<a href="${downloadLink}" target="_blank" class="text-brand-classic-gold hover:underline">${invoice.file_path}</a>` : 'N/A'}
                        </td>
                        <td class="px-4 py-3">${createdAt}</td>
                        <td class="px-4 py-3">
                            <button class="btn-admin-icon edit-invoice-status-button" data-invoice-id="${invoice.invoice_id}" data-invoice-number="${invoice.invoice_number}" data-current-status="${invoice.status}" data-paid-date="${invoice.paid_date || ''}" title="Modifier Statut">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" /></svg>
                            </button>
                            </td>
                    </tr>
                `;
            });
            tableBody.innerHTML = rowsHtml;
            attachStatusEditListeners();
        } else {
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4">${response.message || 'Erreur de chargement des factures.'}</td></tr>`;
        }
    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4">Erreur serveur: ${error.message}</td></tr>`;
    }
}

function attachStatusEditListeners() {
    document.querySelectorAll('.edit-invoice-status-button').forEach(button => {
        button.addEventListener('click', function() {
            const invoiceId = this.dataset.invoiceId;
            const invoiceNumber = this.dataset.invoiceNumber;
            const currentStatus = this.dataset.currentStatus;
            const paidDate = this.dataset.paidDate;

            document.getElementById('modal-invoice-id-status').value = invoiceId;
            document.getElementById('modal-invoice-number-status').textContent = invoiceNumber;
            const statusSelect = document.getElementById('modal-select-invoice-status');
            statusSelect.value = currentStatus;
            
            const paidDateInput = document.getElementById('modal-invoice-paid-date');
            const paidDateContainer = document.getElementById('modal-paid-date-container');

            if (currentStatus === 'paid' && paidDate) {
                paidDateInput.value = paidDate; // Format YYYY-MM-DD
                paidDateContainer.style.display = 'block';
            } else if (currentStatus === 'paid' && !paidDate) { // If paid but no date, default to today
                paidDateInput.value = new Date().toISOString().split('T')[0];
                paidDateContainer.style.display = 'block';
            }
            else {
                paidDateInput.value = '';
                paidDateContainer.style.display = 'none';
            }
            
            document.getElementById('update-invoice-status-modal').style.display = 'flex';
        });
    });
}

async function handleUpdateInvoiceStatus(event) {
    event.preventDefault();
    const form = event.target;
    const invoiceId = form.querySelector('#modal-invoice-id-status').value;
    const newStatus = form.querySelector('#modal-select-invoice-status').value;
    let paidDate = form.querySelector('#modal-invoice-paid-date').value;

    if (newStatus !== 'paid') {
        paidDate = null; // Clear paid_date if status is not 'paid'
    } else if (newStatus === 'paid' && !paidDate) {
        // If status is 'paid' and date is empty, backend might default it or you can set it here
        paidDate = new Date().toISOString().split('T')[0];
    }


    const payload = { status: newStatus };
    if (paidDate) {
        payload.paid_date = paidDate;
    }

    try {
        const response = await makeAdminApiRequest(`/invoices/b2b/${invoiceId}/status`, 'PUT', payload);
        if (response.success) {
            showAdminGlobalMessage(response.message || "Statut de la facture mis à jour.", "success");
            document.getElementById('update-invoice-status-modal').style.display = 'none';
            if (currentSelectedB2BUserId) {
                await loadAdminInvoicesForUser(currentSelectedB2BUserId); // Refresh list
            }
        } else {
            showAdminGlobalMessage(response.message || "Erreur lors de la mise à jour du statut.", "error");
        }
    } catch (error) {
        showAdminGlobalMessage(`Erreur serveur: ${error.message}`, "error");
    }
}


window.initializeAdminManageInvoicesPage = initializeAdminManageInvoicesPage;
