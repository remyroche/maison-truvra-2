// File: website/admin/js/admin_main.js

// --- Sidebar Loading & Highlighting ---
async function loadAdminSidebar() {
    const sidebarContainer = document.getElementById('admin-sidebar-container');
    if (sidebarContainer && !sidebarContainer.dataset.loaded) {
        try {
            // Assuming admin_sidebar.html is at a fixed relative path from where admin pages are served
            // e.g., if pages are in /website/admin/ and sidebar is in /admin/
            // This might need adjustment based on actual deployment/serving structure.
            // For dev, if all admin html is in website/admin/, and sidebar is /website/admin/admin_sidebar.html
            const response = await fetch('admin_sidebar.html'); // Adjust if path is different
            if (response.ok) {
                sidebarContainer.innerHTML = await response.text();
                sidebarContainer.dataset.loaded = 'true';
                attachSidebarEventListeners();
                highlightActiveSidebarLink();
            } else {
                console.error('Failed to load sidebar HTML:', response.status, response.statusText);
                sidebarContainer.innerHTML = '<p class="text-red-400 p-4">Error loading sidebar.</p>';
            }
        } catch (error) {
            console.error('Error fetching admin sidebar:', error);
            sidebarContainer.innerHTML = '<p class="text-red-400 p-4">Could not fetch sidebar.</p>';
        }
    } else if (sidebarContainer && sidebarContainer.dataset.loaded === 'true') {
        attachSidebarEventListeners(); // Re-attach for safety if this function is called multiple times
        highlightActiveSidebarLink();
    }
}

function attachSidebarEventListeners() {
    const logoutButton = document.getElementById('admin-logout-button');
    if (logoutButton && typeof adminLogout === 'function') {
        logoutButton.removeEventListener('click', adminLogout); // Prevent multiple listeners
        logoutButton.addEventListener('click', adminLogout);
    }
}

function highlightActiveSidebarLink() {
    const sidebarContainer = document.getElementById('admin-sidebar-container');
    if (!sidebarContainer) return;

    const currentFile = window.location.pathname.split('/').pop();
    const sidebarLinks = sidebarContainer.querySelectorAll('nav a');

    sidebarLinks.forEach(link => {
        const linkFile = link.getAttribute('href').split('/').pop();
        link.classList.remove('bg-gray-700', 'text-white', 'font-semibold');
        link.classList.add('hover:bg-gray-700', 'hover:text-white');

        if (linkFile === currentFile) {
            link.classList.add('bg-gray-700', 'text-white', 'font-semibold');
            link.classList.remove('hover:bg-gray-700', 'hover:text-white');
        }
    });
}

// --- Custom Confirm Modal ---
let confirmCallback = null;
const confirmModalElement = document.getElementById('confirmModal');
const confirmModalTitleElement = document.getElementById('confirmModalTitle');
const confirmModalMessageElement = document.getElementById('confirmModalMessage');
const confirmModalConfirmBtnElement = document.getElementById('confirmModalConfirmBtn');
const confirmModalCancelBtnElement = document.getElementById('confirmModalCancelBtn');

function showConfirmModal(title, message, onConfirm) {
    if (!confirmModalElement || !confirmModalTitleElement || !confirmModalMessageElement || !confirmModalConfirmBtnElement || !confirmModalCancelBtnElement) {
        console.warn("Confirm modal elements not all found. Falling back to native confirm.");
        if (confirm(`${title}\n${message}`)) {
            if (typeof onConfirm === 'function') onConfirm();
        }
        return;
    }
    confirmModalTitleElement.textContent = title;
    confirmModalMessageElement.innerHTML = message; // Allow simple HTML for emphasis
    confirmCallback = onConfirm;

    // Set button text for confirmation if needed, or keep generic
    // confirmModalConfirmBtnElement.textContent = "Confirm"; 

    confirmModalElement.classList.remove('opacity-0', 'pointer-events-none');
    confirmModalElement.classList.add('opacity-100');
    document.body.classList.add('modal-active');
}

function closeConfirmModal() {
    if (!confirmModalElement) return;
    confirmModalElement.classList.add('opacity-0');
    confirmModalElement.classList.remove('opacity-100');
    setTimeout(() => {
        confirmModalElement.classList.add('pointer-events-none');
        document.body.classList.remove('modal-active');
    }, 250);
    confirmCallback = null;
}

if (confirmModalConfirmBtnElement) {
    confirmModalConfirmBtnElement.addEventListener('click', () => {
        if (typeof confirmCallback === 'function') {
            confirmModalConfirmBtnElement.disabled = true; // Prevent double-click
            confirmModalConfirmBtnElement.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
            try {
                confirmCallback(); // Execute the action
            } catch (e) {
                console.error("Error in confirm callback", e);
                // Optionally show an error message here
            } finally {
                // Re-enable button after a short delay, or callback should handle UI
                setTimeout(() => {
                     if (confirmModalConfirmBtnElement) { // Check if still exists
                        confirmModalConfirmBtnElement.disabled = false;
                        confirmModalConfirmBtnElement.textContent = 'Confirm'; // Reset text
                     }
                }, 500); // Delay to allow async operations in callback to potentially start
                closeConfirmModal(); // Close modal regardless of callback success/failure for now
            }
        } else {
             closeConfirmModal();
        }
    });
}
if (confirmModalCancelBtnElement) {
    confirmModalCancelBtnElement.addEventListener('click', closeConfirmModal);
}
window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && confirmModalElement && !confirmModalElement.classList.contains('pointer-events-none')) {
        closeConfirmModal();
    }
});


