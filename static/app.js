const dateLabel = document.getElementById('today');
if (dateLabel) {
  dateLabel.textContent = new Intl.DateTimeFormat('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  }).format(new Date()).toUpperCase();
}

document.querySelectorAll('.flash-close').forEach((button) => {
  button.addEventListener('click', () => button.closest('.flash').remove());
});

document.querySelectorAll('.refresh-button[type="submit"]').forEach((button) => {
  button.closest('form').addEventListener('submit', () => {
    button.disabled = true;
    button.innerHTML = '<span>↻</span> Checking feeds…';
  });
});

if (document.querySelector('[data-auto-refresh-pending]')) {
  window.setTimeout(() => window.location.reload(), 30000);
}
