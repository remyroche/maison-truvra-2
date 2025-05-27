// File: website/admin/js/admin_categories.js
document.addEventListener('DOMContentLoaded', () => {
    if (typeof ensureAdminAuthenticated === 'function' && !ensureAdminAuthenticated()) { return; }

    const addCategoryBtn = document.getElementById('addCategoryBtn');
    const categoryModal = document.getElementById('categoryModal');
    const closeModalBtn = categoryModal ? categoryModal.querySelector('#closeModalBtn') : null;
    const cancelModalBtn = categoryModal ? categoryModal.querySelector('#cancelModalBtn') : null;
    const categoryForm = document.getElementById('categoryForm');
    const modalTitle = categoryModal ? categoryModal.querySelector('#modalTitle') : null;
    const categoriesTableBody = document.getElementById('categoriesTableBody');
    const saveCategoryBtn = document.getElementById('saveCategoryBtn');
    const formMessageContainer = categoryModal ? categoryModal.querySelector('#formMessage') : null;

    let editingCategoryId = null;

    const openModal = (isEdit = false, category = null) => {
        if (!categoryModal || !categoryForm || !modalTitle || !saveCategoryBtn) return;
        clearFormMessage();
        categoryForm.reset();
        saveCategoryBtn.disabled = false;
        saveCategoryBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save Category';

        if (isEdit && category) {
            modalTitle.textContent = 'Edit Category';
            editingCategoryId = category.id;
            document.getElementById('categoryId').value = category.id;
            document.getElementById('categoryName').value = category.name;
            document.getElementById('categoryDescription').value = category.description || '';
        } else {
            modalTitle.textContent = 'Add New Category';
            editingCategoryId = null;
            if(document.getElementById('categoryId')) document.getElementById('categoryId').value = '';
        }
        categoryModal.classList.remove('opacity-0', 'pointer-events-none');
        categoryModal.classList.add('opacity-100');
        document.body.classList.add('modal-active');
    };

    const closeModal = () => {
        if (!categoryModal) return;
        categoryModal.classList.add('opacity-0');
        categoryModal.classList.remove('opacity-100');
        setTimeout(() => {
            categoryModal.classList.add('pointer-events-none');
            document.body.classList.remove('modal-active');
        }, 250);
    };

    if (addCategoryBtn) addCategoryBtn.addEventListener('click', () => openModal());
    if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeModal);
    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && categoryModal && !categoryModal.classList.contains('pointer-events-none')) {
            closeModal();
        }
    });


    const renderCategories = (categories) => {
        if (!categoriesTableBody) return;
        categoriesTableBody.innerHTML = '';
        if (!categories || categories.length === 0) {
            categoriesTableBody.innerHTML = `<tr><td colspan="5" class="px-6 py-4 text-center text-sm text-gray-500">No categories found.</td></tr>`;
            return;
        }
        categories.forEach(category => {
            const row = categoriesTableBody.insertRow();
            row.className = 'hover:bg-gray-50 transition-colors';
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${category.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${category.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 max-w-xs truncate" title="${category.description || ''}">${category.description || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${category.product_count === undefined ? 'N/A' : category.product_count}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button class="edit-btn text-indigo-600 hover:text-indigo-800 p-1 rounded hover:bg-indigo-100" data-id="${category.id}" title="Edit ${category.name}"><i class="fas fa-pencil-alt fa-fw"></i></button>
                    <button class="delete-btn text-red-600 hover:text-red-800 p-1 rounded hover:bg-red-100" data-id="${category.id}" title="Delete ${category.name}"><i class="fas fa-trash-alt fa-fw"></i></button>
                </td>
            `;
        });

        document.querySelectorAll('.edit-btn').forEach(button => button.addEventListener('click', handleEditCategory));
        document.querySelectorAll('.delete-btn').forEach(button => button.addEventListener('click', handleDeleteCategory));
    };

    const fetchAndDisplayCategories = async () => {
        if (!categoriesTableBody) return;
        categoriesTableBody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i>Loading categories...</td></tr>`;
        try {
            // Assuming API returns an array for categories or an object { categories: [] }
            const response = await adminApi.getCategories(undefined, 1, 200); // Fetch all for now
            let categoryList = [];
            if (Array.isArray(response)) {
                categoryList = response;
            } else if (response && response.categories && Array.isArray(response.categories)) {
                categoryList = response.categories;
            } else if (response && response.data && Array.isArray(response.data)) { // Adapt to various possible API responses
                categoryList = response.data;
            }


            renderCategories(categoryList);
            if (categoryList.length === 0) {
                categoriesTableBody.innerHTML = `<tr><td colspan="5" class="px-6 py-4 text-center text-sm text-gray-500">No categories created yet. Click 'Add New Category'.</td></tr>`;
            }

        } catch (error) {
            console.error('Failed to fetch categories:', error);
            categoriesTableBody.innerHTML = `<tr><td colspan="5" class="px-6 py-4 text-center text-sm text-red-500">Error loading categories: ${error.message}</td></tr>`;
            if (typeof showGlobalUIMessage === 'function') showGlobalUIMessage(`Error fetching categories: ${error.message}`, 'error');
        }
    };

    if (categoryForm) {
        categoryForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (!saveCategoryBtn) return;

            const categoryData = {
                name: document.getElementById('categoryName').value,
                description: document.getElementById('categoryDescription').value,
            };

            // Basic client-side validation
            if (!categoryData.name.trim()) {
                showFormMessage('Category name is required.', 'error');
                document.getElementById('categoryName').focus();
                return;
            }

            saveCategoryBtn.disabled = true;
            saveCategoryBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
            clearFormMessage();

            try {
                let response;
                if (editingCategoryId) {
                    response = await adminApi.updateCategory(editingCategoryId, categoryData);
                } else {
                    response = await adminApi.addCategory(categoryData);
                }

                if (response && (response.id || (response.message && response.message.toLowerCase().includes('success')))) {
                    if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(response.message || (editingCategoryId ? 'Category updated successfully!' : 'Category added successfully!'), 'success');
                    fetchAndDisplayCategories();
                    closeModal();
                } else {
                     // Handle specific validation errors from backend if provided
                    if (response && response.errors) {
                        let errorMessages = Object.values(response.errors).join('<br>');
                        showFormMessage(`Validation failed:<br>${errorMessages}`, 'error');
                    } else {
                        throw new Error(response.error || 'Failed to save category.');
                    }
                }
            } catch (error) {
                console.error('Failed to save category:', error);
                showFormMessage(`Error: ${error.message}`, 'error');
            } finally {
                saveCategoryBtn.disabled = false;
                saveCategoryBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save Category';
            }
        });
    }

    const handleEditCategory = async (event) => {
        const button = event.currentTarget;
        const categoryId = button.dataset.id;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        button.disabled = true;

        try {
            const category = await adminApi.getCategoryById(categoryId);
            if (category) {
                openModal(true, category);
            } else {
                 if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage('Could not fetch category details to edit.', 'error');
            }
        } catch (error) {
            console.error('Error fetching category for edit:', error);
             if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(`Error fetching category: ${error.message}`, 'error');
        } finally {
            button.innerHTML = '<i class="fas fa-pencil-alt fa-fw"></i>';
            button.disabled = false;
        }
    };

    const handleDeleteCategory = (event) => {
        const button = event.currentTarget;
        const categoryId = button.dataset.id;
        const categoryName = button.closest('tr').querySelector('td:nth-child(2)').textContent || `Category ID ${categoryId}`;

        if (typeof showConfirmModal === 'function') {
            showConfirmModal(
                `Delete Category: ${categoryName}?`,
                `Are you sure you want to delete "<strong>${categoryName}</strong>"? This might affect products associated with it. This action cannot be undone.`,
                async () => { // onConfirm callback
                    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    button.disabled = true;
                    try {
                        const response = await adminApi.deleteCategory(categoryId);
                        if (response && response.message && response.message.toLowerCase().includes('success')) {
                            if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(response.message, 'success');
                            fetchAndDisplayCategories();
                        } else {
                            throw new Error(response.error || 'Failed to delete category.');
                        }
                    } catch (error) {
                        console.error('Failed to delete category:', error);
                        if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(`Error deleting category: ${error.message}`, 'error');
                        button.innerHTML = '<i class="fas fa-trash-alt fa-fw"></i>'; // Reset icon on error
                        button.disabled = false;
                    }
                }
            );
        } else {
            if(confirm(`Are you sure you want to delete "${categoryName}"?`)) {
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                button.disabled = true;
                adminApi.deleteCategory(categoryId)
                    .then((response) => {
                        alert(response.message || "Category deleted.");
                        fetchAndDisplayCategories();
                    })
                    .catch(err => {
                        alert(`Error: ${err.message}`);
                        button.innerHTML = '<i class="fas fa-trash-alt fa-fw"></i>';
                        button.disabled = false;
                    });
            }
        }
    };

    const showFormMessage = (message, type = 'info') => {
        if (!formMessageContainer) return;
        formMessageContainer.innerHTML = message; // Use innerHTML for potential <br>
        formMessageContainer.className = 'text-sm p-3 rounded-md mt-2 ';
        if (type === 'success') formMessageContainer.classList.add('text-green-700', 'bg-green-100');
        else if (type === 'error') formMessageContainer.classList.add('text-red-700', 'bg-red-100');
        else formMessageContainer.classList.add('text-blue-700', 'bg-blue-100');
        formMessageContainer.classList.remove('hidden');
    };
    const clearFormMessage = () => {
        if (!formMessageContainer) return;
        formMessageContainer.textContent = '';
        formMessageContainer.classList.add('hidden');
    };

    const initializePage = async () => {
        await fetchAndDisplayCategories();
    };

    initializePage();
});
