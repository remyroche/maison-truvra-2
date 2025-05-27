// website/admin/js/admin_invoices.js
// This script handles B2B invoice management in the admin panel.

// Global variables for this page
let currentSelectedB2BUserId = null;
let currentSelectedB2BUserName = '';
let invoiceTemplateDefaults = {}; // To store company defaults for invoice template

// Main initialization function for the B2B Invoices page
async function initializeAdminManageInvoicesPage() {
    console.log("Initializing Admin Manage B2B Invoices Page...");

    // --- DOM Element References ---
    const b2bUserSelect = document.getElementById('select-b2b-user-for-invoice');
    const createInvoiceFormSection = document.getElementById('create-invoice-form-section');
    const userInvoicesListSection = document.getElementById('user-invoices-list-section');
    const adminCreateInvoiceForm = document.getElementById('admin-create-invoice-form');
    const addInvoiceItemButton = document.getElementById('add-invoice-item-button');
    // const invoiceLineItemsContainer = document.getElementById('invoice-line-items-container'); // Used within functions

    const loadInvoiceTemplateDefaultsButton = document.getElementById('load-invoice-template-defaults-button');
    
    // Status Update Modal Elements
    const updateStatusModal = document.getElementById('update-invoice-status-modal');
    const updateStatusForm = document.getElementById('update-invoice-status-form');
    const cancelUpdateStatusModalButton = document.getElementById('cancel-update-status-modal');
    const paidDateContainer = document.getElementById('modal-paid-date-container');
    const statusSelectModal = document.getElementById('modal-select-invoice-status');

    // --- Ensure Global UI Functions are available (showAlert, showGlobalAdminMessage) ---
    if (!window.showAlert) {
        console.warn("Global showAlert function not found. Using console.log fallback.");
        window.showAlert = (message, title = "Alert") => console.log(`ALERT (${title}): ${message}`);
    }
    if (!window.showGlobalAdminMessage) {
        console.warn("Global showGlobalAdminMessage function not found. Using console.log fallback.");
        window.showGlobalAdminMessage = (message, type = "info") => console.log(`GLOBAL MSG (${type}): ${message}`);
    }
    // --- End UI Function Checks ---


    // --- Event Listeners ---
    if (loadInvoiceTemplateDefaultsButton) {
        loadInvoiceTemplateDefaultsButton.addEventListener('click', populateInvoiceTemplateFormWithDefaults);
        await fetchInvoiceTemplateDefaults(); // Fetch on page load
    }

    if (statusSelectModal) {
        statusSelectModal.addEventListener('change', function() {
            if(paidDateContainer) paidDateContainer.style.display = this.value === 'paid' ? 'block' : 'none';
            const paidDateInput = document.getElementById('modal-invoice-paid-date');
            if (this.value === 'paid' && paidDateInput && !paidDateInput.value) {
                 paidDateInput.value = new Date().toISOString().split('T')[0]; // Default to today
            }
        });
    }
    if (cancelUpdateStatusModalButton && updateStatusModal) {
        cancelUpdateStatusModalButton.addEventListener('click', () => updateStatusModal.style.display = 'none');
    }
    if (updateStatusForm) {
        updateStatusForm.addEventListener('submit', handleUpdateInvoiceStatus);
    }

    await loadB2BUsersForInvoiceSelect();

    if (b2bUserSelect) {
        b2bUserSelect.addEventListener('change', async (event) => {
            currentSelectedB2BUserId = event.target.value;
            const selectedOption = event.target.options[event.target.selectedIndex];
            currentSelectedB2BUserName = selectedOption.dataset.userName || selectedOption.text;

            const userNameSpanInvoice = document.getElementById('selected-b2b-user-name-invoice');
            const userNameSpanList = document.getElementById('selected-b2b-user-name-list');
            const invoiceUserIdHidden = document.getElementById('invoice-user-id-hidden');

            if (currentSelectedB2BUserId) {
                if(userNameSpanInvoice) userNameSpanInvoice.textContent = currentSelectedB2BUserName;
                if(userNameSpanList) userNameSpanList.textContent = currentSelectedB2BUserName;
                if(invoiceUserIdHidden) invoiceUserIdHidden.value = currentSelectedB2BUserId;
                
                populateClientInfoForInvoice(selectedOption.dataset);

                if(createInvoiceFormSection) createInvoiceFormSection.style.display = 'block';
                if(userInvoicesListSection) userInvoicesListSection.style.display = 'block';
                await loadAdminInvoicesForUser(currentSelectedB2BUserId);
                resetCreateInvoiceForm();
            } else {
                if(createInvoiceFormSection) createInvoiceFormSection.style.display = 'none';
                if(userInvoicesListSection) userInvoicesListSection.style.display = 'none';
                if(userNameSpanInvoice) userNameSpanInvoice.textContent = '';
                if(userNameSpanList) userNameSpanList.textContent = '';
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
        ['create-invoice-discount', 'create-invoice-vat-rate'].forEach(id => {
            const input = document.getElementById(id);
            if (input) input.addEventListener('input', updateInvoiceTotalsPreview);
        });
    }
    updateInvoiceTotalsPreview(); // Initial call for default values
    if (window.applyI18nToElement) window.applyI18nToElement(document.body); // Apply i18n to the page
}

async function fetchInvoiceTemplateDefaults() {
    try {
        // Ensure makeAdminApiRequest is defined (expected from admin_api.js)
        if (!window.makeAdminApiRequest) throw new Error("adminApi.js not loaded or makeAdminApiRequest not defined.");
        const response = await makeAdminApiRequest('/settings/invoice-template', 'GET');
        if (response.success && response.settings) {
            invoiceTemplateDefaults = response.settings;
        } else {
            window.showGlobalAdminMessage(response.message || "Erreur lors du chargement des paramètres du modèle de facture.", "error");
        }
    } catch (error) {
        console.error("Error fetching invoice template defaults:", error);
        window.showGlobalAdminMessage(`Erreur serveur (paramètres modèle): ${error.message}`, "error");
    }
}

function populateInvoiceTemplateFormWithDefaults() {
    if (!invoiceTemplateDefaults) {
        window.showGlobalAdminMessage("Aucun paramètre par défaut à charger.", "warn");
        return;
    }
    document.getElementById('template-company-name').value = invoiceTemplateDefaults.company_name || '';
    document.getElementById('template-company-contact').value = invoiceTemplateDefaults.company_contact_info || '';
    document.getElementById('template-company-address').value = (invoiceTemplateDefaults.company_address_lines || []).join('\n');
    document.getElementById('template-company-siret').value = invoiceTemplateDefaults.company_siret || '';
    document.getElementById('template-company-vat').value = invoiceTemplateDefaults.company_vat_number || '';
    document.getElementById('template-footer-text').value = invoiceTemplateDefaults.invoice_footer_text || '';
    document.getElementById('template-bank-details').value = invoiceTemplateDefaults.bank_details || '';
    window.showGlobalAdminMessage("Infos de l'entreprise par défaut chargées dans le formulaire.", "info");
}

function populateClientInfoForInvoice(userData) {
    document.getElementById('create-client-company-name').value = userData.companyName || '';
    document.getElementById('create-client-contact-person').value = `${userData.prenom || ''} ${userData.nom || ''}`.trim();
    document.getElementById('create-client-address-lines').value = userData.addressLines || ''; // Assuming addressLines is in dataset
    document.getElementById('create-client-vat-number').value = userData.vatNumber || ''; // Assuming vatNumber is in dataset
}

async function loadB2BUsersForInvoiceSelect() {
    const selectElement = document.getElementById('select-b2b-user-for-invoice');
    if (!selectElement) return;
    selectElement.innerHTML = `<option value="">${window.translateToken ? translateToken('admin.invoices.loadingB2BUsers', 'Chargement...') : 'Chargement...'}</option>`;
    try {
        if (!window.makeAdminApiRequest) throw new Error("adminApi.js not loaded or makeAdminApiRequest not defined.");
        const response = await makeAdminApiRequest('/users?user_type=b2b&is_active=true', 'GET'); // Ensure API filters by is_active
        selectElement.innerHTML = `<option value="">-- ${window.translateToken ? translateToken('admin.invoices.selectB2BClientPlaceholder' ,'Sélectionner un client B2B') : 'Sélectionner un client B2B'} --</option>`;
        if (response.success && response.users) {
            response.users.forEach(user => {
                // Backend should ideally only return active B2B users if requested
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `${user.company_name || user.email} (${user.email})`;
                option.dataset.userName = user.company_name || user.email;
                option.dataset.companyName = user.company_name || '';
                option.dataset.nom = user.last_name || ''; // Assuming backend provides last_name, first_name
                option.dataset.prenom = user.first_name || '';
                option.dataset.addressLines = (user.address?.street && user.address?.city) ? `${user.address.street}\n${user.address.postal_code} ${user.address.city}\n${user.address.country}` : '';
                option.dataset.vatNumber = user.vat_number || '';
                selectElement.appendChild(option);
            });
        } else {
             selectElement.innerHTML = `<option value="">${window.translateToken ? translateToken('admin.invoices.errorLoadingB2BUsers', 'Erreur de chargement') : 'Erreur de chargement'}</option>`;
        }
    } catch (error) {
        console.error("Error loading B2B users:", error);
        selectElement.innerHTML = `<option value="">${window.translateToken ? translateToken('admin.invoices.serverErrorB2BUsers', 'Erreur serveur') : 'Erreur serveur'}</option>`;
        window.showGlobalAdminMessage(`Erreur chargement utilisateurs B2B: ${error.message}`, 'error');
    }
}

function addInvoiceLineItem() {
    const container = document.getElementById('invoice-line-items-container');
    if (!container) return;
    const itemIndex = container.children.length;
    const itemHtml = `
        <div class="grid grid-cols-12 gap-2 items-center invoice-line-item py-1">
            <div class="col-span-5">
                <input type="text" name="items[${itemIndex}][description]" class="form-input-admin text-sm" placeholder="${window.translateToken ? translateToken('admin.invoices.itemDescriptionPlaceholder', 'Description article') : 'Description article'}" required>
            </div>
            <div class="col-span-2">
                <input type="number" name="items[${itemIndex}][quantity]" class="form-input-admin text-sm" placeholder="${window.translateToken ? translateToken('admin.invoices.itemQtyPlaceholder', 'Qté') : 'Qté'}" required min="1" value="1">
            </div>
            <div class="col-span-2">
                <input type="number" name="items[${itemIndex}][unit_price_ht]" step="0.01" class="form-input-admin text-sm" placeholder="${window.translateToken ? translateToken('admin.invoices.itemUnitPricePlaceholder', 'Prix U. HT') : 'Prix U. HT'}" required min="0">
            </div>
            <div class="col-span-2">
                <input type="text" name="items[${itemIndex}][total_ht]" class="form-input-admin text-sm bg-gray-100" placeholder="${window.translateToken ? translateToken('admin.invoices.itemTotalHTPlaceholder', 'Total HT') : 'Total HT'}" readonly>
            </div>
            <div class="col-span-1 flex justify-center">
                <button type="button" class="btn-admin-danger remove-invoice-item-button" title="${window.translateToken ? translateToken('admin.invoices.removeItemTooltip', 'Supprimer article') : 'Supprimer article'}">&times;</button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', itemHtml);
    const newItemRow = container.lastElementChild;
    newItemRow.querySelector('input[name$="[quantity]"]').addEventListener('input', updateInvoiceTotalsPreview);
    newItemRow.querySelector('input[name$="[unit_price_ht]"]').addEventListener('input', updateInvoiceTotalsPreview);
    newItemRow.querySelector('.remove-invoice-item-button').addEventListener('click', function() {
        this.closest('.invoice-line-item').remove();
        reindexLineItems(); // Re-index before updating totals to ensure correct calculation
        updateInvoiceTotalsPreview();
    });
    updateInvoiceTotalsPreview();
}

function reindexLineItems() {
    const container = document.getElementById('invoice-line-items-container');
    if (!container) return;
    const items = container.querySelectorAll('.invoice-line-item');
    items.forEach((item, index) => {
        item.querySelectorAll('input, select, textarea').forEach(input => {
            if (input.name && input.name.startsWith('items[')) {
                input.name = input.name.replace(/items\[\d+\]/, `items[${index}]`);
            }
        });
    });
}

function updateInvoiceTotalsPreview() {
    let totalHtBeforeDiscount = 0;
    const lineItemsContainer = document.getElementById('invoice-line-items-container');
    if (!lineItemsContainer) return;
    const lineItems = lineItemsContainer.querySelectorAll('.invoice-line-item');
    
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

    const previewTotalHtBeforeDiscount = document.getElementById('preview-total-ht-before-discount');
    const createInvoiceDiscount = document.getElementById('create-invoice-discount');
    const createInvoiceVatRate = document.getElementById('create-invoice-vat-rate');
    const previewDiscountAmount = document.getElementById('preview-discount-amount');
    const previewTotalHtAfterDiscount = document.getElementById('preview-total-ht-after-discount');
    const previewVatAmount = document.getElementById('preview-vat-amount');
    const previewTotalTtc = document.getElementById('preview-total-ttc');

    if(previewTotalHtBeforeDiscount) previewTotalHtBeforeDiscount.textContent = totalHtBeforeDiscount.toFixed(2);

    const discountPercent = parseFloat(createInvoiceDiscount?.value) || 0;
    const vatRatePercent = parseFloat(createInvoiceVatRate?.value) || 0;

    const discountAmount = (totalHtBeforeDiscount * discountPercent) / 100;
    if(previewDiscountAmount) previewDiscountAmount.textContent = discountAmount.toFixed(2);

    const totalHtAfterDiscount = totalHtBeforeDiscount - discountAmount;
    if(previewTotalHtAfterDiscount) previewTotalHtAfterDiscount.textContent = totalHtAfterDiscount.toFixed(2);

    const vatAmount = (totalHtAfterDiscount * vatRatePercent) / 100;
    if(previewVatAmount) previewVatAmount.textContent = vatAmount.toFixed(2);

    const totalTtc = totalHtAfterDiscount + vatAmount;
    if(previewTotalTtc) previewTotalTtc.textContent = totalTtc.toFixed(2);
}

async function handleAdminCreateInvoice(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    window.showGlobalAdminMessage(window.translateToken ? translateToken('admin.invoices.generatingInvoiceMsg', "Génération de la facture en cours...") : "Génération de la facture en cours...", "info");
    const previewArea = document.getElementById('invoice-preview-area');
    const downloadLink = document.getElementById('generated-pdf-download-link');
    if(previewArea) previewArea.style.display = 'none'; 
    if(downloadLink) downloadLink.style.display = 'none';

    try {
        if (!window.makeAdminApiRequest) throw new Error("adminApi.js not loaded or makeAdminApiRequest not defined.");
        // makeAdminApiRequest needs to handle FormData correctly (not stringify, not set Content-Type)
        const result = await makeAdminApiRequest('/invoices/b2b', 'POST', formData, true); // true indicates FormData

        if (result.success) {
            window.showGlobalAdminMessage(result.message || (window.translateToken ? translateToken('admin.invoices.invoiceCreatedSuccess', "Facture créée avec succès!") : "Facture créée avec succès!"), "success");
            resetCreateInvoiceForm();
            if (currentSelectedB2BUserId) await loadAdminInvoicesForUser(currentSelectedB2BUserId);

            if (result.pdf_download_url && previewArea && downloadLink) {
                const pdfIframe = document.getElementById('pdf-preview-iframe');
                const fullPdfUrl = result.pdf_download_url.startsWith('http') ? result.pdf_download_url : `${(window.API_BASE_URL || '')}${result.pdf_download_url}`;

                downloadLink.href = fullPdfUrl;
                downloadLink.textContent = `${window.translateToken ? translateToken('admin.invoices.download', 'Télécharger') : 'Télécharger'} ${result.pdf_filename || 'Facture PDF'}`;
                downloadLink.style.display = 'inline-block';
                
                if(pdfIframe) pdfIframe.src = `https://docs.google.com/gview?url=${encodeURIComponent(fullPdfUrl)}&embedded=true`;
                previewArea.style.display = 'block';
            }
        } else {
            window.showGlobalAdminMessage(result.message || (window.translateToken ? translateToken('admin.invoices.invoiceCreationError', "Erreur lors de la création de la facture.") : "Erreur lors de la création de la facture."), "error");
        }
    } catch (error) {
        console.error("Error creating invoice:", error);
        window.showGlobalAdminMessage(`${window.translateToken ? translateToken('admin.invoices.serverError', 'Erreur serveur') : 'Erreur serveur'}: ${error.message}`, "error");
    }
}

