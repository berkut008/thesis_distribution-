// Общие функции JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Автоскрытие alert через 5 секунд
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Функция для показа уведомлений
function showNotification(message, type = 'success') {
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.querySelector('.container').insertBefore(notification, document.querySelector('.container').firstChild);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Подтверждение действий
function confirmAction(message) {
    return confirm(message);
}