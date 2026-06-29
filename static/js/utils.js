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

// ===== MODAL XÁC NHẬN =====
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

// Đóng modal khi click ra ngoài
document.getElementById('modalConfirm')?.addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

// ===== VALIDATE FILE =====
function validateFile(file, maxMB = 10) {
  const allowed = ['.pdf', '.doc', '.docx', '.png', '.jpg'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast(`Định dạng không hợp lệ. Chỉ chấp nhận: ${allowed.join(', ')}`, 'danger');
    return false;
  }
  if (file.size > maxMB * 1024 * 1024) {
    showToast(`File quá lớn. Tối đa ${maxMB}MB`, 'danger');
    return false;
  }
  return true;
}

// ===== FORMAT DATE =====
function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// ===== PASSWORD TOGGLE =====
function togglePassword(btn) {
  const input = btn.previousElementSibling;
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  btn.querySelector('.eye-open').style.display = show ? 'none' : '';
  btn.querySelector('.eye-slash').style.display = show ? '' : 'none';
  btn.title = show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu';
}

// ===== CSRF TOKEN (cho fetch/AJAX) =====
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}
const csrfToken = getCookie('csrftoken');