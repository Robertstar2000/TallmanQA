// Main JavaScript file for interactive elements

document.addEventListener('DOMContentLoaded', function() {
    // Add active class to current navigation item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
            link.setAttribute('aria-current', 'page');
        }
    });

    // Flash message auto-dismiss
    const flashMessages = document.querySelectorAll('.alert');
    if (flashMessages.length > 0) {
        flashMessages.forEach(message => {
            setTimeout(() => {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 300);
            }, 5000);
        });
    }

    // Form validation
    const forms = document.querySelectorAll('form[novalidate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

// Function to show loading state
function setLoading(button, isLoading) {
    const buttonElement = button instanceof HTMLElement ? button : document.querySelector(button);
    if (buttonElement) {
        if (isLoading) {
            buttonElement.disabled = true;
            buttonElement.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
        } else {
            buttonElement.disabled = false;
            // Restore original content if data-original-text is set
            const originalText = buttonElement.getAttribute('data-original-text');
            buttonElement.innerHTML = originalText || buttonElement.textContent;
        }
    }
}

// Function to show/hide elements
function toggleElement(selector, show = true) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
        el.style.display = show ? '' : 'none';
    });
}

// Function to show toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast show align-items-center text-white bg-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove toast after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.position = 'fixed';
    container.style.top = '20px';
    container.style.right = '20px';
    container.style.zIndex = '1100';
    document.body.appendChild(container);
    return container;
}
