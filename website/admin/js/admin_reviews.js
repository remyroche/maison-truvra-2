// This file (website/admin/js/admin_reviews.js) contains the JavaScript logic for managing product reviews.

// Ensure adminApi is available (loaded via admin_api.js)
// Ensure i18n functions are available (loaded via i18n.js and initialized by admin_main.js)
// Ensure showGlobalAdminMessage and other UI functions are available (from admin_ui.js or admin_main.js)

let currentPage = 1;
const reviewsPerPage = 10; // Or make this configurable

async function initAdminReviewsPage() {
    console.log("Initializing Admin Reviews Page...");

    const reviewsTableBody = document.getElementById('reviews-table-body');
    const filterStatusSelect = document.getElementById('filter-status');
    const filterProductIdInput = document.getElementById('filter-product-id');
    const applyFiltersBtn = document.getElementById('apply-filters-btn');
    const paginationControls = document.getElementById('pagination-controls');

    const adminCommentModal = document.getElementById('admin-comment-modal');
    const adminCommentTextarea = document.getElementById('admin-comment-textarea');
    const modalConfirmActionBtn = document.getElementById('modal-confirm-action-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const closeModalAdminCommentBtn = document.getElementById('close-admin-comment-modal-btn');
    
    let currentReviewAction = null; // { reviewId, actionType ('approve'/'reject'/'comment'), newStatus }


    // --- Alert/Confirm Modal (Ensure this is available from admin_main.js or admin_ui.js) ---
    if (!window.showAlert || !window.showConfirm) {
        console.warn("Global showAlert/showConfirm not found. Using basic stubs for admin_reviews.js.");
        window.showAlert = (message, title) => console.log(`REVIEW ALERT (${title}): ${message}`);
        window.showConfirm = (message, title, callback) => {
            const confirmed = confirm(`${title}: ${message}`);
            callback(confirmed);
        };
    }
     // --- Global Message (Ensure showGlobalAdminMessage is available from admin_ui.js or admin_main.js) ---
    if (!window.showGlobalAdminMessage) {
        console.warn("showGlobalAdminMessage function not found. Messages will be logged to console.");
        window.showGlobalAdminMessage = (message, type = 'info') => {
            console.log(`Global Admin Message (${type}): ${message}`);
        };
    }


    // Format date (simple version)
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            return new Date(dateString).toLocaleDateString(getCurrentLocale(), { // Use i18n locale
                day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
            });
        } catch (e) { return dateString; }
    }
    
    function getCurrentLocale() {
        return window.currentLocale || document.documentElement.lang || 'en';
    }

    // Render reviews in the table
    function renderReviews(reviews) {
        reviewsTableBody.innerHTML = ''; // Clear previous reviews or loading row
        if (!reviews || reviews.length === 0) {
            reviewsTableBody.innerHTML = `<tr><td colspan="8" class="text-center py-10" data-i18n="admin.reviews.noReviewsFound">No reviews found matching your criteria.</td></tr>`;
            if(window.translateSingleElement) translateSingleElement(reviewsTableBody.querySelector('td'));
            return;
        }

        reviews.forEach(review => {
            const row = reviewsTableBody.insertRow();
            row.innerHTML = `
                <td class="px-5 py-4 border-b border-gray-200 bg-white text-sm">${review.id}</td>
                <td class="px-5 py-4 border-b border-gray-200 bg-white text-sm">
                    ${review.product_name || 'N/A'} (ID: ${review.product_id || 'N/A'})
                </td>
                <td class="px-5 py-4 border-b border-gray-200 bg-white text-sm">${review.user_name || review.user_email || 'N/A'}</td>
                <td class="px-5 py-4 border-b border-gray-200 bg-white text-sm">
                    <div class="flex items-center">${renderStars(review.rating)} (${review.rating})</div>
                </td>
                <td class="px-5 py-4 border-b border-gray-200 bg-white text-sm max-w-xs truncate" title="${review.comment}">${review.comment}</td>
                <td class="px-5 py-4 border-b border-gray-200 bg-white text-sm">${formatDate(review.created_at)}</td>
                <td class="px-5 py-4 border-b border-gray-200 bg-white text-sm">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                        ${review.status === 'approved' ? 'bg-green-100 text-green-800' :
                          review.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                          review.status === 'rejected' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'}">
                        ${review.status ? review.status.charAt(0).toUpperCase() + review.status.slice(1) : 'N/A'}
                    </span>
                    ${review.admin_comment ? `<i class="fas fa-comment-dots ml-2 text-blue-500" title="Admin comment: ${review.admin_comment}"></i>` : ''}
                </td>
                <td class="px-5 py-4 border-b border-gray-200 bg-white text-sm">
                    ${review.status === 'pending' ? `
                        <button class="text-green-600 hover:text-green-900 approve-review-btn" data-id="${review.id}" data-i18n-title="admin.reviews.approveTooltip" title="Approve">
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="text-red-600 hover:text-red-900 reject-review-btn ml-2" data-id="${review.id}" data-i18n-title="admin.reviews.rejectTooltip" title="Reject">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : review.status === 'approved' ? `
                        <button class="text-red-600 hover:text-red-900 reject-review-btn ml-2" data-id="${review.id}" data-i18n-title="admin.reviews.rejectTooltip" title="Reject">
                            <i class="fas fa-ban"></i> </button>
                    ` : review.status === 'rejected' ? `
                         <button class="text-green-600 hover:text-green-900 approve-review-btn" data-id="${review.id}" data-i18n-title="admin.reviews.approveTooltip" title="Approve">
                            <i class="fas fa-check-circle"></i> </button>
                    `: ''}
                     <button class="text-blue-600 hover:text-blue-900 comment-review-btn ml-2" data-id="${review.id}" data-comment="${review.admin_comment || ''}" data-i18n-title="admin.reviews.commentTooltip" title="Admin Comment">
                        <i class="fas fa-comment-alt"></i>
                    </button>
                </td>
            `;
        });
        if (window.applyI18nToElement) applyI18nToElement(reviewsTableBody); // Apply i18n to newly added buttons/tooltips
        attachReviewActionListeners();
    }

    function renderStars(rating) {
        let stars = '';
        for (let i = 1; i <= 5; i++) {
            stars += `<i class="fas fa-star ${i <= rating ? 'text-yellow-400' : 'text-gray-300'}"></i>`;
        }
        return stars;
    }
    
    // Fetch reviews from API
    async function fetchReviews(page = 1, status = 'all', productId = null) {
        reviewsTableBody.innerHTML = `<tr><td colspan="8" class="text-center py-10" id="loading-reviews-row"><i class="fas fa-spinner fa-spin text-2xl text-brand-primary"></i><p class="mt-2" data-i18n="admin.reviews.loading">Chargement des avis...</p></td></tr>`;
        if(window.translateSingleElement) translateSingleElement(reviewsTableBody.querySelector('td p'));

        try {
            // Assumes adminApi.getReviews supports pagination, status and productId filters
            const response = await adminApi.getReviews({ page, limit: reviewsPerPage, status, product_id: productId });
            if (response && response.reviews) {
                renderReviews(response.reviews);
                renderPagination(response.total_reviews || response.total_items, reviewsPerPage, page);
            } else {
                renderReviews([]);
                renderPagination(0, reviewsPerPage, page);
                console.warn("No reviews data in API response:", response);
            }
        } catch (error) {
            console.error("Failed to fetch reviews:", error);
            reviewsTableBody.innerHTML = `<tr><td colspan="8" class="text-center py-10 text-red-500" data-i18n="admin.reviews.errorLoading">Error loading reviews. Please try again.</td></tr>`;
            if(window.translateSingleElement) translateSingleElement(reviewsTableBody.querySelector('td'));
            window.showAlert('Failed to load reviews: ' + error.message, 'Error');
        }
    }

    // Render pagination controls
    function renderPagination(totalItems, limit, currentPage) {
        if (!paginationControls) return;
        paginationControls.innerHTML = '';
        const totalPages = Math.ceil(totalItems / limit);

        if (totalPages <= 1) return;

        for (let i = 1; i <= totalPages; i++) {
            const button = document.createElement('button');
            button.textContent = i;
            button.classList.add('px-3', 'py-1', 'border', 'rounded-md', 'text-sm');
            if (i === currentPage) {
                button.classList.add('bg-brand-primary', 'text-white', 'border-brand-primary');
            } else {
                button.classList.add('bg-white', 'text-brand-primary', 'hover:bg-gray-100');
            }
            button.addEventListener('click', () => {
                fetchReviews(i, filterStatusSelect.value, filterProductIdInput.value || null);
            });
            paginationControls.appendChild(button);
        }
    }

    // Handle review actions (approve, reject, comment)
    async function handleReviewAction() {
        if (!currentReviewAction || !currentReviewAction.reviewId) return;
        
        const { reviewId, actionType, newStatus } = currentReviewAction;
        const adminComment = adminCommentTextarea.value.trim();

        try {
            let payload = { admin_comment: adminComment };
            if (actionType === 'approve' || actionType === 'reject') {
                payload.status = newStatus;
            }
            
            await adminApi.updateReview(reviewId, payload); // Assumes adminApi.updateReview(reviewId, { status, admin_comment })
            
            window.showGlobalAdminMessage('Review updated successfully!', 'success');
            adminCommentModal.classList.add('hidden');
            fetchReviews(currentPage, filterStatusSelect.value, filterProductIdInput.value || null); // Refresh list
        } catch (error) {
            console.error(`Failed to ${actionType} review:`, error);
            window.showAlert(`Error updating review: ${error.message}`, 'Error');
        } finally {
            currentReviewAction = null;
            adminCommentTextarea.value = '';
        }
    }
    
    // Attach listeners to action buttons
    function attachReviewActionListeners() {
        document.querySelectorAll('.approve-review-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const reviewId = e.currentTarget.dataset.id;
                currentReviewAction = { reviewId, actionType: 'approve', newStatus: 'approved' };
                // Ask for optional admin comment for approval
                adminCommentTextarea.value = ''; // Clear previous comment
                adminCommentTextarea.setAttribute('placeholder_i18n', 'admin.reviews.modalPlaceholderApprove');
                if(window.translateSingleElementByPlaceholder) translateSingleElementByPlaceholder(adminCommentTextarea);
                adminCommentModal.classList.remove('hidden');
                // Or directly approve if no comment needed:
                // window.showConfirm('Approve this review?', 'Confirm Approval', (confirmed) => {
                // if (confirmed) handleReviewAction({ reviewId, actionType: 'approve', newStatus: 'approved', adminComment: '' });
                // });
            });
        });

        document.querySelectorAll('.reject-review-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const reviewId = e.currentTarget.dataset.id;
                currentReviewAction = { reviewId, actionType: 'reject', newStatus: 'rejected' };
                adminCommentTextarea.value = '';
                adminCommentTextarea.setAttribute('placeholder_i18n', 'admin.reviews.modalPlaceholderReject');
                if(window.translateSingleElementByPlaceholder) translateSingleElementByPlaceholder(adminCommentTextarea);
                adminCommentModal.classList.remove('hidden'); // Always ask for comment on rejection
            });
        });
        
        document.querySelectorAll('.comment-review-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const reviewId = e.currentTarget.dataset.id;
                const existingComment = e.currentTarget.dataset.comment;
                currentReviewAction = { reviewId, actionType: 'comment' }; // No status change, just comment
                adminCommentTextarea.value = existingComment || '';
                adminCommentTextarea.setAttribute('placeholder_i18n', 'admin.reviews.modalPlaceholderComment');
                 if(window.translateSingleElementByPlaceholder) translateSingleElementByPlaceholder(adminCommentTextarea);
                adminCommentModal.classList.remove('hidden');
            });
        });
    }

    // Event listeners for filters
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', () => {
            currentPage = 1; // Reset to first page on new filter
            const productId = filterProductIdInput.value.trim();
            fetchReviews(currentPage, filterStatusSelect.value, productId ? parseInt(productId, 10) : null);
        });
    }

    // Event listeners for modal
    if (modalConfirmActionBtn) {
        modalConfirmActionBtn.addEventListener('click', handleReviewAction);
    }
    if (modalCancelBtn) {
        modalCancelBtn.addEventListener('click', () => {
            adminCommentModal.classList.add('hidden');
            adminCommentTextarea.value = '';
            currentReviewAction = null;
        });
    }
    if (closeModalAdminCommentBtn) {
         closeModalAdminCommentBtn.addEventListener('click', () => {
            adminCommentModal.classList.add('hidden');
            adminCommentTextarea.value = '';
            currentReviewAction = null;
        });
    }


    // Initial fetch of reviews
    fetchReviews(currentPage, filterStatusSelect.value);

     // Initialize global message close button, if it's managed here
     // However, this is often better placed in admin_ui.js or admin_main.js for global elements
    const closeAdminGlobalMessageBtn = document.getElementById('close-admin-global-message');
    if (closeAdminGlobalMessageBtn && !closeAdminGlobalMessageBtn.dataset.listenerAttached) { // Avoid multiple listeners
        closeAdminGlobalMessageBtn.addEventListener('click', () => {
            document.getElementById('admin-global-message').classList.add('hidden');
        });
        closeAdminGlobalMessageBtn.dataset.listenerAttached = 'true';
    }
}


// The original inline script called initAdminReviewsPage on DOMContentLoaded.
// If admin_main.js doesn't specifically call this, we should ensure it runs.
// A common pattern is for admin_main.js to detect the current page and call the relevant init function.
// If not, this script itself can self-initialize:
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminReviewsPage);
} else {
    // DOMContentLoaded has already fired
    initAdminReviewsPage();
}
