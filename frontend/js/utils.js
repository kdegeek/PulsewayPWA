function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    // Basic styling for the toast, assuming CSS will be added later for .toast, .toast-error, .toast-success
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.padding = '10px 20px';
    toast.style.borderRadius = '5px';
    toast.style.color = 'white';
    toast.style.zIndex = '1001'; // Ensure it's above most content

    if (type === 'error') {
        toast.style.backgroundColor = 'var(--error-glow, #ff0055)';
    } else if (type === 'success') {
        toast.style.backgroundColor = 'var(--success-glow, #00ff88)';
    } else {
        toast.style.backgroundColor = 'var(--primary-glow, #00f5ff)'; // Default to primary for info
    }

    toast.className = `toast toast-${type}`; // For potential CSS styling
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function showError(message) {
    showToast(message, 'error');
    console.error(message); // Keep console log for now
}

function showSuccess(message) {
    showToast(message, 'success');
    console.log(message); // Keep console log for now
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatLastSeen(lastSeen) {
    if (!lastSeen) return 'Never';
    const date = new Date(lastSeen);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now'; // Less than 1 minute
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`; // Less than 1 hour
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`; // Less than 1 day
    return `${Math.floor(diff / 86400000)}d ago`; // Days ago
}

function formatTimeAgo(datetime) {
    if (!datetime) return 'Unknown';

    const now = new Date();
    const date = new Date(datetime);
    const diffMs = now - date;

    if (diffMs < 60000) return 'Just now';
    if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
    if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`;
    if (diffMs < 604800000) return `${Math.floor(diffMs / 86400000)}d ago`; // up to 7 days
    return date.toLocaleDateString(); // Older than 7 days, show date
}

function formatFullDateTime(datetime) {
    if (!datetime) return 'Unknown';
    return new Date(datetime).toLocaleString();
}

function getPriorityIcon(priority) {
    switch (priority) {
        case 'critical': return '🚨';
        case 'elevated': return '⚠️';
        case 'normal': return 'ℹ️';
        case 'low': return '💡';
        default: return '📝';
    }
}
