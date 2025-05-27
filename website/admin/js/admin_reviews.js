// File: website/admin/js/admin_reviews.js
document.addEventListener('DOMContentLoaded', () => {
    if (typeof ensureAdminAuthenticated === 'function' && !ensureAdminAuthenticated()) { return; }

    const reviewsTableBody = document.getElementById('reviewsTableBody');
    const reviewSearchInput = document.getElementById('reviewSearchInput');
    const paginationControls = document.getElementById('paginationControls');

    const reviewModal = document.getElementById('reviewModal');
    const closeModalBtn = reviewModal ? reviewModal.querySelector('#closeModalBtn') : null;
    const cancelModalBtn = reviewModal ? reviewModal.querySelector('#cancelModalBtn') : null;
    const reviewApprovalForm = document.getElementById('reviewApprovalForm');
    const saveReviewStatusBtn = document.getElementById('saveReviewStatusBtn');
    const formMessageContainer = reviewModal ? reviewModal.querySelector('#formMessage') : null;

    const reviewProductName = document.getElementById('reviewProductName');
    const reviewProductId = document.getElementById('reviewProductId');
    const reviewUserName = document.getElementById('reviewUserName');
    const reviewUserId = document.getElementById('reviewUserId');
    const reviewDate = document.getElementById('reviewDate');
    const reviewRatingStars = document.getElementById('reviewRatingStars');
    const reviewCommentText = document.getElementById('reviewCommentText');
    const reviewStatusSelect = document.getElementById('reviewStatus');
    const reviewIdInput = document.getElementById('reviewId');


    let currentReviews = [];
    let editingReviewId = null;
    let currentPage = 1;
    const reviewsPerPage = 10;

    const openModal = (review) => {
        if (!reviewModal || !reviewApprovalForm || !saveReviewStatusBtn) return;
        clearFormMessage();
        reviewApprovalForm.reset();
        saveReviewStatusBtn.disabled = false;
        saveReviewStatusBtn.innerHTML = '<i class="fas fa-check-circle mr-2"></i>Update Status';

        editingReviewId = review.id;
        if (reviewIdInput) reviewIdInput.value = review.id;
        if (reviewProductName) reviewProductName.textContent = review.product_name || 'N/A';
        if (reviewProductId) reviewProductId.textContent = review.product_id || 'N/A';
        if (reviewUserName) reviewUserName.textContent = review.user_name || 'Anonymous';
        if (reviewUserId) reviewUserId.textContent = review.user_id || 'N/A';
        if (reviewDate) reviewDate.textContent = new Date(review.created_at).toLocaleDateString();
        if (reviewRatingStars) reviewRatingStars.innerHTML = generateStarRating(review.rating);
        if (reviewCommentText) reviewCommentText.textContent = review.comment || 'No comment provided.';
        if (reviewStatusSelect) reviewStatusSelect.value = review.is_approved ? "true" : "false";

        reviewModal.classList.remove('opacity-0', 'pointer-events-none');
        reviewModal.classList.add('opacity-100');
        document.body.classList.add('modal-active');
    };

    const closeModal = () => {
        if (!reviewModal) return;
        reviewModal.classList.add('opacity-0');
        reviewModal.classList.remove('opacity-100');
        setTimeout(() => {
            reviewModal.classList.add('pointer-events-none');
            document.body.classList.remove('modal-active');
        }, 250);
    };

    if(closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    if(cancelModalBtn) cancelModalBtn.addEventListener('click', closeModal);
    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && reviewModal && !reviewModal.classList.contains('pointer-events-none')) {
            closeModal();
        }
    });

    const generateStarRating = (rating) => {
        let stars = '';
        for (let i = 1; i <= 5; i++) {
            stars += `<i class="fas fa-star rating-star ${i <= rating ? 'selected text-yellow-400' : 'text-gray-300'}"></i>`;
        }
        return stars || '<span class="text-gray-500">Not rated</span>';
    };

    const renderReviews = (reviews) => {
        if(!reviewsTableBody) return;
        reviewsTableBody.innerHTML = '';
        if (!reviews || reviews.length === 0) {
            reviewsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 text-center text-sm text-gray-500">No reviews found.</td></tr>`;
            return;
        }
        reviews.forEach(review => {
            const row = reviewsTableBody.insertRow();
            row.className = `hover:bg-gray-50 transition-colors ${!review.is_approved ? 'bg-yellow-50 opacity-80 hover:opacity-100' : ''}`; // Style pending reviews
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700" title="Product ID: ${review.product_id}">${review.product_name || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700" title="User ID: ${review.user_id}">${review.user_name || 'Anonymous'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">${generateStarRating(review.rating)}</td>
                <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" title="${review.comment}">${review.comment || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${new Date(review.created_at).toLocaleDateString()}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${review.is_approved ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}">
                        ${review.is_approved ? 'Approved' : 'Pending'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button class="view-btn text-blue-600 hover:text-blue-800 p-1 rounded hover:bg-blue-100" data-id="${review.id}" title="View Details & Approve/Reject"><i class="fas fa-eye fa-fw"></i></button>
                    <button class="delete-btn text-red-600 hover:text-red-800 p-1 rounded hover:bg-red-100" data-id="${review.id}" title="Delete Review"><i class="fas fa-trash-alt fa-fw"></i></button>
                </td>
            `;
        });

        document.querySelectorAll('.view-btn').forEach(button => button.addEventListener('click', handleViewReview));
        document.querySelectorAll('.delete-btn').forEach(button => button.addEventListener('click', handleDeleteReview));
    };

    const setupPaginationForReviews = (totalReviews) => {
        if (!paginationControls) return;
        paginationControls.innerHTML = '';
        const totalPages = Math.ceil(totalReviews / reviewsPerPage);
        if (totalPages <= 1) return;

        const createPageButton = (htmlContent, pageNum, isDisabled = false, isActive = false) => {
            const button = document.createElement('button');
            button.innerHTML = htmlContent;
            button.className = `px-3 py-1 rounded-md text-sm font-medium border border-gray-300 transition-colors ${isDisabled ? 'bg-gray-200 text-gray-400 cursor-not-allowed' : isActive ? 'bg-indigo-500 text-white border-indigo-500 z-10' : 'bg-white text-gray-700 hover:bg-gray-50'}`;
            button.disabled = isDisabled;
            if (isActive) button.setAttribute('aria-current', 'page');
            button.addEventListener('click', () => { if (!isDisabled && !isActive) { currentPage = pageNum; fetchAndDisplayReviews(); } });
            return button;
        };
        paginationControls.appendChild(createPageButton(`<i class="fas fa-chevron-left mr-1"></i> Prev`, currentPage - 1, currentPage === 1));
        const pageRange = 1; let pagesShown = new Set(); pagesShown.add(1);
        for (let i = Math.max(2, currentPage - pageRange); i <= Math.min(totalPages - 1, currentPage + pageRange); i++) pagesShown.add(i);
        pagesShown.add(totalPages);
        const sortedPages = Array.from(pagesShown).sort((a,b)=>a-b); let lastPageAdded = 0;
        sortedPages.forEach(pageNum => {
            if(lastPageAdded > 0 && pageNum > lastPageAdded + 1) paginationControls.appendChild(createPageButton('...', pageNum -1, true));
            paginationControls.appendChild(createPageButton(pageNum.toString(), pageNum, false, pageNum === currentPage));
            lastPageAdded = pageNum;
        });
        paginationControls.appendChild(createPageButton(`Next <i class="fas fa-chevron-right ml-1"></i>`, currentPage + 1, currentPage === totalPages));
    };


    const fetchAndDisplayReviews = async () => {
        if(!reviewsTableBody) return;
        reviewsTableBody.innerHTML = `<tr><td colspan="7" class="text-center p-4 text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i>Loading reviews...</td></tr>`;
        if(paginationControls) paginationControls.innerHTML = '';

        try {
            const searchTerm = reviewSearchInput ? reviewSearchInput.value.trim() : '';
            const response = await adminApi.getReviews(searchTerm, currentPage, reviewsPerPage);
            if (response && response.reviews) {
                currentReviews = response.reviews;
                renderReviews(currentReviews);
                setupPaginationForReviews(response.total_reviews || currentReviews.length);
                if (currentReviews.length === 0 && searchTerm) {
                     reviewsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">No reviews found matching "${searchTerm}".</td></tr>`;
                } else if (currentReviews.length === 0) {
                    reviewsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">No reviews submitted yet.</td></tr>`;
                }
            } else {
                renderReviews([]);
                if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage('Review data is missing in the server response.', 'error');
            }
        } catch (error) {
            console.error('Failed to fetch reviews:', error);
            reviewsTableBody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 text-center text-sm text-red-500">Error loading reviews: ${error.message}</td></tr>`;
            if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(`Error fetching reviews: ${error.message}`, 'error');
        }
    };

    if (reviewApprovalForm) {
        reviewApprovalForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (!saveReviewStatusBtn) return;

            const reviewData = {
                is_approved: reviewStatusSelect.value === "true", // Ensure it's a boolean for the backend
            };

            saveReviewStatusBtn.disabled = true;
            saveReviewStatusBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Updating...';
            clearFormMessage();

            try {
                const response = await adminApi.updateReview(editingReviewId, reviewData);
                if (response && response.message && response.message.toLowerCase().includes('success')) {
                    if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(response.message, 'success');
                    fetchAndDisplayReviews();
                    closeModal();
                } else {
                    throw new Error(response.error || 'Failed to update review status.');
                }
            } catch (error) {
                console.error('Failed to update review status:', error);
                showFormMessage(`Error: ${error.message}`, 'error');
            } finally {
                saveReviewStatusBtn.disabled = false;
                saveReviewStatusBtn.innerHTML = '<i class="fas fa-check-circle mr-2"></i>Update Status';
            }
        });
    }

    const handleViewReview = async (event) => {
        const button = event.currentTarget;
        const reviewId = button.dataset.id;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        button.disabled = true;

        try {
            let review = currentReviews.find(r => r.id == reviewId);
            if (!review) { // If not in current list (e.g. due to pagination), fetch directly
                review = await adminApi.getReviewById(reviewId);
            }

            if (review) {
                openModal(review);
            } else {
                if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage('Could not fetch review details.', 'error');
            }
        } catch (error) {
            console.error('Error fetching review for viewing:', error);
             if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(`Error fetching review: ${error.message}`, 'error');
        } finally {
            button.innerHTML = '<i class="fas fa-eye fa-fw"></i>';
            button.disabled = false;
        }
    };

    const handleDeleteReview = (event) => {
        const button = event.currentTarget;
        const reviewId = button.dataset.id;
        const reviewText = button.closest('tr').querySelector('td:nth-child(4)').textContent.substring(0,30) + '...' || `Review ID ${reviewId}`;


        if (typeof showConfirmModal === 'function') {
            showConfirmModal(
                `Delete Review?`,
                `Are you sure you want to delete the review: "<strong>${reviewText}</strong>"? This action cannot be undone.`,
                async () => { // onConfirm callback
                    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    button.disabled = true;
                    try {
                        const response = await adminApi.deleteReview(reviewId);
                        if (response && response.message && response.message.toLowerCase().includes('success')) {
                            if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(response.message, 'success');
                            fetchAndDisplayReviews();
                        } else {
                            throw new Error(response.error || 'Failed to delete review.');
                        }
                    } catch (error) {
                        console.error('Failed to delete review:', error);
                        if(typeof showGlobalUIMessage === 'function') showGlobalUIMessage(`Error deleting review: ${error.message}`, 'error');
                        button.innerHTML = '<i class="fas fa-trash-alt fa-fw"></i>';
                        button.disabled = false;
                    }
                }
            );
        } else {
            if(confirm(`Are you sure you want to delete review ID ${reviewId}?`)) {
                 button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                 button.disabled = true;
                adminApi.deleteReview(reviewId)
                    .then((response) => {
                        alert(response.message || "Review deleted.");
                        fetchAndDisplayReviews();
                    })
                    .catch(err => {
                        alert(`Error: ${err.message}`);
                        button.innerHTML = '<i class="fas fa-trash-alt fa-fw"></i>';
                        button.disabled = false;
                    });
            }
        }
    };

    let searchTimeout;
    if (reviewSearchInput) {
        reviewSearchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentPage = 1;
                fetchAndDisplayReviews();
            }, 300);
        });
    }

    const showFormMessage = (message, type = 'info') => {
        if (!formMessageContainer) return;
        formMessageContainer.innerHTML = message;
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
        await fetchAndDisplayReviews();
    };

    initializePage();
});