function resetCreateInvoiceForm() {
    const form = document.getElementById('admin-create-invoice-form');
    if (form) form.reset();
    const lineItemsContainer = document.getElementById('invoice-line-items-container');
    if(lineItemsContainer) lineItemsContainer.innerHTML = '';
    addInvoiceLineItem(); // Add one default line item
    updateInvoiceTotalsPreview();
    
    const previewArea = document.getElementById('invoice-preview-area');
    const downloadLink = document.getElementById('generated-pdf-download-link');
    if(previewArea) previewArea.style.display = 'none';
    if(downloadLink) downloadLink.style.display = 'none';

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
    if (!tableBody) return;
    tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4">${window.translateToken ? translateToken('admin.invoices.loadingInvoices', 'Chargement des factures...') : 'Chargement des factures...'}</td></tr>`;
    try {
        if (!window.makeAdminApiRequest) throw new Error("adminApi.js not loaded or makeAdminApiRequest not defined.");
        const response = await makeAdminApiRequest(`/invoices/b2b/for-user/${userId}`, 'GET');
        if (response.success && response.invoices) {
            if (response.invoices.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4">${window.translateToken ? translateToken('admin.invoices.noInvoicesFound', 'Aucune facture trouvée pour ce client.') : 'Aucune facture trouvée pour ce client.'}</td></tr>`;
                return;
            }
            let rowsHtml = '';
            response.invoices.forEach(invoice => {
                const invoiceDate = invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString(window.currentLocale || 'fr-FR') : 'N/A';
                const paidDate = invoice.paid_date ? new Date(invoice.paid_date).toLocaleDateString(window.currentLocale || 'fr-FR') : 'N/A';
                const createdAt = invoice.created_at ? new Date(invoice.created_at).toLocaleDateString(window.currentLocale || 'fr-FR') : 'N/A';
                
                let downloadLink = '#';
                if (invoice.file_path) {
                    // Ensure API_BASE_URL is available, typically from config.js
                    const baseUrl = window.API_BASE_URL || '';
                    // Assuming the download URL is relative to API_BASE_URL or a full URL is provided
                    downloadLink = invoice.file_path.startsWith('http') ? invoice.file_path : `${baseUrl}${invoice.file_path.startsWith('/') ? '' : '/'}${invoice.file_path}`;
                }

                rowsHtml += `
                    <tr class="border-b hover:bg-gray-50">
                        <td class="admin-table td">${invoice.invoice_number}</td>
                        <td class="admin-table td">${invoiceDate}</td>
                        <td class="admin-table td">${parseFloat(invoice.total_amount_ttc || 0).toFixed(2)} €</td>
                        <td class="admin-table td">
                            <span class="status-badge status-${(invoice.status || 'pending').toLowerCase()}">${invoice.status || 'pending'}</span>
                        </td>
                        <td class="admin-table td">${paidDate}</td>
                        <td class="admin-table td">
                            ${invoice.file_path ? `<a href="${downloadLink}" target="_blank" class="text-indigo-600 hover:text-indigo-800 hover:underline">${invoice.invoice_number}.pdf</a>` : 'N/A'}
                        </td>
                        <td class="admin-table td">${createdAt}</td>
                        <td class="admin-table td text-right">
                            <button class="text-indigo-600 hover:text-indigo-900 edit-invoice-status-button p-1" data-invoice-id="${invoice.invoice_id}" data-invoice-number="${invoice.invoice_number}" data-current-status="${invoice.status || 'pending'}" data-paid-date="${invoice.paid_date || ''}" title="${window.translateToken ? translateToken('admin.invoices.editStatusTooltip', 'Modifier Statut') : 'Modifier Statut'}">
                                <i class="fas fa-edit"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
            tableBody.innerHTML = rowsHtml;
            attachStatusEditListeners();
        } else {
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4">${response.message || (window.translateToken ? translateToken('admin.invoices.errorLoadingInvoices', 'Erreur de chargement des factures.') : 'Erreur de chargement des factures.')}</td></tr>`;
        }
    } catch (error) {
        console.error("Error loading invoices for user:", error);
        tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4">${window.translateToken ? translateToken('admin.invoices.serverErrorLoadingInvoices', 'Erreur serveur') : 'Erreur serveur'}: ${error.message}</td></tr>`;
    }
}

function attachStatusEditListeners() {
    document.querySelectorAll('.edit-invoice-status-button').forEach(button => {
        button.addEventListener('click', function() {
            const invoiceId = this.dataset.invoiceId;
            const invoiceNumber = this.dataset.invoiceNumber;
            const currentStatus = this.dataset.currentStatus;
            const paidDate = this.dataset.paidDate; // This will be YYYY-MM-DD from backend if set

            const modalInvoiceIdInput = document.getElementById('modal-invoice-id-status');
            const modalInvoiceNumberSpan = document.getElementById('modal-invoice-number-status');
            const statusSelect = document.getElementById('modal-select-invoice-status');
            const paidDateInput = document.getElementById('modal-invoice-paid-date');
            const paidDateContainer = document.getElementById('modal-paid-date-container');
            const updateModal = document.getElementById('update-invoice-status-modal');


            if(modalInvoiceIdInput) modalInvoiceIdInput.value = invoiceId;
            if(modalInvoiceNumberSpan) modalInvoiceNumberSpan.textContent = invoiceNumber;
            if(statusSelect) statusSelect.value = currentStatus;
            
            if (paidDateContainer && paidDateInput) {
                if (currentStatus === 'paid') {
                    paidDateInput.value = paidDate ? paidDate.split('T')[0] : new Date().toISOString().split('T')[0]; // Ensure correct format
                    paidDateContainer.style.display = 'block';
                } else {
                    paidDateInput.value = '';
                    paidDateContainer.style.display = 'none';
                }
            }
            if(updateModal) updateModal.style.display = 'flex';
        });
    });
}

async function handleUpdateInvoiceStatus(event) {
    event.preventDefault();
    const form = event.target;
    const invoiceId = form.querySelector('#modal-invoice-id-status').value;
    const newStatus = form.querySelector('#modal-select-invoice-status').value;
    let paidDate = form.querySelector('#modal-invoice-paid-date').value;
    const updateModal = document.getElementById('update-invoice-status-modal');


    if (newStatus !== 'paid') {
        paidDate = null; 
    } else if (newStatus === 'paid' && !paidDate) {
        paidDate = new Date().toISOString().split('T')[0]; // Default to today if paid and no date
    }

    const payload = { status: newStatus };
    if (paidDate) { // Only include paid_date if it's relevant and has a value
        payload.paid_date = paidDate;
    }

    try {
        if (!window.makeAdminApiRequest) throw new Error("adminApi.js not loaded or makeAdminApiRequest not defined.");
        const response = await makeAdminApiRequest(`/invoices/b2b/${invoiceId}/status`, 'PUT', payload);
        if (response.success) {
            window.showGlobalAdminMessage(response.message || (window.translateToken ? translateToken('admin.invoices.statusUpdateSuccess', "Statut de la facture mis à jour.") : "Statut de la facture mis à jour."), "success");
            if(updateModal) updateModal.style.display = 'none';
            if (currentSelectedB2BUserId) {
                await loadAdminInvoicesForUser(currentSelectedB2BUserId);
            }
        } else {
            window.showGlobalAdminMessage(response.message || (window.translateToken ? translateToken('admin.invoices.statusUpdateError', "Erreur lors de la mise à jour du statut.") : "Erreur lors de la mise à jour du statut."), "error");
        }
    } catch (error) {
        console.error("Error updating invoice status:", error);
        window.showGlobalAdminMessage(`${window.translateToken ? translateToken('admin.invoices.serverError', 'Erreur serveur') : 'Erreur serveur'}: ${error.message}`, "error");
    }
}

// Make the initialization function globally accessible if admin_main.js is to call it.
// Otherwise, call it directly on DOMContentLoaded.
if (typeof window.initializeAdminManageInvoicesPage === 'undefined') {
    window.initializeAdminManageInvoicesPage = initializeAdminManageInvoicesPage;
}

// Self-initialize if not called by admin_main.js
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAdminManageInvoicesPage);
} else {
    // DOMContentLoaded has already fired
    initializeAdminManageInvoicesPage();
}
