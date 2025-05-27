// This file (website/admin/js/admin_categories.js) will contain the JavaScript logic for managing categories.
// Assuming the content was previously in 'admin/admin_manage_categories.html'

document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Categories JS Loaded");

    const categoryForm = document.getElementById('categoryForm');
    const categoriesTableBody = document.getElementById('categoriesTableBody');
    let editingCategoryId = null;

    // --- Modal for Confirmations/Alerts (Re-use or ensure it's globally available if in admin_main.js) ---
    // For simplicity, defining it here. If it's in admin_main.js, you wouldn't redefine.
    let alertModal, alertModalTitle, alertModalMessage, alertModalCloseButton, alertModalActions;

    function setupModal() {
        if (document.getElementById('alertModal')) {
            alertModal = document.getElementById('alertModal');
            alertModalTitle = document.getElementById('alertModalTitle');
            alertModalMessage = document.getElementById('alertModalMessage');
            alertModalCloseButton = document.getElementById('alertModalCloseButton');
            alertModalActions = document.getElementById('alertModalActions');
        } else {
            // Create modal if not present (e.g. if admin_main.js didn't load it or this script runs first)
            const modalHTML = `
                <div class="relative p-5 border w-full max-w-md m-auto flex-col flex rounded-lg shadow-lg bg-white">
                    <div class="flex justify-between items-center">
                        <h3 class="text-lg font-medium text-gray-900" id="alertModalTitle">Alert</h3>
                        <button type="button" class="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm p-1.5 ml-auto inline-flex items-center" id="alertModalCloseButton">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
                        </button>
                    </div>
                    <div class="p-2 mt-2 text-center">
                        <p class="text-sm text-gray-500" id="alertModalMessage">Modal message goes here.</p>
                    </div>
                    <div class="mt-3 flex justify-end space-x-2" id="alertModalActions">
                        <button id="alertModalOkButton" class="px-4 py-2 bg-indigo-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">OK</button>
                    </div>
                </div>`;
            const tempModal = document.createElement('div');
            tempModal.id = 'alertModal';
            tempModal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex items-center justify-center hidden z-50';
            tempModal.innerHTML = modalHTML;
            document.body.appendChild(tempModal);
            
            alertModal = tempModal;
            alertModalTitle = document.getElementById('alertModalTitle');
            alertModalMessage = document.getElementById('alertModalMessage');
            alertModalCloseButton = document.getElementById('alertModalCloseButton');
            alertModalActions = document.getElementById('alertModalActions');
        }
    }
    setupModal();


    function showAlert(message, title = "Alert") {
        if (!alertModal) setupModal(); // Ensure modal is initialized
        alertModalTitle.textContent = title;
        alertModalMessage.textContent = message;
        alertModalActions.innerHTML = `<button id="alertModalOkButton" class="px-4 py-2 bg-indigo-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">OK</button>`;
        alertModal.classList.remove('hidden');
        document.getElementById('alertModalOkButton').onclick = () => alertModal.classList.add('hidden');
        alertModalCloseButton.onclick = () => alertModal.classList.add('hidden');
    }

    function showConfirm(message, title = "Confirm", callback) {
        if (!alertModal) setupModal();
        alertModalTitle.textContent = title;
        alertModalMessage.textContent = message;
        alertModalActions.innerHTML = `
            <button id="confirmModalCancelButton" class="px-4 py-2 bg-gray-200 text-gray-800 text-base font-medium rounded-md shadow-sm hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500">Cancel</button>
            <button id="confirmModalConfirmButton" class="px-4 py-2 bg-red-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500">Confirm</button>
        `;
        alertModal.classList.remove('hidden');

        const confirmBtn = document.getElementById('confirmModalConfirmButton');
        const cancelBtn = document.getElementById('confirmModalCancelButton');

        confirmBtn.onclick = () => {
            alertModal.classList.add('hidden');
            callback(true);
        };
        cancelBtn.onclick = () => {
            alertModal.classList.add('hidden');
            callback(false);
        };
        alertModalCloseButton.onclick = () => {
            alertModal.classList.add('hidden');
            callback(false);
        };
    }
    // --- End Modal ---

    // Load categories and populate table
    async function loadCategories() {
        try {
            const categories = await adminApi.getCategories(); // Assumes adminApi.getCategories is defined
            if (!categoriesTableBody) {
                console.warn("Categories table body not found on this page.");
                return;
            }
            categoriesTableBody.innerHTML = ''; // Clear existing categories
            if (categories.length === 0) {
                categoriesTableBody.innerHTML = `<tr><td colspan="3" class="text-center py-4">No categories found.</td></tr>`;
                return;
            }
            categories.forEach(category => {
                const row = categoriesTableBody.insertRow();
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${category.id}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${category.name}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-indigo-600 hover:text-indigo-900 edit-cat-btn" data-id="${category.id}" data-name="${category.name}">Edit</button>
                        <button class="text-red-600 hover:text-red-900 delete-cat-btn ml-4" data-id="${category.id}">Delete</button>
                    </td>
                `;
            });
            attachCategoryActionListeners();
        } catch (error) {
            console.error("Failed to load categories:", error);
             if (categoriesTableBody) {
                categoriesTableBody.innerHTML = `<tr><td colspan="3" class="text-center py-4 text-red-500">Error loading categories.</td></tr>`;
            }
            showAlert("Could not load categories. Please try again.", "Error");
        }
    }

    // Handle category form submission (Add/Edit)
    if (categoryForm) {
        categoryForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const categoryNameInput = document.getElementById('categoryName');
            const name = categoryNameInput.value.trim();

            if (!name) {
                showAlert("Category name cannot be empty.", "Validation Error");
                return;
            }

            const categoryData = { name };

            try {
                if (editingCategoryId) {
                    await adminApi.updateCategory(editingCategoryId, categoryData); // Assumes adminApi.updateCategory
                    showAlert("Category updated successfully!", "Success");
                } else {
                    await adminApi.addCategory(categoryData); // Assumes adminApi.addCategory
                    showAlert("Category added successfully!", "Success");
                }
                categoryForm.reset();
                editingCategoryId = null;
                document.getElementById('formCategoryTitle').textContent = 'Add New Category';
                document.getElementById('submitCategoryButton').textContent = 'Add Category';
                loadCategories(); // Refresh category list
            } catch (error) {
                console.error("Failed to save category:", error);
                showAlert(`Error saving category: ${error.message || 'Unknown error.'}`, "Error");
            }
        });
    }

    // Attach event listeners for edit and delete buttons
    function attachCategoryActionListeners() {
        document.querySelectorAll('.edit-cat-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const categoryId = event.target.dataset.id;
                const categoryName = event.target.dataset.name;
                populateCategoryFormForEdit(categoryId, categoryName);
            });
        });

        document.querySelectorAll('.delete-cat-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const categoryId = event.target.dataset.id;
                showConfirm('Are you sure you want to delete this category?', 'Delete Category', async (confirmed) => {
                    if (confirmed) {
                        try {
                            await adminApi.deleteCategory(categoryId); // Assumes adminApi.deleteCategory
                            showAlert("Category deleted successfully!", "Success");
                            loadCategories(); // Refresh category list
                        } catch (error) {
                            console.error("Failed to delete category:", error);
                            showAlert(`Error deleting category: ${error.message || 'Unknown error.'}`, "Error");
                        }
                    }
                });
            });
        });
    }

    // Populate form for editing a category
    function populateCategoryFormForEdit(categoryId, categoryName) {
        if (categoryForm) {
            document.getElementById('categoryName').value = categoryName;
            editingCategoryId = categoryId;
            document.getElementById('formCategoryTitle').textContent = 'Edit Category';
            document.getElementById('submitCategoryButton').textContent = 'Update Category';
            categoryForm.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Initial load
    if (categoriesTableBody) {
        loadCategories();
    }
});
