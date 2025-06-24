document.getElementById('sendBtn').addEventListener('click', function () {
  const btn = this;
  btn.disabled = true;
  btn.textContent = 'تم الإرسال';

  // TODO: Replace with actual AJAX call
  setTimeout(() => {
    document.getElementById('answerText').textContent = 'يرجى الانتظار قليلاً، سيتم الرد خلال ٢٤ ساعة.';
  }, 1500);
});

// Toggle visual feedback (optional)
const checkbox = document.getElementById('quick-response');
const toggleWrapper = checkbox.nextElementSibling;
const dot = toggleWrapper.querySelector('.dot');
checkbox.addEventListener('change', () => {
  dot.style.transform = checkbox.checked ? 'translateX(16px)' : 'translateX(0)';
  toggleWrapper.classList.toggle('bg-pink-500', checkbox.checked);
  toggleWrapper.classList.toggle('bg-gray-300', !checkbox.checked);
});
