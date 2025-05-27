// website/admin/js/admin_reviews.js

// Assumes: makeAdminApiRequest, showAdminGlobalMessage, checkAdminLogin, translate, API_BASE_URL are available
let currentReviews = [];
let currentPage = 1;
const reviewsPerPage = 20; // or get from a config

async function fetchReviews(page = 1, status = 'all', productId = null) {
    const tableBody = document.getElementById('reviews-table-body');
    const loadingRow = document.getElementById('loading-reviews-row');
    
    if (loadingRow) loadingRow.classList.remove('hidden');
    if (page === 1) tableBody.innerHTML = ''; // Clear for new filter/first load
    if (loadingRow && page === 1) tableBody.appendChild(loadingRow);


    let url = `/api/admin/reviews?page=${page}&limit=${reviewsPerPage}`;
    if (status && status !== 'all') {
        url += `&status=${status}`;
    }
    if (productId) {
        url += `&product_id=${productId}`;
    }

    try {
        const data = await makeAdminApiRequest(url, 'GET');
        currentReviews = data.reviews || [];
        if (loadingRow) loadingRow.classList.add('hidden');
        
        if (currentReviews.length === 0 && page === 1) {
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-6" data-i18n="admin.reviews.noReviewsFound">${translate('admin.reviews.noReviewsFound')}</td></tr>`;
        } else if (page === 1) { // Only clear if it's the first page of a new load
             tableBody.innerHTML = ''; // Clear loading row before adding actual data
        }


        currentReviews.forEach(review => {
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td class="border-b border-gray-200 px-4 py-2">${review.id}</td>
                <td class="border-b border-gray-200 px-4 py-2">
                    <a href="admin_manage_products.html?edit=${review.product_id}" target="_blank" class="text-brand-primary hover:underline">
                        ${review.product_name || `ID: ${review.product_id}`}
                    </a>
                </td>
                <td class="border-b border-gray-200 px-4 py-2">${review.user_name || review.user_email || 'N/A'}</td>
                <td class="border-b border-gray-200 px-4 py-2 text-yellow-500">${'<i class="fas fa-star"></i>'.repeat(review.rating)}${'<i class="far fa-star"></i>'.repeat(5 - review.rating)}</td>
                <td class="border-b border-gray-200 px-4 py-2 max-w-xs truncate" title="${review.comment}">${review.comment}</td>
                <td class="border-b border-gray-200 px-4 py-2">${new Date(review.created_at).toLocaleDateString()}</td>
                <td class="border-b border-gray-200 px-4 py-2">
                    <span class="px-2 py-1 text-xs font-semibold rounded-full ${review.is_approved ? 'bg-green-200 text-green-800' : 'bg-yellow-200 text-yellow-800'}">
                        ${review.is_approved ? translate('admin.reviews.statusApproved') : translate('admin.reviews.statusPending')}
                    </span>
                    ${review.admin_comment ? `<p class="text-xs text-gray-500 mt-1" title="${review.admin_comment}"><i class="fas fa-comment-dots mr-1"></i>${review.admin_comment.substring(0,20)}...</p>` : ''}
                </td>
                <td class="border-b border-gray-200 px-4 py-2 whitespace-nowrap">
                    ${!review.is_approved ? `<button onclick="handleReviewAction(${review.id}, 'approve')" class="approve-btn mr-1" title="${translate('admin.reviews.approveAction')}"><i class="fas fa-check"></i></button>` : ''}
                    ${!review.is_approved ? `<button onclick="handleReviewAction(${review.id}, 'reject')" class="reject-btn mr-1" title="${translate('admin.reviews.rejectAction')}"><i class="fas fa-times"></i></button>` : ''}
                    <button onclick="handleReviewAction(${review.id}, 'delete')" class="delete-btn" title="${translate('admin.reviews.deleteAction')}"><i class="fas fa-trash"></i></button>
                </td>
            `;
        });
        setupPagination(data.total_pages, data.current_page, data.total_reviews);
        currentPage = data.current_page;

    } catch (error) {
        console.error('Error fetching reviews:', error);
        if (loadingRow) loadingRow.classList.add('hidden');
        tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-500">${translate('admin.reviews.errorLoading')}: ${error.message}</td></tr>`;
    }
}

function setupPagination(totalPages, currentPageNum, totalReviews) {
    const paginationControls = document.getElementById('pagination-controls');
    if (!paginationControls) return;
    paginationControls.innerHTML = '';

    if (totalReviews === 0) return;

    const statusFilter = document.getElementById('filter-status').value;
    const productIdFilter = document.getElementById('filter-product-id').value;

    // Previous Button
    if (currentPageNum > 1) {
        const prevButton = document.createElement('button');
        prevButton.innerHTML = `<i class="fas fa-chevron-left mr-1"></i> ${translate('admin.pagination.previous')}`;
        prevButton.className = 'px-3 py-1 border rounded-md bg-white text-sm hover:bg-gray-50';
        prevButton.onclick = () => fetchReviews(currentPageNum - 1, statusFilter, productIdFilter || null);
        paginationControls.appendChild(prevButton);
    }

    // Page Numbers (simplified)
    let startPage = Math.max(1, currentPageNum - 2);
    let endPage = Math.min(totalPages, currentPageNum + 2);

    if (startPage > 1) {
        const firstButton = document.createElement('button');
        firstButton.textContent = '1';
        firstButton.className = `px-3 py-1 border rounded-md text-sm ${1 === currentPageNum ? 'bg-brand-primary text-white' : 'bg-white hover:bg-gray-50'}`;
        firstButton.onclick = () => fetchReviews(1, statusFilter, productIdFilter || null);
        paginationControls.appendChild(firstButton);
        if (startPage > 2) paginationControls.insertAdjacentHTML('beforeend',`<span class="px-3 py-1 text-sm">...</span>`);
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageButton = document.createElement('button');
        pageButton.textContent = i;
        pageButton.className = `px-3 py-1 border rounded-md text-sm ${i === currentPageNum ? 'bg-brand-primary text-white' : 'bg-white hover:bg-gray-50'}`;
        pageButton.onclick = () => fetchReviews(i, statusFilter, productIdFilter || null);
        paginationControls.appendChild(pageButton);
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) paginationControls.insertAdjacentHTML('beforeend',`<span class="px-3 py-1 text-sm">...</span>`);
        const lastButton = document.createElement('button');
        lastButton.textContent = totalPages;
        lastButton.className = `px-3 py-1 border rounded-md text-sm ${totalPages === currentPageNum ? 'bg-brand-primary text-white' : 'bg-white hover:bg-gray-50'}`;
        lastButton.onclick = () => fetchReviews(totalPages, statusFilter, productIdFilter || null);
        paginationControls.appendChild(lastButton);
    }


    // Next Button
    if (currentPageNum < totalPages) {
        const nextButton = document.createElement('button');
        nextButton.innerHTML = `${translate('admin.pagination.next')} <i class="fas fa-chevron-right ml-1"></i>`;
        nextButton.className = 'px-3 py-1 border rounded-md bg-white text-sm hover:bg-gray-50';
        nextButton.onclick = () => fetchReviews(currentPageNum + 1, statusFilter, productIdFilter || null);
        paginationControls.appendChild(nextButton);
    }
}


let currentAction = null;
let currentReviewId = null;

function handleReviewAction(reviewId, action) {
    currentReviewId = reviewId;
    currentAction = action;

    const modal = document.getElementById('admin-comment-modal');
    const confirmBtn = document.getElementById('modal-confirm-action-btn');
    const commentTextarea = document.getElementById('admin-comment-textarea');
    commentTextarea.value = ''; // Clear previous comment

    if (action === 'delete') {
        if (confirm(translate('admin.reviews.confirmDelete'))) {
            performReviewAction(); // No modal for delete, direct action
        }
    } else if (action === 'approve' || action === 'reject') {
        // Show modal for optional admin comment
        modal.classList.remove('hidden');
        confirmBtn.onclick = performReviewAction; // Set specific action for confirm button
    }
}

async function performReviewAction() {
    const modal = document.getElementById('admin-comment-modal');
    const adminComment = document.getElementById('admin-comment-textarea').value;
    let url, method, body = {};

    if (currentAction === 'approve') {
        url = `/api/admin/reviews/${currentReviewId}/approve`;
        method = 'POST';
        body = { admin_comment: adminComment || translate('admin.reviews.commentApproved') };
    } else if (currentAction === 'reject') {
        url = `/api/admin/reviews/${currentReviewId}/reject`; // This endpoint marks as not approved
        method = 'POST';
        body = { admin_comment: adminComment || translate('admin.reviews.commentRejected') };
    } else if (currentAction === 'delete') {
        url = `/api/admin/reviews/${currentReviewId}`;
        method = 'DELETE';
    } else {
        return; // Should not happen
    }

    try {
        const response = await makeAdminApiRequest(url, method, body);
        showAdminGlobalMessage(response.message || `${translate('admin.reviews.actionSuccessPrefix')} ${currentAction}`, 'success');
        // Refresh the current page of reviews
        const statusFilter = document.getElementById('filter-status').value;
        const productIdFilter = document.getElementById('filter-product-id').value;
        fetchReviews(currentPage, statusFilter, productIdFilter || null);
    } catch (error) {
        showAdminGlobalMessage(error.message || `${translate('admin.reviews.actionErrorPrefix')} ${currentAction}`, 'error');
    } finally {
        if (modal) modal.classList.add('hidden');
        currentAction = null;
        currentReviewId = null;
    }
}


async function initAdminReviewsPage() {
    await checkAdminLogin(); // Redirects if not logged in

    const applyFiltersBtn = docum
