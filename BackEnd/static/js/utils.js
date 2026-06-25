// ===== TOAST =====
function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-message">${message}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
  `;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ===== CONFIRMATION MODAL =====
function openModal(title, body, onConfirm) {
  document.getElementById('modalTitle').textContent = title;
  document.getElementById('modalBody').textContent = body;
  document.getElementById('modalConfirmBtn').onclick = () => {
    onConfirm();
    closeModal();
  };
  document.getElementById('modalConfirm').classList.add('open');
}

function closeModal() {
  document.getElementById('modalConfirm').classList.remove('open');
}

// Close modal when clicking outside
document.getElementById('modalConfirm')?.addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

// ===== VALIDATE FILE =====
function validateFile(file, maxMB = 10) {
  const allowed = ['.pdf', '.doc', '.docx', '.png', '.jpg'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast(`Invalid format. Only accepted: ${allowed.join(', ')}`, 'danger');
    return false;
  }
  if (file.size > maxMB * 1024 * 1024) {
    showToast(`File too large. Maximum size is ${maxMB}MB`, 'danger');
    return false;
  }
  return true;
}

// ===== FORMAT DATE =====
function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// ===== CSRF TOKEN (for fetch/AJAX) =====
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}
const csrfToken = getCookie('csrftoken');