// --- Global UI Message Utility (Toast Notifications) ---
function showGlobalUIMessage(message, type = 'info', duration = 5000) {
    const containerId = 'globalMessageContainer';
    let messageContainer = document.getElementById(containerId);

    if (!messageContainer) {
        // Attempt to find a main content area to append to, or create one fixed.
        const mainContent = document.querySelector('.flex-1.p-10.overflow-y-auto') || document.body;
        const existingContainer = mainContent.querySelector(`#${containerId}-dynamic`);
        if (existingContainer) {
            messageContainer = existingContainer;
        } else {
            messageContainer = document.createElement('div');
            messageContainer.id = `${containerId}-dynamic`; // Dynamic ID if created
            messageContainer.className = 'fixed top-5 right-5 z-[1000] space-y-3 w-full max-w-sm';
            mainContent.appendChild(messageContainer);
        }
    }
     // If the specific page defines its own #globalMessageContainer, use that instead of fixed.
    const pageLevelContainer = document.getElementById('globalMessageContainer');
    if (pageLevelContainer) messageContainer = pageLevelContainer;


    const messageDiv = document.createElement('div');
    messageDiv.setAttribute('role', 'alert');
    
    let iconHTML = '';
    let baseClasses = 'p-4 text-sm rounded-lg shadow-xl flex items-start relative overflow-hidden transition-all duration-500 ease-in-out transform opacity-0 translate-y-[-20px]';
    let typeClasses = '';

    switch (type) {
        case 'success':
            typeClasses = 'bg-green-50 border-l-4 border-green-500 text-green-700';
            iconHTML = '<i class="fas fa-check-circle fa-lg mr-3 mt-1 text-green-500"></i>';
            break;
        case 'error':
            typeClasses = 'bg-red-50 border-l-4 border-red-500 text-red-700';
            iconHTML = '<i class="fas fa-exclamation-triangle fa-lg mr-3 mt-1 text-red-500"></i>';
            break;
        default: // info
            typeClasses = 'bg-blue-50 border-l-4 border-blue-500 text-blue-700';
            iconHTML = '<i class="fas fa-info-circle fa-lg mr-3 mt-1 text-blue-500"></i>';
            break;
    }
    messageDiv.className = `${baseClasses} ${typeClasses}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.innerHTML = `<strong class="font-semibold">${type.charAt(0).toUpperCase() + type.slice(1)}!</strong> ${message}`; // Allow basic HTML in message

    const messageContentWrapper = document.createElement('div');
    messageContentWrapper.className = 'flex-grow';
    messageContentWrapper.appendChild(contentDiv);

    messageDiv.innerHTML = iconHTML; // Add icon first
    messageDiv.appendChild(messageContentWrapper); // Then add text content

    const closeButton = document.createElement('button');
    closeButton.innerHTML = '<i class="fas fa-times"></i>';
    closeButton.className = 'ml-auto -mx-1.5 -my-1.5 bg-transparent text-current rounded-lg focus:ring-2 focus:ring-current p-1.5 inline-flex h-8 w-8 hover:opacity-75';
    closeButton.setAttribute('aria-label', 'Close');
    
    const closeAndRemove = () => {
        messageDiv.classList.add('opacity-0', 'translate-y-[-20px]');
        messageDiv.classList.remove('opacity-100', 'translate-y-0');
        setTimeout(() => {
            if (messageDiv.parentElement) messageDiv.remove();
        }, 500); // Allow fade out
    };
    closeButton.onclick = closeAndRemove;
    messageDiv.appendChild(closeButton);

    messageContainer.appendChild(messageDiv);

    // Animate in
    setTimeout(() => {
        messageDiv.classList.remove('opacity-0', 'translate-y-[-20px]');
        messageDiv.classList.add('opacity-100', 'translate-y-0');
    }, 10);

    if (duration > 0) {
        setTimeout(closeAndRemove, duration);
    }
}


// --- DOMContentLoaded Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    const sidebarContainer = document.getElementById('admin-sidebar-container');
    if (sidebarContainer) {
        // If sidebar is meant to be loaded dynamically by JS:
        // loadAdminSidebar(); 
        // If sidebar HTML is directly in each page:
        highlightActiveSidebarLink();
        attachSidebarEventListeners();
    }

    // Global check for authentication (from admin_auth.js)
    if (typeof ensureAdminAuthenticated === 'function') {
        if (!window.location.pathname.endsWith('admin_login.html')) {
            ensureAdminAuthenticated();
        }
    } else {
        console.warn('ensureAdminAuthenticated function from admin_auth.js not found. Admin pages might not be secure.');
    }
});
