// website/admin/js/admin_categories.js
document.addEventListener('DOMContentLoaded', () => {
    const categoriesTableBody = document.getElementById('categoriesTableBody');
    const addCategoryBtn = document.getElementById('addCategoryBtn');
    const categoryModal = document.getElementById('categoryModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const categoryForm = document.getElementById('categoryForm');
    const modalTitle = document.getElementById('modalTitle');
    const categoryIdField = document.getElementById('categoryId');
    const formError = document.getElementById('formError');
    const formImagePreview = document.getElementById('formImagePreview');
    const imageUrlInput = document.getElementById('image_url');

    const deleteConfirmModal = document.getElementById('deleteConfirmModal');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const categoryNameToDelete = document.getElementById('categoryNameToDelete');
    const deleteError = document.getElementById('deleteError');
    
    const categoriesLoading = document.getElementById('categories-loading');
    const categoriesError = document.getElementById('categories-error');
    const noCategoriesMessage = document.getElementById('no-categories-message');

    let currentEditingCategoryId = null;
    let categoryToDeleteId = null;

    const API_BASE_URL = '/admin/api'; // Make sure this matches your Flask app's base URL for admin API

    // Toast notification elements
    const toast = document.getElementById('toast-notification');
    const toastMessage = document.getElementById('toast-message');

    function showToast(message, isError = false) {
        toastMessage.textContent = message;
        toast.classList.remove('hidden', 'bg-green-500', 'bg-red-500');
        if (isError) {
            toast.classList.add('bg-red-500');
        } else {
            toast.classList.add('bg-green-500');
        }
        toast.classList.add('opacity-100');
        setTimeout(() => {
            toast.classList.add('opacity-0');
            setTimeout(()_ => toast.classList.add('hidden'), 300); // wait for fade out
        }, 3000);
    }


    // --- Modal Handling ---
    function openModal(isEdit = false, category = null) {
        formError.textContent = '';
        formError.classList.add('hidden');
        categoryForm.reset();
        formImagePreview.classList.add('hidden');
        formImagePreview.src = '#';

        if (isEdit && category) {
            modalTitle.textContent = 'Modifier la Catégorie';
            categoryIdField.value = category.id;
            document.getElementById('name_fr').value = category.name_fr || '';
            document.getElementById('name_en').value = category.name_en || '';
            document.getElementById('description_fr').value = category.description_fr || '';
            document.getElementById('description_en').value = category.description_en || '';
            document.getElementById('slug').value = category.slug || '';
            imageUrlInput.value = category.image_url || '';
            if (category.image_url) {
                formImagePreview.src = category.image_url;
                formImagePreview.classList.remove('hidden');
            }
            currentEditingCategoryId = category.id;
        } else {
            modalTitle.textContent = 'Ajouter une Catégorie';
            categoryIdField.value = '';
            currentEditingCategoryId = null;
        }
        categoryModal.classList.add('active');
    }

    function closeModal() {
        categoryModal.classList.remove('active');
        categoryForm.reset();
        formImagePreview.classList.add('hidden');
        formImagePreview.src = '#';
    }

    function openDeleteModal(categoryId, categoryName) {
        deleteError.textContent = '';
        deleteError.classList.add('hidden');
        categoryNameToDelete.textContent = categoryName;
        categoryToDeleteId = categoryId;
        deleteConfirmModal.classList.add('active');
    }

    function closeDeleteModal() {
        deleteConfirmModal.classList.remove('active');
        categoryToDeleteId = null;
    }

    addCategoryBtn.addEventListener('click', () => openModal());
    closeModalBtn.addEventListener('click', closeModal);
    cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    
    // Close modal if backdrop is clicked
    categoryModal.addEventListener('click', (event) => {
        if (event.target === categoryModal) {
            closeModal();
        }
    });
    deleteConfirmModal.addEventListener('click', (event) => {
        if (event.target === deleteConfirmModal) {
            closeDeleteModal();
        }
    });


    imageUrlInput.addEventListener('input', (event) => {
        const url = event.target.value;
        if (url) {
            formImagePreview.src = url;
            formImagePreview.classList.remove('hidden');
        } else {
            formImagePreview.classList.add('hidden');
            formImagePreview.src = '#';
        }
    });
    formImagePreview.onerror = () => {
        formImagePreview.classList.add('hidden');
        // Optionally show a placeholder or error for bad image URLs
    };


    // --- API Calls ---
    async function fetchCategories() {
        categoriesLoading.style.display = 'block';
        categoriesError.classList.add('hidden');
        noCategoriesMessage.classList.add('hidden');
        categoriesTableBody.innerHTML = ''; // Clear existing rows

        try {
            // Using per_page=0 to get all categories, as pagination for categories is not implemented yet on frontend
            const response = await adminApi.get('/categories?per_page=0'); 
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
                throw new Error(`Erreur ${response.status}: ${errorData.error || errorData.detail}`);
            }
            const data = await response.json();
            categoriesLoading.style.display = 'none';
            if (data.categories && data.categories.length > 0) {
                renderCategories(data.categories);
            } else {
                noCategoriesMessage.classList.remove('hidden');
            }
            // Implement pagination display if using it
        } catch (error) {
            console.error('Erreur lors de la récupération des catégories:', error);
            categoriesLoading.style.display = 'none';
            categoriesError.textContent = `Impossible de charger les catégories: ${error.message}`;
            categoriesError.classList.remove('hidden');
            showToast(`Erreur: ${error.message}`, true);
        }
    }

    async function saveCategory(event) {
        event.preventDefault();
        formError.textContent = '';
        formError.classList.add('hidden');

        const formData = new FormData(categoryForm);
        const categoryData = {
            name_fr: formData.get('name_fr'),
            name_en: formData.get('name_en'),
            description_fr: formData.get('description_fr'),
            description_en: formData.get('description_en'),
            slug: formData.get('slug') || null, // Send null if empty, backend will generate
            image_url: formData.get('image_url')
        };

        const categoryId = formData.get('categoryId');
        const method = categoryId ? 'PUT' : 'POST';
        const url = categoryId ? `/categories/${categoryId}` : '/categories';

        try {
            const response = await adminApi.request(url, method, categoryData);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
                throw new Error(`Erreur ${response.status}: ${errorData.error || errorData.detail}`);
            }
            const result = await response.json();
            showToast(result.message || (categoryId ? 'Catégorie mise à jour avec succès!' : 'Catégorie créée avec succès!'));
            closeModal();
            fetchCategories(); // Refresh the list
        } catch (error) {
            console.error('Erreur lors de l_enregistrement de la catégorie:', error);
            formError.textContent = error.message;
            formError.classList.remove('hidden');
            showToast(`Erreur: ${error.message}`, true);
        }
    }

    async function deleteCategory() {
        if (!categoryToDeleteId) return;
        deleteError.textContent = '';
        deleteError.classList.add('hidden');

        try {
            const response = await adminApi.delete(`/categories/${categoryToDeleteId}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
                throw new Error(`Erreur ${response.status}: ${errorData.error || errorData.detail}`);
            }
            const result = await response.json();
            showToast(result.message || 'Catégorie supprimée avec succès!');
            closeDeleteModal();
            fetchCategories(); // Refresh the list
        } catch (error) {
            console.error('Erreur lors de la suppression de la catégorie:', error);
            deleteError.textContent = error.message;
            deleteError.classList.remove('hidden');
            showToast(`Erreur: ${error.message}`, true);
        }
    }

    // --- Rendering ---
    function renderCategories(categories) {
        categoriesTableBody.innerHTML = ''; // Clear previous entries
        if (!categories || categories.length === 0) {
            noCategoriesMessage.classList.remove('hidden');
            return;
        }
        noCategoriesMessage.classList.add('hidden');

        categories.forEach(category => {
            const row = categoriesTableBody.insertRow();
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${category.id}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    ${category.image_url ? `<img src="${category.image_url}" alt="${category.name_fr || 'Category Image'}" class="image-preview" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"> <span style="display:none;">N/A</span>` : '<span>N/A</span>'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${category.name_fr || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${category.name_en || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${category.slug || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <a href="admin_manage_products.html?category_id=${category.id}" class="text-blue-600 hover:text-blue-800">Voir produits</a>
                    </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button class="edit-button" data-id="${category.id}"><i class="fas fa-edit"></i> Modifier</button>
                    <button class="delete-button ml-2" data-id="${category.id}" data-name="${category.name_fr || 'cette catégorie'}"><i class="fas fa-trash"></i> Supprimer</button>
                </td>
            `;
            // Add event listeners for edit and delete buttons
            row.querySelector('.edit-button').addEventListener('click', () => openModal(true, category));
            row.querySelector('.delete-button').addEventListener('click', (e) => {
                const id = e.currentTarget.dataset.id;
                const name = e.currentTarget.dataset.name;
                openDeleteModal(id, name);
            });
        });
    }

    // --- Event Listeners ---
    categoryForm.addEventListener('submit', saveCategory);
    confirmDeleteBtn.addEventListener('click', deleteCategory);

    // Initial fetch
    if (adminApi.getAuthToken()) { // Ensure token is available before fetching
        fetchCategories();
    } else {
        // Handle case where token is not available, perhaps redirect to login
        // This should ideally be handled by admin_main.js global check
        console.warn("Token d'authentification admin non trouvé. Le chargement des catégories est annulé.");
        categoriesLoading.style.display = 'none';
        categoriesError.textContent = "Vous n'êtes pas authentifié. Veuillez vous reconnecter.";
        categoriesError.classList.remove('hidden');
    }
});
